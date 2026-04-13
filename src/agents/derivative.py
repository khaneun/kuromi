from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.binance_client import BinanceClient
from src.indicators.crypto import (
    funding_rate_signal,
    kimchi_premium,
    long_short_signal,
    spread_signal,
)


class DerivativeAgent(BaseAgent):
    """Collects crypto-specific derivative indicators and publishes them as
    signal.derivative events. These get merged into the signal bundle
    by StrategyAgent/MultiFactor strategies.

    Sources: Binance (funding, OI, L/S ratio), Upbit (orderbook spread).
    """

    name = "derivative"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        binance: BinanceClient,
        tickers: list[str],
        poll_sec: float = 30.0,
        usdkrw: float = 1380.0,
    ) -> None:
        super().__init__(bus, state)
        self.binance = binance
        self.tickers = tickers
        self.poll_sec = poll_sec
        self.usdkrw = usdkrw
        self._orderbook: dict[str, dict] = {}
        self.subscribe("market.orderbook", self._on_orderbook)

    async def _on_orderbook(self, event: Event) -> None:
        p = event.payload
        self._orderbook[p["ticker"]] = {
            "bid": float(p["bid"]),
            "ask": float(p["ask"]),
        }

    async def run(self) -> None:
        self.log(f"derivative polling: tickers={self.tickers}")
        while not self.stopping:
            for ticker in self.tickers:
                try:
                    signals = await self._collect(ticker)
                    if signals:
                        await self.emit(
                            "signal.derivative",
                            {"ticker": ticker, "signals": signals},
                        )
                except Exception as exc:
                    self.log(f"derivative error {ticker}: {exc}")
            await self.sleep(self.poll_sec)

    async def _collect(self, ticker: str) -> dict[str, float]:
        symbol = BinanceClient.map_ticker(ticker)
        signals: dict[str, float] = {}

        if symbol:
            try:
                fr = await self.binance.funding_rate(symbol)
                signals["funding_rate_raw"] = fr["funding_rate"]
                signals["funding_rate"] = funding_rate_signal(fr["funding_rate"])
                idx = fr["index_price"]

                upbit_price = self.state.last_prices.get(ticker, 0)
                if upbit_price > 0 and idx > 0:
                    signals["kimchi_premium"] = kimchi_premium(
                        upbit_price, idx, self.usdkrw
                    )
            except Exception:
                pass

            try:
                oi = await self.binance.open_interest(symbol)
                signals["open_interest"] = oi["open_interest"]
            except Exception:
                pass

            try:
                ls = await self.binance.long_short_ratio(symbol)
                signals["long_ratio"] = ls["long_ratio"]
                signals["long_short"] = long_short_signal(ls["long_ratio"])
            except Exception:
                pass

        ob = self._orderbook.get(ticker)
        if ob:
            signals["spread"] = spread_signal(ob["bid"], ob["ask"])

        return signals
