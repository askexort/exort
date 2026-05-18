# Getting Started with Exort

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git

## Installation

### From Source (Development)

```bash
# Clone the repo
git clone https://github.com/Exort-ai/Exort.git
cd Exort

# Install in editable mode
pip install -e ".[all]"

# Verify installation
Exort --help
```

### From PyPI (Coming Soon)

```bash
pip install Exort
```

### Docker

```bash
docker build -t Exort .
docker run -it --env-file .env Exort
```

## Configuration

### Quick Config

```bash
# Set up with Groq (free, no credit card)
Exort config set provider groq
Exort config set groq.api_key YOUR_KEY_HERE
Exort config set model llama-3.3-70b-versatile
```

### Config File

Exort uses `~/.Exort/config.yaml`:

```yaml
provider: groq
model: llama-3.3-70b-versatile

providers:
  groq:
    api_key: gsk_...
  ollama:
    base_url: http://localhost:11434
  openai:
    api_key: sk-...
```

### Environment Variables

```bash
export Exort_PROVIDER=groq
export GROQ_API_KEY=gsk_...
export Exort_MODEL=llama-3.3-70b-versatile
```

## Your First Chat

```bash
# Start chatting with Groq (free)
Exort chat --provider groq

# Use a specific model
Exort chat --provider groq --model mixtral-8x7b

# Chat with local Ollama
Exort chat --provider ollama
```

## Free Providers (No Credit Card)

| Provider | Free Tier | Speed | Quality |
|----------|-----------|-------|---------|
| Groq     | 14K req/day | ⚡⚡⚡ | ⭐⭐⭐ |
| Ollama   | Unlimited (local) | ⚡⚡ | ⭐⭐⭐ |
| Together | $25 credit | ⚡⚡ | ⭐⭐⭐ |

## Telegram Bot

```bash
# Get a bot token from @BotFather on Telegram
export TELEGRAM_BOT_TOKEN=your_token
export GROQ_API_KEY=your_key

python bot/telegram_bot.py
```

## Next Steps

- [Architecture Overview](architecture.md)
- [API Reference](api-reference.md)
- [Token & Tokenomics](tokenomics.md)
- [Deployment Guide](deployment.md)
