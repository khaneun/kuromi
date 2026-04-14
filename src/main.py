from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import uvicorn
from loguru import logger

from config.runtime_config import RuntimeConfig
from config.settings import get_settings
from src.agents.derivative import DerivativeAgent
from src.agents.execution import ExecutionAgent
from src.agents.improver import ImproverAgent
from src.agents.market_data import MarketDataAgent
from src.agents.monitor import MonitorAgent
from src.agents.notifier import NotifierAgent
from src.agents.onchain import OnchainAgent
from src.agents.performance import PerformanceAgent
from src.agents.persistence import PersistenceAgent
from src.agents.portfolio import PortfolioAgent
from src.agents.risk import RiskAgent
from src.agents.signal import SignalAgent
from src.agents.strategy import StrategyAgent
from src.core.equity_tracker import EquityTracker
from src.core.event_bus import EventBus
from src.core.orchestrator import Orchestrator
from src.core.state import SharedState
from src.dashboard.app import create_app
from src.exchange.binance_client import BinanceClient
from src.exchange.onchain_client import CryptoQuantClient
from src.exchange.upbit_client import UpbitClient
from src.storage.db import init_db
from src.telegram.bot import TelegramBot


def _configure_logging(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level, enqueue=True)
    Path("logs").mkdir(exist_ok=True)
    logger.add("logs/kuromi.log", level=level, rotation="20 MB", retention="14 days", enqueue=True)


async def amain() -> None:
    settings = get_settings()
    Path("data").mkdir(exist_ok=True)

    rcfg = RuntimeConfig.load_or_create(
        "data/runtime_config.json",
        defaults=settings.initial_runtime_defaults(),
    )
    _configure_logging(rcfg.log_level)

    bus = EventBus()
    state = SharedState()
    equity_tracker = EquityTracker()

    if settings.initial_capital_krw > 0:
        state.capital.set_krw(settings.initial_capital_krw)
        state.capital._initial_krw = settings.initial_capital_krw

    session_factory = await init_db(settings.database_url)
    persistence = PersistenceAgent(bus, state, session_factory)

    upbit = UpbitClient(settings.upbit_access_key, settings.upbit_secret_key)
    binance = BinanceClient()
    cryptoquant = CryptoQuantClient(api_key=settings.cryptoquant_api_key)

    telegram = TelegramBot(
        settings.telegram_bot_token,
        settings.telegram_admin_chat_id,
        bus,
        state,
        persistence=persistence,
        dashboard_url=(
            settings.dashboard_public_url
            or f"http://localhost:{settings.dashboard_port}"
        ),
    )
    await telegram.start()

    tickers = rcfg.trading_tickers

    agents = [
        MarketDataAgent(bus, state, upbit, tickers, poll_sec=1.0),
        SignalAgent(bus, state, window=60),
        DerivativeAgent(
            bus, state, binance, tickers,
            poll_sec=30.0, usdkrw=rcfg.usdkrw_rate,
        ),
        OnchainAgent(bus, state, cryptoquant, tickers, poll_sec=300.0),
        StrategyAgent(bus, state),
        RiskAgent(
            bus,
            state,
            max_positions=rcfg.max_concurrent_positions,
            per_trade_risk_pct=rcfg.per_trade_risk_pct,
            daily_loss_limit_pct=rcfg.daily_loss_limit_pct,
            min_profit_pct=rcfg.min_profit_pct,
            stop_loss_pct=rcfg.stop_loss_pct,
        ),
        persistence,
        ExecutionAgent(
            bus, state, upbit,
            dry_run=rcfg.dry_run,
            persistence=persistence,
        ),
        PortfolioAgent(
            bus, state, client=upbit,
            equity_tracker=equity_tracker,
            live=(not rcfg.dry_run),
            trading_tickers=tickers,
        ),
        PerformanceAgent(bus, state, persistence=persistence),
        ImproverAgent(
            bus,
            state,
            api_key=settings.anthropic_api_key,
            cadence_sec=rcfg.improver_cadence_sec,
            seed_file=settings.improver_seed_file,
            upbit=upbit,
        ),
        NotifierAgent(bus, state, send=telegram.send),
        MonitorAgent(bus, state),
    ]

    orchestrator = Orchestrator(agents)
    orchestrator.install_signal_handlers(asyncio.get_running_loop())
    await orchestrator.start()

    telegram.orchestrator = orchestrator

    # RuntimeConfig 초기값을 state에도 반영
    rcfg.apply(orchestrator, state, bus)

    app = create_app(
        bus, state,
        persistence=persistence,
        orchestrator=orchestrator,
        equity_tracker=equity_tracker,
        runtime_cfg=rcfg,
    )

    # uvicorn을 별도 스레드에서 실행 — 에이전트 이벤트 루프와 분리
    import threading
    dashboard_cfg = uvicorn.Config(
        app,
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        log_level="info",
    )
    dashboard = uvicorn.Server(dashboard_cfg)
    # 비-메인 스레드에서는 signal handler 설치가 불가능하므로 무력화
    dashboard.install_signal_handlers = lambda: None  # type: ignore[method-assign]

    def _run_dashboard() -> None:
        import sys
        import traceback as _tb
        print("DASHBOARD: starting", flush=True, file=sys.stderr)
        try:
            asyncio.run(dashboard.serve())
            print("DASHBOARD: serve() returned normally", flush=True, file=sys.stderr)
        except BaseException as exc:
            print(f"DASHBOARD: CRASH [{type(exc).__name__}]: {exc}", flush=True, file=sys.stderr)
            print(_tb.format_exc(), flush=True, file=sys.stderr)
        finally:
            print("DASHBOARD: EXITED", flush=True, file=sys.stderr)

    dashboard_thread = threading.Thread(target=_run_dashboard, name="dashboard", daemon=True)
    dashboard_thread.start()

    try:
        await orchestrator.wait()
    finally:
        dashboard.should_exit = True
        dashboard_thread.join(timeout=5.0)
        await telegram.stop()
        await binance.aclose()
        await cryptoquant.aclose()
        await upbit.aclose()


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
