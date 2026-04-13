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
from src.backtest.candle_merge import TimedCandle, merge
from src.backtest.mock_execution import MockExecutionAgent
from src.backtest.runner import fetch_candles
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class UnifiedBacktester:
    """Portfolio-level backtest: single Capital pool, shared EventBus,
    merged candle timeline across multiple tickers."""

    def __init__(
        self,
        tickers: list[str],
        ticker_candles: dict[str, list[dict]],
        initial_krw: float = 1_000_000.0,
        max_positions: int = 3,
        per_trade_risk_pct: float = 0.1,
        signal_window: int = 60,
        slippage_bps: float = 5.0,
        decision_threshold: float = 0.5,
    ) -> None:
        self.tickers = tickers
        self.ticker_candles = ticker_candles
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
            max_positions=max_positions,
            per_trade_risk_pct=per_trade_risk_pct,
            daily_loss_limit_pct=1.0,
            min_order_krw=0.0,
        )
        self.executor = MockExecutionAgent(self.bus, self.state, slippage_bps=slippage_bps)
        self.portfolio = PortfolioAgent(self.bus, self.state, snapshot_sec=10**9)
        self.perf = PerformanceAgent(self.bus, self.state, report_sec=10**9)

        self.fills: list[dict] = []
        self.equity_curve: list[float] = []
        self.timeline: list[TimedCandle] = []
        self.bus.subscribe("order.filled", self._record_fill)

    async def _record_fill(self, event: Event) -> None:
        self.fills.append(event.payload)

    async def run(self) -> dict:
        agents = [
            self.signal, self.strategy, self.risk,
            self.executor, self.portfolio, self.perf,
        ]
        for agent in agents:
            await agent.setup()

        merged = list(merge(self.ticker_candles))
        self.timeline = merged

        for tc in merged:
            self.state.last_prices[tc.ticker] = tc.price
            await self.bus.publish(
                Event(
                    topic="market.tick",
                    payload={"ticker": tc.ticker, "price": tc.price},
                    source="backtest",
                )
            )
            equity = self.state.capital.total_equity(self.state.last_prices)
            self.equity_curve.append(equity)

        return self._report()

    def _report(self) -> dict:
        per_ticker = self._per_ticker_stats()
        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_krw
        total_return = (final_equity - self.initial_krw) / self.initial_krw

        all_returns = []
        total_wins = 0
        total_closed = 0
        for stats in per_ticker.values():
            all_returns.extend(stats["returns"])
            total_wins += stats["wins"]
            total_closed += stats["closed"]

        return {
            "tickers": self.tickers,
            "candles_total": len(self.timeline),
            "initial_krw": self.initial_krw,
            "final_equity": round(final_equity, 0),
            "total_return": round(total_return, 6),
            "total_pnl_krw": round(final_equity - self.initial_krw, 0),
            "closed_trades": total_closed,
            "win_rate": round(total_wins / total_closed, 4) if total_closed else 0.0,
            "avg_trade_return": round(fmean(all_returns), 6) if all_returns else 0.0,
            "max_drawdown": round(_max_drawdown(self.equity_curve), 6),
            "sharpe_like": round(_sharpe(all_returns), 4) if len(all_returns) > 1 else 0.0,
            "open_positions": list(self.state.capital.positions.keys()),
            "per_ticker": {
                t: {
                    "closed": s["closed"],
                    "wins": s["wins"],
                    "win_rate": round(s["wins"] / s["closed"], 4) if s["closed"] else 0.0,
                    "avg_return": round(fmean(s["returns"]), 6) if s["returns"] else 0.0,
                }
                for t, s in per_ticker.items()
            },
            "strategy_weights": self.state.strategy_params.get("strategy_weights"),
        }

    def _per_ticker_stats(self) -> dict[str, dict]:
        buys: dict[str, list[dict]] = {t: [] for t in self.tickers}
        sells: dict[str, list[dict]] = {t: [] for t in self.tickers}
        for f in self.fills:
            t = f["ticker"]
            if t not in buys:
                buys[t] = []
                sells[t] = []
            if f["side"] == "buy":
                buys[t].append(f)
            else:
                sells[t].append(f)

        result: dict[str, dict] = {}
        for t in set(list(buys.keys()) + list(sells.keys())):
            returns: list[float] = []
            wins = 0
            for b, s in zip(buys.get(t, []), sells.get(t, [])):
                r = (s["price"] - b["price"]) / b["price"]
                returns.append(r)
                if r > 0:
                    wins += 1
            result[t] = {"closed": len(returns), "wins": wins, "returns": returns}
        return result


def _max_drawdown(equity: list[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, (v - peak) / peak)
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
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        logger.error("no tickers")
        return

    logger.info(f"fetching candles for {tickers}")
    ticker_candles: dict[str, list[dict]] = {}
    for t in tickers:
        candles = await fetch_candles(t, args.minutes, args.count)
        if candles:
            ticker_candles[t] = candles
            logger.info(f"  {t}: {len(candles)} candles")
        else:
            logger.warning(f"  {t}: no candles, skipped")

    if not ticker_candles:
        logger.error("no candles for any ticker")
        return

    bt = UnifiedBacktester(
        tickers=list(ticker_candles.keys()),
        ticker_candles=ticker_candles,
        initial_krw=args.capital,
        max_positions=args.max_positions,
        per_trade_risk_pct=args.risk_pct,
        signal_window=args.window,
        slippage_bps=args.slippage,
        decision_threshold=args.threshold,
    )
    report = await bt.run()

    print("=== UNIFIED BACKTEST REPORT ===")
    for k, v in report.items():
        if k == "per_ticker":
            print(f"  per_ticker:")
            for ticker, stats in v.items():
                print(f"    {ticker}: {stats}")
        elif isinstance(v, float) and abs(v) >= 1000:
            print(f"  {k}: {v:,.0f}")
        else:
            print(f"  {k}: {v}")


def main() -> None:
    p = argparse.ArgumentParser(prog="kuromi-unified-backtest")
    p.add_argument("--tickers", default="KRW-BTC,KRW-ETH,KRW-XRP")
    p.add_argument(
        "--minutes", type=int, default=5, choices=[1, 3, 5, 10, 15, 30, 60, 240]
    )
    p.add_argument("--count", type=int, default=200)
    p.add_argument("--capital", type=float, default=1_000_000.0)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--risk-pct", type=float, default=0.1)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--slippage", type=float, default=5.0)
    p.add_argument("--threshold", type=float, default=0.5)
    asyncio.run(amain(p.parse_args()))


if __name__ == "__main__":
    main()
