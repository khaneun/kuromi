"""On-chain indicator normalization to [-1, 1] signal range."""

from __future__ import annotations


def netflow_signal(netflow: float) -> float:
    """Exchange netflow. Positive = coins flowing into exchanges → bearish
    (sell pressure). Negative = outflow → bullish (HODLing)."""
    if netflow == 0:
        return 0.0
    return max(-1.0, min(1.0, -netflow / max(abs(netflow), 1.0)))


def nvt_signal(nvt: float) -> float:
    """Network Value to Transactions. High NVT (>100) → overvalued → bearish.
    Low NVT (<30) → undervalued → bullish. Neutral around 50-70."""
    if nvt <= 0:
        return 0.0
    if nvt < 30:
        return min(1.0, (30 - nvt) / 30)
    if nvt > 100:
        return max(-1.0, -(nvt - 100) / 100)
    return 0.0


def mvrv_signal(mvrv: float) -> float:
    """Market Value to Realized Value. MVRV > 3 → market overvalued → bearish.
    MVRV < 1 → undervalued → bullish."""
    if mvrv <= 0:
        return 0.0
    if mvrv < 1.0:
        return min(1.0, (1.0 - mvrv))
    if mvrv > 3.0:
        return max(-1.0, -(mvrv - 3.0) / 3.0)
    return 0.0


def active_addr_change_signal(current: int, previous: int) -> float:
    """Growing active addresses → bullish network activity.
    Declining → bearish."""
    if previous <= 0:
        return 0.0
    pct = (current - previous) / previous
    return max(-1.0, min(1.0, pct * 10))
