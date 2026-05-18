#!/bin/bash
# OpenMind Telegram Bot — Linux/Mac launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

if [ ! -f .env ]; then
    echo "❌ No .env file found. Copy env.example to .env and fill in your keys."
    exit 1
fi

source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not set in .env"
    exit 1
fi

echo "🧠 Installing dependencies..."
pip install -q python-telegram-bot

echo "🚀 Starting OpenMind Bot..."
python bot/telegram_bot.py
