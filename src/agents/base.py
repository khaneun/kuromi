from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from loguru import logger

from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, bus: EventBus, state: SharedState) -> None:
        self.bus = bus
        self.state = state
        self._stop = asyncio.Event()

    async def setup(self) -> None:
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

    def log(self, msg: str) -> None:
        logger.info(f"[{self.name}] {msg}")

    async def sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
