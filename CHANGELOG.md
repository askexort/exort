# 📋 Changelog

All notable changes to OpenMind will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [0.1.0] - 2024-01-15

### Added
- 🤖 **Core Agent** — Agentic loop (think → act → observe → repeat)
- 🔌 **Multi-Provider Support**:
  - OpenAI provider (GPT-4o, GPT-4o-mini, etc.)
  - Groq provider (Llama 3.1, Mixtral — free tier)
  - Ollama provider (local Llama, Mistral, etc.)
- 🛠️ **Tool System**:
  - Decorator-based tool registration (`@tool`)
  - Class-based tools (`BaseTool`)
  - Auto-discovery of tools
- 📦 **Built-in Tools**:
  - `web_search` — Web search via DuckDuckGo
  - `fetch_url` — Fetch and extract text from URLs
  - `read_file` — Read file contents
  - `write_file` — Write content to files
  - `list_directory` — List directory contents
  - `run_shell` — Execute shell commands
  - `execute_python` — Run Python code in sandbox
- 💾 **Conversation Memory**:
  - SQLite-backed persistent storage
  - Conversation history management
  - Token usage tracking
- 🎨 **CLI**:
  - `openmind chat` — Interactive chat sessions
  - `openmind config` — Configuration management
  - `openmind test` — Provider testing
  - `openmind providers` — List providers
  - `openmind tools` — List tools
  - `openmind serve` — API server (coming soon)
- ⚡ **Streaming** — Real-time token streaming for all providers
- 📄 **Configuration**:
  - YAML config file (`~/.openmind/config.yaml`)
  - Environment variable overrides
  - CLI overrides
- 📚 **Documentation**:
  - Comprehensive README
  - Contributing guide
  - Code of conduct
- 🧪 **Testing**:
  - Unit tests for agent, tools, and providers
  - Mock providers for testing
- 📦 **Packaging**:
  - Modern `pyproject.toml` packaging
  - Optional dependencies for each provider
  - Development dependencies

### Technical Details
- Python 3.10+ required
- MIT License
- Type hints throughout
- Comprehensive docstrings

## [0.0.1] - 2024-01-01

### Added
- Initial project structure
- Basic README and LICENSE

---

## Release Notes

### v0.1.0 — Initial Release

This is the first public release of OpenMind! 🎉

**Highlights:**
- Full agentic loop implementation
- Three LLM providers (OpenAI, Groq, Ollama)
- Seven built-in tools
- Beautiful CLI with streaming support
- SQLite conversation memory
- YAML configuration

**Getting Started:**
```bash
pip install openmind-agent
export GROQ_API_KEY="your-key"
openmind chat
```

**What's Next:**
- REST API server
- More providers (Anthropic, Cohere, etc.)
- Advanced memory (vector search, RAG)
- Tool marketplace
- Web UI

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE).
