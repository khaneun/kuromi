from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncIterator

import websockets
from loguru import logger

UPBIT_WS_URL = "wss://api.upbit.com/websocket/v1"


class UpbitWSClient:
    """Async generator over Upbit public WebSocket. Auto-reconnects with
    exponential backoff. Emits the raw message dicts."""

    def __init__(
        self,
        tickers: list[str],
        types: tuple[str, ...] = ("ticker",),
        wire_format: str = "DEFAULT",
    ) -> None:
        self.tickers = tickers
        self.types = list(types)
        self.wire_format = wire_format

    def _request(self) -> list[dict]:
        req: list[dict] = [{"ticket": str(uuid.uuid4())}]
        for t in self.types:
            req.append({"type": t, "codes": self.tickers, "isOnlyRealtime": False})
        req.append({"format": self.wire_format})
        return req

    async def stream(self) -> AsyncIterator[dict]:
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(
                    UPBIT_WS_URL, ping_interval=60, ping_timeout=20, max_size=2**20
                ) as ws:
                    await ws.send(json.dumps(self._request()))
                    logger.info(
                        f"upbit ws connected tickers={self.tickers} types={self.types}"
                    )
                    backoff = 1.0
                    async for raw in ws:
                        data = raw if isinstance(raw, str) else raw.decode("utf-8")
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"upbit ws disconnect: {exc}; retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 2)
