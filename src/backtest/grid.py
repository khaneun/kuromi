from __future__ import annotations

import argparse
import asyncio
import itertools
import json
from pathlib import Path
from typing import Any

from loguru import logger

from src.backtest.runner import Backtester, fetch_candles


def _cartesian(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(grid.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*[grid[k] for k in keys])]


def _score(report: dict) -> float:
    """Risk-adjusted: reward return, penalize drawdown, break ties with sharpe."""
    return (
        report["total_return"]
        + 0.5 * report["max_drawdown"]
        + 0.05 * report["sharpe_like"]
    )


async def _run_one(ticker: str, candles: list[dict], point: dict[str, Any]) -> dict:
    bt = Backtester(
        ticker=ticker,
        candles=candles,
        initial_krw=point.get("initial_krw", 1_000_000.0),
        signal_window=point.get("window", 60),
        slippage_bps=point.get("slippage", 5.0),
        decision_threshold=point.get("decision_threshold", 0.5),
        per_trade_risk_pct=point.get("risk_pct", 0.1),
    )
    weights = point.get("strategy_weights")
    if isinstance(weights, dict):
        bt.state.strategy_params["strategy_weights"].update(weights)
    report = await bt.run()
    return {"params": point, "report": report, "score": _score(report)}


async def grid_search(
    ticker: str,
    candles: list[dict],
    grid: dict[str, list[Any]],
    top_k: int = 5,
    concurrency: int = 4,
) -> list[dict]:
    points = _cartesian(grid)
    logger.info(f"grid search: {len(points)} combinations")
    sem = asyncio.Semaphore(concurrency)

    async def worker(p: dict) -> dict:
        async with sem:
            return await _run_one(ticker, candles, p)

    results = await asyncio.gather(*(worker(p) for p in points))
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def _to_seed(params: dict[str, Any]) -> dict[str, Any]:
    """Shape best-point params so Improver can publish them directly."""
    seed: dict[str, Any] = {}
    if "decision_threshold" in params:
        seed["decision_threshold"] = params["decision_threshold"]
    if isinstance(params.get("strategy_weights"), dict):
        seed["strategy_weights"] = params["strategy_weights"]
    return seed


async def amain(args: argparse.Namespace) -> None:
    candles = await fetch_candles(args.ticker, args.minutes, args.count)
    if not candles:
        logger.error("no candles")
        return

    grid: dict[str, list[Any]] = {
        "decision_threshold": [0.3, 0.4, 0.5, 0.6, 0.7],
        "window": [30, 60, 120],
        "slippage": [args.slippage],
    }
    if args.sweep_weights:
        grid["strategy_weights"] = [
            {"momentum": w_m, "mean_reversion": w_r}
            for w_m in (0.5, 1.0, 1.5)
            for w_r in (0.5, 1.0, 1.5)
        ]

    top = await grid_search(
        args.ticker, candles, grid, top_k=args.top, concurrency=args.jobs
    )

    print("=== GRID TOP ===")
    for i, row in enumerate(top, 1):
        print(f"#{i} score={row['score']:.4f}  params={row['params']}")
        print(f"    report={row['report']}")

    if args.out and top:
        seed = _to_seed(top[0]["params"])
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(seed, indent=2))
        print(f"\nseed written: {out}  payload={seed}")


def main() -> None:
    p = argparse.ArgumentParser(prog="kuromi-grid")
    p.add_argument("--ticker", default="KRW-BTC")
    p.add_argument(
        "--minutes", type=int, default=5, choices=[1, 3, 5, 10, 15, 30, 60, 240]
    )
    p.add_argument("--count", type=int, default=200)
    p.add_argument("--slippage", type=float, default=5.0)
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--sweep-weights", action="store_true", help="expand grid with weight combos")
    p.add_argument("--out", default="data/improver_seed.json")
    asyncio.run(amain(p.parse_args()))


if __name__ == "__main__":
    main()
