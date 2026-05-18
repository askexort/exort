"""
Exort Telegram Bot — AI agent accessible via Telegram.

Uses the Exort Agent framework with full conversation memory,
tool use, and multi-provider support.

Features:
  - Per-user conversation memory (SQLite-backed)
  - Tool use (web search, code execution, file ops)
  - Multiple model selection via inline buttons
  - Rate limiting
  - Group chat support (responds when @mentioned)
  - Streaming-style "typing" indicator

Setup:
  1. Create a bot with @BotFather on Telegram
  2. Set TELEGRAM_BOT_TOKEN in ~/.exort/.env
  3. Run: exort serve

Commands:
  /start    — Welcome message
  /help     — Show help
  /new      — Start new conversation
  /model    — Switch model
  /status   — Show current model and usage
  /clear    — Clear conversation history
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Optional

from exort.agent import Agent
from exort.config import Config

logger = logging.getLogger(__name__)


class ExortTelegramBot:
    """Telegram bot powered by the Exort Agent."""

    def __init__(self, token: str, config: Config):
        self.token = token
        self.config = config
        self._agents: dict[int, Agent] = {}  # per-user agents
        self._rate_limits: dict[int, list[float]] = defaultdict(list)
        self._rate_limit = config.get("telegram.rate_limit_per_min", 10)

    def _get_agent(self, user_id: int) -> Agent:
        """Get or create an Agent for a specific user."""
        if user_id not in self._agents:
            self._agents[user_id] = Agent(
                config=self.config,
                verbose=False,
            )
            self._agents[user_id].start_session(title=f"Telegram user {user_id}")
        return self._agents[user_id]

    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limit."""
        now = time.time()
        window = 60  # 1 minute
        self._rate_limits[user_id] = [
            t for t in self._rate_limits[user_id] if now - t < window
        ]
        if len(self._rate_limits[user_id]) >= self._rate_limit:
            return False
        self._rate_limits[user_id].append(now)
        return True

    async def start_command(self, update, context):
        """Handle /start command."""
        welcome = (
            "🤖 *Welcome to Exort!*\n\n"
            "I'm an AI assistant with superpowers — I can:\n"
            "• 🔍 Search the web\n"
            "• 💻 Write and run code\n"
            "• 📁 Read and write files\n"
            "• 🐚 Run shell commands\n"
            "• 🧠 Remember our conversation\n\n"
            "Just send me a message and I'll help!\n\n"
            "Commands:\n"
            "/new — Start a new conversation\n"
            "/model — Switch AI model\n"
            "/status — Show current status\n"
            "/help — Show this help"
        )
        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def help_command(self, update, context):
        """Handle /help command."""
        await self.start_command(update, context)

    async def new_command(self, update, context):
        """Handle /new command — start fresh conversation."""
        user_id = update.effective_user.id
        if user_id in self._agents:
            self._agents[user_id].end_session()
        self._agents[user_id] = Agent(config=self.config)
        self._agents[user_id].start_session(title=f"Telegram user {user_id}")
        await update.message.reply_text("✅ New conversation started! What's on your mind?")

    async def status_command(self, update, context):
        """Handle /status command."""
        user_id = update.effective_user.id
        agent = self._get_agent(user_id)
        status = agent.get_status()
        usage = status["usage"]
        text = (
            f"📊 *Status*\n\n"
            f"Provider: `{status['provider']}`\n"
            f"Model: `{status['model']}`\n"
            f"Turns: {status['turns']}\n"
            f"Tool calls: {status['tool_calls']}\n"
            f"Tokens: {usage['total_tokens']} total\n"
            f"Tools: {status['tools_available']} available"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def model_command(self, update, context):
        """Handle /model command — show model selection."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        models = [
            ("llama-3.3-70b", "llama-3.3-70b-versatile"),
            ("llama-3.1-8b", "llama-3.1-8b-instant"),
            ("mixtral-8x7b", "mixtral-8x7b-32768"),
            ("gpt-4o-mini", "gpt-4o-mini"),
        ]
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"model:{model_id}")]
            for name, model_id in models
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🤖 Choose a model:", reply_markup=reply_markup)

    async def model_callback(self, update, context):
        """Handle model selection callback."""
        query = update.callback_query
        await query.answer()

        data = query.data
        if data.startswith("model:"):
            model = data.split(":", 1)[1]
            user_id = query.from_user.id
            agent = self._get_agent(user_id)
            agent._model = model
            await query.edit_message_text(f"✅ Model changed to: `{model}`", parse_mode="Markdown")

    async def handle_message(self, update, context):
        """Handle regular text messages."""
        user_id = update.effective_user.id
        message_text = update.message.text

        if not message_text:
            return

        # Rate limiting
        if not self._check_rate_limit(user_id):
            await update.message.reply_text("⚠️ Rate limit exceeded. Please wait a moment.")
            return

        # In group chats, only respond when mentioned
        if update.effective_chat.type in ("group", "supergroup"):
            bot_username = context.bot.username
            if not (message_text.startswith(f"@{bot_username}") or
                    (update.message.reply_to_message and
                     update.message.reply_to_message.from_user.id == context.bot.id)):
                return
            # Remove @mention from message
            message_text = message_text.replace(f"@{bot_username}", "").strip()

        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Get agent and process
        agent = self._get_agent(user_id)
        try:
            response = agent.chat(message_text, stream=False)

            # Truncate for Telegram (4096 char limit)
            if len(response) > 4000:
                response = response[:4000] + "\n\n...[response truncated]"

            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


def run_bot(token: str, config: Config):
    """Run the Telegram bot."""
    try:
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            MessageHandler,
            CallbackQueryHandler,
            filters,
        )
    except ImportError:
        print("Error: python-telegram-bot not installed.")
        print("Install it with: pip install 'python-telegram-bot>=21.0'")
        return

    bot = ExortTelegramBot(token, config)
    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", bot.start_command))
    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(CommandHandler("new", bot.new_command))
    app.add_handler(CommandHandler("status", bot.status_command))
    app.add_handler(CommandHandler("model", bot.model_command))

    # Callback handler for model selection
    app.add_handler(CallbackQueryHandler(bot.model_callback, pattern="^model:"))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    print(f"🤖 Exort Telegram Bot starting...")
    print(f"   Send /start to your bot on Telegram to begin.")
    app.run_polling()
