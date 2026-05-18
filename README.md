<div align="center">

# 🤖 Exort

### AI Agent for Everyone

An open-source AI agent that can **search the web**, **write and run code**, **manage files**, and **remember conversations** — all through a simple CLI or Telegram.

[![CI](https://github.com/askexort/exort/actions/workflows/ci.yml/badge.svg)](https://github.com/askexort/exort/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Quick Start](#-quick-start) • [Features](#-features) • [Providers](#-providers) • [Telegram Bot](#-telegram-bot) • [Tools](#-tools) • [API](#-python-api) • [Contributing](#-contributing)

</div>

---

## 🚀 Quick Start

### Install (30 seconds)

```bash
# Clone the repo
git clone https://github.com/askexort/exort.git
cd exort

# Install
pip install -e .
```

### Set up your API key

```bash
# Option 1: Groq (FREE, fast — recommended for beginners)
# Get your key at: https://console.groq.com
echo "GROQ_API_KEY=your-key-here" > ~/.exort/.env

# Option 2: OpenAI
echo "OPENAI_API_KEY=your-key-here" > ~/.exort/.env

# Option 3: Ollama (100% local, no API key needed)
# Install Ollama: https://ollama.ai
ollama pull llama3.1
```

### Run it!

```bash
# Interactive chat
exort chat

# Ask a single question
exort chat "What is quantum computing?"

# Use a specific provider
exort chat -p ollama "Hello!"

# Start the Telegram bot
exort serve
```

**That's it!** You now have an AI agent that can search the web, run code, manage files, and more.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Multi-Provider** | Use Groq (free), OpenAI, Anthropic, or local Ollama |
| 🔧 **Tool Use** | Web search, code execution, file ops, shell commands |
| 💾 **Memory** | Persistent conversation history (SQLite-backed) |
| 💬 **Interactive CLI** | Beautiful REPL with slash commands |
| 📱 **Telegram Bot** | Deploy as a Telegram bot for mobile access |
| 🐳 **Docker Ready** | One-command deployment |
| 🔌 **Extensible** | Easy to add custom tools and providers |
| 🆓 **Free Tier** | Works with Groq's free API — no credit card needed |

---

## 🏗️ Architecture

```
exort/
├── agent.py          # Core agent loop (think → act → observe)
├── cli.py            # Interactive CLI with REPL
├── config.py         # YAML configuration manager
├── utils.py          # Utilities and terminal formatting
├── providers/        # LLM provider implementations
│   ├── base.py       # Abstract provider interface
│   ├── groq_provider.py    # Groq Cloud (free, fast)
│   ├── openai_provider.py  # OpenAI / compatible APIs
│   ├── ollama_provider.py  # Local Ollama
│   └── anthropic_provider.py  # Anthropic Claude
├── tools/            # Built-in tools
│   ├── registry.py   # Tool discovery and registration
│   ├── web.py        # Web search (DuckDuckGo)
│   ├── file_ops.py   # Read, write, list, search files
│   ├── shell.py      # Shell command execution
│   ├── code.py       # Python code execution
│   └── vision.py     # Image analysis
├── memory/
│   └── store.py      # SQLite conversation memory
├── skills/
│   └── manager.py    # Skill file management
└── bot/
    └── telegram_bot.py  # Telegram bot server
```

### How It Works

```
You: "Search for the latest Python 3.13 features and summarize them"

Agent thinks → calls web_search("Python 3.13 features")
  ↓
Agent reads search results
  ↓
Agent thinks → calls fetch_url(url_of_top_result)
  ↓
Agent reads page content
  ↓
Agent responds with a summary
```

The agent follows a **think → act → observe** loop:
1. Your message goes to the LLM
2. The LLM decides if it needs tools
3. If yes, it calls tools and processes the results
4. It repeats until it has a final answer

---

## 🔌 Providers

Exort supports 4 LLM providers out of the box:

### Groq (Recommended for Getting Started)
- **Cost**: FREE (30 requests/min)
- **Speed**: Fastest inference available
- **Setup**: Get key at [console.groq.com](https://console.groq.com)
- **Models**: llama-3.3-70b, llama-3.1-8b, mixtral-8x7b

```bash
echo "GROQ_API_KEY=gsk_..." > ~/.exort/.env
exort chat -p groq -m llama-3.3-70b-versatile "Hello!"
```

### OpenAI
- **Cost**: Pay-per-token
- **Quality**: GPT-4 class models
- **Setup**: Get key at [platform.openai.com](https://platform.openai.com/api-keys)

```bash
echo "OPENAI_API_KEY=sk-..." > ~/.exort/.env
exort chat -p openai -m gpt-4o-mini "Hello!"
```

### Anthropic (Claude)
- **Cost**: Pay-per-token
- **Quality**: Excellent reasoning
- **Setup**: Get key at [console.anthropic.com](https://console.anthropic.com)
- **Extra**: `pip install anthropic`

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > ~/.exort/.env
exort chat -p anthropic -m claude-sonnet-4-20250514 "Hello!"
```

### Ollama (100% Local)
- **Cost**: FREE (runs on your machine)
- **Privacy**: Everything stays on your computer
- **Setup**: Install [Ollama](https://ollama.ai), then `ollama pull llama3.1`

```bash
exort chat -p ollama -m llama3.1 "Hello!"
```

---

## 🛠️ Tools

The agent has access to these built-in tools:

### 🔍 Web Search
```python
# The agent can search the web
"Search for the best Python web frameworks in 2025"
```

### 💻 Code Execution
```python
# The agent can write and run Python code
"Calculate the first 20 Fibonacci numbers"
"Write a script that renames all .txt files in a directory"
```

### 📁 File Operations
```python
# The agent can read, write, and manage files
"Read the contents of config.json"
"Create a new Python file with a hello world program"
"List all Python files in the current directory"
```

### 🐚 Shell Commands
```python
# The agent can run shell commands
"What's my current directory?"
"Show me the git log for the last 5 commits"
"Check if Python is installed and what version"
```

---

## 💬 CLI Commands

When in interactive mode (`exort chat`), use these commands:

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/new` | Start a new conversation |
| `/status` | Show agent status (provider, model, tokens) |
| `/model <name>` | Switch model |
| `/provider <name>` | Switch provider |
| `/tools` | List available tools |
| `/providers` | List available providers |
| `/history` | Show current conversation |
| `/sessions` | List saved sessions |
| `/load <id>` | Load a saved session |
| `/clear` | Clear screen |
| `/quit` | Exit |

---

## 📱 Telegram Bot

Deploy Exort as a Telegram bot for mobile access:

### Setup

1. **Create a bot**: Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow the prompts
2. **Save the token**: Copy the bot token
3. **Configure**:
   ```bash
   echo "TELEGRAM_BOT_TOKEN=your-token-here" >> ~/.exort/.env
   ```
4. **Run**:
   ```bash
   exort serve
   ```

### Bot Commands
- `/start` — Welcome message
- `/new` — Start new conversation
- `/model` — Switch AI model (inline buttons)
- `/status` — Show current model and usage

### Features
- Per-user conversation memory
- Tool use (web search, code execution, etc.)
- Rate limiting (10 messages/min per user)
- Group chat support (responds when @mentioned)

---

## 🐳 Docker

Run with Docker (no local Python needed):

```bash
# Interactive CLI
docker compose run cli chat

# Telegram bot
docker compose up bot

# With API key
GROQ_API_KEY=your-key docker compose run cli chat
```

---

## ⚙️ Configuration

Exort uses a YAML config file at `~/.exort/config.yaml`:

```yaml
# Default provider and model
provider: groq
model: llama-3.3-70b-versatile

# Agent settings
agent:
  max_iterations: 25      # Max tool call loops per response
  max_tokens: 4096        # Max response length
  temperature: 0.7        # Creativity (0.0-1.0)

# Memory settings
memory:
  enabled: true
  max_history: 50         # Messages to keep in context

# Display settings
display:
  show_token_usage: true
  show_tool_calls: true
  streaming: true

# Telegram settings
telegram:
  rate_limit_per_min: 10
  allowed_users: []       # Empty = allow all
```

### Config CLI

```bash
exort config show                          # View all settings
exort config set provider openai           # Change provider
exort config set model gpt-4o              # Change model
exort config set agent.temperature 0.5     # Change temperature
```

---

## 🐍 Python API

Use Exort as a Python library:

### Simple Usage

```python
from exort import Agent

agent = Agent()
response = agent.chat("What is the capital of France?")
print(response)
```

### With Streaming

```python
from exort import Agent

agent = Agent(provider="groq", model="llama-3.3-70b-versatile")
for chunk in agent.chat("Tell me a joke", stream=True):
    print(chunk, end="", flush=True)
```

### With Memory

```python
from exort import Agent

agent = Agent()
agent.start_session("My Project")

# First message
print(agent.chat("I'm building a Python web app"))

# Second message — agent remembers context
print(agent.chat("Add error handling to the code"))
```

### With Custom Provider

```python
from exort import Agent

# Use local Ollama
agent = Agent(provider="ollama", model="llama3.1")
print(agent.chat("Hello!"))

# Use OpenAI
agent = Agent(provider="openai", model="gpt-4o")
print(agent.chat("Hello!"))
```

### With Custom Tools

```python
from exort import Agent
from exort.tools.registry import ToolRegistry

registry = ToolRegistry()
registry.discover()  # Load built-in tools

# Add custom tool
registry.register(
    name="get_weather",
    description="Get current weather for a city",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"}
        },
        "required": ["city"]
    },
    handler=lambda city: f"Weather in {city}: 72°F, sunny"
)

agent = Agent(tools=registry)
print(agent.chat("What's the weather in Tokyo?"))
```

---

## 🧩 Adding Custom Tools

Create a new tool in 3 steps:

```python
# 1. Create exort/tools/my_tool.py

def _my_function(param: str) -> dict:
    """Your tool logic here."""
    return {"result": f"Processed: {param}"}

def register_tools(registry):
    """Called by the tool discovery system."""
    registry.register(
        name="my_tool",
        description="Does something useful",
        parameters={
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "Input parameter"
                }
            },
            "required": ["param"]
        },
        handler=_my_function,
    )
```

```python
# 2. Add to exort/tools/__init__.py imports (optional — auto-discovered)

# 3. Test it
from exort import Agent
agent = Agent()
print(agent.chat("Use my_tool with param 'hello'"))
```

---

## 📂 Project Structure

```
exort/
├── __init__.py           # Package exports
├── agent.py              # Core agent loop (think → act → observe)
├── cli.py                # Interactive CLI + click commands
├── config.py             # YAML config + .env loading
├── utils.py              # Colors, formatting, helpers
├── providers/
│   ├── __init__.py       # Provider registry
│   ├── base.py           # Abstract provider interface
│   ├── groq_provider.py  # Groq Cloud (free!)
│   ├── openai_provider.py # OpenAI + compatible APIs
│   ├── ollama_provider.py # Local Ollama
│   └── anthropic_provider.py # Anthropic Claude
├── tools/
│   ├── __init__.py       # Tool registry
│   ├── registry.py       # Auto-discovery system
│   ├── base.py           # @tool decorator + BaseTool
│   ├── web.py            # web_search, fetch_url
│   ├── file_ops.py       # read_file, write_file, list_directory, search_files
│   ├── shell.py          # run_shell
│   ├── code.py           # execute_python
│   └── vision.py         # analyze_image
├── memory/
│   ├── __init__.py
│   └── store.py          # SQLite conversation store
├── skills/
│   ├── __init__.py
│   └── manager.py        # Skill file manager
├── bot/
│   ├── __init__.py
│   └── telegram_bot.py   # Telegram bot server
└── tests/
    ├── test_agent.py     # Agent tests
    └── test_tools.py     # Tool tests
```

---

## 🤝 Contributing

We welcome contributions! Here's how:

### Quick Contributions
1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

### Development Setup

```bash
# Clone and install in dev mode
git clone https://github.com/askexort/exort.git
cd exort
pip install -e ".[full,dev]"

# Run tests
make test

# Lint
make lint

# Format
make format
```

### Ideas for Contributions
- 🔌 New LLM providers (Google Gemini, Mistral, etc.)
- 🛠️ New tools (image generation, PDF reading, database queries)
- 📱 New platform bots (Discord, Slack, WhatsApp)
- 📖 Documentation improvements
- 🧪 More tests
- 🐛 Bug fixes

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) for free, fast LLM inference
- [Ollama](https://ollama.ai) for local model support
- [OpenAI](https://openai.com) for the API standard
- The open-source community

---

<div align="center">

**Built with ❤️ for the AI community**

[Star this repo](https://github.com/askexort/exort) • [Report a bug](https://github.com/askexort/exort/issues) • [Request a feature](https://github.com/askexort/exort/issues)

</div>
