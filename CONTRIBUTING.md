# Contributing to Exort

Thank you for your interest in contributing to Exort! 🎉

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/exort.git
   cd exort
   ```
3. **Install** in development mode:
   ```bash
   pip install -e ".[full,dev]"
   ```
4. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Run Tests
```bash
make test
```

### Lint
```bash
make lint
```

### Format
```bash
make format
```

## What Can I Contribute?

### 🔌 New Providers
Add support for new LLM providers (Google Gemini, Mistral, Cohere, etc.).

Create `exort/providers/your_provider.py`:
```python
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register_provider

class YourProvider(BaseProvider):
    name = "your_provider"
    
    def chat(self, messages, model=None, tools=None, **kwargs):
        # Your implementation
        return ProviderResponse(content="...", model="...")
    
    def validate(self):
        return bool(self.api_key)

register_provider("your_provider", YourProvider)
```

### 🛠️ New Tools
Add new capabilities to the agent.

Create `exort/tools/your_tool.py`:
```python
def _your_function(param: str) -> dict:
    return {"result": "..."}

def register_tools(registry):
    registry.register(
        name="your_tool",
        description="What it does",
        parameters={
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Input"}
            },
            "required": ["param"]
        },
        handler=_your_function,
    )
```

### 📖 Documentation
- Improve the README
- Add examples
- Fix typos
- Write tutorials

### 🐛 Bug Fixes
- Check [open issues](https://github.com/askexort/exort/issues)
- Add tests that reproduce the bug
- Fix the bug
- Verify tests pass

## Code Style

We use `ruff` for linting and formatting:
```bash
ruff check exort/    # Check for issues
ruff format exort/   # Auto-format
```

## Pull Request Process

1. Update tests if needed
2. Run `make test` and `make lint`
3. Update documentation if needed
4. Submit your PR with a clear description

## Questions?

Open an issue or start a discussion!

Thank you for contributing! 🚀
