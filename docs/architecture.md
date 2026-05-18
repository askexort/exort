# Exort Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Exort Framework                     │
├─────────────┬─────────────┬──────────────┬───────────────┤
│    CLI      │   Agent     │    Tools     │    Memory     │
│  (click)    │  (loop)     │  (plugins)   │   (sqlite)    │
├─────────────┴─────────────┴──────────────┴───────────────┤
│                    Provider Layer                         │
├──────────┬──────────────┬───────────────┬────────────────┤
│  OpenAI  │    Groq      │    Ollama     │   Custom...    │
└──────────┴──────────────┴───────────────┴────────────────┘
```

## Agent Loop

The core of Exort is the agentic loop:

```
User Input
    │
    ▼
┌──────────┐     ┌──────────┐     ┌──────────┐
│  THINK   │────▶│   ACT    │────▶│ OBSERVE  │
│ (LLM)    │     │ (Tool)   │     │ (Result) │
└──────────┘     └──────────┘     └────┬─────┘
    ▲                                   │
    └───────────────────────────────────┘
              (repeat until done)
```

1. **THINK**: Send context to LLM, get response (may include tool calls)
2. **ACT**: If LLM requests a tool, execute it
3. **OBSERVE**: Feed tool result back to LLM
4. Repeat until LLM produces a final answer (no more tool calls)

Max iterations: 10 (configurable) to prevent infinite loops.

## Provider System

All providers implement `BaseProvider`:

```python
class BaseProvider(ABC):
    name: str
    models: list[str]
    requires_key: bool

    @abstractmethod
    async def chat(self, messages, model, **kwargs) -> ProviderResponse

    @abstractmethod
    async def stream(self, messages, model, **kwargs) -> AsyncIterator[str]
```

Adding a new provider:
1. Create `Exort/providers/yourprovider.py`
2. Implement `BaseProvider`
3. Register with `@ProviderRegistry.register("name")`

## Tool System

Tools are Python functions decorated with `@tool`:

```python
from Exort.tools.base import tool

@tool(
    name="web_search",
    description="Search the web",
    parameters={
        "query": {"type": "string", "description": "Search query"}
    }
)
async def web_search(query: str) -> str:
    # implementation
    return results
```

Tools are auto-discovered from `Exort/tools/` on import.

## Memory System

SQLite-backed conversation store:
- Per-user conversation threads
- Message history with timestamps
- Token usage tracking
- Automatic pruning (configurable max history)

## File Structure

```
Exort/
├── Exort/              # Core package
│   ├── __init__.py        # Public API
│   ├── agent.py           # Agent loop
│   ├── cli.py             # CLI commands
│   ├── config.py          # Config management
│   ├── utils.py           # Helpers
│   ├── providers/         # LLM providers
│   │   ├── base.py        # Abstract provider
│   │   ├── openai.py      # OpenAI/compatible
│   │   ├── groq.py        # Groq (free)
│   │   └── ollama.py      # Ollama (local)
│   ├── tools/             # Tool plugins
│   │   ├── base.py        # Registry + decorator
│   │   ├── web.py         # Web search/fetch
│   │   ├── file.py        # File operations
│   │   ├── shell.py       # Shell commands
│   │   └── code.py        # Code execution
│   └── memory/            # Conversation memory
│       └── store.py       # SQLite store
├── bot/                   # Telegram bot
├── contracts/             # Smart contracts
├── landing/               # Landing page
├── docs/                  # Documentation
└── tests/                 # Test suite
```
