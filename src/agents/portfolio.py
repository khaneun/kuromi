from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.equity_tracker import EquityTracker
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.upbit_client import UpbitClient


class PortfolioAgent(BaseAgent):
    """Tracks capital, positions, and equity. In live mode syncs with Upbit
    accounts periodically. Records equity history for dashboard charting."""

    name = "portfolio"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        client: UpbitClient | None = None,
        equity_tracker: EquityTracker | None = None,
        snapshot_sec: int = 30,
        sync_sec: int = 60,
        live: bool = False,
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.equity_tracker = equity_tracker or EquityTracker()
        self.snapshot_sec = snapshot_sec
        self.sync_sec = sync_sec
        self.live = live
        self._sync_counter = 0
        self.subscribe("order.filled", self._on_filled)

    async def setup(self) -> None:
        if self.live and self.client:
            await self._sync_upbit()
            self.log(
                f"synced from upbit: "
                f"KRW={self.state.capital.available_krw:,.0f}  "
                f"positions={list(self.state.capital.positions.keys())}"
            )

    async def run(self) -> None:
        while not self.stopping:
            self._sync_counter += self.snapshot_sec
            if self.live and self.client and self._sync_counter >= self.sync_sec:
                self._sync_counter = 0
                try:
                    await self._sync_upbit()
                except Exception as exc:
                    self.log(f"upbit sync error: {exc}")

            snap = self.state.capital.snapshot(self.state.last_prices)
            snap["daily_pnl"] = self.state.daily_pnl
            self.equity_tracker.record(
                equity=snap["total_equity"],
                available_krw=snap["available_krw"],
                unrealized_pnl=snap["unrealized_pnl"],
                realized_pnl=snap["realized_pnl"],
                position_count=len(snap["positions"]),
            )
            await self.emit("portfolio.snapshot", snap)
            await self.sleep(self.snapshot_sec)

    async def _on_filled(self, event: Event) -> None:
        o = event.payload
        ticker = o["ticker"]
        price = float(o["price"])
        volume = float(o.get("executed_volume") or o.get("volume") or 0)

        if o["side"] == "buy":
            try:
                self.state.capital.open_position(ticker, price, volume)
            except Exception as exc:
                self.log(f"open_position failed: {exc}")
                return
        elif o["side"] == "sell":
            self.state.capital.close_position(ticker, price)
            entry = self.state.positions.get(ticker, {}).get("entry_price", price)
            if entry:
                self.state.daily_pnl += (price - entry) / entry

    async def _sync_upbit(self) -> None:
        if not self.client:
            return
        accounts = await self.client.get_accounts()
        self.state.capital.sync_from_upbit(accounts, self.state.last_prices)
