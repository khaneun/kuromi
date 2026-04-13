from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.core.event_bus import Event, EventBus
from src.core.state import SharedState

if TYPE_CHECKING:
    from src.agents.persistence import PersistenceAgent


class TelegramBot:
    """Telegram control plane. Commands:
    /status  – capital & position snapshot
    /halt    – set halt flag
    /resume  – clear halt flag
    /params  – current strategy params
    /orders  – recent order history
    /trades  – recent trade history
    """

    def __init__(
        self,
        token: str,
        admin_chat_id: str,
        bus: EventBus,
        state: SharedState,
        persistence: "PersistenceAgent | None" = None,
    ) -> None:
        self.token = token
        self.admin_chat_id = str(admin_chat_id)
        self.bus = bus
        self.state = state
        self.persistence = persistence
        self.app: Application | None = None

    async def start(self) -> None:
        if not self.token:
            logger.warning("telegram token missing; bot disabled")
            return
        self.app = Application.builder().token(self.token).build()
        for cmd, handler in [
            ("status", self._status),
            ("halt", self._halt),
            ("resume", self._resume),
            ("params", self._params),
            ("orders", self._orders),
            ("trades", self._trades),
        ]:
            self.app.add_handler(CommandHandler(cmd, handler))
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
        await self.app.bot.send_message(chat_id=self.admin_chat_id, text=text[:4000])

    def _authorized(self, update: Update) -> bool:
        return str(update.effective_chat.id) == self.admin_chat_id

    async def _status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        cap = self.state.capital.snapshot(self.state.last_prices)
        lines = [
            f"halted={self.state.halted}",
            f"equity={cap['total_equity']:,.0f} KRW",
            f"available={cap['available_krw']:,.0f} KRW",
            f"unrealized={cap['unrealized_pnl']:,.0f}",
            f"realized={cap['realized_pnl']:,.0f}",
            f"return={cap['total_return_pct']:+.2%}",
            f"positions={list(cap['positions'].keys())}",
        ]
        await update.message.reply_text("\n".join(lines))

    async def _halt(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        self.state.halted = True
        await self.bus.publish(Event(topic="system.halt", payload={"source": "telegram"}))
        await update.message.reply_text("halted")

    async def _resume(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        self.state.halted = False
        await update.message.reply_text("resumed")

    async def _params(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        await update.message.reply_text(str(self.state.strategy_params))

    async def _orders(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        if not self.persistence:
            await update.message.reply_text("persistence disabled")
            return
        rows = await self.persistence.query_orders(limit=10)
        if not rows:
            await update.message.reply_text("no orders yet")
            return
        lines: list[str] = []
        for r in rows:
            lines.append(
                f"{r['created_at'][:16]}  {r['side']:4s} {r['ticker']:10s} "
                f"price={r['price']:,.0f}  vol={r.get('volume') or 0:.6f}  "
                f"state={r['state']}"
            )
        await update.message.reply_text("\n".join(lines))

    async def _trades(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return
        if not self.persistence:
            await update.message.reply_text("persistence disabled")
            return
        rows = await self.persistence.query_trades(limit=10)
        if not rows:
            await update.message.reply_text("no trades yet")
            return
        lines: list[str] = []
        for r in rows:
            lines.append(
                f"{r['ts'][:16]}  {r['side']:4s} {r['ticker']:10s} "
                f"price={r['price']:,.0f}  vol={r['volume']:.6f}"
            )
        await update.message.reply_text("\n".join(lines))
