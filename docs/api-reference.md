# API Reference

## CLI Commands

### `openmind chat`

Start an interactive chat session.

```bash
openmind chat [OPTIONS]

Options:
  --provider TEXT    LLM provider (openai, groq, ollama)
  --model TEXT       Model name
  --system TEXT      System prompt override
  --max-tokens INT   Max response tokens (default: 1024)
  --temperature FLOAT  Temperature (default: 0.7)
  --stream           Enable streaming (default: true)
```

### `openmind config`

Manage configuration.

```bash
openmind config show              # Show current config
openmind config set KEY VALUE     # Set a config value
openmind config path              # Show config file path
openmind config reset             # Reset to defaults
```

### `openmind providers`

List available providers and their status.

```bash
openmind providers                # List all providers
openmind providers test           # Test connectivity
```

### `openmind tools`

List available tools.

```bash
openmind tools                    # List all tools
openmind tools test TOOL_NAME     # Test a specific tool
```

### `openmind serve`

Start a local API server (coming soon).

```bash
openmind serve [--port 8080] [--host 0.0.0.0]
```

## Python API

### Agent

```python
from openmind import Agent, Config

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
from openmind import Config

config = Config()

# Get/set values
config.get("provider")           # "groq"
config.set("model", "llama-3.3-70b-versatile")

# Load from file
config = Config.from_file("~/.openmind/config.yaml")

# Override with env vars
config = Config.from_env()
```

### Providers

```python
from openmind.providers.groq import GroqProvider

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
from openmind.tools.base import tool, ToolRegistry

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
registry.discover()  # Auto-discover from openmind.tools
result = await registry.execute("web_search", query="hello")
```

### Memory

```python
from openmind.memory.store import MemoryStore

store = MemoryStore()

# Save a message
store.save_message(user_id="user1", role="user", content="Hello")
store.save_message(user_id="user1", role="assistant", content="Hi!")

# Get history
history = store.get_history(user_id="user1", limit=10)

# Stats
stats = store.get_stats(user_id="user1")
```
