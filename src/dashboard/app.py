from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.core.event_bus import Event, EventBus
from src.core.state import SharedState

if TYPE_CHECKING:
    from src.agents.persistence import PersistenceAgent
    from src.core.equity_tracker import EquityTracker
    from src.core.orchestrator import Orchestrator


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
) -> FastAPI:
    app = FastAPI(title="Kuromi")
    clients: set[WebSocket] = set()

    async def broadcast(event: Event) -> None:
        if not clients:
            return
        msg = json.dumps(
            {"topic": event.topic, "source": event.source, "payload": _jsonable(event.payload)}
        )
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

    bus.tap(broadcast)

    # ---------- views ----------
    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        from src.dashboard.frontend import INDEX_HTML
        return INDEX_HTML

    # ---------- read APIs ----------
    @app.get("/api/state")
    async def get_state() -> dict:
        snap = state.capital.snapshot(state.last_prices)
        return {
            "halted": state.halted,
            "dry_run": _get_dry_run(),
            "daily_pnl": state.daily_pnl,
            "last_prices": state.last_prices,
            "strategy_params": state.strategy_params,
            "capital": snap,
        }

    @app.get("/api/agents")
    async def get_agents() -> list[dict]:
        if not orchestrator:
            return []
        return orchestrator.agent_statuses()

    @app.get("/api/equity")
    async def get_equity(last: int = Query(500, ge=1, le=8640)) -> list[dict]:
        if not equity_tracker:
            return []
        return equity_tracker.to_list(last_n=last)

    @app.get("/api/signals")
    async def get_signals() -> dict:
        return state.strategy_params.get("_last_signals", {})

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

    # ---------- control APIs ----------
    @app.post("/api/control/halt")
    async def halt() -> dict:
        state.halted = True
        await bus.publish(Event(topic="system.halt", payload={"source": "dashboard"}))
        return {"status": "halted"}

    @app.post("/api/control/resume")
    async def resume() -> dict:
        state.halted = False
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

    @app.post("/api/control/dry-run")
    async def toggle_dry_run() -> dict:
        if not orchestrator:
            return {"error": "no_orchestrator"}
        agent = orchestrator.get_agent("execution")
        if agent and hasattr(agent, "dry_run"):
            agent.dry_run = not agent.dry_run
            return {"dry_run": agent.dry_run}
        return {"error": "execution_agent_not_found"}

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

    # ---------- WebSocket ----------
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

    # ---------- helpers ----------
    def _get_dry_run() -> bool:
        if orchestrator:
            agent = orchestrator.get_agent("execution")
            if agent and hasattr(agent, "dry_run"):
                return agent.dry_run
        return True

    return app


def _jsonable(obj: object) -> object:
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)
