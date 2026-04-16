from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState
from src.exchange.orders import TERMINAL, Order, OrderState
from src.exchange.upbit_client import UpbitClient

if TYPE_CHECKING:
    from src.agents.persistence import PersistenceAgent


STATE_TOPIC: dict[OrderState, str] = {
    OrderState.SUBMITTED: "order.submitted",
    OrderState.ACCEPTED: "order.accepted",
    OrderState.PARTIALLY_FILLED: "order.partially_filled",
    OrderState.FILLED: "order.filled",
    OrderState.CANCELLED: "order.cancelled",
    OrderState.FAILED: "order.failed",
}

# Upbit 호가 단위 (가격 구간별 tick size)
_UPBIT_TICKS: list[tuple[float, float]] = [
    (2_000_000, 1_000),
    (1_000_000, 500),
    (500_000, 100),
    (100_000, 50),
    (10_000, 10),
    (1_000, 5),
    (100, 1),
    (10, 0.1),
    (0, 0.01),
]


def _tick_round(price: float) -> float:
    """가격을 Upbit 호가 단위에 맞게 반올림 (400 Bad Request 방지)."""
    for threshold, step in _UPBIT_TICKS:
        if price >= threshold:
            return round(round(price / step) * step, 10)
    return round(price, 2)


class ExecutionAgent(BaseAgent):
    """Owns the order state machine. On startup, recovers in-flight orders
    from the database. Submits orders on trade.approved, polls Upbit for
    status, emits events per transition."""

    name = "execution"

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        client: UpbitClient,
        dry_run: bool = True,
        poll_sec: float = 2.0,
        timeout_sec: float = 300.0,
        persistence: "PersistenceAgent | None" = None,
    ) -> None:
        super().__init__(bus, state)
        self.client = client
        self.dry_run = dry_run
        self.poll_sec = poll_sec
        self.timeout_sec = timeout_sec
        self.persistence = persistence
        self._active: dict[str, Order] = {}
        self.subscribe("trade.approved", self._on_approved)

    async def setup(self) -> None:
        if self.dry_run or not self.persistence:
            return
        rows = await self.persistence.load_pending_orders()
        for r in rows:
            if not r.get("uuid"):
                continue
            order = Order(
                client_id=r["client_id"],
                ticker=r["ticker"],
                side=r["side"],
                price=float(r["price"]),
                volume=float(r["volume"]) if r.get("volume") else None,
                uuid=r["uuid"],
                state=OrderState(r["state"]),
                executed_volume=float(r.get("executed_volume", 0)),
                remaining_volume=float(r.get("remaining_volume", 0)),
            )
            self._active[order.uuid] = order
        if rows:
            self.log(f"recovered {len(rows)} in-flight orders from DB")

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.poll_sec)
            for order in list(self._active.values()):
                try:
                    await self._poll(order)
                except Exception as exc:
                    self.log(f"poll error uuid={order.uuid}: {exc}")

    _SLIPPAGE = 0.0005  # 0.05% — 즉시 체결 유도 슬리피지

    async def _on_approved(self, event: Event) -> None:
        intent = event.payload
        ticker = intent["ticker"]
        side = intent["side"]

        # 시그널 가격 대신 현재 시장가 기준으로 호가 설정
        # → 지정가 주문이 시장에서 즉시 체결되도록 유도 (타임아웃 방지)
        raw_price = self.state.last_prices.get(ticker) or float(intent["price"])
        if side == "buy":
            order_price = _tick_round(raw_price * (1 + self._SLIPPAGE))
            # 현재가 기준으로 매수 물량 재계산 (alloc_krw 고정)
            alloc_krw = float(intent.get("alloc_krw") or 0)
            volume = alloc_krw / order_price if order_price > 0 else 0.0
        else:
            order_price = _tick_round(raw_price * (1 - self._SLIPPAGE))
            volume = float(intent.get("volume") or 0)

        if volume <= 0:
            self.log(f"skipping zero-volume intent: {ticker}")
            return

        order = Order(
            client_id=str(uuid.uuid4()),
            ticker=ticker,
            side=side,
            price=order_price,
            volume=volume,
        )
        await self._transition(order, OrderState.SUBMITTED)

        if self.dry_run:
            order.uuid = f"dry-{order.client_id[:8]}"
            order.executed_volume = order.volume
            self.log(
                f"DRY-RUN {order.side} {order.ticker} "
                f"vol={order.volume:.8f} price={order.price:,.0f}"
            )
            await self._transition(order, OrderState.FILLED)
            return

        try:
            result = await self.client.place_order(
                market=order.ticker,
                side=order.side,
                price=order.price,
                volume=order.volume,
            )
            order.uuid = result.get("uuid")
            if not order.uuid:
                raise RuntimeError(f"no uuid in upbit response: {result}")
            self._active[order.uuid] = order
            await self._transition(order, OrderState.ACCEPTED)
        except httpx.HTTPStatusError as exc:
            # 400 응답 바디를 포함해 로깅 (Upbit 에러 코드 확인용)
            body = exc.response.text[:300] if exc.response else ""
            reason = f"HTTP {exc.response.status_code}: {body}"
            order.reason = reason
            perm_errors = ("insufficient", "minimum", "below_min", "잔고", "금액", "400")
            if order.retry_count < 1 and not any(e in reason.lower() for e in perm_errors):
                order.retry_count += 1
                self.log(f"order failed ({reason}), retrying #{order.retry_count} for {ticker}")
                await self._on_approved_retry(order)
            else:
                self.log(f"order permanently failed [{ticker}] {reason}")
                await self._transition(order, OrderState.FAILED)
        except Exception as exc:
            reason = str(exc)
            order.reason = reason
            # 잔고 부족·최소 금액 미달 등 영구 오류는 재시도 없이 즉시 실패
            perm_errors = ("insufficient", "minimum", "below_min", "잔고", "금액")
            if order.retry_count < 1 and not any(e in reason.lower() for e in perm_errors):
                order.retry_count += 1
                self.log(f"order failed ({reason}), retrying #{order.retry_count} for {ticker}")
                await self._on_approved_retry(order)
            else:
                await self._transition(order, OrderState.FAILED)

    async def _on_approved_retry(self, order: Order) -> None:
        """재시도용 내부 메서드. 가격을 최신 시장가로 갱신 후 재발행한다."""
        await asyncio.sleep(2)
        # 재시도 시 가격 재계산
        raw_price = self.state.last_prices.get(order.ticker) or order.price
        if order.side == "buy":
            order.price = _tick_round(raw_price * (1 + self._SLIPPAGE))
        else:
            order.price = _tick_round(raw_price * (1 - self._SLIPPAGE))
        try:
            result = await self.client.place_order(
                market=order.ticker,
                side=order.side,
                price=order.price,
                volume=order.volume,
            )
            order.uuid = result.get("uuid")
            if not order.uuid:
                raise RuntimeError(f"no uuid in retry response: {result}")
            self._active[order.uuid] = order
            await self._transition(order, OrderState.ACCEPTED)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300] if exc.response else ""
            order.reason = f"HTTP {exc.response.status_code}: {body}"
            self.log(f"retry permanently failed [{order.ticker}] {order.reason}")
            await self._transition(order, OrderState.FAILED)
        except Exception as exc:
            order.reason = str(exc)
            await self._transition(order, OrderState.FAILED)

    async def _poll(self, order: Order) -> None:
        if not order.uuid:
            return
        info = await self.client.get_order(order.uuid)
        order.executed_volume = float(info.get("executed_volume") or 0.0)
        order.remaining_volume = float(info.get("remaining_volume") or 0.0)
        upbit_state = info.get("state")

        next_state = order.state
        if upbit_state == "done":
            next_state = OrderState.FILLED
        elif upbit_state == "cancel":
            next_state = OrderState.CANCELLED
        elif upbit_state == "wait":
            next_state = (
                OrderState.PARTIALLY_FILLED if order.executed_volume > 0 else OrderState.ACCEPTED
            )

        age = (datetime.now(timezone.utc) - order.created_at).total_seconds()
        if age > self.timeout_sec and next_state not in TERMINAL:
            next_state = await self._try_cancel(order)

        if next_state != order.state:
            await self._transition(order, next_state)

        if order.state in TERMINAL:
            self._active.pop(order.uuid, None)

    async def _try_cancel(self, order: Order) -> OrderState:
        """타임아웃 주문 취소. 최대 3회 시도, 이후 강제 CANCELLED."""
        order.cancel_attempts += 1
        if order.cancel_attempts > 3:
            self.log(f"force-cancel {order.uuid} (시도 {order.cancel_attempts - 1}회 실패)")
            order.reason = "timeout_force"
            return OrderState.CANCELLED
        try:
            await self.client.cancel_order(order.uuid)
            order.reason = "timeout"
            return OrderState.CANCELLED
        except httpx.HTTPStatusError as exc:
            # 400: 이미 체결·취소된 주문 → 실제 상태 재조회
            body = exc.response.text[:120] if exc.response else ""
            self.log(f"cancel {exc.response.status_code} [{order.cancel_attempts}/3] {order.uuid}: {body}")
            return await self._recheck_state(order)
        except Exception as exc:
            # 네트워크 timeout 등 → 재조회로 상태 확인
            self.log(f"cancel 실패 [{order.cancel_attempts}/3] {order.uuid}: {exc}")
            return await self._recheck_state(order)

    async def _recheck_state(self, order: Order) -> OrderState:
        """취소 실패 후 실제 주문 상태 재조회. 실패 시 현재 상태 유지(다음 poll 재시도)."""
        try:
            recheck = await self.client.get_order(order.uuid)
            actual = recheck.get("state")
            if actual == "done":
                order.executed_volume = float(recheck.get("executed_volume") or 0.0)
                order.remaining_volume = float(recheck.get("remaining_volume") or 0.0)
                return OrderState.FILLED
            if actual == "cancel":
                order.reason = "timeout"
                return OrderState.CANCELLED
        except Exception as exc:
            self.log(f"재조회 실패 {order.uuid}: {exc}")
        return order.state  # 유지 → 다음 poll에서 재시도

    async def _transition(self, order: Order, new_state: OrderState) -> None:
        order.state = new_state
        order.updated_at = datetime.now(timezone.utc)
        topic = STATE_TOPIC[new_state]
        await self.emit(topic, order.to_payload())
