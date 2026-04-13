from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class RSIStrategy(Strategy):
    """Classic RSI overbought/oversold reversal.
    Buy when RSI dips below oversold and starts recovering.
    Sell when RSI rises above overbought."""

    name = "rsi"
    default_params = {"oversold": 30.0, "overbought": 70.0}

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        rsi = ctx.signals.get("rsi_raw")
        if rsi is None:
            return StrategyDecision.hold()

        oversold = self.params["oversold"]
        overbought = self.params["overbought"]

        if rsi <= oversold and ctx.position is None:
            confidence = min(1.0, (oversold - rsi) / oversold)
            return StrategyDecision("buy", confidence, f"rsi={rsi:.1f}")

        if rsi >= overbought and ctx.position is not None:
            confidence = min(1.0, (rsi - overbought) / (100 - overbought))
            return StrategyDecision("sell", confidence, f"rsi={rsi:.1f}")

        return StrategyDecision.hold()
