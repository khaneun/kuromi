from __future__ import annotations

import asyncio
import fnmatch
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

Handler = Callable[["Event"], Awaitable[None]]


@dataclass(slots=True)
class Event:
    topic: str
    payload: Any = None
    source: str = ""
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)
        self._tap: list[Handler] = []

    def subscribe(self, pattern: str, handler: Handler) -> None:
        self._subs[pattern].append(handler)

    def tap(self, handler: Handler) -> None:
        """Receive every event (for Monitor/Dashboard)."""
        self._tap.append(handler)

    async def publish(self, event: Event) -> None:
        handlers: list[Handler] = []
        for pattern, hs in self._subs.items():
            if fnmatch.fnmatchcase(event.topic, pattern):
                handlers.extend(hs)
        handlers.extend(self._tap)
        if handlers:
            await asyncio.gather(
                *(self._safe_call(h, event) for h in handlers), return_exceptions=False
            )

    @staticmethod
    async def _safe_call(handler: Handler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as exc:  # isolate one handler's failure from the bus
            from loguru import logger

            logger.exception(f"handler failed for {event.topic}: {exc}")
