"""
Exort Telegram Bot — the engine in your pocket.

Uses the Engine framework with per-user memory and full gear access.

Setup:
  1. @BotFather → /newbot → copy token
  2. echo "TELEGRAM_BOT_TOKEN=..." >> ~/.exort/.env
  3. exort bot
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Optional

from exort.engine import Engine
from exort.config import Config

logger = logging.getLogger(__name__)


class ExortBot:
    """Telegram frontend for the Exort Engine."""

    def __init__(self, token: str, cfg: Config):
        self.token = token
        self.cfg = cfg
        self._engines: dict[int, Engine] = {}
        self._limits: dict[int, list[float]] = defaultdict(list)
        self._rpm = cfg.get("telegram.rate_per_minute", 10)

    def _engine(self, uid: int) -> Engine:
        if uid not in self._engines:
            e = Engine(config=self.cfg)
            e.open(f"tg-{uid}")
            self._engines[uid] = e
        return self._engines[uid]

    def _ok(self, uid: int) -> bool:
        now = time.time()
        self._limits[uid] = [t for t in self._limits[uid] if now - t < 60]
        if len(self._limits[uid]) >= self._rpm:
            return False
        self._limits[uid].append(now)
        return True

    async def cmd_start(self, update, ctx):
        await update.message.reply_text(
            "⚡ *Exort Engine* — AI Agent\n\n"
            "I can search the web, run code, manage files, and more.\n"
            "Just send me a message!\n\n"
            "/new — fresh conversation\n"
            "/status — engine stats\n"
            "/help — this message",
            parse_mode="Markdown",
        )

    async def cmd_help(self, update, ctx):
        await self.cmd_start(update, ctx)

    async def cmd_new(self, update, ctx):
        uid = update.effective_user.id
        if uid in self._engines:
            self._engines[uid].close()
        e = Engine(config=self.cfg)
        e.open(f"tg-{uid}")
        self._engines[uid] = e
        await update.message.reply_text("✅ Fresh session started.")

    async def cmd_status(self, update, ctx):
        e = self._engine(update.effective_user.id)
        s = e.status()
        t = s["tokens"]
        await update.message.reply_text(
            f"📊 *Engine Status*\n\n"
            f"Provider: `{s['provider']}`\n"
            f"Model: `{s['model']}`\n"
            f"Turns: {s['turns']}\n"
            f"Gear calls: {s['gear_calls']}\n"
            f"Tokens: {t['total_tok']} total\n"
            f"Gear: {s['gear_count']} available",
            parse_mode="Markdown",
        )

    async def on_message(self, update, ctx):
        uid = update.effective_user.id
        text = update.message.text
        if not text:
            return
        if not self._ok(uid):
            await update.message.reply_text("⏳ Rate limit — wait a moment.")
            return
        if update.effective_chat.type in ("group", "supergroup"):
            bot_name = ctx.bot.username
            if not (text.startswith(f"@{bot_name}") or
                    (update.message.reply_to_message and
                     update.message.reply_to_message.from_user.id == ctx.bot.id)):
                return
            text = text.replace(f"@{bot_name}", "").strip()

        await update.message.chat.send_action("typing")
        e = self._engine(uid)
        try:
            resp = e.talk(text, stream=False)
            if len(resp) > 4000:
                resp = resp[:4000] + "\n...[truncated]"
            await update.message.reply_text(resp)
        except Exception as exc:
            await update.message.reply_text(f"❌ {str(exc)[:200]}")


def run_bot(token: str, cfg: Config):
    """Launch the Telegram bot."""
    try:
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
    except ImportError:
        print("Missing: pip install 'python-telegram-bot>=21.0'")
        return

    bot = ExortBot(token, cfg)
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", bot.cmd_start))
    app.add_handler(CommandHandler("help", bot.cmd_help))
    app.add_handler(CommandHandler("new", bot.cmd_new))
    app.add_handler(CommandHandler("status", bot.cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.on_message))

    print("⚡ Exort bot starting... send /start on Telegram to begin.")
    app.run_polling()
