from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class StrategyContext:
    ticker: str
    price: float
    signals: dict[str, float]
    position: dict[str, Any] | None
    params: dict[str, Any]


@dataclass(slots=True)
class StrategyDecision:
    side: str  # "buy" | "sell" | "hold"
    confidence: float  # [0, 1]
    reason: str = ""

    @classmethod
    def hold(cls) -> "StrategyDecision":
        return cls(side="hold", confidence=0.0)


class Strategy(ABC):
    name: str = ""
    default_params: dict[str, Any] = {}

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params: dict[str, Any] = {**self.default_params, **(params or {})}

    @abstractmethod
    def evaluate(self, ctx: StrategyContext) -> StrategyDecision: ...
