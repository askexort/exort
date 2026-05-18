"""
Exort Telegram Bot — Free AI for Everyone
Uses Groq (free tier) as default provider.
"""

import asyncio
import json
import logging
import os
import time
import urllib.request
from collections import defaultdict
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "5"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]


# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger("Exort-bot")

# ─── Rate Limiter ─────────────────────────────────────────────────────────────


class RateLimiter:
    def __init__(self, max_per_min: int = 5):
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

stats = {
    "total_messages": 0,
    "total_users": set(),
    "start_time": datetime.utcnow(),
    "model_usage": defaultdict(int),
}


# ─── Groq API ─────────────────────────────────────────────────────────────────

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

AVAILABLE_MODELS = {
    "llama-3.3-70b": "llama-3.3-70b-versatile",
    "llama-3.1-8b": "llama-3.1-8b-instant",
    "mixtral-8x7b": "mixtral-8x7b-32768",
    "gemma2-9b": "gemma2-9b-it",
}

SYSTEM_PROMPT = (
    "You are Exort AI — a free, open-source AI assistant "
    "created by the Exort community. "
    "You are helpful, harmless, and honest. Be concise but thorough. "
    "You can help with coding, analysis, writing, math, and general questions. "
    "If you don't know something, say so honestly. "
    "Keep responses under 2000 characters for Telegram readability."
)


async def chat_with_groq(message: str, model: str = None) -> str:
    """Send a message to Groq API and return the response."""
    model = model or DEFAULT_MODEL

    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }
    ).encode()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Exort-Bot/0.1.0",
    }

    req = urllib.request.Request(GROQ_URL, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return f"⚠️ API error: {str(e)[:100]}. Try again in a moment."


# ─── Command Handlers ────────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    stats["total_users"].add(update.effective_user.id)

    keyboard = [
        [
            InlineKeyboardButton("💬 Chat", callback_data="help_chat"),
            InlineKeyboardButton("🤖 Models", callback_data="models"),
        ],
        [
            InlineKeyboardButton("🌐 Website", url="https://Exort-ai.github.io/Exort"),
            InlineKeyboardButton("📦 GitHub", url="https://github.com/Exort-ai/Exort"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        "🧠 **Welcome to Exort AI!**\n\n"
        "I'm a free, open-source AI assistant powered by cutting-edge models.\n\n"
        "**Quick Start:**\n"
        "• Just send me any message to chat\n"
        "• `/help` — All commands\n\n"
        "🆓 **100% Free** • 🔓 **Open Source** • 🌍 **For Everyone**\n\n"
        "_Built by the Exort community_"
    )

    await update.message.reply_text(
        welcome, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all commands."""
    help_text = (
        "📖 **Exort Bot Commands**\n\n"
        "**Chat:**\n"
        "• Send any message — I'll respond!\n"
        "• `/chat <message>` — Explicit chat\n\n"
        "**Settings:**\n"
        "• `/models` — View/switch AI models\n"
        "• `/model <name>` — Set model directly\n\n"
        "**Info:**\n"
        "• `/stats` — Usage statistics\n"
        "• `/about` — About Exort\n"
        "• `/help` — This message\n\n"
        f"**Rate Limit:** {RATE_LIMIT} messages/min\n"
        f"**Current Model:** `{DEFAULT_MODEL}`"
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)



# ─── Chat Commands ───────────────────────────────────────────────────────────


async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle explicit /chat command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/chat <your message>`", parse_mode=ParseMode.MARKDOWN
        )
        return

    message = " ".join(context.args)
    await handle_message(update, context, message)


async def cmd_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available models."""
    keyboard = []
    for name, model_id in AVAILABLE_MODELS.items():
        indicator = " ✅" if model_id == DEFAULT_MODEL else ""
        keyboard.append(
            [InlineKeyboardButton(f"{name}{indicator}", callback_data=f"setmodel:{model_id}")]
        )

    await update.message.reply_text(
        "🤖 **Available Models:**\n\n"
        "• **llama-3.3-70b** — Best quality (recommended)\n"
        "• **llama-3.1-8b** — Fastest responses\n"
        "• **mixtral-8x7b** — Great for coding\n"
        "• **gemma2-9b** — Balanced\n\n"
        f"Current: `{DEFAULT_MODEL}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set model directly."""
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


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show usage statistics."""
    uptime = datetime.utcnow() - stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    text = (
        "📊 **Exort Bot Stats**\n\n"
        f"👥 Total Users: `{len(stats['total_users'])}`\n"
        f"💬 Total Messages: `{stats['total_messages']}`\n"
        f"⏱ Uptime: `{hours}h {minutes}m`\n"
        f"🤖 Current Model: `{DEFAULT_MODEL}`\n"
        f"⚡ Rate Limit: `{RATE_LIMIT}/min`"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About Exort."""
    text = (
        "🧠 **About Exort**\n\n"
        "Exort is a free, open-source AI agent framework + "
        "decentralized AI platform.\n\n"
        "**Our Mission:** Make AI accessible to everyone, everywhere.\n\n"
        "**Features:**\n"
        "• Free AI chat (no paywalls)\n"
        "• Open-source code (MIT license)\n"
        "• Multi-provider support\n"
        "• Community driven\n\n"
        "**Links:**\n"
        "• [GitHub](https://github.com/Exort-ai/Exort)\n"
        "• [Website](https://Exort-ai.github.io/Exort)\n"
        "• [Telegram](https://t.me/Exortai)\n"
    )

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )



# ─── Message Handler ─────────────────────────────────────────────────────────


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, explicit_msg: str = None
):
    """Handle incoming messages — main chat logic."""
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

    # Check API key
    if not GROQ_API_KEY:
        await update.message.reply_text(
            "⚠️ API key not configured. Set GROQ_API_KEY environment variable."
        )
        return

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Update stats
    stats["total_messages"] += 1
    stats["total_users"].add(user_id)
    stats["model_usage"][DEFAULT_MODEL] += 1

    logger.info(f"User {username} ({user_id}): {message[:80]}...")

    # Get AI response
    response = await chat_with_groq(message)

    # Telegram has 4096 char limit
    if len(response) > 4000:
        response = response[:4000] + "\n\n_[Response truncated]_"

    logger.info(f"Response ({len(response)} chars)")

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in groups — only respond when mentioned."""
    if update.message and update.message.text:
        bot_username = context.bot.username
        if f"@{bot_username}" in update.message.text:
            # Strip the mention
            message = update.message.text.replace(f"@{bot_username}", "").strip()
            if message:
                await handle_message(update, context, message)


# ─── Callback Handler ────────────────────────────────────────────────────────


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
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

    elif query.data == "stats":
        uptime = datetime.utcnow() - stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        await query.edit_message_text(
            f"📊 **Stats**\n\n"
            f"👥 Users: `{len(stats['total_users'])}`\n"
            f"💬 Messages: `{stats['total_messages']}`\n"
            f"⏱ Uptime: `{hours}h {minutes}m`\n"
            f"🤖 Model: `{DEFAULT_MODEL}`",
            parse_mode=ParseMode.MARKDOWN,
        )



# ─── Error Handler ────────────────────────────────────────────────────────────


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Error: {context.error}", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")



# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        print("   Get one from @BotFather on Telegram")
        print("   Set it: export TELEGRAM_BOT_TOKEN=your_token_here")
        return

    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not set — bot will respond with error messages.")
        print("   Get a free key at: https://console.groq.com")
        print("   Set it: export GROQ_API_KEY=your_key_here")

    print("🧠 Exort Telegram Bot starting...")
    print(f"   Model: {DEFAULT_MODEL}")
    print(f"   Rate limit: {RATE_LIMIT}/min")

    app = Application.builder().token(BOT_TOKEN).build()

    # AI Chat commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("model", cmd_model))
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


if __name__ == "__main__":
    main()
