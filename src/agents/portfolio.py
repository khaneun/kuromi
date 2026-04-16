from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.equity_tracker import EquityTracker
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.upbit_client import UpbitClient

if TYPE_CHECKING:
    from config.runtime_config import RuntimeConfig


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
        runtime_cfg: "RuntimeConfig | None" = None,
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.equity_tracker = equity_tracker or EquityTracker()
        self.snapshot_sec = snapshot_sec
        self.sync_sec = sync_sec
        self.live = live
        self._sync_counter = 0
        self._trading_tickers: set[str] = set(trading_tickers or [])
        self._runtime_cfg = runtime_cfg
        self.subscribe("order.filled", self._on_filled)

    async def setup(self) -> None:
        # 실매매 모드 시 시작 직후 Upbit 잔고를 동기화한다.
        # ExecutionAgent.setup()이 복구 주문 체결 이벤트를 emit하기 전에
        # 자본 상태가 정확해야 open_position 오류를 방지할 수 있다.
        if self.live and self.client:
            try:
                await self._sync_upbit()
                self.log("initial Upbit sync completed")
            except Exception as exc:
                self.log(f"initial Upbit sync failed: {exc}")

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
            if ticker in self.state.capital.positions:
                # 재시작 후 Upbit 동기화로 이미 포지션이 반영된 경우 — open_position 스킵
                self.log(f"[{ticker}] position already synced from Upbit, skipping open_position")
            else:
                try:
                    self.state.capital.open_position(ticker, price, volume)
                except Exception as exc:
                    self.log(f"open_position failed: {exc}")
                    return
            # 매수 체결 → 관리 목록에서 제거 (재진입·중복매수 차단)
            self._remove_from_trading(ticker)

        elif o["side"] == "sell":
            # close_position이 position을 제거하기 전에 entry_price 저장
            pos = self.state.capital.positions.get(ticker)
            entry_price = pos.entry_price if pos else price
            pnl = self.state.capital.close_position(ticker, price)
            if entry_price > 0:
                self.state.daily_pnl += (price - entry_price) / entry_price
            # pnl 포함 이벤트 emit → PerformanceAgent·PersistenceAgent가 구독
            await self.emit("trade.closed", {**o, "pnl": pnl, "entry_price": entry_price})
            # 매도 체결 → 관리 목록에서 제거 (매수 시 이미 제거됐을 수 있으나 방어적으로 재시도)
            self._remove_from_trading(ticker)

    def _remove_from_trading(self, ticker: str) -> None:
        """체결된 종목을 관리 목록에서 제거하고 설정 파일에 영속화한다."""
        # state의 허용 목록 제거 → RiskAgent가 해당 종목 매수 의도를 차단
        was_present = ticker in self.state.trading_tickers
        self.state.trading_tickers.discard(ticker)
        # 내부 orphan 감지 목록 제거 → 이제 포지션 보유 시 orphan으로 관리
        self._trading_tickers.discard(ticker)

        # runtime_config 파일에도 반영 (재시작 후에도 유지)
        if self._runtime_cfg and was_present:
            updated = [t for t in self._runtime_cfg.trading_tickers if t != ticker]
            self._runtime_cfg.update_and_save({"trading_tickers": updated})
            self.log(f"trading ticker removed after fill: {ticker}")

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
