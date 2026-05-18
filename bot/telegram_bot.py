"""
OpenMind Telegram Bot — Free AI for Everyone + Token Tracker
Uses Groq (free tier) as default provider.
Tracks token buy/sell events across multiple chains.
"""

import asyncio
import json
import logging
import os
import time
import urllib.request
from collections import defaultdict
from datetime import datetime

from scanner import (
    CHAIN_CONFIG,
    check_price_alerts,
    classify_trade,
    decode_transfer,
    format_trade_alert,
    get_latest_block,
    get_token_info,
    get_token_transfers,
)
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
from tracker_store import TrackerStore

# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "5"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "60"))  # seconds

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger("openmind-bot")

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

# ─── Tracker Store ────────────────────────────────────────────────────────────

tracker = TrackerStore()

# Block heights per chain (for incremental scanning)
last_scanned_blocks: dict[str, int] = {}

# ─── Groq API ─────────────────────────────────────────────────────────────────

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

AVAILABLE_MODELS = {
    "llama-3.3-70b": "llama-3.3-70b-versatile",
    "llama-3.1-8b": "llama-3.1-8b-instant",
    "mixtral-8x7b": "mixtral-8x7b-32768",
    "gemma2-9b": "gemma2-9b-it",
}

SYSTEM_PROMPT = (
    "You are OpenMind AI — a free, open-source AI assistant "
    "created by the OpenMind community. "
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
        "User-Agent": "OpenMind-Bot/0.1.0",
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
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("🪙 Token", callback_data="token"),
        ],
        [
            InlineKeyboardButton("📈 Tracker", callback_data="help_tracker"),
        ],
        [
            InlineKeyboardButton("🌐 Website", url="https://openmind-ai.github.io/openmind"),
            InlineKeyboardButton("📦 GitHub", url="https://github.com/openmind-ai/openmind"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        "🧠 **Welcome to OpenMind AI!**\n\n"
        "I'm a free, open-source AI assistant powered by cutting-edge models.\n\n"
        "**Quick Start:**\n"
        "• Just send me any message to chat\n"
        "• `/track <chain> <address>` — Track a token\n"
        "• `/price <chain> <address>` — Get price\n"
        "• `/tracked` — Your tracked tokens\n"
        "• `/help` — All commands\n\n"
        "🆓 **100% Free** • 🔓 **Open Source** • 🌍 **For Everyone**\n\n"
        "_Built by the OpenMind community_"
    )

    await update.message.reply_text(
        welcome, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all commands."""
    help_text = (
        "📖 **OpenMind Bot Commands**\n\n"
        "**Chat:**\n"
        "• Send any message — I'll respond!\n"
        "• `/chat <message>` — Explicit chat\n\n"
        "**Token Tracker:**\n"
        "• `/track <chain> <address>` — Track a token for alerts\n"
        "• `/untrack <address>` — Stop tracking\n"
        "• `/tracked` — List your tracked tokens\n"
        "• `/price <chain> <address>` — Get current price\n"
        "• `/chains` — Supported chains\n\n"
        "**Settings:**\n"
        "• `/models` — View/switch AI models\n"
        "• `/model <name>` — Set model directly\n\n"
        "**Info:**\n"
        "• `/stats` — Usage statistics\n"
        "• `/about` — About OpenMind\n"
        "• `/token` — $MIND token info\n"
        "• `/help` — This message\n\n"
        f"**Rate Limit:** {RATE_LIMIT} messages/min\n"
        f"**Current Model:** `{DEFAULT_MODEL}`"
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


# ─── Tracker Commands ────────────────────────────────────────────────────────


async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track a token for buy/sell alerts.

    Usage: /track <chain> <token_address>
    Example: /track base 0x1234...abcd
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/track <chain> <address>`\n\n"
            "**Examples:**\n"
            "• `/track base 0x1234...abcd`\n"
            "• `/track ethereum 0xdAC17F958D2ee523a2206206994597C13D831ec7`\n"
            "• `/track solana EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            f"**Chains:** {', '.join(CHAIN_CONFIG.keys())}\n"
            "Use `/chains` for details.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chain = context.args[0].lower()
    address = context.args[1].strip()

    if chain not in CHAIN_CONFIG:
        await update.message.reply_text(
            f"❌ Unknown chain `{chain}`.\nSupported: {', '.join(CHAIN_CONFIG.keys())}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Validate address format
    if chain != "solana" and not address.startswith("0x"):
        await update.message.reply_text("❌ Invalid EVM address. Must start with 0x.")
        return

    # Get token info
    status_msg = await update.message.reply_text("🔍 Looking up token...")

    token_info = get_token_info(address, chain)
    if not token_info and chain == "solana":
        from scanner import get_solana_token_info

        token_info = get_solana_token_info(address)

    token_name = token_info.get("token_name", "Unknown") if token_info else "Unknown"
    token_symbol = token_info.get("token_symbol", "???") if token_info else "???"

    added = tracker.add_token(
        chat_id=chat_id,
        user_id=user_id,
        token_address=address,
        chain=chain,
        token_name=token_name,
        token_symbol=token_symbol,
    )

    if not added:
        await status_msg.edit_text(
            f"⚠️ **{token_symbol}** is already being tracked in this chat.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chain_name = CHAIN_CONFIG[chain]["name"]

    if token_info:
        price = token_info.get("price_usd", 0)
        price_str = f"${price:.8f}" if price < 0.01 else f"${price:.4f}"
        vol = token_info.get("volume_24h", 0)
        liq = token_info.get("liquidity_usd", 0)

        response = (
            f"✅ **Now Tracking: {token_symbol}** ({token_name})\n"
            f"🔗 Chain: {chain_name}\n"
            f"💰 Price: {price_str}\n"
            f"📊 Vol 24h: ${vol:,.0f} | 💧 Liq: ${liq:,.0f}\n\n"
            f"You'll receive alerts for buy/sell activity and big price moves.\n"
            f"Use `/untrack {address[:10]}...` to stop."
        )
    else:
        response = (
            f"✅ **Now Tracking:** `{address[:8]}...{address[-6:]}`\n"
            f"🔗 Chain: {chain_name}\n\n"
            f"⚠️ Couldn't fetch token info — the address may be wrong or "
            f"the token isn't on a DEX yet. You'll still get alerts if "
            f"transfer activity is detected."
        )

    await status_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)


async def cmd_untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop tracking a token.

    Usage: /untrack <token_address_or_partial>
    """
    if not context.args:
        tracked = tracker.get_tracked(update.effective_chat.id)
        if not tracked:
            await update.message.reply_text("You're not tracking any tokens.")
            return

        keyboard = []
        for t in tracked[:10]:
            sym = t.get("token_symbol", "???")
            addr = t["token_address"]
            keyboard.append(
                [InlineKeyboardButton(f"❌ {sym} ({addr[:8]}...)", callback_data=f"untrack:{addr}")]
            )

        await update.message.reply_text(
            "Select a token to untrack:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    query = context.args[0].lower().strip()
    chat_id = update.effective_chat.id

    # Try exact match first
    if tracker.remove_token(chat_id, query):
        await update.message.reply_text(f"✅ Stopped tracking `{query[:10]}...`")
        return

    # Try partial match
    tracked = tracker.get_tracked(chat_id)
    matches = [t for t in tracked if query in t["token_address"]]

    if len(matches) == 1:
        tracker.remove_token(chat_id, matches[0]["token_address"])
        sym = matches[0].get("token_symbol", "???")
        await update.message.reply_text(f"✅ Stopped tracking **{sym}**")
    elif len(matches) > 1:
        msg = "Multiple matches found:\n"
        for t in matches:
            msg += f"• {t.get('token_symbol', '???')} — `{t['token_address']}`\n"
        msg += "\nUse the full address to untrack."
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ No matching tracked token found.")


async def cmd_tracked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all tracked tokens for this chat."""
    tracked = tracker.get_tracked(update.effective_chat.id)

    if not tracked:
        await update.message.reply_text(
            "📭 No tokens tracked yet.\n\nUse `/track <chain> <address>` to start tracking!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines = [f"📈 **Tracked Tokens** ({len(tracked)})\n"]

    for t in tracked:
        sym = t.get("token_symbol", "???")
        chain = t.get("chain", "?")
        addr = t["token_address"]
        chain_cfg = CHAIN_CONFIG.get(chain, {})
        chain_emoji = {
            "ethereum": "⟠",
            "base": "🔵",
            "polygon": "🟣",
            "bsc": "🟡",
            "arbitrum": "🔷",
            "solana": "◎",
        }.get(chain, "⛓")

        lines.append(
            f"{chain_emoji} **{sym}** — {chain_cfg.get('name', chain)}\n"
            f"   `{addr[:8]}...{addr[-6:]}`"
        )

    lines.append("\nUse `/untrack` to remove tokens.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current price for a token.

    Usage: /price <chain> <address>
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/price <chain> <address>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chain = context.args[0].lower()
    address = context.args[1].strip()

    if chain not in CHAIN_CONFIG:
        await update.message.reply_text(f"❌ Unknown chain: `{chain}`")
        return

    status_msg = await update.message.reply_text("🔍 Fetching price...")

    token_info = get_token_info(address, chain)
    if not token_info and chain == "solana":
        from scanner import get_solana_token_info

        token_info = get_solana_token_info(address)

    if not token_info:
        await status_msg.edit_text("❌ Couldn't find token info. Check the address and chain.")
        return

    alert = format_trade_alert(token_info, chain)
    await status_msg.edit_text(alert, parse_mode=ParseMode.MARKDOWN)


async def cmd_chains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List supported chains."""
    lines = ["⛓ **Supported Chains**\n"]
    for key, cfg in CHAIN_CONFIG.items():
        lines.append(f"• **{key}** — {cfg['name']}")
    lines.append("\nUse chain name in `/track`, `/price` commands.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


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

    all_tracked = tracker.get_all_tracked()
    unique_tokens = len(set(t["token_address"] for t in all_tracked))
    unique_chats = len(set(t["chat_id"] for t in all_tracked))

    text = (
        "📊 **OpenMind Bot Stats**\n\n"
        f"👥 Total Users: `{len(stats['total_users'])}`\n"
        f"💬 Total Messages: `{stats['total_messages']}`\n"
        f"⏱ Uptime: `{hours}h {minutes}m`\n"
        f"🤖 Current Model: `{DEFAULT_MODEL}`\n"
        f"⚡ Rate Limit: `{RATE_LIMIT}/min`\n\n"
        f"📈 **Tracker:**\n"
        f"🪙 Tokens Tracked: `{unique_tokens}`\n"
        f"💬 Chats with Trackers: `{unique_chats}`"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About OpenMind."""
    text = (
        "🧠 **About OpenMind**\n\n"
        "OpenMind is a free, open-source AI agent framework + "
        "decentralized AI platform.\n\n"
        "**Our Mission:** Make AI accessible to everyone, everywhere.\n\n"
        "**Features:**\n"
        "• Free AI chat (no paywalls)\n"
        "• Token tracker with buy/sell alerts\n"
        "• Open-source code (MIT license)\n"
        "• Multi-provider support\n"
        "• Community governed via $MIND token\n\n"
        "**Links:**\n"
        "• [GitHub](https://github.com/openmind-ai/openmind)\n"
        "• [Website](https://openmind-ai.github.io/openmind)\n"
        "• [Telegram](https://t.me/openmindai)\n"
    )

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )


async def cmd_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """$MIND token info."""
    text = (
        "🪙 **$MIND Token**\n\n"
        "**Chain:** Base (Ethereum L2)\n"
        "**Total Supply:** 1,000,000,000 MIND\n"
        "**Contract:** _Coming soon (testnet deployed)_\n\n"
        "**Distribution:**\n"
        "• 40% Community & Airdrop\n"
        "• 20% Liquidity Pool\n"
        "• 15% Development\n"
        "• 15% Marketing\n"
        "• 10% Team (12-month vest)\n\n"
        "**Utility:**\n"
        "• Governance voting\n"
        "• Premium features access\n"
        "• Staking rewards\n"
        "• Community incentives\n\n"
        "_Token launch: Q2 2025_"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


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
    elif query.data == "help_tracker":
        await query.edit_message_text(
            "📈 **Token Tracker Guide**\n\n"
            "**Track a token:**\n"
            "`/track base 0x1234...abcd`\n\n"
            "**Get price:**\n"
            "`/price ethereum 0xdAC17...ec7`\n\n"
            "**List tracked:** `/tracked`\n"
            "**Stop tracking:** `/untrack`\n"
            "**Supported chains:** `/chains`\n\n"
            "You'll get alerts for:\n"
            "• 🟢 Buy events (tokens bought on DEX)\n"
            "• 🔴 Sell events (tokens sold on DEX)\n"
            "• 📈📉 Big price moves (>20% in 5m, >50% in 1h)",
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
    elif query.data.startswith("untrack:"):
        addr = query.data.split(":", 1)[1]
        chat_id = update.effective_chat.id
        removed = tracker.remove_token(chat_id, addr)
        if removed:
            await query.edit_message_text(f"✅ Stopped tracking `{addr[:10]}...`")
        else:
            await query.edit_message_text("❌ Token not found in tracker.")
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
    elif query.data == "token":
        await query.edit_message_text(
            "🪙 **$MIND Token**\n\n"
            "Chain: Base | Supply: 1B\n"
            "Launch: Q2 2025\n\n"
            "Use `/token` for full details.",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─── Error Handler ────────────────────────────────────────────────────────────


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Error: {context.error}", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")


# ─── Background Scanner ──────────────────────────────────────────────────────


async def token_scanner(app: Application):
    """Background task: scan tracked tokens for price changes and trades."""
    logger.info("📈 Token scanner started")

    while True:
        try:
            unique_tokens = tracker.get_unique_tokens()
            if not unique_tokens:
                await asyncio.sleep(SCAN_INTERVAL)
                continue

            logger.info(f"Scanning {len(unique_tokens)} unique tokens...")

            for token_entry in unique_tokens:
                try:
                    token_addr = token_entry["token_address"]
                    chain = token_entry["chain"]

                    # Get current price data
                    token_info = get_token_info(token_addr, chain)
                    if not token_info and chain == "solana":
                        from scanner import get_solana_token_info

                        token_info = get_solana_token_info(token_addr)

                    if not token_info:
                        continue

                    # Check for price alerts
                    alert_msg = check_price_alerts(token_info)

                    # Build alert message
                    chats = tracker.get_chats_for_token(token_addr, chain)

                    if alert_msg:
                        # Send price alert to all chats tracking this token
                        full_alert = (
                            f"🚨 **Price Alert**\n\n"
                            f"{format_trade_alert(token_info, chain)}\n\n"
                            f"{alert_msg}"
                        )
                        for chat_entry in chats:
                            try:
                                await app.bot.send_message(
                                    chat_id=chat_entry["chat_id"],
                                    text=full_alert,
                                    parse_mode=ParseMode.MARKDOWN,
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to send alert to {chat_entry['chat_id']}: {e}"
                                )

                    # Check for buy/sell on-chain (EVM only)
                    chain_cfg = CHAIN_CONFIG.get(chain, {})
                    if chain_cfg.get("chain_id", 0) > 0:
                        await _scan_onchain(app, token_addr, chain, token_info, chats)

                    # Update last checked
                    tracker.update_last_checked(token_addr, chain)

                    # Small delay between tokens to avoid rate limits
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error scanning {token_entry.get('token_address', '?')}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Scanner error: {e}")

        await asyncio.sleep(SCAN_INTERVAL)


async def _scan_onchain(
    app: Application,
    token_addr: str,
    chain: str,
    token_info: dict,
    chats: list[dict],
):
    """Scan on-chain Transfer events for buy/sell detection."""
    global last_scanned_blocks

    chain_cfg = CHAIN_CONFIG.get(chain, {})
    current_block = get_latest_block(chain)
    if current_block == 0:
        return

    last_block = last_scanned_blocks.get(chain, current_block - 50)
    if last_block >= current_block:
        return

    transfers = get_token_transfers(
        token_addr,
        chain,
        from_block=last_block + 1,
        to_block=current_block,
    )

    last_scanned_blocks[chain] = current_block

    if not transfers:
        return

    symbol = token_info.get("token_symbol", "???")
    price = token_info.get("price_usd", 0)
    price_str = f"${price:.8f}" if price < 0.01 else f"${price:.4f}"
    explorer = chain_cfg.get("explorer", "")

    # Process transfers — look for buys/sells
    seen_txs = set()
    alert_count = 0

    for log in transfers:
        decoded = decode_transfer(log, chain)
        if not decoded:
            continue

        tx_hash = decoded["tx_hash"]
        if tx_hash in seen_txs:
            continue
        seen_txs.add(tx_hash)

        side = classify_trade(decoded, chain)
        if not side:
            continue

        alert_count += 1
        if alert_count > 5:  # Cap alerts per scan
            break

        value = decoded["value"]
        # Assume 18 decimals for most tokens
        amount_token = value / (10**18)
        amount_usd = amount_token * price

        # Skip tiny transfers
        if amount_usd < 1.0 and amount_token < 1:
            continue

        emoji = "🟢" if side == "BUY" else "🔴"
        explorer_link = f"{explorer}/tx/{tx_hash}" if explorer else tx_hash

        alert_text = (
            f"{emoji} **{side}** — {symbol}\n\n"
            f"💰 Amount: {amount_token:,.2f} {symbol}\n"
            f"💵 Value: ~${amount_usd:,.2f}\n"
            f"📊 Price: {price_str}\n"
            f"🔗 Chain: {chain_cfg.get('name', chain)}\n"
            f"📝 [Tx]({explorer_link})\n"
        )

        for chat_entry in chats:
            try:
                await app.bot.send_message(
                    chat_id=chat_entry["chat_id"],
                    text=alert_text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.warning(f"Failed to send buy/sell alert: {e}")


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

    print("🧠 OpenMind Telegram Bot starting...")
    print(f"   Model: {DEFAULT_MODEL}")
    print(f"   Rate limit: {RATE_LIMIT}/min")
    print(f"   Scan interval: {SCAN_INTERVAL}s")

    app = Application.builder().token(BOT_TOKEN).build()

    # AI Chat commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("token", cmd_token))

    # Tracker commands
    app.add_handler(CommandHandler("track", cmd_track))
    app.add_handler(CommandHandler("untrack", cmd_untrack))
    app.add_handler(CommandHandler("tracked", cmd_tracked))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("chains", cmd_chains))

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

    # Background scanner
    app.post_init = lambda a: asyncio.create_task(token_scanner(a))

    print("✅ Bot running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
