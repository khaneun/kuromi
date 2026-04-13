from __future__ import annotations

from typing import Any

import httpx

CRYPTOQUANT_BASE = "https://api.cryptoquant.com/v1"

UPBIT_TO_CHAIN: dict[str, str] = {
    "KRW-BTC": "btc",
    "KRW-ETH": "eth",
}


class CryptoQuantClient:
    """CryptoQuant free-tier API client. Provides on-chain metrics:
    - Exchange reserve (inflow/outflow proxy)
    - Active addresses
    - NVT ratio (network value to transactions)
    - MVRV ratio (market value to realized value)

    Free tier: 10 requests/minute, limited window. Set API key in .env.
    """

    def __init__(self, api_key: str = "", timeout: float = 10.0) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=CRYPTOQUANT_BASE,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def exchange_reserve(self, chain: str) -> dict[str, Any]:
        resp = await self._client.get(
            f"/{chain}/exchange-flows/reserve",
            params={"window": "day", "limit": 1},
        )
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("data", [])
        if not rows:
            return {}
        row = rows[0]
        return {
            "exchange_reserve": float(row.get("reserve", 0)),
            "exchange_reserve_usd": float(row.get("reserveUsd", 0)),
        }

    async def exchange_netflow(self, chain: str) -> dict[str, Any]:
        resp = await self._client.get(
            f"/{chain}/exchange-flows/netflow",
            params={"window": "day", "limit": 1},
        )
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("data", [])
        if not rows:
            return {}
        row = rows[0]
        return {
            "exchange_netflow": float(row.get("netflow", 0)),
        }

    async def active_addresses(self, chain: str) -> dict[str, Any]:
        resp = await self._client.get(
            f"/{chain}/network-data/active-addresses",
            params={"window": "day", "limit": 1},
        )
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("data", [])
        if not rows:
            return {}
        return {"active_addresses": int(rows[0].get("activeAddresses", 0))}

    async def nvt(self, chain: str) -> dict[str, Any]:
        resp = await self._client.get(
            f"/{chain}/network-indicator/nvt",
            params={"window": "day", "limit": 1},
        )
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("data", [])
        if not rows:
            return {}
        return {"nvt": float(rows[0].get("nvt", 0))}

    async def mvrv(self, chain: str) -> dict[str, Any]:
        resp = await self._client.get(
            f"/{chain}/market-indicator/mvrv",
            params={"window": "day", "limit": 1},
        )
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("data", [])
        if not rows:
            return {}
        return {"mvrv": float(rows[0].get("mvrv", 0))}

    @staticmethod
    def map_chain(upbit_ticker: str) -> str | None:
        return UPBIT_TO_CHAIN.get(upbit_ticker)
