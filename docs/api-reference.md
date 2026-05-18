# API Reference

## CLI Commands

### `Exort chat`

Start an interactive chat session.

```bash
Exort chat [OPTIONS]

Options:
  --provider TEXT    LLM provider (openai, groq, ollama)
  --model TEXT       Model name
  --system TEXT      System prompt override
  --max-tokens INT   Max response tokens (default: 1024)
  --temperature FLOAT  Temperature (default: 0.7)
  --stream           Enable streaming (default: true)
```

### `Exort config`

Manage configuration.

```bash
Exort config show              # Show current config
Exort config set KEY VALUE     # Set a config value
Exort config path              # Show config file path
Exort config reset             # Reset to defaults
```

### `Exort providers`

List available providers and their status.

```bash
Exort providers                # List all providers
Exort providers test           # Test connectivity
```

### `Exort tools`

List available tools.

```bash
Exort tools                    # List all tools
Exort tools test TOOL_NAME     # Test a specific tool
```

### `Exort serve`

Start a local API server (coming soon).

```bash
Exort serve [--port 8080] [--host 0.0.0.0]
```

## Python API

### Agent

```python
from Exort import Agent, Config

config = Config()
agent = Agent(config)

# Simple chat
response = await agent.chat("What is 2+2?")
print(response)

# Chat with tool use
response = await agent.chat("Search the web for latest AI news")
print(response)

# Streaming
async for chunk in agent.stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

### Config

```python
from Exort import Config

config = Config()

# Get/set values
config.get("provider")           # "groq"
config.set("model", "llama-3.3-70b-versatile")

# Load from file
config = Config.from_file("~/.Exort/config.yaml")

# Override with env vars
config = Config.from_env()
```

### Providers

```python
from Exort.providers.groq import GroqProvider

provider = GroqProvider(api_key="gsk_...")

# Non-streaming
response = await provider.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="llama-3.3-70b-versatile"
)
print(response.content)

# Streaming
async for chunk in provider.stream(messages=[...], model="..."):
    print(chunk, end="")
```

### Tools

```python
from Exort.tools.base import tool, ToolRegistry

# Register a custom tool
@tool(
    name="my_tool",
    description="Does something cool",
    parameters={
        "input": {"type": "string", "description": "Input text"}
    }
)
async def my_tool(input: str) -> str:
    return f"Processed: {input}"

# Use the registry
registry = ToolRegistry()
registry.discover()  # Auto-discover from Exort.tools
result = await registry.execute("web_search", query="hello")
```

### Memory

```python
from Exort.memory.store import MemoryStore

store = MemoryStore()

# Save a message
store.save_message(user_id="user1", role="user", content="Hello")
store.save_message(user_id="user1", role="assistant", content="Hi!")

# Get history
history = store.get_history(user_id="user1", limit=10)

# Stats
stats = store.get_stats(user_id="user1")
```
