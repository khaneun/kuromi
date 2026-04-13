from __future__ import annotations

import hashlib
import uuid
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

UPBIT_BASE = "https://api.upbit.com"


class UpbitClient:
    """Thin async wrapper around Upbit REST API.

    Public endpoints do not require auth. Private endpoints sign requests
    with JWT. Query params (GET/DELETE) and JSON bodies (POST) both flow
    through the same query_hash signing path.
    """

    def __init__(self, access_key: str = "", secret_key: str = "", timeout: float = 5.0) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self._client = httpx.AsyncClient(base_url=UPBIT_BASE, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----- public -----
    async def get_current_prices(self, tickers: list[str]) -> dict[str, float]:
        resp = await self._client.get("/v1/ticker", params={"markets": ",".join(tickers)})
        resp.raise_for_status()
        return {row["market"]: float(row["trade_price"]) for row in resp.json()}

    async def get_candles(self, ticker: str, unit: int = 1, count: int = 200) -> list[dict]:
        resp = await self._client.get(
            f"/v1/candles/minutes/{unit}", params={"market": ticker, "count": count}
        )
        resp.raise_for_status()
        return resp.json()

    # ----- private -----
    async def get_accounts(self) -> list[dict]:
        return await self._signed("GET", "/v1/accounts")

    async def place_order(
        self,
        market: str,
        side: str,
        price: float,
        volume: float | None = None,
        ord_type: str = "limit",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "market": market,
            "side": "bid" if side == "buy" else "ask",
            "ord_type": ord_type,
        }
        if volume is not None:
            body["volume"] = str(volume)
        if ord_type in ("limit", "price"):
            body["price"] = str(price)
        return await self._signed("POST", "/v1/orders", body=body)

    async def get_order(self, order_uuid: str) -> dict[str, Any]:
        return await self._signed("GET", "/v1/order", params={"uuid": order_uuid})

    async def cancel_order(self, order_uuid: str) -> dict[str, Any]:
        return await self._signed("DELETE", "/v1/order", params={"uuid": order_uuid})

    # ----- internal -----
    async def _signed(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        to_sign = params if params is not None else body
        payload: dict[str, Any] = {"access_key": self.access_key, "nonce": str(uuid.uuid4())}
        if to_sign:
            qs = urlencode(to_sign).encode()
            h = hashlib.sha512()
            h.update(qs)
            payload["query_hash"] = h.hexdigest()
            payload["query_hash_alg"] = "SHA512"
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        if method in ("GET", "DELETE"):
            resp = await self._client.request(method, path, headers=headers, params=params)
        else:
            resp = await self._client.request(method, path, headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()
