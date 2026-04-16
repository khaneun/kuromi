from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.capital import Capital


@dataclass
class SharedState:
    last_prices: dict[str, float] = field(default_factory=dict)
    last_signals: dict[str, dict] = field(default_factory=dict)   # C: 티커별 최신 시그널
    daily_pnl: float = 0.0
    halted: bool = False
    strategy_params: dict[str, Any] = field(default_factory=dict)
    capital: Capital = field(default_factory=Capital)
    # 현재 매매 허용 종목 집합 — 체결 시 제거, 대시보드 저장 시 갱신
    trading_tickers: set[str] = field(default_factory=set)

    @property
    def positions(self) -> dict[str, Any]:
        return {
            t: {"entry_price": p.entry_price, "volume": p.volume}
            for t, p in self.capital.positions.items()
        }
