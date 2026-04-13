from __future__ import annotations

import heapq
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator


@dataclass(slots=True, order=True)
class TimedCandle:
    ts: datetime
    ticker: str
    price: float
    candle: dict

    @classmethod
    def from_upbit(cls, ticker: str, raw: dict) -> "TimedCandle":
        ts = datetime.fromisoformat(
            raw.get("candle_date_time_utc", raw.get("candle_date_time_kst", ""))
        )
        return cls(
            ts=ts,
            ticker=ticker,
            price=float(raw["trade_price"]),
            candle=raw,
        )


def merge(ticker_candles: dict[str, list[dict]]) -> Iterator[TimedCandle]:
    """Merge multiple tickers' candle lists into a single chronological stream.

    Each ticker's list must already be in ascending time order (oldest first).
    Uses a heap so memory stays O(num_tickers) regardless of total candle count.
    """
    heap: list[tuple[datetime, int, int, str, dict]] = []
    lists: dict[str, list[dict]] = ticker_candles

    for ticker, candles in lists.items():
        if candles:
            c = candles[0]
            tc = TimedCandle.from_upbit(ticker, c)
            heapq.heappush(heap, (tc.ts, 0, 0, ticker, c))

    seq = 0
    while heap:
        ts, idx, _, ticker, raw = heapq.heappop(heap)
        yield TimedCandle.from_upbit(ticker, raw)

        next_idx = idx + 1
        candles = lists[ticker]
        if next_idx < len(candles):
            c = candles[next_idx]
            tc = TimedCandle.from_upbit(ticker, c)
            seq += 1
            heapq.heappush(heap, (tc.ts, next_idx, seq, ticker, c))
