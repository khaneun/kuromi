from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod

from loguru import logger

from src.core.agent_metrics import AgentMetrics
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, bus: EventBus, state: SharedState) -> None:
        self.bus = bus
        self.state = state
        self._stop = asyncio.Event()
        self.metrics = AgentMetrics()

    async def setup(self) -> None:
        self.metrics.started_at = time.time()
        return None

    @abstractmethod
    async def run(self) -> None: ...

    async def stop(self) -> None:
        self._stop.set()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    async def emit(self, topic: str, payload: object = None) -> None:
        await self.bus.publish(Event(topic=topic, payload=payload, source=self.name))

    def subscribe(self, pattern: str, handler) -> None:
        """Metrics-tracked subscription wrapper."""
        import functools

        @functools.wraps(handler)
        async def _tracked(event):
            try:
                await handler(event)
                self.metrics.record_success()
            except Exception as exc:
                self.metrics.record_failure(str(exc))
                raise

        self.bus.subscribe(pattern, _tracked)

    def tap(self, handler) -> None:
        """Metrics-tracked tap wrapper."""
        import functools

        @functools.wraps(handler)
        async def _tracked(event):
            try:
                await handler(event)
                self.metrics.record_success()
            except Exception as exc:
                self.metrics.record_failure(str(exc))
                raise

        self.bus.tap(_tracked)

    def log(self, msg: str) -> None:
        logger.info(f"[{self.name}] {msg}")

    async def sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
