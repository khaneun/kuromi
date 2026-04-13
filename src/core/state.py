from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.capital import Capital


@dataclass
class SharedState:
    last_prices: dict[str, float] = field(default_factory=dict)
    daily_pnl: float = 0.0
    halted: bool = False
    strategy_params: dict[str, Any] = field(default_factory=dict)
    capital: Capital = field(default_factory=Capital)

    @property
    def positions(self) -> dict[str, Any]:
        return {
            t: {"entry_price": p.entry_price, "volume": p.volume}
            for t, p in self.capital.positions.items()
        }
