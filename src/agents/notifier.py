from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.event_bus import Event, EventBus
from src.core.state import SharedState


class NotifierAgent(BaseAgent):
    """Bridges the bus to the Telegram bot. The bot owns network I/O;
    this agent only decides what to forward and how to format it."""

    name = "notifier"

    # trade.rejected는 이 reason 목록만 발송 (routine rejection 제외)
    CRITICAL_REJECT_REASONS = {"system_halted"}

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

    @staticmethod
    def _sym(ticker: str) -> str:
        """KRW- 프리픽스 제거 (표시용)."""
        return (ticker or "?").replace("KRW-", "")

    def _format(self, event: Event) -> str | None:
        topic = event.topic
        p = event.payload or {}

        if topic == "order.failed":
            sym = self._sym(p.get("ticker", "?"))
            reason = p.get("reason", "unknown")
            # 잔고 부족은 정상 케이스 — 알림 불필요
            if any(kw in reason.lower() for kw in ("insufficient", "잔고", "부족")):
                return None
            return f"💥 <b>주문 실패</b> [{sym}]\n사유: {reason}"

        if topic == "order.cancelled":
            sym = self._sym(p.get("ticker", "?"))
            reason = p.get("reason", "")
            side = p.get("side", "")
            # 매도 주문 시간 경과 철회 — 오류 아닌 정보성 알림
            if side == "sell" and "시간경과" in reason:
                return f"📤 <b>매도 철회</b> [{sym}]\n시간 경과로 주문을 철회합니다. 조건 재평가 대기"
            return f"❌ <b>주문 취소</b> [{sym}]\n사유: {reason or 'timeout'}"

        if topic == "trade.rejected":
            reason = p.get("reason", "") if isinstance(p, dict) else ""
            if reason not in self.CRITICAL_REJECT_REASONS:
                return None
            sym = self._sym(p.get("ticker", "?") if isinstance(p, dict) else "?")
            icons = {"system_halted": "🛑"}
            icon = icons.get(reason, "⚠️")
            return f"{icon} <b>거래 거절</b> [{sym}]\n사유: {reason}"

        if topic == "system.halt":
            source = p.get("source", "?") if isinstance(p, dict) else "?"
            return f"🛑 <b>시스템 정지</b>\n출처: {source}"

        if topic == "system.resume":
            return "✅ <b>매매 재개</b>"

        if topic == "system.alert":
            msg = p.get("message", str(p)) if isinstance(p, dict) else str(p)
            return f"⚠️ <b>시스템 알림</b>\n{msg}"


        return None
