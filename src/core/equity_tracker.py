from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class EquityPoint:
    ts: float
    equity: float
    available_krw: float
    unrealized_pnl: float
    realized_pnl: float
    position_count: int


class EquityTracker:
    """Ring buffer of equity snapshots for charting."""

    def __init__(self, max_points: int = 8640) -> None:
        self._points: deque[EquityPoint] = deque(maxlen=max_points)

    def record(
        self,
        equity: float,
        available_krw: float,
        unrealized_pnl: float,
        realized_pnl: float,
        position_count: int,
    ) -> None:
        self._points.append(
            EquityPoint(
                ts=time.time(),
                equity=equity,
                available_krw=available_krw,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                position_count=position_count,
            )
        )

    def to_list(self, last_n: int | None = None) -> list[dict]:
        pts = list(self._points)
        if last_n:
            pts = pts[-last_n:]
        return [
            {
                "ts": p.ts,
                "equity": p.equity,
                "available_krw": p.available_krw,
                "unrealized_pnl": p.unrealized_pnl,
                "realized_pnl": p.realized_pnl,
                "position_count": p.position_count,
            }
            for p in pts
        ]
