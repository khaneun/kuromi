from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class BollingerStrategy(Strategy):
    """Mean-reversion on Bollinger Band percent-B.
    Buy when price breaks below lower band, sell above upper."""

    name = "bollinger"
    default_params = {"buy_pct_b": -0.3, "sell_pct_b": 0.3}

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        pct_b = ctx.signals.get("bollinger_pct_b")
        if pct_b is None:
            return StrategyDecision.hold()

        if pct_b <= self.params["buy_pct_b"] and ctx.position is None:
            confidence = min(1.0, abs(pct_b))
            return StrategyDecision("buy", confidence, f"pct_b={pct_b:.2f}")

        if pct_b >= self.params["sell_pct_b"] and ctx.position is not None:
            confidence = min(1.0, abs(pct_b))
            return StrategyDecision("sell", confidence, f"pct_b={pct_b:.2f}")

        return StrategyDecision.hold()
