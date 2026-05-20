"""
Exort Telegram Bot — Free AI for Everyone
Self-healing multi-provider with auto-failover, key rotation, and admin alerts.

Features:
  - Multi-key rotation per provider (survive rate limits)
  - Auto-failover chain (never return errors to users)
  - Health monitoring with admin Telegram alerts
  - Usage dashboard at /dashboard
  - Provider health tracking

Setup:
  1. @BotFather → /newbot → copy token
  2. Set env vars: TELEGRAM_BOT_TOKEN, GROQ_API_KEY (or OPENROUTER_API_KEY)
  3. Optional: CEREBRAS_API_KEY, MIMO_API_KEY for extra capacity
  4. Optional: ADMIN_IDS=your_telegram_id for alerts
  5. exort bot
"""

import asyncio
import json
import logging
import os
import time
import urllib.request
from collections import defaultdict
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from dotenv import load_dotenv

# Load .env from ~/.exort/.env
load_dotenv(os.path.expanduser('~/.exort/.env'))

from exort.resilience import get_chain, start_dashboard

logger = logging.getLogger(__name__)


# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "google/gemma-4-26b-a4b-it:free")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))

AVAILABLE_MODELS = {
    "deepseek-v4-flash": "deepseek/deepseek-v4-flash:free",
    "gemma-4-31b": "google/gemma-4-31b-it:free",
    "gemma-4-26b": "google/gemma-4-26b-a4b-it:free",
    "llama-3.3-70b": "llama-3.3-70b-versatile",
    "llama-3.1-8b": "llama-3.1-8b-instant",
    "mixtral-8x7b": "mixtral-8x7b-32768",
    "gemma2-9b": "gemma2-9b-it",
    "mimo-v2.5-pro": "mimo-v2.5-pro",
}

SYSTEM_PROMPT = (
    "You are Exort AI — a free, open-source AI assistant "
    "created by the Exort community. "
    "You are helpful, harmless, and honest. Be concise but thorough. "
    "You can help with coding, analysis, writing, math, and general questions. "
    "If you don't know something, say so honestly. "
    "Keep responses under 2000 characters for Telegram readability."
)


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self, max_per_min: int = 10):
        self.max_per_min = max_per_min
        self.user_timestamps: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        window = now - 60
        self.user_timestamps[user_id] = [ts for ts in self.user_timestamps[user_id] if ts > window]
        if len(self.user_timestamps[user_id]) >= self.max_per_min:
            return False
        self.user_timestamps[user_id].append(now)
        return True


rate_limiter = RateLimiter(RATE_LIMIT)

# ─── Stats ────────────────────────────────────────────────────────────────────

stats: dict = {
    "total_messages": 0,
    "total_users": set(),
    "start_time": datetime.utcnow(),
    "model_usage": defaultdict(int),
}


# ─── AI Chat (uses resilient chain) ───────────────────────────────────────────

async def chat_with_ai(message: str, model: str = None) -> str:
    """Send message to AI with automatic failover and key rotation."""
    chain = get_chain()
    return await chain.chat(message, SYSTEM_PROMPT)


# ─── Command Handlers ────────────────────────────────────────────────────────

async def cmd_start(update, context):
    """Welcome message."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode

    stats["total_users"].add(update.effective_user.id)

    keyboard = [
        [
            InlineKeyboardButton("💬 Chat", callback_data="help_chat"),
            InlineKeyboardButton("🤖 Models", callback_data="models"),
        ],
        [
            InlineKeyboardButton("📊 Health", callback_data="health"),
            InlineKeyboardButton("🌐 Website", url="https://askexort.github.io/exort"),
        ],
        [
            InlineKeyboardButton("📦 GitHub", url="https://github.com/askexort/exort"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        "⚡ **Exort Engine** — Self-Healing AI Agent\n\n"
        "I can help with coding, analysis, writing, math, and more.\n\n"
        "**Quick Start:**\n"
        "• Just send me any message to chat\n"
        "• `/help` — All commands\n"
        "• `/health` — Provider status\n\n"
        "🆓 **100% Free** • 🔓 **Open Source** • 🌍 **For Everyone**\n\n"
        "_Built by the Exort community_"
    )

    await update.message.reply_text(
        welcome, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    )


async def cmd_help(update, context):
    """List all commands."""
    from telegram.constants import ParseMode

    help_text = (
        "📖 **Exort Bot Commands**\n\n"
        "**Chat:**\n"
        "• Send any message — I'll respond!\n"
        "• `/chat <message>` — Explicit chat\n\n"
        "**Settings:**\n"
        "• `/models` — View/switch AI models\n"
        "• `/model <name>` — Set model directly\n\n"
        "**Monitoring:**\n"
        "• `/health` — Provider health report\n"
        "• `/stats` — Usage statistics\n\n"
        "**Info:**\n"
        "• `/about` — About Exort\n"
        "• `/new` — Fresh conversation\n"
        "• `/help` — This message\n\n"
        f"**Rate Limit:** {RATE_LIMIT} messages/min\n"
        f"**Current Model:** `{DEFAULT_MODEL}`"
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def cmd_new(update, context):
    """Fresh conversation."""
    await update.message.reply_text("✅ Fresh session started. Send me a message!")


async def cmd_chat(update, context):
    """Handle explicit /chat command."""
    from telegram.constants import ParseMode

    if not context.args:
        await update.message.reply_text(
            "Usage: `/chat <your message>`", parse_mode=ParseMode.MARKDOWN
        )
        return

    message = " ".join(context.args)
    await handle_message(update, context, message)


async def cmd_models(update, context):
    """Show available models."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode

    keyboard = []
    for name, model_id in AVAILABLE_MODELS.items():
        indicator = " ✅" if model_id == DEFAULT_MODEL else ""
        keyboard.append(
            [InlineKeyboardButton(f"{name}{indicator}", callback_data=f"setmodel:{model_id}")]
        )

    await update.message.reply_text(
        "🤖 **Available Models:**\n\n"
        "**Groq (free, 100K tok/day):**\n"
        "• **llama-3.3-70b** — Best quality ✅\n"
        "• **llama-3.1-8b** — Fastest\n"
        "• **mixtral-8x7b** — Great for coding\n"
        "• **gemma2-9b** — Balanced\n\n"
        "**OpenRouter (free models):**\n"
        "• **gemma-4-26b** — Google's latest\n"
        "• **gemma-4-31b** — Larger variant\n"
        "• **deepseek-v4-flash** — Fast reasoning\n\n"
        "**MiMo (Xiaomi):**\n"
        "• **mimo-v2.5-pro** — Top reasoning\n\n"
        f"Current: `{DEFAULT_MODEL}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cmd_model(update, context):
    """Set model directly."""
    from telegram.constants import ParseMode

    global DEFAULT_MODEL
    if not context.args:
        await update.message.reply_text(
            f"Current model: `{DEFAULT_MODEL}`", parse_mode=ParseMode.MARKDOWN
        )
        return

    model_name = context.args[0].lower()
    if model_name in AVAILABLE_MODELS:
        DEFAULT_MODEL = AVAILABLE_MODELS[model_name]
        await update.message.reply_text(
            f"✅ Model set to **{model_name}** (`{DEFAULT_MODEL}`)", parse_mode=ParseMode.MARKDOWN
        )
    elif model_name in AVAILABLE_MODELS.values():
        DEFAULT_MODEL = model_name
        await update.message.reply_text(
            f"✅ Model set to `{DEFAULT_MODEL}`", parse_mode=ParseMode.MARKDOWN
        )
    else:
        models_list = ", ".join(AVAILABLE_MODELS.keys())
        await update.message.reply_text(f"❌ Unknown model. Available: {models_list}")


async def cmd_health(update, context):
    """Show provider health report."""
    from telegram.constants import ParseMode

    chain = get_chain()
    report = await chain.health_check()
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)


async def cmd_stats(update, context):
    """Show usage statistics."""
    from telegram.constants import ParseMode

    chain = get_chain()
    chain_stats = chain.stats

    uptime = datetime.utcnow() - stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)

    success_rate = 0
    if chain_stats["total_requests"] > 0:
        success_rate = round((chain_stats["total_success"] / chain_stats["total_requests"]) * 100)

    text = (
        "📊 **Exort Bot Stats**\n\n"
        f"👥 Total Users: `{len(stats['total_users'])}`\n"
        f"💬 Total Messages: `{stats['total_messages']}`\n"
        f"⏱ Uptime: `{hours}h {minutes}m`\n"
        f"🤖 Current Model: `{DEFAULT_MODEL}`\n"
        f"⚡ Rate Limit: `{RATE_LIMIT}/min`\n\n"
        f"**Provider Stats:**\n"
        f"📡 Total Requests: `{chain_stats['total_requests']}`\n"
        f"✅ Success Rate: `{success_rate}%`\n"
        f"❌ Failures: `{chain_stats['total_failures']}`"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_about(update, context):
    """About Exort."""
    from telegram.constants import ParseMode

    text = (
        "⚡ **About Exort**\n\n"
        "Exort is a free, open-source AI agent framework + "
        "decentralized AI platform.\n\n"
        "**Our Mission:** Make AI accessible to everyone, everywhere.\n\n"
        "**Features:**\n"
        "• Free AI chat (no paywalls)\n"
        "• Open-source code (MIT license)\n"
        "• Self-healing provider chain\n"
        "• Multi-key rotation (survive rate limits)\n"
        "• Auto-failover (never go down)\n"
        "• Health monitoring dashboard\n"
        "• Community driven\n\n"
        "**Links:**\n"
        "• [GitHub](https://github.com/askexort/exort)\n"
        "• [Website](https://askexort.github.io/exort)\n"
        "• [Dashboard](https://exort-bot.onrender.com/dashboard)\n"
        "• [Telegram](https://t.me/Exortai)\n"
    )

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )


# ─── Message Handler ─────────────────────────────────────────────────────────

async def handle_message(update, context, explicit_msg: str = None):
    """Handle incoming messages — main chat logic."""
    from telegram.constants import ChatAction, ParseMode

    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    message = explicit_msg or update.message.text

    if not message or not message.strip():
        return

    # Rate limit check
    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(
            f"⏳ Rate limit: max {RATE_LIMIT} messages per minute. Please wait."
        )
        return

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Update stats
    stats["total_messages"] += 1
    stats["total_users"].add(user_id)
    stats["model_usage"][DEFAULT_MODEL] += 1

    logger.info(f"User {username} ({user_id}): {message[:80]}...")

    # Get AI response (async — doesn't block the event loop)
    response = await chat_with_ai(message)

    # Telegram has 4096 char limit
    if len(response) > 4000:
        response = response[:4000] + "\n\n_[Response truncated]_"

    logger.info(f"Response ({len(response)} chars)")

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


async def handle_group_message(update, context):
    """Handle messages in groups — only respond when mentioned."""
    if update.message and update.message.text:
        bot_username = context.bot.username
        if f"@{bot_username}" in update.message.text:
            message = update.message.text.replace(f"@{bot_username}", "").strip()
            if message:
                await handle_message(update, context, message)


# ─── Callback Handler ────────────────────────────────────────────────────────

async def handle_callback(update, context):
    """Handle inline keyboard callbacks."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode

    global DEFAULT_MODEL
    query = update.callback_query
    await query.answer()

    if query.data == "help_chat":
        await query.edit_message_text(
            "💬 **How to Chat:**\n\n"
            "Just send me any message directly!\n"
            "Or use `/chat <your message>`\n\n"
            "Example: `/chat What is quantum computing?`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif query.data == "models":
        keyboard = []
        for name, model_id in AVAILABLE_MODELS.items():
            indicator = " ✅" if model_id == DEFAULT_MODEL else ""
            keyboard.append(
                [InlineKeyboardButton(f"{name}{indicator}", callback_data=f"setmodel:{model_id}")]
            )
        await query.edit_message_text(
            "🤖 Select a model:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data.startswith("setmodel:"):
        model_id = query.data.split(":", 1)[1]
        DEFAULT_MODEL = model_id
        await query.edit_message_text(
            f"✅ Model set to `{model_id}`", parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == "health":
        chain = get_chain()
        report = await chain.health_check()
        await query.edit_message_text(report, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "stats":
        chain = get_chain()
        chain_stats = chain.stats

        uptime = datetime.utcnow() - stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        success_rate = 0
        if chain_stats["total_requests"] > 0:
            success_rate = round((chain_stats["total_success"] / chain_stats["total_requests"]) * 100)

        await query.edit_message_text(
            f"📊 **Stats**\n\n"
            f"👥 Users: `{len(stats['total_users'])}`\n"
            f"💬 Messages: `{stats['total_messages']}`\n"
            f"⏱ Uptime: `{hours}h {minutes}m`\n"
            f"🤖 Model: `{DEFAULT_MODEL}`\n"
            f"✅ Success Rate: `{success_rate}%`",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─── Error Handler ────────────────────────────────────────────────────────────

async def error_handler(update, context):
    """Log errors."""
    logger.error(f"Error: {context.error}", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")


# ─── Main Entry Point ────────────────────────────────────────────────────────

def run_bot(token: str, cfg=None):
    """Launch the Telegram bot. Called by `exort bot` CLI command."""
    from telegram.ext import (
        ApplicationBuilder,
        CallbackQueryHandler,
        CommandHandler,
        MessageHandler,
        filters,
    )

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return

    # Initialize the resilient provider chain
    chain = get_chain()
    if not chain.providers:
        print("⚠️  No AI provider configured!")
        print("   Set OPENROUTER_API_KEY (free models): https://openrouter.ai/keys")
        print("   Or set GROQ_API_KEY (free, 100K tok/day): https://console.groq.com")
        print("   Or set CEREBRAS_API_KEY (free, 1M tok/day): https://cloud.cerebras.ai")

    # Start dashboard server (health check + monitoring UI)
    port = int(os.environ.get("PORT", "8080"))
    start_dashboard(port)
    logger.info(f"Dashboard server on port {port}")

    # Print startup info
    active_providers = [p.name for p in chain.providers if p.has_available_key]
    print(f"⚡ Exort bot starting... send /start on Telegram to begin.")
    print(f"   Providers: {' → '.join(active_providers) or 'none'}")
    print(f"   Model: {DEFAULT_MODEL}")
    print(f"   Rate limit: {RATE_LIMIT}/min")
    print(f"   Dashboard: http://localhost:{port}/dashboard")

    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("about", cmd_about))

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Group messages (respond only when mentioned)
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_group_message
        )
    )

    # Private messages (always respond)
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Errors
    app.add_error_handler(error_handler)

    print("✅ Bot running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)
