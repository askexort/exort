# 🧠 OpenMind

[![PyPI version](https://img.shields.io/pypi/v/openmind-agent.svg)](https://pypi.org/project/openmind-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Stars](https://img.shields.io/github/stars/openmind-ai/openmind?style=social)](https://github.com/openmind-ai/openmind)

**Open-source AI Agent Framework** — Build autonomous agents with tool use, memory, and multi-provider support.

> *Think → Act → Observe → Repeat*

---

## ✨ Features

- 🤖 **Agentic Loop** — Think → Act → Observe architecture for autonomous reasoning
- 🔌 **Multi-Provider** — OpenAI, Ollama (local), Groq (free tier) out of the box
- 🛠️ **Plugin Tools** — Decorator-based tool registration system
- 💾 **Conversation Memory** — SQLite-backed persistent conversations
- ⚡ **Streaming** — Real-time token streaming for all providers
- 🎨 **Beautiful CLI** — Rich terminal interface with colors and commands
- 📄 **YAML Config** — Simple configuration management
- 🔧 **Extensible** — Easy to add providers, tools, and capabilities
- 📦 **Zero Lock-in** — Switch providers with a single flag

---

## 🚀 Quick Start

### Install

```bash
# Basic install
pip install openmind-agent

# With all providers
pip install openmind-agent[all]

# Development
git clone https://github.com/openmind-ai/openmind.git
cd openmind
pip install -e ".[dev,all]"
```

### Configure

```bash
# Set up config file
openmind config --init

# Set your Groq API key (free at https://console.groq.com)
export GROQ_API_KEY="your-key-here"

# Or for OpenAI
export OPENAI_API_KEY="your-key-here"
```

### Chat

```bash
# Start chatting (uses Groq free tier by default)
openmind chat

# Use a specific provider
openmind chat --provider groq
openmind chat --provider openai --model gpt-4o
openmind chat --provider ollama --model llama3.1
```

### Python API

```python
from openmind import Agent

# Quick start
agent = Agent(provider="groq")
response = agent.chat("What is the capital of France?")
print(response)

# With tools and custom settings
agent = Agent(
    provider="groq",
    system_prompt="You are a helpful coding assistant.",
)

# Streaming
for chunk in agent.chat_stream("Tell me a joke"):
    print(chunk, end="")

# Check usage
print(agent.get_stats())
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      OpenMind CLI                        │
│                   (openmind chat)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                  Agent Loop                      │   │
│  │                                                  │   │
│  │   ┌──────┐    ┌──────┐    ┌──────────┐         │   │
│  │   │Think │───▶│ Act  │───▶│ Observe  │──┐      │   │
│  │   │(LLM) │    │(Tool)│    │(Result)  │  │      │   │
│  │   └──────┘    └──────┘    └──────────┘  │      │   │
│  │       ▲                                 │      │   │
│  │       └─────────────────────────────────┘      │   │
│  │              (repeat until done)                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │Providers │  │  Tools   │  │  Memory  │             │
│  ├──────────┤  ├──────────┤  ├──────────┤             │
│  │ OpenAI   │  │ Web      │  │ SQLite   │             │
│  │ Groq     │  │ File     │  │ History  │             │
│  │ Ollama   │  │ Shell    │  │ Tokens   │             │
│  │ (custom) │  │ Code     │  │ Search   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔌 Provider Comparison

| Provider | Free Tier | Speed | Models | Setup |
|----------|-----------|-------|--------|-------|
| **Groq** | ✅ Yes | ⚡ Ultra-fast | Llama 3.1, Mixtral | `GROQ_API_KEY` |
| **OpenAI** | 💳 Pay-per-use | 🏃 Fast | GPT-4o, GPT-4o-mini | `OPENAI_API_KEY` |
| **Ollama** | ✅ Local | 🐢 Hardware-dependent | Llama, Mistral, etc. | `ollama serve` |

### Groq (Recommended for Getting Started)

```bash
# 1. Get free API key at https://console.groq.com
# 2. Set it
export GROQ_API_KEY="gsk_..."

# 3. Chat
openmind chat --provider groq
```

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
openmind chat --provider openai --model gpt-4o-mini
```

### Ollama (100% Local)

```bash
# 1. Install Ollama: https://ollama.ai
# 2. Pull a model
ollama pull llama3.1

# 3. Chat
openmind chat --provider ollama
```

---

## 🛠️ Tool Development Guide

### Using the Decorator

```python
from openmind.tools.base import tool

@tool(
    name="my_tool",
    description="Describe what your tool does",
)
def my_tool(query: str, max_results: int = 5) -> str:
    """Tool implementation.

    Args:
        query: Search query.
        max_results: Max results to return.

    Returns:
        JSON string with results.
    """
    import json
    results = [{"id": i, "text": f"Result {i}"} for i in range(max_results)]
    return json.dumps({"query": query, "results": results})
```

### Using a Class

```python
from openmind.tools.base import BaseTool

class MySearchTool(BaseTool):
    name = "advanced_search"
    description = "Search with advanced options"

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "filters": {"type": "object", "description": "Optional filters"},
            },
            "required": ["query"],
        }

    def execute(self, query: str, filters: dict = None) -> str:
        # Your implementation here
        return json.dumps({"results": []})
```

### Built-in Tools

| Tool | Description |
|------|-------------|
| `web_search` | Search the web via DuckDuckGo |
| `fetch_url` | Fetch and extract text from URLs |
| `read_file` | Read file contents |
| `write_file` | Write content to files |
| `list_directory` | List directory contents |
| `run_shell` | Execute shell commands |
| `execute_python` | Run Python code in sandbox |

---

## ⚙️ Configuration

### Config File (`~/.openmind/config.yaml`)

```yaml
provider: groq
model: llama-3.1-8b-instant
temperature: 0.7
max_tokens: 4096
max_iterations: 10

memory:
  enabled: true

tools:
  enabled: true
  auto_discover: true

ui:
  stream: true
  show_tool_calls: true
  color: true
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENMIND_PROVIDER` | Default provider |
| `OPENMIND_MODEL` | Default model |
| `OPENMIND_TEMPERATURE` | Default temperature |
| `GROQ_API_KEY` | Groq API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `OLLAMA_HOST` | Ollama server URL |

### CLI Commands

```bash
openmind chat                     # Start chat
openmind chat --provider groq     # Use Groq
openmind chat --provider ollama   # Use local Ollama
openmind config --list            # Show config
openmind config --init            # Create config file
openmind config -k provider -v groq  # Set config value
openmind test --provider groq     # Test a provider
openmind providers                # List providers
openmind tools                    # List tools
```

### In-Chat Commands

```
/help    - Show help
/stats   - Show session statistics
/reset   - Reset conversation
/tools   - List available tools
exit     - Exit chat
```

---

## 📦 Project Structure

```
openmind/
├── openmind/
│   ├── __init__.py          # Package entry point
│   ├── agent.py             # Core agentic loop
│   ├── cli.py               # CLI commands
│   ├── config.py            # YAML config management
│   ├── providers/           # LLM providers
│   │   ├── base.py          # Abstract provider
│   │   ├── openai.py        # OpenAI/compatible
│   │   ├── ollama.py        # Local Ollama
│   │   └── groq.py          # Groq cloud
│   ├── tools/               # Tool system
│   │   ├── base.py          # Tool registry
│   │   ├── web.py           # Web search
│   │   ├── file.py          # File operations
│   │   ├── shell.py         # Shell commands
│   │   └── code.py          # Code execution
│   ├── memory/              # Conversation memory
│   │   └── store.py         # SQLite store
│   └── utils.py             # Helpers
├── tests/                   # Test suite
├── pyproject.toml           # Package config
├── README.md                # This file
├── CONTRIBUTING.md          # Contributing guide
├── CHANGELOG.md             # Release notes
└── LICENSE                  # MIT License
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone the repo
git clone https://github.com/openmind-ai/openmind.git
cd openmind

# Install dev dependencies
pip install -e ".[dev,all]"

# Run tests
make test

# Run linter
make lint
```

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🪙 $MIND Token

> *Coming Soon*

The $MIND token will power the OpenMind ecosystem:

- 🔹 **Governance** — Vote on framework features and priorities
- 🔹 **Staking** — Earn rewards for contributing tools and providers
- 🔹 **Payments** — Pay for premium API access and compute
- 🔹 **Incentives** — Reward developers for high-quality contributions

*Stay tuned for the tokenomics paper and launch details.*

---

## 🙏 Acknowledgments

Built with ❤️ by the open-source community.

Special thanks to:
- [OpenAI](https://openai.com) for the function calling API
- [Groq](https://groq.com) for fast, free inference
- [Ollama](https://ollama.ai) for local LLM support
- All our contributors and early adopters

---

<p align="center">
  <b>🧠 OpenMind — Think. Act. Observe. Repeat.</b><br>
  <sub>Open-source AI agent framework for everyone.</sub>
</p>
