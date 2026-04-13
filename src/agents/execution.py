from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.orders import TERMINAL, Order, OrderState
from src.exchange.upbit_client import UpbitClient

if TYPE_CHECKING:
    from src.agents.persistence import PersistenceAgent


STATE_TOPIC: dict[OrderState, str] = {
    OrderState.SUBMITTED: "order.submitted",
    OrderState.ACCEPTED: "order.accepted",
    OrderState.PARTIALLY_FILLED: "order.partially_filled",
    OrderState.FILLED: "order.filled",
    OrderState.CANCELLED: "order.cancelled",
    OrderState.FAILED: "order.failed",
}


class ExecutionAgent(BaseAgent):
    """Owns the order state machine. On startup, recovers in-flight orders
    from the database. Submits orders on trade.approved, polls Upbit for
    status, emits events per transition."""

    name = "execution"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        client: UpbitClient,
        dry_run: bool = True,
        poll_sec: float = 2.0,
        timeout_sec: float = 300.0,
        persistence: "PersistenceAgent | None" = None,
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.dry_run = dry_run
        self.poll_sec = poll_sec
        self.timeout_sec = timeout_sec
        self.persistence = persistence
        self._active: dict[str, Order] = {}
        self.subscribe("trade.approved", self._on_approved)

    async def setup(self) -> None:
        if self.dry_run or not self.persistence:
            return
        rows = await self.persistence.load_pending_orders()
        for r in rows:
            if not r.get("uuid"):
                continue
            order = Order(
                client_id=r["client_id"],
                ticker=r["ticker"],
                side=r["side"],
                price=float(r["price"]),
                volume=float(r["volume"]) if r.get("volume") else None,
                uuid=r["uuid"],
                state=OrderState(r["state"]),
                executed_volume=float(r.get("executed_volume", 0)),
                remaining_volume=float(r.get("remaining_volume", 0)),
            )
            self._active[order.uuid] = order
        if rows:
            self.log(f"recovered {len(rows)} in-flight orders from DB")

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.poll_sec)
            for order in list(self._active.values()):
                try:
                    await self._poll(order)
                except Exception as exc:
                    self.log(f"poll error uuid={order.uuid}: {exc}")

    async def _on_approved(self, event: Event) -> None:
        intent = event.payload
        volume = float(intent.get("volume") or 0)
        if volume <= 0:
            self.log(f"skipping zero-volume intent: {intent.get('ticker')}")
            return
        order = Order(
            client_id=str(uuid.uuid4()),
            ticker=intent["ticker"],
            side=intent["side"],
            price=float(intent["price"]),
            volume=volume,
        )
        await self._transition(order, OrderState.SUBMITTED)

        if self.dry_run:
            order.uuid = f"dry-{order.client_id[:8]}"
            order.executed_volume = order.volume
            self.log(
                f"DRY-RUN {order.side} {order.ticker} "
                f"vol={order.volume:.8f} price={order.price:,.0f}"
            )
            await self._transition(order, OrderState.FILLED)
            return

        try:
            result = await self.client.place_order(
                market=order.ticker,
                side=order.side,
                price=order.price,
                volume=order.volume,
            )
            order.uuid = result.get("uuid")
            if not order.uuid:
                raise RuntimeError(f"no uuid in upbit response: {result}")
            self._active[order.uuid] = order
            await self._transition(order, OrderState.ACCEPTED)
        except Exception as exc:
            order.reason = str(exc)
            await self._transition(order, OrderState.FAILED)

    async def _poll(self, order: Order) -> None:
        if not order.uuid:
            return
        info = await self.client.get_order(order.uuid)
        order.executed_volume = float(info.get("executed_volume") or 0.0)
        order.remaining_volume = float(info.get("remaining_volume") or 0.0)
        upbit_state = info.get("state")

        next_state = order.state
        if upbit_state == "done":
            next_state = OrderState.FILLED
        elif upbit_state == "cancel":
            next_state = OrderState.CANCELLED
        elif upbit_state == "wait":
            next_state = (
                OrderState.PARTIALLY_FILLED if order.executed_volume > 0 else OrderState.ACCEPTED
            )

        age = (datetime.now(timezone.utc) - order.created_at).total_seconds()
        if age > self.timeout_sec and next_state not in TERMINAL:
            try:
                await self.client.cancel_order(order.uuid)
            except Exception as exc:
                self.log(f"cancel-on-timeout failed {order.uuid}: {exc}")
            order.reason = "timeout"
            next_state = OrderState.CANCELLED

        if next_state != order.state:
            await self._transition(order, next_state)

        if order.state in TERMINAL:
            self._active.pop(order.uuid, None)

    async def _transition(self, order: Order, new_state: OrderState) -> None:
        order.state = new_state
        order.updated_at = datetime.now(timezone.utc)
        topic = STATE_TOPIC[new_state]
        await self.emit(topic, order.to_payload())
