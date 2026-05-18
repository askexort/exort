# 🤝 Contributing to Exort

Thank you for your interest in contributing to Exort! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account

### Development Setup

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/Exort.git
cd Exort

# 3. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 4. Install in development mode
pip install -e ".[dev,all]"

# 5. Install pre-commit hooks
pre-commit install

# 6. Run tests to verify setup
make test
```

## 📋 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation changes
- `refactor/` — Code refactoring
- `test/` — Test additions/changes

### 2. Make Your Changes

- Write clean, well-documented code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

```bash
# Run tests
make test

# Run linter
make lint

# Format code
make format

# Type checking
make typecheck
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new provider for Anthropic Claude"
```

Commit message format:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Tests
- `refactor:` — Refactoring
- `chore:` — Maintenance

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## 🧪 Testing

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Specific test file
pytest tests/test_agent.py -v

# Specific test
pytest tests/test_agent.py::TestAgent::test_agent_chat -v
```

### Writing Tests

```python
import pytest
from Exort.agent import Agent
from Exort.providers.base import BaseProvider, ProviderResponse

class MockProvider(BaseProvider):
    name = "mock"

    @property
    def default_model(self):
        return "mock-model"

    def generate(self, messages, **kwargs):
        return ProviderResponse(content="Test response")

def test_my_feature():
    agent = Agent(provider=MockProvider())
    response = agent.chat("Hello")
    assert response == "Test response"
```

## 📝 Code Style

We use **Ruff** for linting and formatting:

```bash
# Check style
make lint

# Auto-format
make format
```

### Key Guidelines

- Line length: 100 characters max
- Use type hints for all function signatures
- Write docstrings for all public methods
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants

### Docstring Format

```python
def my_function(param1: str, param2: int = 10) -> bool:
    """Short description of the function.

    Longer description if needed. Explain the purpose,
    behavior, and any important details.

    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 10.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.
    """
```

## 🛠️ Adding a New Provider

1. Create `Exort/providers/my_provider.py`:

```python
from Exort.providers.base import BaseProvider, ProviderResponse

class MyProvider(BaseProvider):
    name = "my_provider"

    @property
    def default_model(self):
        return "my-default-model"

    def generate(self, messages, tools=None, temperature=0.7, max_tokens=4096, **kwargs):
        # Implement API call
        return ProviderResponse(content="response")

    def generate_stream(self, messages, **kwargs):
        # Implement streaming
        yield ProviderResponse(content="chunk")
```

2. Register in `Exort/providers/__init__.py`:

```python
from Exort.providers.my_provider import MyProvider

PROVIDERS["my_provider"] = MyProvider
```

3. Add to `pyproject.toml` optional dependencies if needed.

4. Write tests in `tests/test_providers.py`.

## 🔧 Adding a New Tool

1. Create or edit a file in `Exort/tools/`:

```python
from Exort.tools.base import tool

@tool(
    name="my_tool",
    description="What this tool does",
)
def my_tool(param: str) -> str:
    """Tool implementation."""
    return "result"
```

2. Import in `Exort/tools/__init__.py`.

3. Write tests in `tests/test_tools.py`.

## 📚 Documentation

- Update README.md for user-facing changes
- Add docstrings to all new public APIs
- Include code examples in docstrings
- Update CHANGELOG.md for all changes

## 🐛 Reporting Bugs

1. Check existing issues first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Relevant logs or error messages

## 💡 Suggesting Features

1. Check existing issues and discussions
2. Create a feature request with:
   - Clear description of the feature
   - Use cases and motivation
   - Proposed implementation (if any)
   - Alternatives considered

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions make Exort better for everyone. We appreciate your time and effort!
