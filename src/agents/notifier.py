from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class NotifierAgent(BaseAgent):
    """Bridges the bus to the Telegram bot. The bot owns network I/O;
    this agent only decides what to forward and how to format it."""

    name = "notifier"

    # trade.rejected는 이 reason 목록만 발송 (routine rejection 제외)
    CRITICAL_REJECT_REASONS = {"system_halted", "daily_loss_limit"}

    def __init__(self, bus: EventBus, state: SharedState, send) -> None:
        super().__init__(bus, state)
        self._send = send  # async callable(text: str) -> None
        self.tap(self._on_any)

    async def run(self) -> None:
        await self._stop.wait()

    async def _on_any(self, event: Event) -> None:
        text = self._format(event)
        if text:
            await self._send(text)

    def _format(self, event: Event) -> str | None:
        topic = event.topic
        p = event.payload or {}

        if topic == "order.failed":
            ticker = p.get("ticker", "?")
            reason = p.get("reason", "unknown")
            return f"💥 <b>주문 실패</b> [{ticker}]\n사유: {reason}"

        if topic == "order.cancelled":
            ticker = p.get("ticker", "?")
            reason = p.get("reason", "timeout")
            return f"❌ <b>주문 취소</b> [{ticker}]\n사유: {reason}"

        if topic == "trade.rejected":
            reason = p.get("reason", "") if isinstance(p, dict) else ""
            if reason not in self.CRITICAL_REJECT_REASONS:
                return None
            ticker = p.get("ticker", "?") if isinstance(p, dict) else "?"
            icons = {"system_halted": "🛑", "daily_loss_limit": "⛔"}
            icon = icons.get(reason, "⚠️")
            return f"{icon} <b>거래 거절</b> [{ticker}]\n사유: {reason}"

        if topic == "system.halt":
            source = p.get("source", "?") if isinstance(p, dict) else "?"
            return f"🛑 <b>시스템 정지</b>\n출처: {source}"

        if topic == "system.resume":
            return "✅ <b>매매 재개</b>"

        if topic == "system.alert":
            msg = p.get("message", str(p)) if isinstance(p, dict) else str(p)
            return f"⚠️ <b>시스템 알림</b>\n{msg}"

        if topic == "improver.params_updated":
            if not isinstance(p, dict) or not p:
                return "🤖 <b>Improver 파라미터 업데이트</b>\n변경 없음"
            lines = "\n".join(
                f"  <code>{k}</code>: <code>{v}</code>"
                for k, v in p.items()
            )
            return f"🤖 <b>Improver 파라미터 업데이트</b> ({len(p)}건)\n{lines}"

        return None
