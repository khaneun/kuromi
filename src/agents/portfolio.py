from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.equity_tracker import EquityTracker
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.upbit_client import UpbitClient


class PortfolioAgent(BaseAgent):
    """Tracks capital, positions, and equity. In live mode syncs with Upbit
    accounts periodically. Records equity history for dashboard charting."""

    name = "portfolio"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        client: UpbitClient | None = None,
        equity_tracker: EquityTracker | None = None,
        snapshot_sec: int = 30,
        sync_sec: int = 60,
        live: bool = False,
        trading_tickers: list[str] | None = None,
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.equity_tracker = equity_tracker or EquityTracker()
        self.snapshot_sec = snapshot_sec
        self.sync_sec = sync_sec
        self.live = live
        self._sync_counter = 0
        self._trading_tickers: set[str] = set(trading_tickers or [])
        self.subscribe("order.filled", self._on_filled)

    async def setup(self) -> None:
        pass  # initial sync happens in run() to avoid blocking startup

    async def run(self) -> None:
        while not self.stopping:
            self._sync_counter += self.snapshot_sec
            if self.live and self.client and self._sync_counter >= self.sync_sec:
                self._sync_counter = 0
                try:
                    await self._sync_upbit()
                except Exception as exc:
                    self.log(f"upbit sync error: {exc}")

            # 거래 목록에 없지만 보유 중인 종목 현재가 갱신
            await self._refresh_orphan_prices()

            snap = self.state.capital.snapshot(self.state.last_prices)
            snap["daily_pnl"] = self.state.daily_pnl
            self.equity_tracker.record(
                equity=snap["total_equity"],
                available_krw=snap["available_krw"],
                unrealized_pnl=snap["unrealized_pnl"],
                realized_pnl=snap["realized_pnl"],
                position_count=len(snap["positions"]),
            )
            await self.emit("portfolio.snapshot", snap)
            await self.sleep(self.snapshot_sec)

    async def _on_filled(self, event: Event) -> None:
        o = event.payload
        ticker = o["ticker"]
        price = float(o["price"])
        volume = float(o.get("executed_volume") or o.get("volume") or 0)

        if o["side"] == "buy":
            try:
                self.state.capital.open_position(ticker, price, volume)
            except Exception as exc:
                self.log(f"open_position failed: {exc}")
                return
        elif o["side"] == "sell":
            # close_position이 position을 제거하기 전에 entry_price 저장
            pos = self.state.capital.positions.get(ticker)
            entry_price = pos.entry_price if pos else price
            pnl = self.state.capital.close_position(ticker, price)
            if entry_price > 0:
                self.state.daily_pnl += (price - entry_price) / entry_price
            # pnl 포함 이벤트 emit → PerformanceAgent·PersistenceAgent가 구독
            await self.emit("trade.closed", {**o, "pnl": pnl, "entry_price": entry_price})

    async def _refresh_orphan_prices(self) -> None:
        """거래 종목 목록에서 제외됐지만 포지션이 남아 있는 자산의 현재가를 REST로 갱신.

        last_prices를 업데이트해 대시보드에 현재가·손익이 표기되도록 하고,
        market.tick을 emit해 SignalAgent 가격 히스토리를 쌓음
        (60틱 ≈ 30분 경과 후 자동 매도 파이프라인 정상 작동).
        """
        if not self.client:
            return
        orphans = [
            t for t in self.state.capital.positions
            if t not in self._trading_tickers
        ]
        if not orphans:
            return
        try:
            prices = await self.client.get_current_prices(orphans)
            for ticker, price in prices.items():
                self.state.last_prices[ticker] = price
                await self.emit("market.tick", {"ticker": ticker, "price": price})
            self.log(f"orphan prices refreshed: {list(prices.keys())}")
        except Exception as exc:
            self.log(f"orphan price fetch error: {exc}")

    async def _sync_upbit(self) -> None:
        if not self.client:
            return
        accounts = await self.client.get_accounts()
        self.state.capital.sync_from_upbit(accounts, self.state.last_prices)
