# Getting Started with OpenMind

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git

## Installation

### From Source (Development)

```bash
# Clone the repo
git clone https://github.com/openmind-ai/openmind.git
cd openmind

# Install in editable mode
pip install -e ".[all]"

# Verify installation
openmind --help
```

### From PyPI (Coming Soon)

```bash
pip install openmind
```

### Docker

```bash
docker build -t openmind .
docker run -it --env-file .env openmind
```

## Configuration

### Quick Config

```bash
# Set up with Groq (free, no credit card)
openmind config set provider groq
openmind config set groq.api_key YOUR_KEY_HERE
openmind config set model llama-3.3-70b-versatile
```

### Config File

OpenMind uses `~/.openmind/config.yaml`:

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
export OPENMIND_PROVIDER=groq
export GROQ_API_KEY=gsk_...
export OPENMIND_MODEL=llama-3.3-70b-versatile
```

## Your First Chat

```bash
# Start chatting with Groq (free)
openmind chat --provider groq

# Use a specific model
openmind chat --provider groq --model mixtral-8x7b

# Chat with local Ollama
openmind chat --provider ollama
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
