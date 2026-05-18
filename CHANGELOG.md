# Changelog

## v1.0.0 (2024)

### 🎉 Initial Major Release

**Core Agent:**
- Think → Act → Observe agent loop with tool use
- Multi-provider support (Groq, OpenAI, Ollama, Anthropic)
- Streaming responses
- Token usage tracking

**Tools:**
- Web search (DuckDuckGo, no API key needed)
- URL fetching
- File read/write/list/search
- Shell command execution
- Python code execution
- Image analysis (vision models)

**Memory:**
- SQLite-backed conversation persistence
- Full-text search across all messages
- Session management

**CLI:**
- Interactive REPL with slash commands
- Rich terminal formatting
- Setup wizard

**Telegram Bot:**
- Per-user conversation memory
- Tool use in Telegram
- Rate limiting
- Group chat support
- Model selection via inline buttons

**Infrastructure:**
- Docker support
- GitHub Actions CI
- Comprehensive documentation
