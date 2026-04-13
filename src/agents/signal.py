from __future__ import annotations

from collections import defaultdict, deque

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.indicators import technical as ta


class SignalAgent(BaseAgent):
    """Compute a bundle of normalized signals per tick and publish as one event.

    Signals are normalized to [-1, 1] where possible:
      momentum, zscore, rsi, bollinger_pct_b, macd_hist,
      stochastic_k, obv_slope

    Raw values (for strategies that prefer them):
      rsi_raw, bb_lower, bb_upper, macd_line, macd_signal,
      atr_raw, vwap_raw, stoch_k_raw, stoch_d_raw
    """

    name = "signal"

    def __init__(self, bus: EventBus, state: SharedState, window: int = 60) -> None:
        super().__init__(bus, state)
        self.window = window
        self._closes: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=max(window, 200)))
        self._highs: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=max(window, 200)))
        self._lows: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=max(window, 200)))
        self._volumes: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=max(window, 200)))
        self.subscribe("market.tick", self._on_price)
        self.subscribe("market.trade", self._on_trade)

    async def run(self) -> None:
        await self._stop.wait()

    async def _on_trade(self, event: Event) -> None:
        ticker = event.payload["ticker"]
        price = float(event.payload["price"])
        volume = float(event.payload.get("volume", 0))
        self._update_bars(ticker, price, volume)
        await self._emit_signals(ticker, price)

    async def _on_price(self, event: Event) -> None:
        ticker = event.payload["ticker"]
        price = float(event.payload["price"])
        self._update_bars(ticker, price, 0.0)
        await self._emit_signals(ticker, price)

    def _update_bars(self, ticker: str, price: float, volume: float) -> None:
        self._closes[ticker].append(price)
        self._highs[ticker].append(price)
        self._lows[ticker].append(price)
        self._volumes[ticker].append(volume)

    async def _emit_signals(self, ticker: str, price: float) -> None:
        closes = self._closes[ticker]
        if len(closes) < self.window:
            return

        highs = self._highs[ticker]
        lows = self._lows[ticker]
        vols = self._volumes[ticker]

        signals: dict[str, float] = {}

        signals["momentum"] = self._momentum(closes)
        signals["zscore"] = self._zscore(closes)

        rsi_val = ta.rsi(closes, 14)
        if rsi_val is not None:
            signals["rsi_raw"] = rsi_val
            signals["rsi"] = (rsi_val - 50.0) / 50.0

        bb = ta.bollinger_bands(closes, 20, 2.0)
        if bb is not None:
            signals["bb_lower"] = bb[0]
            signals["bb_upper"] = bb[2]
        pct_b = ta.bollinger_pct_b(closes, 20, 2.0)
        if pct_b is not None:
            signals["bollinger_pct_b"] = max(-1.0, min(1.0, (pct_b - 0.5) * 2))

        macd_result = ta.macd(closes, 12, 26, 9)
        if macd_result is not None:
            m_line, m_signal, m_hist = macd_result
            signals["macd_line"] = m_line
            signals["macd_signal"] = m_signal
            norm = price * 0.01 if price > 0 else 1.0
            signals["macd_hist"] = max(-1.0, min(1.0, m_hist / norm))

        stoch = ta.stochastic(highs, lows, closes, 14, 3)
        if stoch is not None:
            signals["stoch_k_raw"] = stoch[0]
            signals["stoch_d_raw"] = stoch[1]
            signals["stochastic_k"] = (stoch[0] - 50.0) / 50.0

        atr_val = ta.atr(highs, lows, closes, 14)
        if atr_val is not None:
            signals["atr_raw"] = atr_val

        obv = ta.obv_signal(closes, vols, 20)
        if obv is not None:
            signals["obv_slope"] = obv

        vwap_val = ta.vwap(closes, vols, 20)
        if vwap_val is not None:
            signals["vwap_raw"] = vwap_val

        await self.emit(
            "signal.generated",
            {"ticker": ticker, "price": price, "signals": signals},
        )

    @staticmethod
    def _momentum(values: deque[float]) -> float:
        first, last = values[0], values[-1]
        if first == 0:
            return 0.0
        return max(-1.0, min(1.0, (last - first) / first * 20))

    @staticmethod
    def _zscore(values: deque[float]) -> float:
        import statistics
        mean = statistics.fmean(values)
        std = statistics.pstdev(values)
        if std == 0:
            return 0.0
        return max(-1.0, min(1.0, (values[-1] - mean) / std / 3))
