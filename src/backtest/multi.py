from __future__ import annotations

import argparse
import asyncio
import json
from statistics import fmean

from loguru import logger

from src.backtest.runner import Backtester, fetch_candles
from src.backtest.unified import UnifiedBacktester


async def _run_ticker(
    ticker: str,
    minutes: int,
    count: int,
    signal_window: int,
    slippage_bps: float,
    decision_threshold: float,
    capital: float,
    risk_pct: float,
) -> dict:
    candles = await fetch_candles(ticker, minutes, count)
    if not candles:
        return {"ticker": ticker, "error": "no_candles"}
    bt = Backtester(
        ticker=ticker,
        candles=candles,
        initial_krw=capital,
        signal_window=signal_window,
        slippage_bps=slippage_bps,
        decision_threshold=decision_threshold,
        per_trade_risk_pct=risk_pct,
    )
    return await bt.run()


def _aggregate(per_ticker: list[dict]) -> dict:
    valid = [r for r in per_ticker if "error" not in r]
    if not valid:
        return {"tickers": len(per_ticker), "valid": 0}
    return {
        "tickers": len(per_ticker),
        "valid": len(valid),
        "avg_return": round(fmean(r["total_return"] for r in valid), 6),
        "best": max(valid, key=lambda r: r["total_return"])["ticker"],
        "worst": min(valid, key=lambda r: r["total_return"])["ticker"],
        "avg_win_rate": round(
            fmean(r["win_rate"] for r in valid if r["closed_trades"] > 0)
            if any(r["closed_trades"] > 0 for r in valid)
            else 0.0,
            4,
        ),
        "avg_drawdown": round(fmean(r["max_drawdown"] for r in valid), 6),
    }


async def _run_independent(args: argparse.Namespace) -> None:
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        logger.error("no tickers provided")
        return
    logger.info(f"independent backtest: {len(tickers)} tickers")

    sem = asyncio.Semaphore(args.jobs)

    async def worker(t: str) -> dict:
        async with sem:
            return await _run_ticker(
                t, args.minutes, args.count, args.window,
                args.slippage, args.threshold, args.capital, args.risk_pct,
            )

    per_ticker = await asyncio.gather(*(worker(t) for t in tickers))
    report = {"per_ticker": per_ticker, "aggregate": _aggregate(per_ticker)}

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("=== PER-TICKER (independent) ===")
    for r in per_ticker:
        if "error" in r:
            print(f"  {r['ticker']}: ERROR {r['error']}")
            continue
        print(
            f"  {r['ticker']:10s}  ret={r['total_return']:+.4f}  "
            f"equity={r.get('final_equity', 0):>12,.0f}  "
            f"trades={r['closed_trades']:3d}  win={r['win_rate']:.2%}  "
            f"dd={r['max_drawdown']:+.4f}  sharpe={r['sharpe_like']:+.3f}"
        )
    print("=== AGGREGATE ===")
    for k, v in report["aggregate"].items():
        print(f"  {k}: {v}")


async def _run_unified(args: argparse.Namespace) -> None:
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        logger.error("no tickers provided")
        return
    logger.info(f"unified backtest: {len(tickers)} tickers, shared capital={args.capital:,.0f}")

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

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    print("=== UNIFIED BACKTEST REPORT ===")
    for k, v in report.items():
        if k == "per_ticker":
            print("  per_ticker:")
            for ticker, stats in v.items():
                print(f"    {ticker}: {stats}")
        elif isinstance(v, float) and abs(v) >= 1000:
            print(f"  {k}: {v:,.0f}")
        else:
            print(f"  {k}: {v}")


async def amain(args: argparse.Namespace) -> None:
    if args.unified:
        await _run_unified(args)
    else:
        await _run_independent(args)


def main() -> None:
    p = argparse.ArgumentParser(prog="kuromi-multi-backtest")
    p.add_argument("--tickers", default="KRW-BTC,KRW-ETH,KRW-XRP,KRW-SOL")
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
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--unified", action="store_true",
        help="run unified portfolio-level backtest (shared capital) instead of independent per-ticker",
    )
    asyncio.run(amain(p.parse_args()))


if __name__ == "__main__":
    main()
