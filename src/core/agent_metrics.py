from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class AgentMetrics:
    started_at: float = 0.0
    events_processed: int = 0
    events_success: int = 0
    events_failed: int = 0
    last_activity_ts: float = 0.0
    last_error: str | None = None
    last_error_ts: float | None = None

    def record_success(self) -> None:
        self.events_processed += 1
        self.events_success += 1
        self.last_activity_ts = time.time()

    def record_failure(self, error: str) -> None:
        self.events_processed += 1
        self.events_failed += 1
        now = time.time()
        self.last_activity_ts = now
        self.last_error = error
        self.last_error_ts = now

    @property
    def success_rate(self) -> float:
        return self.events_success / self.events_processed if self.events_processed > 0 else 1.0

    @property
    def uptime_sec(self) -> float:
        return time.time() - self.started_at if self.started_at > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "events_processed": self.events_processed,
            "events_success": self.events_success,
            "events_failed": self.events_failed,
            "success_rate": round(self.success_rate, 4),
            "uptime_sec": round(self.uptime_sec, 1),
            "last_activity_ts": self.last_activity_ts,
            "last_error": self.last_error,
            "last_error_ts": self.last_error_ts,
        }
