"""
Exort configuration system.

Manages settings, API keys, and runtime preferences.
All config lives in ~/.exort/ (or EXORT_DIR env override).

Config priority:  runtime args > env vars > config.yaml > defaults
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


def exort_dir() -> Path:
    """Return the Exort data directory. Defaults to ~/.exort/."""
    override = os.environ.get("EXORT_DIR")
    return Path(override) if override else Path.home() / ".exort"


# ── Factory Defaults ──────────────────────────────────────
# These are the sane defaults. Override in ~/.exort/config.yaml.

BUILT_IN_DEFAULTS = {
    # Which AI backend to use
    "engine": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "max_rounds": 20,           # max tool-call loops per reply
        "max_tokens": 4096,
        "temperature": 0.7,
    },

    # Provider credentials and endpoints
    "providers": {
        "groq": {
            "key_var": "GROQ_API_KEY",
            "endpoint": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
        },
        "openai": {
            "key_var": "OPENAI_API_KEY",
            "endpoint": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        },
        "ollama": {
            "key_var": None,
            "endpoint": "http://localhost:11434/v1",
            "model": "llama3.1",
        },
        "anthropic": {
            "key_var": "ANTHROPIC_API_KEY",
            "endpoint": "https://api.anthropic.com/v1",
            "model": "claude-sonnet-4-20250514",
        },
    },

    # Conversation memory
    "memory": {
        "enabled": True,
        "window": 50,               # messages kept in active context
    },

    # Gear (tool) settings
    "gear": {
        "enabled": True,
        "allow_unsafe": False,      # shell/exec require explicit opt-in
    },

    # Playbook (knowledge file) settings
    "playbooks": {
        "enabled": True,
        "autoload": [],
    },

    # Display preferences
    "display": {
        "stream": True,
        "show_gear_calls": True,
        "show_tokens": True,
        "color": True,
    },

    # Telegram bot
    "telegram": {
        "token_var": "TELEGRAM_BOT_TOKEN",
        "max_tokens": 2048,
        "rate_per_minute": 10,
        "allowed_users": [],
    },
}


class Config:
    """
    Exort configuration.

    Reads ~/.exort/config.yaml on init, merges with built-in defaults,
    and exposes .get() / .set() for dot-path access.

        cfg = Config()
        provider = cfg.get("engine.provider")       # "groq"
        cfg.set("engine.temperature", 0.3)
        cfg.save()
    """

    def __init__(self, path: Optional[str] = None):
        self._dir = exort_dir()
        self._path = Path(path) if path else self._dir / "config.yaml"
        self._data: dict = {}
        self._load_yaml()
        self._load_dotenv()

    # ── Loading ───────────────────────────────────────────

    def _load_yaml(self):
        merged = _deepcopy(BUILT_IN_DEFAULTS)
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            merged = _deepmerge(merged, user)
        self._data = merged

    def _load_dotenv(self):
        """Load key=value pairs from ~/.exort/.env into os.environ."""
        env = self._dir / ".env"
        if not env.exists():
            return
        with open(env, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip(""'")
                if k and k not in os.environ:
                    os.environ[k] = v

    # ── Access ────────────────────────────────────────────

    def get(self, dotpath: str, default: Any = None) -> Any:
        """Read a config value by dot-path.  e.g. 'engine.temperature'"""
        node = self._data
        for key in dotpath.split("."):
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, dotpath: str, value: Any):
        """Write a config value by dot-path."""
        keys = dotpath.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    def save(self):
        """Persist current config to YAML."""
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    # ── Helpers ───────────────────────────────────────────

    def api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Resolve the API key env-var for a provider."""
        prov = provider or self.get("engine.provider", "groq")
        var = self.get(f"providers.{prov}.key_var")
        return os.environ.get(var) if var else None

    def provider_conf(self, provider: Optional[str] = None) -> dict:
        """Return the full provider sub-dict."""
        prov = provider or self.get("engine.provider", "groq")
        return self.get(f"providers.{prov}", {})

    @property
    def data(self) -> dict:
        return self._data

    def __repr__(self):
        return f"Config(provider={self.get('engine.provider')}, model={self.get('engine.model')})"


# ── Private helpers ───────────────────────────────────────

def _deepcopy(d: dict) -> dict:
    return {k: _deepcopy(v) if isinstance(v, dict) else v for k, v in d.items()}


def _deepmerge(base: dict, override: dict) -> dict:
    out = base.copy()
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deepmerge(out[k], v)
        else:
            out[k] = v
    return out


def ensure_exort_dir() -> Path:
    """Create ~/.exort/ skeleton if missing. Returns the path."""
    d = exort_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "playbooks").mkdir(exist_ok=True)
    (d / "logs").mkdir(exist_ok=True)
    return d
