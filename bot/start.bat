@echo off
REM OpenMind Telegram Bot — Windows launcher

if not exist .env (
    echo ❌ No .env file found. Copy env.example to .env and fill in your keys.
    exit /b 1
)

for /f "tokens=1,* delims==" %%a in (.env) do set "%%a=%%b"

if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo ❌ TELEGRAM_BOT_TOKEN not set in .env
    exit /b 1
)

echo 🧠 Installing dependencies...
pip install -q python-telegram-bot

echo 🚀 Starting OpenMind Bot...
python bot\telegram_bot.py
