from __future__ import annotations

from typing import Any

import httpx

BINANCE_FUTURES = "https://fapi.binance.com"
BINANCE_SPOT = "https://api.binance.com"

UPBIT_TO_BINANCE: dict[str, str] = {
    "KRW-BTC": "BTCUSDT",
    "KRW-ETH": "ETHUSDT",
    "KRW-XRP": "XRPUSDT",
    "KRW-SOL": "SOLUSDT",
    "KRW-DOGE": "DOGEUSDT",
    "KRW-ADA": "ADAUSDT",
    "KRW-AVAX": "AVAXUSDT",
    "KRW-DOT": "DOTUSDT",
}


class BinanceClient:
    """Public-only Binance REST client for derivative indicators.
    No API key needed for funding rate and open interest."""

    def __init__(self, timeout: float = 5.0) -> None:
        self._futures = httpx.AsyncClient(base_url=BINANCE_FUTURES, timeout=timeout)
        self._spot = httpx.AsyncClient(base_url=BINANCE_SPOT, timeout=timeout)

    async def aclose(self) -> None:
        await self._futures.aclose()
        await self._spot.aclose()

    async def funding_rate(self, symbol: str) -> dict[str, Any]:
        resp = await self._futures.get(
            "/fapi/v1/premiumIndex", params={"symbol": symbol}
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "symbol": data["symbol"],
            "funding_rate": float(data.get("lastFundingRate", 0)),
            "mark_price": float(data.get("markPrice", 0)),
            "index_price": float(data.get("indexPrice", 0)),
        }

    async def open_interest(self, symbol: str) -> dict[str, Any]:
        resp = await self._futures.get(
            "/fapi/v1/openInterest", params={"symbol": symbol}
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "symbol": data["symbol"],
            "open_interest": float(data.get("openInterest", 0)),
        }

    async def long_short_ratio(self, symbol: str, period: str = "5m") -> dict[str, Any]:
        resp = await self._futures.get(
            "/futures/data/globalLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": 1},
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return {"symbol": symbol, "long_ratio": 0.5, "short_ratio": 0.5}
        row = rows[0]
        return {
            "symbol": symbol,
            "long_ratio": float(row.get("longAccount", 0.5)),
            "short_ratio": float(row.get("shortAccount", 0.5)),
        }

    async def usdt_price(self) -> float:
        """USDT/KRW proxy via Binance spot USDTKRW — not available on Binance.
        We return 0.0 as sentinel; caller should use Upbit for KRW pricing."""
        return 0.0

    @staticmethod
    def map_ticker(upbit_ticker: str) -> str | None:
        return UPBIT_TO_BINANCE.get(upbit_ticker)
