from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"
    default_params = {"oversold": -0.7, "overbought": 0.7}

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        z = ctx.signals.get("zscore")
        if z is None:
            return StrategyDecision.hold()
        if z <= self.params["oversold"] and ctx.position is None:
            return StrategyDecision("buy", min(1.0, float(-z)), "oversold")
        if z >= self.params["overbought"] and ctx.position is not None:
            return StrategyDecision("sell", min(1.0, float(z)), "overbought")
        return StrategyDecision.hold()
