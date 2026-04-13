from __future__ import annotations

import uuid

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.orders import Order, OrderState


class MockExecutionAgent(BaseAgent):
    """Instant-fill executor for backtests. Applies slippage, validates
    against Capital, and updates balances on fill."""

    name = "mock_execution"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        slippage_bps: float = 5.0,
    ) -> None:
        super().__init__(bus, state)
        self.slippage_bps = slippage_bps
        self.bus.subscribe("trade.approved", self._on_approved)

    async def run(self) -> None:
        await self._stop.wait()

    async def _on_approved(self, event: Event) -> None:
        intent = event.payload
        price = float(intent["price"])
        slip = price * self.slippage_bps / 10000.0
        fill_price = price + slip if intent["side"] == "buy" else price - slip
        volume = float(intent.get("volume") or 0)
        if volume <= 0:
            return

        order = Order(
            client_id=str(uuid.uuid4()),
            ticker=intent["ticker"],
            side=intent["side"],
            price=fill_price,
            volume=volume,
            uuid=f"bt-{uuid.uuid4().hex[:8]}",
            state=OrderState.FILLED,
            executed_volume=volume,
        )
        await self.emit("order.filled", order.to_payload())
