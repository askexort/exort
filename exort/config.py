"""
Configuration management for Exort Agent.

Supports:
  - YAML config at ~/.exort/config.yaml
  - Environment variables via .env
  - Multiple profiles
  - Runtime overrides
"""

import os
import shutil
from pathlib import Path
from typing import Any, Optional

import yaml


def get_exort_home() -> Path:
    """Get the Exort home directory. Respects EXORT_HOME env var."""
    home = os.environ.get("EXORT_HOME")
    if home:
        return Path(home)
    return Path.home() / ".exort"


DEFAULTS = {
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "providers": {
        "groq": {
            "api_key_env": "GROQ_API_KEY",
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama-3.3-70b-versatile",
        },
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
        },
        "ollama": {
            "api_key_env": None,
            "base_url": "http://localhost:11434/v1",
            "default_model": "llama3.1",
        },
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com/v1",
            "default_model": "claude-sonnet-4-20250514",
        },
    },
    "agent": {
        "max_iterations": 25,
        "max_tokens": 4096,
        "temperature": 0.7,
        "system_prompt": None,  # Uses built-in default
    },
    "memory": {
        "enabled": True,
        "max_history": 50,
    },
    "skills": {
        "enabled": True,
        "auto_load": [],
    },
    "tools": {
        "enabled": True,
        "allow_dangerous": False,
    },
    "display": {
        "show_token_usage": True,
        "show_tool_calls": True,
        "color": True,
        "streaming": True,
    },
    "telegram": {
        "token_env": "TELEGRAM_BOT_TOKEN",
        "max_tokens": 2048,
        "allowed_users": [],  # Empty = allow all
        "rate_limit_per_min": 10,
    },
}


class Config:
    """
    Exort configuration manager.

    Usage:
        cfg = Config()
        model = cfg.get("model")
        cfg.set("provider", "openai")
        cfg.save()
    """

    def __init__(self, path: Optional[str] = None, profile: Optional[str] = None):
        self._home = get_exort_home()
        self._profile = profile or os.environ.get("EXORT_PROFILE", "default")
        self._path = Path(path) if path else self._home / "config.yaml"
        self._data: dict = {}
        self._load()
        self._load_env()

    def _load(self):
        """Load config from YAML, merging with defaults."""
        merged = self._deep_copy(DEFAULTS)
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
            merged = self._deep_merge(merged, user_cfg)
        self._data = merged

    def _load_env(self):
        """Load .env file from exort home directory."""
        env_path = self._home / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip(""'")
                        if key and key not in os.environ:
                            os.environ[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-notation key. e.g. 'providers.groq.api_key_env'"""
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any):
        """Set a config value by dot-notation key."""
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value

    def save(self):
        """Save current config to YAML file."""
        self._home.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for a provider from env vars."""
        provider = provider or self.get("provider", "groq")
        env_var = self.get(f"providers.{provider}.api_key_env")
        if env_var:
            return os.environ.get(env_var)
        return None

    def get_provider_config(self, provider: Optional[str] = None) -> dict:
        """Get full provider config."""
        provider = provider or self.get("provider", "groq")
        return self.get(f"providers.{provider}", {})

    @property
    def data(self) -> dict:
        return self._data

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _deep_copy(d: dict) -> dict:
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = Config._deep_copy(v)
            else:
                result[k] = v
        return result

    def __repr__(self):
        return f"Config(path={self._path}, provider={self.get('provider')}, model={self.get('model')})"


def ensure_exort_home():
    """Create ~/.exort/ directory structure if it doesn't exist."""
    home = get_exort_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "skills").mkdir(exist_ok=True)
    (home / "logs").mkdir(exist_ok=True)
    return home
