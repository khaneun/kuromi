"""Pure-function technical indicators. All operate on plain sequences
(list/deque of float). No side effects, no state — call per tick."""

from __future__ import annotations

import statistics
from collections import deque


def rsi(closes: deque[float] | list[float], period: int = 14) -> float | None:
    """Relative Strength Index → [0, 100]. Returns None if insufficient data."""
    if len(closes) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    if gains + losses == 0:
        return 50.0
    rs = gains / max(losses, 1e-12)
    return 100.0 - 100.0 / (1.0 + rs)


def bollinger_bands(
    closes: deque[float] | list[float], period: int = 20, num_std: float = 2.0
) -> tuple[float, float, float] | None:
    """Returns (lower, middle, upper) or None if insufficient data."""
    if len(closes) < period:
        return None
    window = list(closes)[-period:]
    mid = statistics.fmean(window)
    std = statistics.pstdev(window)
    return (mid - num_std * std, mid, mid + num_std * std)


def bollinger_pct_b(
    closes: deque[float] | list[float], period: int = 20, num_std: float = 2.0
) -> float | None:
    """Percent-B: position of last close within bands → [0, 1] normal, can exceed."""
    bb = bollinger_bands(closes, period, num_std)
    if bb is None:
        return None
    lower, _, upper = bb
    width = upper - lower
    if width == 0:
        return 0.5
    return (closes[-1] - lower) / width


def macd(
    closes: deque[float] | list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[float, float, float] | None:
    """Returns (macd_line, signal_line, histogram) or None."""
    if len(closes) < slow + signal_period:
        return None
    ema_fast = _ema(list(closes), fast)
    ema_slow = _ema(list(closes), slow)
    macd_line = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
    if len(macd_line) < signal_period:
        return None
    signal_line = _ema(macd_line, signal_period)
    m = macd_line[-1]
    s = signal_line[-1]
    return (m, s, m - s)


def stochastic(
    highs: deque[float] | list[float],
    lows: deque[float] | list[float],
    closes: deque[float] | list[float],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[float, float] | None:
    """Returns (%K, %D) or None."""
    if len(closes) < k_period + d_period - 1:
        return None
    ks: list[float] = []
    for i in range(d_period):
        end = len(closes) - i
        start = end - k_period
        h = max(list(highs)[start:end])
        lo = min(list(lows)[start:end])
        c = list(closes)[end - 1]
        ks.append(100 * (c - lo) / max(h - lo, 1e-12))
    ks.reverse()
    return (ks[-1], statistics.fmean(ks))


def atr(
    highs: deque[float] | list[float],
    lows: deque[float] | list[float],
    closes: deque[float] | list[float],
    period: int = 14,
) -> float | None:
    """Average True Range. Returns None if insufficient data."""
    if len(closes) < period + 1:
        return None
    trs: list[float] = []
    for i in range(-period, 0):
        h, lo, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    return statistics.fmean(trs)


def obv_signal(
    closes: deque[float] | list[float],
    volumes: deque[float] | list[float],
    period: int = 20,
) -> float | None:
    """OBV slope normalized to [-1, 1]. Positive = accumulation."""
    if len(closes) < period + 1 or len(volumes) < period + 1:
        return None
    obv = 0.0
    obvs: list[float] = []
    for i in range(-period, 0):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
        obvs.append(obv)
    if not obvs or obvs[0] == 0:
        return 0.0
    slope = (obvs[-1] - obvs[0]) / max(abs(obvs[0]), 1.0)
    return max(-1.0, min(1.0, slope))


def vwap(
    prices: deque[float] | list[float],
    volumes: deque[float] | list[float],
    period: int = 20,
) -> float | None:
    """Volume-weighted average price over last `period` bars."""
    if len(prices) < period or len(volumes) < period:
        return None
    p = list(prices)[-period:]
    v = list(volumes)[-period:]
    total_vol = sum(v)
    if total_vol == 0:
        return None
    return sum(px * vol for px, vol in zip(p, v)) / total_vol


# ---- internal ----
def _ema(data: list[float], period: int) -> list[float]:
    if len(data) < period:
        return []
    k = 2.0 / (period + 1)
    result = [statistics.fmean(data[:period])]
    for val in data[period:]:
        result.append(val * k + result[-1] * (1 - k))
    return result
