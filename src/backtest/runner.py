from __future__ import annotations

import argparse
import asyncio
import math
from statistics import fmean, pstdev

from loguru import logger

from src.agents.performance import PerformanceAgent
from src.agents.portfolio import PortfolioAgent
from src.agents.risk import RiskAgent
from src.agents.signal import SignalAgent
from src.agents.strategy import StrategyAgent
from src.backtest.mock_execution import MockExecutionAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.upbit_client import UpbitClient


async def fetch_candles(ticker: str, unit: int, count: int) -> list[dict]:
    client = UpbitClient()
    try:
        data = await client.get_candles(ticker, unit=unit, count=count)
    finally:
        await client.aclose()
    return list(reversed(data))


class Backtester:
    def __init__(
        self,
        ticker: str,
        candles: list[dict],
        initial_krw: float = 1_000_000.0,
        signal_window: int = 60,
        slippage_bps: float = 5.0,
        decision_threshold: float = 0.5,
        per_trade_risk_pct: float = 0.1,
    ) -> None:
        self.ticker = ticker
        self.candles = candles
        self.initial_krw = initial_krw
        self.bus = EventBus()
        self.state = SharedState()
        self.state.capital.set_krw(initial_krw)
        self.state.capital._initial_krw = initial_krw
        self.state.strategy_params["decision_threshold"] = decision_threshold

        self.signal = SignalAgent(self.bus, self.state, window=signal_window)
        self.strategy = StrategyAgent(self.bus, self.state)
        self.risk = RiskAgent(
            self.bus,
            self.state,
            max_positions=1,
            per_trade_risk_pct=per_trade_risk_pct,
            min_order_krw=0.0,
        )
        self.executor = MockExecutionAgent(self.bus, self.state, slippage_bps=slippage_bps)
        self.portfolio = PortfolioAgent(self.bus, self.state, snapshot_sec=10**9)
        self.perf = PerformanceAgent(self.bus, self.state, report_sec=10**9)

        self.fills: list[dict] = []
        self.equity_curve: list[float] = []
        self.bus.subscribe("order.filled", self._record_fill)

    async def _record_fill(self, event: Event) -> None:
        self.fills.append(event.payload)

    async def run(self) -> dict:
        for agent in (
            self.signal, self.strategy, self.risk,
            self.executor, self.portfolio, self.perf,
        ):
            await agent.setup()

        for candle in self.candles:
            price = float(candle["trade_price"])
            self.state.last_prices[self.ticker] = price
            await self.bus.publish(
                Event(
                    topic="market.tick",
                    payload={"ticker": self.ticker, "price": price},
                    source="backtest",
                )
            )
            equity = self.state.capital.total_equity(self.state.last_prices)
            self.equity_curve.append(equity)

        return self._report()

    def _report(self) -> dict:
        buys = [f for f in self.fills if f["side"] == "buy"]
        sells = [f for f in self.fills if f["side"] == "sell"]
        trade_returns: list[float] = []
        wins = 0
        for b, s in zip(buys, sells):
            r = (s["price"] - b["price"]) / b["price"]
            trade_returns.append(r)
            if r > 0:
                wins += 1

        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_krw
        total_return = (final_equity - self.initial_krw) / self.initial_krw

        return {
            "ticker": self.ticker,
            "candles": len(self.candles),
            "initial_krw": self.initial_krw,
            "final_equity": round(final_equity, 0),
            "total_return": round(total_return, 6),
            "total_pnl_krw": round(final_equity - self.initial_krw, 0),
            "closed_trades": len(trade_returns),
            "win_rate": round(wins / len(trade_returns), 4) if trade_returns else 0.0,
            "avg_trade_return": round(fmean(trade_returns), 6) if trade_returns else 0.0,
            "max_drawdown": round(_max_drawdown(self.equity_curve), 6),
            "sharpe_like": round(_sharpe(trade_returns), 4) if len(trade_returns) > 1 else 0.0,
            "open_position": self.ticker in self.state.capital.positions,
            "strategy_weights": self.state.strategy_params.get("strategy_weights"),
        }


def _max_drawdown(equity: list[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            dd = (v - peak) / peak
            worst = min(worst, dd)
    return worst


def _sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = fmean(returns)
    std = pstdev(returns)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(len(returns))


async def amain(args: argparse.Namespace) -> None:
    candles = await fetch_candles(args.ticker, args.minutes, args.count)
    if not candles:
        logger.error("no candles fetched")
        return
    bt = Backtester(
        args.ticker,
        candles,
        initial_krw=args.capital,
        signal_window=args.window,
        slippage_bps=args.slippage,
        decision_threshold=args.threshold,
        per_trade_risk_pct=args.risk_pct,
    )
    report = await bt.run()
    print("=== BACKTEST REPORT ===")
    for k, v in report.items():
        if isinstance(v, float) and abs(v) >= 1000:
            print(f"  {k}: {v:,.0f}")
        else:
            print(f"  {k}: {v}")


def main() -> None:
    p = argparse.ArgumentParser(prog="kuromi-backtest")
    p.add_argument("--ticker", default="KRW-BTC")
    p.add_argument(
        "--minutes", type=int, default=1, choices=[1, 3, 5, 10, 15, 30, 60, 240]
    )
    p.add_argument("--count", type=int, default=200, help="candles (Upbit max 200/req)")
    p.add_argument("--capital", type=float, default=1_000_000.0, help="initial KRW")
    p.add_argument("--risk-pct", type=float, default=0.1, help="fraction per trade")
    p.add_argument("--window", type=int, default=60, help="signal rolling window")
    p.add_argument("--slippage", type=float, default=5.0, help="bps")
    p.add_argument("--threshold", type=float, default=0.5)
    asyncio.run(amain(p.parse_args()))


if __name__ == "__main__":
    main()
