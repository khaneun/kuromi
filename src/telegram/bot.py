from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from src.core.event_bus import Event, EventBus
from src.core.state import SharedState

if TYPE_CHECKING:
    from src.agents.persistence import PersistenceAgent
    from src.core.orchestrator import Orchestrator

# ──────────────────────────────────────────
HELP_TEXT = """
<b>📋 Kuromi 명령어 목록</b>

<b>📊 조회</b>
/status      — 자본·포지션 스냅샷
/pnl         — 손익 요약
/positions   — 포지션 상세
/orders      — 최근 주문 10건
/trades      — 최근 체결 10건
/strategies  — 전략 파라미터
/perf        — 성과 지표 (win rate, sharpe)
/agents      — Agent 상태
/dashboard   — 대시보드 링크

<b>⚙️ 제어</b>
/pause       — 매매 일시 정지 (= /halt)
/resume      — 매매 재개 (= /start)
/dryrun      — Dry-run 모드 토글
/liquidate   — 긴급 전량 청산 (확인 필요)
""".strip()


class TelegramBot:
    """Telegram 제어 플레인.

    생성자 파라미터:
      orchestrator  — dry-run 토글·liquidate·agents 조회에 필요
      dashboard_url — /dashboard 명령에 표시할 URL
    """

    def __init__(
        self,
        token: str,
        admin_chat_id: str,
        bus: EventBus,
        state: SharedState,
        persistence: "PersistenceAgent | None" = None,
        orchestrator: "Orchestrator | None" = None,
        dashboard_url: str = "",
    ) -> None:
        self.token = token
        self.admin_chat_id = str(admin_chat_id)
        self.bus = bus
        self.state = state
        self.persistence = persistence
        self.orchestrator = orchestrator
        self.dashboard_url = dashboard_url
        self.app: Application | None = None

    # ──────────────────────────────────────────
    # lifecycle
    # ──────────────────────────────────────────

    async def start(self) -> None:
        if not self.token:
            logger.warning("telegram token missing; bot disabled")
            return
        self.app = Application.builder().token(self.token).build()

        commands = [
            ("help",      self._help),
            ("status",    self._status),
            ("pnl",       self._pnl),
            ("positions", self._positions),
            ("orders",    self._orders),
            ("trades",    self._trades),
            ("strategies", self._strategies),
            ("perf",      self._perf),
            ("agents",    self._agents),
            ("dashboard", self._dashboard),
            ("halt",      self._halt),
            ("pause",     self._halt),
            ("stop",      self._halt),
            ("resume",    self._resume),
            ("start",     self._resume),
            ("dryrun",    self._dryrun),
            ("liquidate", self._liquidate),
            ("params",    self._strategies),  # backward compat
        ]
        for cmd, handler in commands:
            self.app.add_handler(CommandHandler(cmd, handler))

        # 인라인 키보드 콜백 (liquidate 확인)
        self.app.add_handler(CallbackQueryHandler(self._callback))

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("telegram bot started")

    async def stop(self) -> None:
        if not self.app:
            return
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send(self, text: str) -> None:
        if not self.app or not self.admin_chat_id:
            return
        await self.app.bot.send_message(
            chat_id=self.admin_chat_id,
            text=text[:4000],
            parse_mode=ParseMode.HTML,
        )

    def _authorized(self, update: Update) -> bool:
        return str(update.effective_chat.id) == self.admin_chat_id

    async def _reply(self, update: Update, text: str, **kwargs: Any) -> None:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, **kwargs)

    # ──────────────────────────────────────────
    # 조회 명령어
    # ──────────────────────────────────────────

    async def _help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        await self._reply(update, HELP_TEXT)

    async def _status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        cap = self.state.capital.snapshot(self.state.last_prices)
        icon = "🛑" if self.state.halted else "✅"
        pos_list = list(cap["positions"].keys())
        lines = [
            f"{icon} <b>상태</b>: {'정지' if self.state.halted else '운영중'}",
            f"💰 자본: <code>{cap['total_equity']:,.0f} KRW</code>",
            f"💵 가용: <code>{cap['available_krw']:,.0f} KRW</code>",
            f"📈 미실현: <code>{cap['unrealized_pnl']:+,.0f}</code>",
            f"📊 실현: <code>{cap['realized_pnl']:+,.0f}</code>",
            f"📉 수익률: <code>{cap['total_return_pct']:+.2%}</code>",
            f"📦 포지션: {pos_list if pos_list else '없음'}",
        ]
        await self._reply(update, "\n".join(lines))

    async def _pnl(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        cap = self.state.capital.snapshot(self.state.last_prices)
        total_pnl = cap["realized_pnl"] + cap["unrealized_pnl"]
        sign = "📈" if total_pnl >= 0 else "📉"
        lines = [
            "<b>💹 손익 현황</b>",
            f"{sign} 총 PnL: <code>{total_pnl:+,.0f} KRW</code>",
            f"  ├ 실현: <code>{cap['realized_pnl']:+,.0f}</code>",
            f"  └ 미실현: <code>{cap['unrealized_pnl']:+,.0f}</code>",
            f"📊 일일 PnL: <code>{self.state.daily_pnl:+.4f}</code>",
            f"📐 수익률: <code>{cap['total_return_pct']:+.2%}</code>",
        ]
        await self._reply(update, "\n".join(lines))

    async def _positions(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        positions = self.state.capital.positions
        if not positions:
            await self._reply(update, "📭 보유 포지션 없음")
            return
        lines = ["<b>📦 현재 포지션</b>"]
        for ticker, pos in positions.items():
            cur = self.state.last_prices.get(ticker, pos.entry_price)
            pnl_pct = (cur - pos.entry_price) / pos.entry_price * 100 if pos.entry_price else 0
            sign = "📈" if pnl_pct >= 0 else "📉"
            lines.append(
                f"\n{sign} <b>{ticker}</b>"
                f"\n  진입가: <code>{pos.entry_price:,.0f}</code>"
                f"\n  현재가: <code>{cur:,.0f}</code>"
                f"\n  평가손익: <code>{pnl_pct:+.2f}%</code>"
                f"\n  보유량: <code>{pos.volume:.6f}</code>"
            )
        await self._reply(update, "\n".join(lines))

    async def _orders(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        if not self.persistence:
            await self._reply(update, "persistence 비활성")
            return
        rows = await self.persistence.query_orders(limit=10)
        if not rows:
            await self._reply(update, "📭 주문 내역 없음")
            return
        lines = ["<b>📋 최근 주문</b>"]
        for r in rows:
            state_icon = {"filled": "✅", "cancelled": "❌", "failed": "💥"}.get(r["state"], "⏳")
            lines.append(
                f"{state_icon} {r['created_at'][:16]}  "
                f"<code>{r['side']:4s} {r['ticker']:10s}</code>  "
                f"<code>{r['price']:,.0f}</code>  [{r['state']}]"
            )
        await self._reply(update, "\n".join(lines))

    async def _trades(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        if not self.persistence:
            await self._reply(update, "persistence 비활성")
            return
        rows = await self.persistence.query_trades(limit=10)
        if not rows:
            await self._reply(update, "📭 체결 내역 없음")
            return
        lines = ["<b>💱 최근 체결</b>"]
        for r in rows:
            side_icon = "🟢" if r["side"] == "buy" else "🔴"
            lines.append(
                f"{side_icon} {r['ts'][:16]}  "
                f"<code>{r['ticker']:10s}</code>  "
                f"<code>{r['price']:,.0f}</code>  "
                f"vol=<code>{r['volume']:.6f}</code>"
            )
        await self._reply(update, "\n".join(lines))

    async def _strategies(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        params = self.state.strategy_params
        threshold = params.get("decision_threshold", 0.5)
        weights = params.get("strategy_weights", {})
        lines = [
            "<b>⚙️ 전략 파라미터</b>",
            f"결정 임계값: <code>{threshold}</code>",
            "",
            "<b>전략 가중치</b>",
        ]
        for name, w in sorted(weights.items()):
            lines.append(f"  {name}: <code>{w}</code>")
        await self._reply(update, "\n".join(lines))

    async def _perf(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        perf = self.state.strategy_params.get("_last_perf")
        if not perf:
            await self._reply(update, "📭 성과 데이터 아직 없음 (PerformanceAgent 수집 전)")
            return
        lines = [
            "<b>📊 성과 지표</b>",
            f"거래 수: <code>{perf.get('total_trades', 0)}</code>",
            f"승률: <code>{perf.get('win_rate', 0):.1%}</code>",
            f"최대 낙폭: <code>{perf.get('max_drawdown', 0):.2%}</code>",
            f"Sharpe-like: <code>{perf.get('sharpe', 0):.3f}</code>",
            f"총 PnL: <code>{perf.get('total_pnl', 0):+,.0f} KRW</code>",
        ]
        await self._reply(update, "\n".join(lines))

    async def _agents(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        if not self.orchestrator:
            await self._reply(update, "orchestrator 연결 없음")
            return
        statuses = self.orchestrator.agent_statuses()
        lines = ["<b>🤖 Agent 상태</b>"]
        for s in statuses:
            if s.get("task_exception"):
                icon = "💥"
            elif s.get("task_done"):
                icon = "⏹"
            elif s.get("stopping"):
                icon = "🔄"
            else:
                icon = "✅"
            lines.append(f"{icon} <code>{s['name']}</code>")
        await self._reply(update, "\n".join(lines))

    async def _dashboard(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        url = self.dashboard_url or "(URL 미설정)"
        await self._reply(update, f"🖥 대시보드: {url}")

    # ──────────────────────────────────────────
    # 제어 명령어
    # ──────────────────────────────────────────

    async def _halt(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        self.state.halted = True
        await self.bus.publish(Event(topic="system.halt", payload={"source": "telegram"}))
        await self._reply(update, "🛑 매매 <b>정지</b>됨")

    async def _resume(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        self.state.halted = False
        await self.bus.publish(Event(topic="system.resume", payload={"source": "telegram"}))
        await self._reply(update, "✅ 매매 <b>재개</b>됨")

    async def _dryrun(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        if not self.orchestrator:
            await self._reply(update, "orchestrator 연결 없음")
            return
        exec_agent = self.orchestrator.get_agent("execution")
        if exec_agent is None:
            await self._reply(update, "ExecutionAgent를 찾을 수 없음")
            return
        exec_agent.dry_run = not exec_agent.dry_run  # type: ignore[attr-defined]
        status = "ON (모의 주문)" if exec_agent.dry_run else "OFF (실주문 활성)"  # type: ignore[attr-defined]
        await self._reply(update, f"🔧 Dry-run 모드: <b>{status}</b>")

    async def _liquidate(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        # 인자로 confirm이 있으면 즉시 실행
        args = ctx.args or []
        if args and args[0].lower() == "confirm":
            await self._do_liquidate(update)
            return
        # 없으면 인라인 확인 버튼
        positions = list(self.state.capital.positions.keys())
        if not positions:
            await self._reply(update, "📭 청산할 포지션 없음")
            return
        pos_str = ", ".join(positions)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ 확인 청산", callback_data="liquidate:confirm"),
            InlineKeyboardButton("❌ 취소", callback_data="liquidate:cancel"),
        ]])
        await update.message.reply_text(
            f"⚠️ <b>긴급 청산</b>\n보유 포지션: <code>{pos_str}</code>\n전량 시장가 청산합니다.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    async def _callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if not query.from_user or str(query.from_user.id) != self.admin_chat_id:
            return
        data = query.data or ""
        if data == "liquidate:confirm":
            await query.edit_message_reply_markup(reply_markup=None)
            # update.message is None for callback — create fake update wrapper
            class _FakeUpdate:
                message = query.message
            await self._do_liquidate(_FakeUpdate())  # type: ignore[arg-type]
        elif data == "liquidate:cancel":
            await query.edit_message_text("❌ 청산 취소됨")

    async def _do_liquidate(self, update: Any) -> None:
        positions = dict(self.state.capital.positions)
        if not positions:
            await update.message.reply_text("📭 청산할 포지션 없음", parse_mode=ParseMode.HTML)
            return
        for ticker, pos in positions.items():
            price = self.state.last_prices.get(ticker, pos.entry_price)
            await self.bus.publish(Event(
                topic="trade.approved",
                payload={
                    "ticker": ticker,
                    "side": "sell",
                    "price": price,
                    "volume": pos.volume,
                    "alloc_krw": pos.cost,
                    "confidence": 1.0,
                    "reasons": ["emergency_liquidation"],
                },
            ))
        tickers = list(positions.keys())
        await update.message.reply_text(
            f"🔴 <b>긴급 청산 명령 전송</b>\n대상: {tickers}",
            parse_mode=ParseMode.HTML,
        )
