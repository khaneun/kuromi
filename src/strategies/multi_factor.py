from __future__ import annotations

from src.strategies.base import Strategy, StrategyContext, StrategyDecision


class MultiFactorStrategy(Strategy):
    """Composite strategy that weights technical, derivative, and on-chain
    signals. Gracefully degrades: only scores factors that are present in
    the signal bundle.

    Factor groups and their signal keys (normalized to [-1, 1]):
      technical: rsi, bollinger_pct_b, macd_hist, momentum, zscore
      derivative: funding_rate, long_short, kimchi_premium (inverted)
      onchain: exchange_netflow, nvt, mvrv

    Each factor has a configurable weight. The final score is a weighted
    average of all available factors. Positive score → buy, negative → sell.
    """

    name = "multi_factor"
    default_params = {
        "buy_threshold": 0.3,
        "sell_threshold": -0.3,
        "w_rsi": 1.0,
        "w_bollinger": 0.8,
        "w_macd": 1.0,
        "w_momentum": 0.7,
        "w_stochastic": 0.6,
        "w_obv": 0.5,
        "w_funding_rate": 1.2,
        "w_long_short": 0.8,
        "w_kimchi_premium": 0.6,
        "w_exchange_netflow": 1.0,
        "w_nvt": 0.7,
        "w_mvrv": 0.9,
    }

    SIGNAL_WEIGHT_MAP = {
        "rsi": "w_rsi",
        "bollinger_pct_b": "w_bollinger",
        "macd_hist": "w_macd",
        "momentum": "w_momentum",
        "stochastic_k": "w_stochastic",
        "obv_slope": "w_obv",
        "funding_rate": "w_funding_rate",
        "long_short": "w_long_short",
        "exchange_netflow": "w_exchange_netflow",
        "nvt": "w_nvt",
        "mvrv": "w_mvrv",
    }

    def evaluate(self, ctx: StrategyContext) -> StrategyDecision:
        total_weight = 0.0
        weighted_sum = 0.0

        for signal_key, weight_key in self.SIGNAL_WEIGHT_MAP.items():
            val = ctx.signals.get(signal_key)
            if val is None:
                continue
            w = float(self.params.get(weight_key, 1.0))
            weighted_sum += float(val) * w
            total_weight += w

        kimchi = ctx.signals.get("kimchi_premium")
        if kimchi is not None:
            w = float(self.params.get("w_kimchi_premium", 0.6))
            weighted_sum += float(-kimchi) * w
            total_weight += w

        if total_weight == 0:
            return StrategyDecision.hold()

        score = weighted_sum / total_weight
        confidence = min(1.0, abs(score))

        if score >= self.params["buy_threshold"] and ctx.position is None:
            return StrategyDecision("buy", confidence, f"mf_score={score:+.3f}")

        if score <= self.params["sell_threshold"] and ctx.position is not None:
            return StrategyDecision("sell", confidence, f"mf_score={score:+.3f}")

        return StrategyDecision.hold()
