<div align="center">

```
  ▓█████  ██╗  ██╗  ██████  ██████  ████████╗
  ▓█   ▀  ╚██╗██╝  ██╔═══██╗██╔══██╗╚══██╔══╝
  ██████╗  ╚███╝   ██║   ██║██████╔╝   ██║
  ▓█   ▀  ██╔██╗  ██║   ██║██╔══██╗   ██║
  ██████╗ ██╔╝ ██╗ ╚██████╔╝██║  ██║   ██║
  ╚═════╝ ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝
```

# The Open Agent Engine

### Free AI for Everyone

An autonomous AI agent that reasons, acts, and learns through direct tool interaction.
Runs on free-tier APIs or fully offline — no credit card, no gatekeepers.

[![CI](https://github.com/askexort/exort/actions/workflows/ci.yml/badge.svg)](https://github.com/askexort/exort/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Free](https://img.shields.io/badge/price-$0-important)](#getting-started)

[Getting Started](#-getting-started) · [What It Does](#-what-it-does) · [Architecture](#-architecture) · [Providers](#-providers) · [Telegram Bot](#-telegram-bot) · [Python API](#-python-api) · [Contributing](#-contributing)

</div>

---

## Why Exort?

Most AI agent frameworks are built for enterprises with big budgets. Exort is built for **everyone**:

- **$0 to start** — works with Groq's free API (no credit card needed)
- **Runs offline** — use Ollama and your data never leaves your machine
- **Real capabilities** — search the web, run code, manage files, not just chat
- **Own your data** — conversations stored locally in SQLite, not on someone's cloud
- **Hackable** — clean Python, no magic, easy to extend

---

## Getting Started

### Install (60 seconds)

```bash
git clone https://github.com/askexort/exort.git
cd exort
pip install -e .
```

### Pick a provider

**Option A: Groq (free, fast — best for starting out)**
```bash
# 1. Get a free key at https://console.groq.com (no credit card)
# 2. Save it:
mkdir -p ~/.exort
echo "GROQ_API_KEY=gsk_your_key_here" > ~/.exort/.env
```

**Option B: Ollama (100% local, 100% free)**
```bash
# 1. Install Ollama: https://ollama.ai
# 2. Pull a model:
ollama pull llama3.1
# No API key needed.
```

**Option C: OpenAI / Anthropic (paid, higher quality)**
```bash
echo "OPENAI_API_KEY=sk-..." > ~/.exort/.env
# or
echo "ANTHROPIC_API_KEY=sk-ant-..." > ~/.exort/.env
```

### Launch

```bash
exort shell              # interactive terminal
exort ask "hello"        # one-shot question
exort bot                # telegram bot
```

That's it. You now have an AI agent with real-world capabilities.

---

## What It Does

Exort is not a chatbot. It's an **agent** — it reasons about your request,
decides what tools to use, executes them, reads the results, and iterates
until it has a real answer.

```
You: "What are the top 3 Python web frameworks and their GitHub stars?"

Exort thinks → calls web_search("Python web frameworks 2025")
  ↓ reads results
Exort thinks → calls fetch_url("https://github.com/pallets/flask")
  ↓ reads page
Exort thinks → calls fetch_url("https://github.com/django/django")
  ↓ reads page
Exort responds with a ranked comparison table
```

### Built-in Gear (Tools)

| Gear | What It Does |
|------|-------------|
| `web_search` | Search the internet (DuckDuckGo, no API key) |
| `fetch_url` | Read any web page's content |
| `read_file` | View files with line numbers |
| `write_file` | Create or overwrite files |
| `list_directory` | Browse folders |
| `search_files` | Find files or search inside them |
| `run_shell` | Execute system commands |
| `exec_python` | Run Python code |
| `load_image` | Prepare images for vision analysis |

All gear is **opt-in by the engine** — it only calls tools when they're useful.

---

## Architecture

```
exort/
├── engine.py          ← The reasoning core (perceive → reason → act → reflect)
├── cli.py             ← The Exort Shell (interactive terminal)
├── config.py          ← YAML config + .env loading
├── utils.py           ← Terminal formatting, IDs
├── providers/         ← LLM backends
│   ├── base.py        ← Abstract provider interface
│   ├── groq_provider.py
│   ├── openai_provider.py
│   ├── ollama_provider.py
│   └── anthropic_provider.py
├── tools/             ← Built-in gear
│   ├── gear.py        ← GearBox (registration + discovery)
│   ├── web.py         ← Web search + URL fetch
│   ├── file_ops.py    ← File CRUD
│   ├── shell.py       ← Shell execution
│   ├── code.py        ← Python execution
│   └── vision.py      ← Image loading
├── memory/
│   └── store.py       ← SQLite conversation store
├── playbooks/         ← Knowledge files (markdown)
│   └── library.py     ← Playbook loader + search
└── bot/
    └── telegram_bot.py  ← Telegram frontend
```

### The Engine Loop

```
  ┌─────────────┐
  │  PERCEIVE   │  Read user input + tool results
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │   REASON    │  LLM decides: answer now, or call a tool?
  └──────┬──────┘
         ▼
  ┌─────────────┐     ┌──────────┐
  │     ACT     │────▶│   GEAR   │  Execute tool, get result
  └──────┬──────┘     └──────────┘
         ▼
  ┌─────────────┐
  │   REFLECT   │  Observe result → loop back to REASON
  └──────┬──────┘
         ▼
     [answer]
```

This is not a fixed pipeline — the engine **decides its own path** based
on what the user needs. Some questions need zero tools. Others need five.

---

## Providers

| Provider | Cost | Speed | Setup |
|----------|------|-------|-------|
| **Groq** | Free (30 req/min) | Ultra-fast | [console.groq.com](https://console.groq.com) |
| **Ollama** | Free (local) | Depends on hardware | [ollama.ai](https://ollama.ai) |
| **OpenAI** | Pay-per-token | Fast | [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | Pay-per-token | Fast | [console.anthropic.com](https://console.anthropic.com) |
| **Custom** | Varies | Varies | Any OpenAI-compatible API |

Switch at runtime:
```
exort ▸ :switch ollama
exort ▸ :model llama3.1
```

---

## API Setup & Management

### Add an API Key

All API keys are stored in `~/.exort/.env` (one `KEY=value` per line).

```bash
# Built-in providers — just add the key:
echo "GROQ_API_KEY=gsk_your_key" > ~/.exort/.env
echo "OPENAI_API_KEY=sk-your_key" >> ~/.exort/.env
echo "ANTHROPIC_API_KEY=sk-ant-your_key" >> ~/.exort/.env

# Multiple providers at once:
cat > ~/.exort/.env << 'EOF'
GROQ_API_KEY=gsk_your_groq_key
OPENAI_API_KEY=sk-your_openai_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key
TELEGRAM_BOT_TOKEN=your_telegram_token
EOF
```

Or use the interactive wizard:
```bash
exort setup
```

### Edit / Update an API Key

```bash
# View current keys (values are masked)
cat ~/.exort/.env

# Update a specific key — edit the file directly:
# On Linux/Mac:
sed -i 's/GROQ_API_KEY=.*/GROQ_API_KEY=gsk_new_key/' ~/.exort/.env

# On Windows (PowerShell):
(Get-Content ~/.exort/.env) -replace 'GROQ_API_KEY=.*', 'GROQ_API_KEY=gsk_new_key' | Set-Content ~/.exort/.env

# Or just open it in any text editor:
nano ~/.exort/.env        # Linux
notepad ~/.exort/.env     # Windows
```

### Add a Custom API Provider

Exort works with **any OpenAI-compatible API** — Together AI, Fireworks, DeepSeek, Mistral, OpenRouter, LM Studio, vLLM, etc.

Add a custom provider in `~/.exort/config.yaml`:

```yaml
providers:
  together:
    key_var: TOGETHER_API_KEY
    endpoint: https://api.together.xyz/v1
    model: meta-llama/Llama-3-70b-chat-hf

  openrouter:
    key_var: OPENROUTER_API_KEY
    endpoint: https://openrouter.ai/api/v1
    model: meta-llama/llama-3-70b-instruct

  deepseek:
    key_var: DEEPSEEK_API_KEY
    endpoint: https://api.deepseek.com/v1
    model: deepseek-chat

  lmstudio:
    key_var: null                    # local, no key needed
    endpoint: http://localhost:1234/v1
    model: local-model
```

Then add the API key to `~/.exort/.env`:
```bash
echo "TOGETHER_API_KEY=your_key" >> ~/.exort/.env
echo "OPENROUTER_API_KEY=your_key" >> ~/.exort/.env
echo "DEEPSEEK_API_KEY=your_key" >> ~/.exort/.env
```

Use it:
```bash
exort shell -p together
exort shell -p openrouter
# or inside the shell:
exort ▸ :switch together
```

### View Current Configuration

```bash
exort config show                    # all settings
exort config get engine.provider     # current provider
exort config get engine.model        # current model
exort providers                      # list available providers
```

### Change Provider / Model via CLI

```bash
# Via config commands (persists to config.yaml):
exort config set engine.provider openai
exort config set engine.model gpt-4o
exort config set engine.temperature 0.3

# Via shell commands (session only):
exort ▸ :switch ollama
exort ▸ :model llama3.1
```

### Config Priority

```
runtime args (--provider, --model)  >  env vars  >  config.yaml  >  built-in defaults
```

### Custom Provider Requirements

Any API that implements the **OpenAI Chat Completions format** works:
- `POST /v1/chat/completions` with `messages`, `model`, `temperature`, `max_tokens`
- Returns `choices[0].message.content` and optional `tool_calls`
- Streaming via `stream: true` with SSE chunks

Examples of compatible APIs: Together AI, Fireworks AI, DeepSeek, Mistral, OpenRouter, Groq, LM Studio, Ollama, vLLM, text-generation-inference, LiteLLM, and many more.

---

## The Exort Shell

```
  ▓█████  ██╗  ██╗  ██████  ██████  ████████╗
  ...

  provider: groq  model: llama-3.3-70b-versatile  gear: 9
  type :help for commands, :quit to exit

exort ▸ :help

  Exort Commands
  ─────────────────────────────────────
  :help            Show this list
  :new             Start a fresh session
  :status          Provider, model, token stats
  :gear            List available gear (tools)
  :providers       List LLM backends
  :switch <prov>   Switch LLM provider
  :model <name>    Switch model
  :history         Show current conversation
  :sessions        List saved sessions
  :load <id>       Resume a session
  :clear           Clear screen
  :quit            Exit

exort ▸ What is the Fibonacci sequence?

exort ▸ The Fibonacci sequence is a series where each number
  is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13...
```

---

## Telegram Bot

Run Exort as a Telegram bot — AI agent in your pocket.

```bash
# 1. Message @BotFather on Telegram → /newbot → copy token
# 2. Save it:
echo "TELEGRAM_BOT_TOKEN=your_token" >> ~/.exort/.env
# 3. Launch:
exort bot
```

Features:
- Per-user conversation memory
- Full gear access (web search, code execution, etc.)
- Rate limiting
- Group chat support (@mention to trigger)

---

## Python API

```python
from exort import Engine

# Simple
e = Engine()
print(e.talk("What is Rust?"))

# Streaming
for chunk in e.talk("Explain quantum computing", stream=True):
    print(chunk, end="", flush=True)

# With memory
e.open("my project")
e.talk("Build a REST API with FastAPI")
e.talk("Now add authentication")  # remembers context
e.close()

# Local (Ollama)
e = Engine(provider="ollama", model="llama3.1")
print(e.talk("Hello!"))
```

---

## Configuration

`~/.exort/config.yaml`:
```yaml
engine:
  provider: groq
  model: llama-3.3-70b-versatile
  max_rounds: 20
  max_tokens: 4096
  temperature: 0.7

memory:
  enabled: true
  window: 50

gear:
  enabled: true
  allow_unsafe: false

display:
  stream: true
  show_gear_calls: true
  show_tokens: true
```

```
exort config show                        # view all
exort config set engine.provider openai  # change provider
exort config set engine.temperature 0.3  # tune creativity
```

---

## Adding Custom Gear

Create `exort/tools/my_gear.py`:

```python
def _my_tool(param: str) -> dict:
    """Your logic here."""
    return {"result": f"Processed: {param}"}

def register(gearbox):
    gearbox.add(
        name="my_tool",
        info="What it does",
        params={
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Input"}
            },
            "required": ["param"]
        },
        handler=_my_tool,
    )
```

The engine auto-discovers it on next startup.

---

## Docker

```bash
# Interactive shell
docker compose run cli shell

# Telegram bot
docker compose up bot
```

---

## Contributing

We welcome contributions — especially new gear, new providers, and documentation.

```bash
git clone https://github.com/askexort/exort.git
cd exort
pip install -e ".[full,dev]"
make test    # run tests
make lint    # check style
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Ideas
- New providers (Google Gemini, Mistral, Cohere)
- New gear (PDF reader, database queries, image generation)
- Platform bots (Discord, Slack, WhatsApp)
- Playbook packs (domain-specific knowledge)
- Documentation and tutorials

---

## License

MIT — use it, fork it, ship it. No strings attached.

---

<div align="center">

**Built for everyone who believes AI should be free and open.**

[Star](https://github.com/askexort/exort) · [Issues](https://github.com/askexort/exort/issues) · [Discussions](https://github.com/askexort/exort/discussions)

</div>
