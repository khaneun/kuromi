from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.storage.db import OrderRecord, SignalLog, TradeLog


class PersistenceAgent(BaseAgent):
    """Subscribes to bus events and writes them to the database.

    - order.*      → OrderRecord (INSERT on submitted, UPDATE on transitions)
    - order.filled → TradeLog (closed-trade record)
    - signal.generated → SignalLog (sampled, not every tick)
    """

    name = "persistence"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        session_factory: async_sessionmaker[AsyncSession],
        signal_sample_every: int = 10,
    ) -> None:
        super().__init__(bus, state)
        self._sf = session_factory
        self._signal_counter: int = 0
        self._signal_sample_every = signal_sample_every

        self.subscribe("order.submitted", self._on_order_new)
        self.subscribe("order.accepted", self._on_order_update)
        self.subscribe("order.partially_filled", self._on_order_update)
        self.subscribe("order.filled", self._on_order_terminal)
        self.subscribe("order.cancelled", self._on_order_terminal)
        self.subscribe("order.failed", self._on_order_terminal)
        self.subscribe("signal.generated", self._on_signal)

    async def run(self) -> None:
        await self._stop.wait()

    # ---- orders ----
    async def _on_order_new(self, event: Event) -> None:
        p = event.payload
        async with self._sf() as session:
            record = OrderRecord(
                client_id=p["client_id"],
                uuid=p.get("uuid"),
                ticker=p["ticker"],
                side=p["side"],
                price=float(p["price"]),
                volume=float(p["volume"]) if p.get("volume") is not None else None,
                state=p["state"],
                executed_volume=float(p.get("executed_volume", 0)),
                remaining_volume=float(p.get("remaining_volume", 0)),
                reason=p.get("reason", ""),
            )
            session.add(record)
            await session.commit()

    async def _on_order_update(self, event: Event) -> None:
        p = event.payload
        async with self._sf() as session:
            stmt = (
                update(OrderRecord)
                .where(OrderRecord.client_id == p["client_id"])
                .values(
                    uuid=p.get("uuid"),
                    state=p["state"],
                    executed_volume=float(p.get("executed_volume", 0)),
                    remaining_volume=float(p.get("remaining_volume", 0)),
                    reason=p.get("reason", ""),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def _on_order_terminal(self, event: Event) -> None:
        p = event.payload
        async with self._sf() as session:
            stmt = (
                update(OrderRecord)
                .where(OrderRecord.client_id == p["client_id"])
                .values(
                    uuid=p.get("uuid"),
                    state=p["state"],
                    executed_volume=float(p.get("executed_volume", 0)),
                    remaining_volume=float(p.get("remaining_volume", 0)),
                    reason=p.get("reason", ""),
                )
            )
            await session.execute(stmt)

            if p["state"] == "filled":
                trade = TradeLog(
                    ticker=p["ticker"],
                    side=p["side"],
                    price=float(p["price"]),
                    volume=float(p.get("executed_volume") or p.get("volume") or 0),
                    payload=p,
                )
                session.add(trade)

            await session.commit()

    # ---- signals (sampled) ----
    async def _on_signal(self, event: Event) -> None:
        self._signal_counter += 1
        if self._signal_counter % self._signal_sample_every != 0:
            return
        p = event.payload
        signals = p.get("signals", {})
        async with self._sf() as session:
            for source, value in signals.items():
                session.add(
                    SignalLog(
                        ticker=p["ticker"],
                        source=source,
                        value=float(value),
                        payload={"price": p.get("price")},
                    )
                )
            await session.commit()

    # ---- recovery helpers (used by ExecutionAgent) ----
    async def load_pending_orders(self) -> list[dict]:
        async with self._sf() as session:
            stmt = select(OrderRecord).where(
                OrderRecord.state.in_(["accepted", "partially_filled"])
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "client_id": r.client_id,
                    "uuid": r.uuid,
                    "ticker": r.ticker,
                    "side": r.side,
                    "price": r.price,
                    "volume": r.volume,
                    "state": r.state,
                    "executed_volume": r.executed_volume,
                    "remaining_volume": r.remaining_volume,
                }
                for r in rows
            ]

    async def query_orders(self, limit: int = 20, state: str | None = None) -> list[dict]:
        async with self._sf() as session:
            stmt = select(OrderRecord).order_by(OrderRecord.created_at.desc()).limit(limit)
            if state:
                stmt = stmt.where(OrderRecord.state == state)
            result = await session.execute(stmt)
            return [
                {
                    "id": r.id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "client_id": r.client_id,
                    "uuid": r.uuid,
                    "ticker": r.ticker,
                    "side": r.side,
                    "price": r.price,
                    "volume": r.volume,
                    "state": r.state,
                    "executed_volume": r.executed_volume,
                    "reason": r.reason,
                }
                for r in result.scalars().all()
            ]

    async def query_trades(self, limit: int = 20) -> list[dict]:
        async with self._sf() as session:
            stmt = select(TradeLog).order_by(TradeLog.ts.desc()).limit(limit)
            result = await session.execute(stmt)
            return [
                {
                    "id": r.id,
                    "ts": r.ts.isoformat() if r.ts else None,
                    "ticker": r.ticker,
                    "side": r.side,
                    "price": r.price,
                    "volume": r.volume,
                    "pnl": r.pnl,
                }
                for r in result.scalars().all()
            ]
