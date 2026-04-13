from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.event_bus import EventBus
from src.core.state import SharedState
from src.exchange.onchain_client import CryptoQuantClient
from src.indicators.onchain import mvrv_signal, netflow_signal, nvt_signal


class OnchainAgent(BaseAgent):
    """Polls CryptoQuant for on-chain metrics and publishes signal.onchain.
    Gracefully does nothing when API key is not configured."""

    name = "onchain"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        client: CryptoQuantClient,
        tickers: list[str],
        poll_sec: float = 300.0,
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.tickers = tickers
        self.poll_sec = poll_sec

    async def run(self) -> None:
        if not self.client.enabled:
            self.log("CryptoQuant API key not set; onchain agent disabled")
            return
        self.log(f"onchain polling: tickers={self.tickers} every {self.poll_sec}s")
        while not self.stopping:
            for ticker in self.tickers:
                chain = CryptoQuantClient.map_chain(ticker)
                if not chain:
                    continue
                try:
                    signals = await self._collect(chain)
                    if signals:
                        await self.emit(
                            "signal.onchain",
                            {"ticker": ticker, "signals": signals},
                        )
                except Exception as exc:
                    self.log(f"onchain error {ticker}: {exc}")
            await self.sleep(self.poll_sec)

    async def _collect(self, chain: str) -> dict[str, float]:
        signals: dict[str, float] = {}

        try:
            nf = await self.client.exchange_netflow(chain)
            raw = nf.get("exchange_netflow", 0)
            signals["exchange_netflow_raw"] = raw
            signals["exchange_netflow"] = netflow_signal(raw)
        except Exception:
            pass

        try:
            res = await self.client.exchange_reserve(chain)
            if "exchange_reserve" in res:
                signals["exchange_reserve"] = res["exchange_reserve"]
        except Exception:
            pass

        try:
            n = await self.client.nvt(chain)
            raw = n.get("nvt", 0)
            signals["nvt_raw"] = raw
            signals["nvt"] = nvt_signal(raw)
        except Exception:
            pass

        try:
            m = await self.client.mvrv(chain)
            raw = m.get("mvrv", 0)
            signals["mvrv_raw"] = raw
            signals["mvrv"] = mvrv_signal(raw)
        except Exception:
            pass

        return signals
