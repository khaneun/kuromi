from __future__ import annotations

import time
from collections import defaultdict

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class MonitorAgent(BaseAgent):
    """Tracks heartbeat per topic. If no updates arrive within threshold,
    emits system.alert. On repeated failure, halts trading via system.halt."""

    name = "monitor"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        check_sec: int = 30,
        stall_sec: int = 120,
    ) -> None:
        super().__init__(bus, state)
        self.check_sec = check_sec
        self.stall_sec = stall_sec
        self._last_seen: dict[str, float] = defaultdict(lambda: time.time())
        self.bus.tap(self._on_any)

    async def _on_any(self, event: Event) -> None:
        self._last_seen[event.topic] = time.time()

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.check_sec)
            now = time.time()
            tick_age = now - self._last_seen.get("market.tick", now)
            if tick_age > self.stall_sec and not self.state.halted:
                self.state.halted = True
                await self.emit(
                    "system.halt", {"reason": "market.tick stalled", "age_sec": tick_age}
                )
