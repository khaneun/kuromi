from __future__ import annotations

import asyncio

from src.agents.base import BaseAgent
from src.core.event_bus import EventBus
from src.core.state import SharedState
from src.exchange.upbit_client import UpbitClient
from src.exchange.upbit_ws import UpbitWSClient


class MarketDataAgent(BaseAgent):
    """WebSocket-first live market data. REST fallback fills gaps and
    seeds initial prices before the first WS frame arrives."""

    name = "market_data"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        client: UpbitClient,
        tickers: list[str],
        poll_sec: float = 5.0,
        ws_types: tuple[str, ...] = ("ticker", "trade", "orderbook"),
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.tickers = tickers
        self.poll_sec = poll_sec
        self._ws = UpbitWSClient(tickers, types=ws_types)

    async def run(self) -> None:
        self.log(f"streaming tickers={self.tickers}")
        ws_task = asyncio.create_task(self._run_ws(), name="market_data.ws")
        rest_task = asyncio.create_task(self._run_rest(), name="market_data.rest")
        try:
            await self._stop.wait()
        finally:
            for t in (ws_task, rest_task):
                t.cancel()
            await asyncio.gather(ws_task, rest_task, return_exceptions=True)

    async def _run_ws(self) -> None:
        async for msg in self._ws.stream():
            mtype = msg.get("type") or msg.get("ty")
            code = msg.get("code") or msg.get("cd")
            if not (mtype and code):
                continue

            if mtype == "ticker":
                price = msg.get("trade_price") or msg.get("tp")
                if price is None:
                    continue
                self.state.last_prices[code] = float(price)
                await self.emit("market.tick", {"ticker": code, "price": float(price)})

            elif mtype == "trade":
                price = msg.get("trade_price") or msg.get("tp")
                if price is None:
                    continue
                self.state.last_prices[code] = float(price)
                await self.emit(
                    "market.trade",
                    {
                        "ticker": code,
                        "price": float(price),
                        "volume": float(msg.get("trade_volume") or msg.get("tv") or 0.0),
                        "side": msg.get("ask_bid") or msg.get("ab"),
                    },
                )

            elif mtype == "orderbook":
                units = msg.get("orderbook_units") or msg.get("obu") or []
                if units:
                    top = units[0]
                    await self.emit(
                        "market.orderbook",
                        {
                            "ticker": code,
                            "bid": float(top.get("bid_price") or top.get("bp") or 0),
                            "ask": float(top.get("ask_price") or top.get("ap") or 0),
                            "bid_size": float(top.get("bid_size") or top.get("bs") or 0),
                            "ask_size": float(top.get("ask_size") or top.get("as") or 0),
                        },
                    )

    async def _run_rest(self) -> None:
        while not self.stopping:
            try:
                prices = await self.client.get_current_prices(self.tickers)
                for ticker, price in prices.items():
                    self.state.last_prices.setdefault(ticker, price)
            except Exception as exc:
                self.log(f"rest fallback error: {exc}")
            await self.sleep(self.poll_sec)
