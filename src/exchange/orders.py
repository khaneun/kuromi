from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OrderState(str, Enum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL: frozenset[OrderState] = frozenset(
    {OrderState.FILLED, OrderState.CANCELLED, OrderState.FAILED}
)


@dataclass
class Order:
    client_id: str
    ticker: str
    side: str
    price: float
    volume: float | None = None
    uuid: str | None = None
    state: OrderState = OrderState.SUBMITTED
    executed_volume: float = 0.0
    remaining_volume: float = 0.0
    avg_fill_price: float = 0.0  # Upbit 체결 평균가 (price는 요청가)
    reason: str = ""
    retry_count: int = 0
    cancel_attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_payload(self) -> dict:
        return {
            "client_id": self.client_id,
            "uuid": self.uuid,
            "ticker": self.ticker,
            "side": self.side,
            "price": self.avg_fill_price or self.price,  # 실제 체결가 우선
            "volume": self.volume,
            "state": self.state.value,
            "executed_volume": self.executed_volume,
            "remaining_volume": self.remaining_volume,
            "reason": self.reason,
        }
