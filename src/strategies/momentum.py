from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class MomentumStrategy(Strategy):
    name = "momentum"
    default_params = {"entry_threshold": 0.5, "exit_threshold": -0.2}

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        signal = ctx.signals.get("momentum")
        if signal is None:
            return StrategyDecision.hold()
        if signal >= self.params["entry_threshold"] and ctx.position is None:
            return StrategyDecision("buy", min(1.0, float(signal)), "momentum_up")
        if signal <= self.params["exit_threshold"] and ctx.position is not None:
            return StrategyDecision("sell", min(1.0, float(-signal)), "momentum_down")
        return StrategyDecision.hold()
