from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class StochasticStrategy(Strategy):
    """Stochastic %K/%D crossover with overbought/oversold zones."""

    name = "stochastic"
    default_params = {"oversold": 20.0, "overbought": 80.0}

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        k = ctx.signals.get("stoch_k_raw")
        d = ctx.signals.get("stoch_d_raw")
        if k is None or d is None:
            return StrategyDecision.hold()

        if k <= self.params["oversold"] and k > d and ctx.position is None:
            confidence = min(1.0, (self.params["oversold"] - k) / self.params["oversold"])
            return StrategyDecision("buy", max(0.1, confidence), f"stoch_k={k:.1f}")

        if k >= self.params["overbought"] and k < d and ctx.position is not None:
            confidence = min(1.0, (k - self.params["overbought"]) / (100 - self.params["overbought"]))
            return StrategyDecision("sell", max(0.1, confidence), f"stoch_k={k:.1f}")

        return StrategyDecision.hold()
