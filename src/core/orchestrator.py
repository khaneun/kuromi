from __future__ import annotations

import asyncio
import signal
from typing import Any, Iterable

from loguru import logger

from src.agents.base import BaseAgent


class Orchestrator:
    def __init__(self, agents: Iterable[BaseAgent]) -> None:
        self._agents = list(agents)
        self._tasks: list[asyncio.Task] = []
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        for agent in self._agents:
            await agent.setup()
        for agent in self._agents:
            self._tasks.append(asyncio.create_task(agent.run(), name=agent.name))
        logger.info(f"orchestrator started {len(self._agents)} agents")

    async def shutdown(self) -> None:
        if self._stopping.is_set():
            return
        self._stopping.set()
        logger.info("orchestrator shutdown requested")
        for agent in self._agents:
            await agent.stop()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("orchestrator stopped")

    def install_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

    async def wait(self) -> None:
        await asyncio.gather(*self._tasks, return_exceptions=True)

    def agent_statuses(self) -> list[dict[str, Any]]:
        statuses: list[dict[str, Any]] = []
        for agent, task in zip(self._agents, self._tasks):
            statuses.append({
                "name": agent.name,
                "stopping": agent.stopping,
                "task_done": task.done() if task else True,
                "task_exception": str(task.exception()) if task.done() and task.exception() else None,
            })
        return statuses

    def get_agent(self, name: str) -> BaseAgent | None:
        for a in self._agents:
            if a.name == name:
                return a
        return None
