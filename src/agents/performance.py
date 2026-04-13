from __future__ import annotations

import statistics
from collections import deque

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class PerformanceAgent(BaseAgent):
    name = "performance"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        report_sec: int = 300,
        window: int = 500,
    ) -> None:
        super().__init__(bus, state)
        self.report_sec = report_sec
        self._trades: deque[dict] = deque(maxlen=window)
        self._equity_curve: deque[float] = deque(maxlen=window)
        self.subscribe("order.filled", self._on_filled)
        self.subscribe("portfolio.snapshot", self._on_snapshot)

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.report_sec)
            report = self._build_report()
            # /perf 명령에서 조회할 수 있도록 SharedState에 저장
            self.state.strategy_params["_last_perf"] = report
            await self.emit("performance.report", report)

    async def _on_filled(self, event: Event) -> None:
        self._trades.append(event.payload)

    async def _on_snapshot(self, event: Event) -> None:
        eq = event.payload.get("total_equity", 0) if isinstance(event.payload, dict) else 0
        if eq > 0:
            self._equity_curve.append(eq)

    def _build_report(self) -> dict:
        trades = list(self._trades)
        sells = [t for t in trades if t.get("side") == "sell"]
        total_trades = len(trades)
        win_rate = 0.0
        total_pnl = 0.0

        if sells:
            # 수익 거래 = sell 체결이 존재하고 pnl > 0
            wins = sum(1 for t in sells if t.get("pnl", 0) > 0)
            win_rate = wins / len(sells)
            total_pnl = sum(t.get("pnl", 0) for t in sells)

        # max drawdown from equity curve
        max_dd = self._max_drawdown()

        # sharpe-like: mean / std of returns
        sharpe = self._sharpe()

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "max_drawdown": max_dd,
            "sharpe": sharpe,
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
