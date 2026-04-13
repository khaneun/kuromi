from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class RiskAgent(BaseAgent):
    """Gate and size. Rejects intents that violate risk limits, then
    calculates concrete KRW allocation and volume for approved trades."""

    name = "risk"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        max_positions: int,
        per_trade_risk_pct: float,
        daily_loss_limit_pct: float,
        min_order_krw: float = 5000.0,
    ) -> None:
        super().__init__(bus, state)
        self.max_positions = max_positions
        self.per_trade_risk_pct = per_trade_risk_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.min_order_krw = min_order_krw
        self.bus.subscribe("trade.intent", self._on_intent)

    async def run(self) -> None:
        await self._stop.wait()

    async def _on_intent(self, event: Event) -> None:
        intent = event.payload
        reason = self._reject_reason(intent)
        if reason:
            await self.emit("trade.rejected", {**intent, "reason": reason})
            return

        sized = self._size(intent)
        if sized is None:
            await self.emit(
                "trade.rejected", {**intent, "reason": "insufficient_funds"}
            )
            return
        await self.emit("trade.approved", sized)

    def _reject_reason(self, intent: dict) -> str | None:
        if self.state.halted:
            return "system_halted"
        if self.state.daily_pnl <= -self.daily_loss_limit_pct:
            return "daily_loss_limit"
        if (
            intent["side"] == "buy"
            and len(self.state.capital.positions) >= self.max_positions
        ):
            return "max_positions"
        return None

    def _size(self, intent: dict) -> dict | None:
        price = float(intent["price"])
        if price <= 0:
            return None

        cap = self.state.capital
        if intent["side"] == "sell":
            pos = cap.positions.get(intent["ticker"])
            if pos is None:
                return None
            return {
                **intent,
                "volume": pos.volume,
                "alloc_krw": pos.cost,
            }

        equity = cap.total_equity(self.state.last_prices)
        alloc_krw = equity * self.per_trade_risk_pct
        alloc_krw = min(alloc_krw, cap.available_krw)
        if alloc_krw < self.min_order_krw:
            return None

        volume = alloc_krw / price
        return {
            **intent,
            "volume": volume,
            "alloc_krw": alloc_krw,
        }
