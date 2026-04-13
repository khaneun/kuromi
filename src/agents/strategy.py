from __future__ import annotations

import time
from collections import defaultdict
from typing import Iterable

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.strategies.base import Strategy, StrategyContext
from src.strategies.registry import load as load_strategies

# 같은 (ticker, side) 조합에 대해 이 초 동안 중복 intent를 발행하지 않음
_INTENT_COOLDOWN_SEC = 60.0


class StrategyAgent(BaseAgent):
    """Ensemble host. Merges signals from technical, derivative, and on-chain
    sources, then runs every loaded Strategy plugin against the combined
    signal bundle. Emits trade.intent when aggregate confidence exceeds
    the decision threshold.

    Signal merge: derivative and onchain signals are cached per-ticker and
    folded into the next signal.generated event for that ticker.
    """

    name = "strategy"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        strategy_names: Iterable[str] | None = None,
    ) -> None:
        super().__init__(bus, state)
        self.strategies: list[Strategy] = load_strategies(strategy_names)
        self._extra_signals: dict[str, dict[str, float]] = defaultdict(dict)
        # (ticker, side) → last emit timestamp
        self._last_intent: dict[tuple[str, str], float] = {}

        weights = state.strategy_params.setdefault("strategy_weights", {})
        for s in self.strategies:
            weights.setdefault(s.name, 1.0)
            state.strategy_params.setdefault(f"{s.name}.params", dict(s.params))
        state.strategy_params.setdefault("decision_threshold", 0.5)

        self.subscribe("signal.generated", self._on_signal)
        self.subscribe("signal.derivative", self._on_extra)
        self.subscribe("signal.onchain", self._on_extra)
        self.subscribe("improver.params_updated", self._on_params)

    async def setup(self) -> None:
        self.log(f"loaded {len(self.strategies)} strategies: {[s.name for s in self.strategies]}")

    async def run(self) -> None:
        await self._stop.wait()

    async def _on_extra(self, event: Event) -> None:
        ticker = event.payload.get("ticker")
        signals = event.payload.get("signals", {})
        if ticker and signals:
            self._extra_signals[ticker].update(signals)

    async def _on_signal(self, event: Event) -> None:
        ticker = event.payload["ticker"]
        price = event.payload["price"]
        signals = dict(event.payload["signals"])
        signals.update(self._extra_signals.get(ticker, {}))
        position = self.state.positions.get(ticker)

        weights = self.state.strategy_params.get("strategy_weights", {})
        threshold = float(self.state.strategy_params.get("decision_threshold", 0.5))

        votes = {"buy": 0.0, "sell": 0.0}
        reasons: list[str] = []

        for strategy in self.strategies:
            override = self.state.strategy_params.get(f"{strategy.name}.params")
            if override:
                strategy.params.update(override)
            ctx = StrategyContext(
                ticker=ticker,
                price=price,
                signals=signals,
                position=position,
                params=strategy.params,
            )
            decision = strategy.evaluate(ctx)
            if decision.side == "hold":
                continue
            w = float(weights.get(strategy.name, 1.0))
            votes[decision.side] += decision.confidence * w
            reasons.append(f"{strategy.name}:{decision.side}@{decision.confidence:.2f}")

        side, score = max(votes.items(), key=lambda kv: kv[1])
        if score < threshold:
            return

        # 쿨다운: 같은 (ticker, side)를 60초 내 중복 발행 금지
        key = (ticker, side)
        now = time.monotonic()
        if now - self._last_intent.get(key, 0.0) < _INTENT_COOLDOWN_SEC:
            return
        self._last_intent[key] = now

        await self.emit(
            "trade.intent",
            {
                "ticker": ticker,
                "side": side,
                "price": price,
                "confidence": score,
                "reasons": reasons,
            },
        )

    async def _on_params(self, event: Event) -> None:
        updates = event.payload or {}
        if not isinstance(updates, dict):
            return
        self.state.strategy_params.update(updates)
        self.log(f"params updated: {list(updates.keys())}")
