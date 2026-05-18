# Exort Setup Guide

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- An API key (Groq recommended — it's free!)

## Step 1: Install Exort

```bash
# Clone the repository
git clone https://github.com/askexort/exort.git
cd exort

# Install
pip install -e .
```

## Step 2: Get an API Key

### Option A: Groq (FREE — Recommended)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free, no credit card)
3. Create an API key
4. Copy the key

### Option B: OpenAI

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create an API key
3. Copy the key

### Option C: Ollama (100% Local)

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull a model:
   ```bash
   ollama pull llama3.1
   ```
3. No API key needed!

## Step 3: Configure

```bash
# Create the config directory
mkdir -p ~/.exort

# Add your API key
echo "GROQ_API_KEY=your-key-here" > ~/.exort/.env

# Or use the setup wizard
exort setup
```

## Step 4: Run!

```bash
# Start chatting
exort chat

# Ask a single question
exort chat "What is Python?"

# Use a specific provider
exort chat -p ollama "Hello!"
```

## Optional: Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token
4. Add to your .env:
   ```bash
   echo "TELEGRAM_BOT_TOKEN=your-token" >> ~/.exort/.env
   ```
5. Run:
   ```bash
   exort serve
   ```

## Optional: Docker

```bash
# With Docker Compose
GROQ_API_KEY=your-key docker compose run cli chat

# Telegram bot
docker compose up bot
```

## Troubleshooting

### "No API key found"
Make sure `~/.exort/.env` exists and contains your key:
```bash
cat ~/.exort/.env
# Should show: GROQ_API_KEY=gsk_...
```

### "Module not found"
Reinstall:
```bash
pip install -e ".[full]"
```

### "Connection refused" (Ollama)
Make sure Ollama is running:
```bash
ollama serve
```

## Need Help?

- Open an issue: [github.com/askexort/exort/issues](https://github.com/askexort/exort/issues)
- Read the docs: [github.com/askexort/exort#readme](https://github.com/askexort/exort#readme)
