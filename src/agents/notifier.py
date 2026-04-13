from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class NotifierAgent(BaseAgent):
    """Bridges the bus to the Telegram bot. The bot owns network I/O;
    this agent only decides what to forward."""

    name = "notifier"

    FORWARD = {
        "order.filled",
        "order.failed",
        "order.cancelled",
        "system.alert",
        "system.halt",
    }

    # trade.rejected 중 Telegram으로 보낼 critical reason 목록
    CRITICAL_REJECT_REASONS = {"system_halted", "daily_loss_limit"}

    def __init__(self, bus: EventBus, state: SharedState, send) -> None:
        super().__init__(bus, state)
        self._send = send  # async callable(text: str) -> None
        self.bus.tap(self._on_any)

    async def run(self) -> None:
        await self._stop.wait()

    async def _on_any(self, event: Event) -> None:
        if event.topic == "trade.rejected":
            reason = event.payload.get("reason", "") if isinstance(event.payload, dict) else ""
            if reason not in self.CRITICAL_REJECT_REASONS:
                return
        elif event.topic not in self.FORWARD:
            return
        await self._send(f"[{event.topic}] {event.payload}")
