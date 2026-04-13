from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class MACDCrossStrategy(Strategy):
    """MACD histogram crossover. Buy on histogram turning positive,
    sell on histogram turning negative. Confidence scales with magnitude."""

    name = "macd_cross"
    default_params = {"hist_threshold": 0.05}

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        hist = ctx.signals.get("macd_hist")
        if hist is None:
            return StrategyDecision.hold()

        threshold = self.params["hist_threshold"]

        if hist >= threshold and ctx.position is None:
            confidence = min(1.0, abs(hist))
            return StrategyDecision("buy", confidence, f"macd_hist={hist:.3f}")

        if hist <= -threshold and ctx.position is not None:
            confidence = min(1.0, abs(hist))
            return StrategyDecision("sell", confidence, f"macd_hist={hist:.3f}")

        return StrategyDecision.hold()
