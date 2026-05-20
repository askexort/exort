# Changelog

## v2.1.0 (2026)

### 🚀 Massive Provider & Tool Expansion

**18 LLM Providers (up from 4):**
- Groq (free), OpenAI, Ollama (local), Anthropic
- Together AI, Mistral, Google Gemini, DeepSeek
- Perplexity, Fireworks AI, Cohere, Replicate
- xAI (Grok), Hugging Face, Moonshot, SiliconFlow
- OpenRouter (200+ models gateway)
- Custom (any OpenAI-compatible endpoint)

**New CLI Commands:**
- `exort providers list` — list all providers
- `exort providers add <name> --key <key>` — configure provider
- `exort providers remove <name>` — remove provider
- `exort providers test [name]` — test provider connections
- `exort skills` — list available skills/playbooks

**29 Tools (up from 6):**
- Core: web_search, fetch_url, read_file, write_file, list_directory, search_files, run_shell, exec_python, load_image
- Calculator: math expressions with sin/cos/sqrt/log/etc
- DateTime: now, convert, diff between dates
- JSON: parse, format, query (dot notation), merge
- HTTP: full REST client (GET/POST/PUT/DELETE/PATCH)
- CSV: read, parse, convert from JSON
- Hash: md5/sha256/sha512/blake2b + base64 encode/decode
- UUID: generate (v1/v4) and validate
- Text: word_count, case_convert, extract_emails/urls, word_frequency
- Regex: match, replace, split with flags
- URL: parse, encode, decode, build
- Diff: text_diff, file_diff, text_similarity
- Color: convert between hex/rgb/hsl

**17 Built-in Skill Playbooks:**
- web-research, code-review, debugging, data-analysis
- api-design, security-audit, performance, git-workflow
- python-best-practices, creative-writing, summarization
- math-solving, email-drafting, devops, project-management
- regex-guide, markdown-guide

**Resilience Layer:**
- 11 providers in failover chain (up from 4)
- Multi-key rotation for all providers
- Priority-based auto-failover

**Other:**
- Version bump to 2.1.0
- Updated setup wizard with 10 provider choices
- Gear categorized by type in display
- Playbook library with builtin + user-created skills

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
