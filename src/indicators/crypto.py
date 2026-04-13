"""Crypto-specific derivative indicators computed from external data."""

from __future__ import annotations


def kimchi_premium(upbit_krw_price: float, global_usd_price: float, usdkrw: float) -> float:
    """Korean premium percentage. Positive = Upbit is overpriced vs global."""
    if global_usd_price <= 0 or usdkrw <= 0:
        return 0.0
    fair_krw = global_usd_price * usdkrw
    if fair_krw == 0:
        return 0.0
    return (upbit_krw_price - fair_krw) / fair_krw


def funding_rate_signal(rate: float) -> float:
    """Normalize funding rate to [-1, 1].
    High positive → market overleveraged long → bearish signal.
    Negative → overleveraged short → bullish signal."""
    return max(-1.0, min(1.0, -rate * 100))


def long_short_signal(long_ratio: float) -> float:
    """Normalize long/short ratio to [-1, 1].
    > 0.5 long = market is crowded long → contrarian bearish."""
    return max(-1.0, min(1.0, (0.5 - long_ratio) * 4))


def spread_signal(bid: float, ask: float) -> float:
    """Bid-ask spread as fraction of mid-price. Tight spread → liquid → 0.
    Wider spread → less liquid → higher absolute value."""
    if bid <= 0 or ask <= 0:
        return 0.0
    mid = (bid + ask) / 2
    return (ask - bid) / mid
