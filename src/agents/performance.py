from __future__ import annotations

from collections import deque

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class PerformanceAgent(BaseAgent):
    name = "performance"

    def __init__(
        self, bus: EventBus, state: SharedState, report_sec: int = 300, window: int = 500
    ) -> None:
        super().__init__(bus, state)
        self.report_sec = report_sec
        self._trades: deque[dict] = deque(maxlen=window)
        self.bus.subscribe("order.filled", self._on_filled)

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.report_sec)
            await self.emit("performance.report", self._build_report())

    async def _on_filled(self, event: Event) -> None:
        self._trades.append(event.payload)

    def _build_report(self) -> dict:
        total = len(self._trades)
        wins = sum(1 for t in self._trades if t.get("side") == "sell" and t.get("price", 0) > 0)
        return {
            "trades": total,
            "wins": wins,
            "daily_pnl": self.state.daily_pnl,
            "open_positions": len(self.state.positions),
        }
