from __future__ import annotations

import asyncio
import json
import subprocess
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.core.event_bus import Event, EventBus
from src.core.state import SharedState

if TYPE_CHECKING:
    from config.runtime_config import RuntimeConfig
    from src.agents.persistence import PersistenceAgent
    from src.core.equity_tracker import EquityTracker
    from src.core.orchestrator import Orchestrator


AGENT_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "market_data": ("시장 데이터", "실시간 시세 수집 (Upbit WebSocket + REST)"),
    "signal": ("시그널 생성", "기술적 지표 8종 계산 및 정규화 시그널 발행"),
    "derivative": ("파생상품 지표", "펀딩비·OI·김치프리미엄 수집 (Binance)"),
    "onchain": ("온체인 분석", "Exchange netflow·NVT·MVRV 수집 (CryptoQuant)"),
    "strategy": ("전략 앙상블", "7개 전략 가중 투표 → 매매 의사결정"),
    "risk": ("리스크 관리", "포지션 한도·일일 손실 한도·실자본 사이징"),
    "persistence": ("데이터 저장", "주문·거래·시그널 DB 영속화 + 크래시 복구"),
    "execution": ("주문 실행", "Upbit 주문 제출·상태 머신·타임아웃 취소"),
    "portfolio": ("포트폴리오", "실자본 추적·Upbit 계좌 동기화·Equity 기록"),
    "performance": ("성과 분석", "승률·PnL·샤프비율·Max Drawdown 산출"),
    "improver": ("파라미터 최적화", "LLM 성과 분석 → 전략 파라미터 자동 개선"),
    "notifier": ("알림 발송", "주요 이벤트 Telegram 전달"),
    "monitor": ("시스템 감시", "데이터 중단 감지·자동 정지"),
}


class ParamsUpdate(BaseModel):
    params: dict[str, Any]


class ImproverPrompt(BaseModel):
    system_prompt: str


def create_app(
    bus: EventBus,
    state: SharedState,
    persistence: "PersistenceAgent | None" = None,
    orchestrator: "Orchestrator | None" = None,
    equity_tracker: "EquityTracker | None" = None,
    runtime_cfg: "RuntimeConfig | None" = None,
) -> FastAPI:
    app = FastAPI(title="Kuromi")
    clients: set[WebSocket] = set()

    _LOG_TOPICS = {
        "order.submitted", "order.accepted", "order.filled",
        "order.cancelled", "order.failed",
        "trade.approved",
        "system.halt", "system.alert", "system.resume",
        "improver.params_updated",
        "improver.ticker_advice",
        "trade.closed",
        "performance.report",
    }
    _CRITICAL_REJECT = {"system_halted", "daily_loss_limit"}

    _uvicorn_loop: asyncio.AbstractEventLoop | None = None

    @app.on_event("startup")
    async def _capture_loop() -> None:
        nonlocal _uvicorn_loop
        _uvicorn_loop = asyncio.get_running_loop()

    async def _do_broadcast(msg: str) -> None:
        dead: list[WebSocket] = []
        for ws in list(clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

    async def broadcast(event: Event) -> None:
        if not clients:
            return
        if event.topic == "trade.rejected":
            reason = event.payload.get("reason", "") if isinstance(event.payload, dict) else ""
            if reason not in _CRITICAL_REJECT:
                return
        elif event.topic not in _LOG_TOPICS:
            return
        msg = json.dumps(
            {"topic": event.topic, "source": event.source, "payload": _jsonable(event.payload)}
        )
        # uvicorn이 별도 스레드에서 실행될 경우, 해당 루프에 WebSocket 전송을 위임
        if _uvicorn_loop is not None and _uvicorn_loop.is_running():
            asyncio.run_coroutine_threadsafe(_do_broadcast(msg), _uvicorn_loop)
        else:
            await _do_broadcast(msg)

    bus.tap(broadcast)

    # ── 페이지 ──
    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        from src.dashboard.frontend import INDEX_HTML
        return INDEX_HTML

    # ── 조회 API ──
    @app.get("/api/state")
    async def get_state() -> dict:
        snap = state.capital.snapshot(state.last_prices)
        # C: 티커별 시그널 요약 (avg + 개별값)
        _SIG_KEYS = ["momentum", "zscore", "rsi", "bollinger_pct_b", "macd_hist", "stochastic_k", "obv_slope"]
        signals_summary: dict[str, dict] = {}
        for ticker, sigs in state.last_signals.items():
            vals = [sigs[k] for k in _SIG_KEYS if k in sigs]
            avg = round(sum(vals) / len(vals), 3) if vals else 0.0
            signals_summary[ticker] = {"avg": avg, **{k: round(sigs[k], 3) for k in _SIG_KEYS if k in sigs}}
        return {
            "halted": state.halted,
            "dry_run": _get_dry_run(),
            "daily_pnl": state.daily_pnl,
            "last_prices": state.last_prices,
            "capital": snap,
            "last_signals": signals_summary,
        }

    @app.get("/api/agents")
    async def get_agents() -> list[dict]:
        if not orchestrator:
            return []
        statuses = orchestrator.agent_statuses()
        for s in statuses:
            desc = AGENT_DESCRIPTIONS.get(s["name"])
            if desc:
                s["label"] = desc[0]
                s["description"] = desc[1]
        return statuses

    @app.get("/api/agents/{name}")
    async def get_agent_detail(name: str) -> dict:
        if not orchestrator:
            return {"error": "no_orchestrator"}
        agent = orchestrator.get_agent(name)
        if not agent:
            return {"error": "not_found"}
        desc = AGENT_DESCRIPTIONS.get(name, ("", ""))
        result: dict[str, Any] = {
            "name": name,
            "label": desc[0],
            "description": desc[1],
            "metrics": agent.metrics.to_dict(),
            "stopping": agent.stopping,
        }
        if name == "improver" and hasattr(agent, "feedback_log"):
            result["feedback_log"] = agent.feedback_log()
        return result

    @app.get("/api/equity")
    async def get_equity(last: int = Query(500, ge=1, le=8640)) -> list[dict]:
        if not equity_tracker:
            return []
        return equity_tracker.to_list(last_n=last)

    @app.get("/api/orders")
    async def get_orders(
        limit: int = Query(20, ge=1, le=200),
        state_filter: str | None = Query(None, alias="state"),
    ) -> list[dict]:
        if not persistence:
            return []
        return await persistence.query_orders(limit=limit, state=state_filter)

    @app.get("/api/trades")
    async def get_trades(limit: int = Query(20, ge=1, le=200)) -> list[dict]:
        if not persistence:
            return []
        return await persistence.query_trades(limit=limit)

    @app.get("/api/improver/log")
    async def get_improver_log() -> list[dict]:
        if not orchestrator:
            return []
        agent = orchestrator.get_agent("improver")
        if agent and hasattr(agent, "feedback_log"):
            return agent.feedback_log()
        return []

    @app.get("/api/improver/ticker-advice")
    async def get_ticker_advice() -> dict:
        """B: ImproverAgent의 최신 티커 편입/편출 추천."""
        if not orchestrator:
            return {"add": [], "remove": []}
        agent = orchestrator.get_agent("improver")
        if agent and hasattr(agent, "ticker_advice"):
            return agent.ticker_advice()
        return {"add": [], "remove": []}

    @app.get("/api/logs")
    async def get_logs(lines: int = Query(100, ge=1, le=1000)) -> dict:
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), "logs/kuromi.log"],
                capture_output=True, text=True, timeout=5,
            )
            return {"lines": result.stdout.splitlines()}
        except Exception:
            return {"lines": []}

    # ── Runtime Config API ──
    @app.get("/api/config")
    async def get_config() -> dict:
        if not runtime_cfg:
            return {}
        return runtime_cfg.model_dump()

    @app.put("/api/config")
    async def update_config(body: dict[str, Any]) -> dict:
        if not runtime_cfg:
            return {"error": "no_runtime_cfg"}
        runtime_cfg.update_and_save(body)
        applied: list[str] = []
        if orchestrator:
            applied = runtime_cfg.apply(orchestrator, state, bus)
        return {"status": "saved", "applied": applied, "config": runtime_cfg.model_dump()}

    # ── 제어 API ──
    @app.post("/api/control/halt")
    async def halt() -> dict:
        state.halted = True
        await bus.publish(Event(topic="system.halt", payload={"source": "dashboard"}))
        return {"status": "halted"}

    @app.post("/api/control/resume")
    async def resume() -> dict:
        state.halted = False
        await bus.publish(Event(topic="system.resume", payload={"source": "dashboard"}))
        return {"status": "resumed"}

    @app.post("/api/control/liquidate")
    async def liquidate() -> dict:
        positions = state.capital.positions
        if not positions:
            return {"status": "no_positions"}
        count = 0
        for ticker, pos in positions.items():
            price = state.last_prices.get(ticker, pos.entry_price)
            await bus.publish(
                Event(
                    topic="trade.approved",
                    payload={
                        "ticker": ticker,
                        "side": "sell",
                        "price": price,
                        "volume": pos.volume,
                        "reason": "emergency_liquidation",
                    },
                    source="dashboard",
                )
            )
            count += 1
        return {"status": "liquidating", "positions": count}

    @app.post("/api/control/params")
    async def update_params(body: ParamsUpdate) -> dict:
        await bus.publish(
            Event(topic="improver.params_updated", payload=body.params, source="dashboard")
        )
        return {"status": "applied", "keys": list(body.params.keys())}

    @app.post("/api/control/improver-prompt")
    async def update_improver_prompt(body: ImproverPrompt) -> dict:
        if not orchestrator:
            return {"error": "no_orchestrator"}
        agent = orchestrator.get_agent("improver")
        if agent and hasattr(agent, "SYSTEM_PROMPT"):
            agent.SYSTEM_PROMPT = body.system_prompt
            return {"status": "updated", "length": len(body.system_prompt)}
        return {"error": "improver_not_found"}

    @app.post("/api/control/system-stop")
    async def system_stop() -> dict:
        state.halted = True
        await bus.publish(Event(topic="system.halt", payload={"source": "dashboard", "action": "ec2_stop"}))
        asyncio.get_running_loop().call_later(3.0, _stop_system)
        return {"status": "stopping_in_3s"}

    # ── WebSocket ──
    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        clients.add(ws)
        try:
            while True:
                await asyncio.sleep(30)
                await ws.send_text(json.dumps({"topic": "heartbeat"}))
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(ws)

    # ── 헬퍼 ──
    def _get_dry_run() -> bool:
        if runtime_cfg:
            return runtime_cfg.dry_run
        if orchestrator:
            agent = orchestrator.get_agent("execution")
            if agent and hasattr(agent, "dry_run"):
                return agent.dry_run
        return True

    def _stop_system() -> None:
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)

    return app


def _jsonable(obj: object) -> object:
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)
