from __future__ import annotations

import statistics
from collections import deque
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState

if TYPE_CHECKING:
    from src.agents.persistence import PersistenceAgent


class PerformanceAgent(BaseAgent):
    name = "performance"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        persistence: "PersistenceAgent | None" = None,
        report_sec: int = 300,
        window: int = 500,
    ) -> None:
        super().__init__(bus, state)
        self.report_sec = report_sec
        self.persistence = persistence
        self._trades: deque[dict] = deque(maxlen=window)
        self._equity_curve: deque[float] = deque(maxlen=window)
        # sell 완료(pnl 확정) 이벤트만 구독
        self.subscribe("trade.closed", self._on_trade_closed)
        self.subscribe("portfolio.snapshot", self._on_snapshot)

    async def setup(self) -> None:
        await super().setup()
        if not self.persistence:
            return
        try:
            rows = await self.persistence.query_trades(limit=500)
            # query_trades는 최신 순 반환 → 오래된 순으로 복원
            for r in reversed(rows):
                if r.get("side") == "sell":
                    self._trades.append(r)
            if self._trades:
                self.log(f"DB에서 거래 내역 {len(self._trades)}건 복구")
        except Exception as exc:
            self.log(f"거래 내역 복구 실패: {exc}")

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.report_sec)
            report = self._build_report()
            self.state.strategy_params["_last_perf"] = report
            await self.emit("performance.report", report)

    async def _on_trade_closed(self, event: Event) -> None:
        """PortfolioAgent가 pnl 확정 후 emit하는 trade.closed 수신."""
        self._trades.append(event.payload)

    async def _on_snapshot(self, event: Event) -> None:
        eq = event.payload.get("total_equity", 0) if isinstance(event.payload, dict) else 0
        if eq > 0:
            self._equity_curve.append(eq)

    def _build_report(self) -> dict:
        # _trades는 모두 sell(trade.closed) 이므로 전수 집계
        trades = list(self._trades)
        total_trades = len(trades)
        win_rate = 0.0
        total_pnl = 0.0

        if trades:
            wins = sum(1 for t in trades if float(t.get("pnl", 0)) > 0)
            win_rate = wins / total_trades
            total_pnl = sum(float(t.get("pnl", 0)) for t in trades)

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "max_drawdown": self._max_drawdown(),
            "sharpe": self._sharpe(),
            "daily_pnl": self.state.daily_pnl,
            "open_positions": len(self.state.positions),
        }

    def _max_drawdown(self) -> float:
        curve = list(self._equity_curve)
        if len(curve) < 2:
            return 0.0
        peak = curve[0]
        max_dd = 0.0
        for eq in curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def _sharpe(self) -> float:
        curve = list(self._equity_curve)
        if len(curve) < 3:
            return 0.0
        returns = [(curve[i] - curve[i - 1]) / curve[i - 1] for i in range(1, len(curve))]
        mean_r = statistics.fmean(returns)
        try:
            std_r = statistics.stdev(returns)
        except statistics.StatisticsError:
            return 0.0
        return mean_r / std_r if std_r > 0 else 0.0
