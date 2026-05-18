"""
Configuration management for Exort.

Loads configuration from YAML files and environment variables.
Supports layered configuration with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Default configuration
DEFAULTS: dict[str, Any] = {
    "provider": "groq",
    "model": None,  # Use provider default
    "temperature": 0.7,
    "max_tokens": 4096,
    "max_iterations": 10,
    "memory": {
        "enabled": True,
        "db_path": None,  # Use default ~/.Exort/memory.db
    },
    "tools": {
        "enabled": True,
        "auto_discover": True,
    },
    "ui": {
        "stream": True,
        "show_tool_calls": True,
        "show_token_usage": True,
        "color": True,
    },
}


class Config:
    """Layered configuration manager.

    Configuration is loaded from (in order of priority):

    1. Constructor arguments
    2. Environment variables (``Exort_*``)
    3. Config file (``~/.Exort/config.yaml``)
    4. Built-in defaults

    Args:
        config_path: Path to YAML config file.
            Defaults to ``~/.Exort/config.yaml``.
        overrides: Dict of override values.

    Example::

        config = Config()
        print(config["provider"])  # "groq"

        config = Config(overrides={"provider": "openai", "model": "gpt-4o"})
        print(config["provider"])  # "openai"
    """

    def __init__(
        self,
        config_path: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> None:
        self._data: dict[str, Any] = {}
        self._config_path = config_path

        # Layer 1: Defaults
        self._data = _deep_copy(DEFAULTS)

        # Layer 2: Config file
        file_config = self._load_yaml_config(config_path)
        if file_config:
            _deep_merge(self._data, file_config)

        # Layer 3: Environment variables
        env_config = self._load_env_config()
        if env_config:
            _deep_merge(self._data, env_config)

        # Layer 4: Explicit overrides
        if overrides:
            _deep_merge(self._data, overrides)

    @property
    def config_path(self) -> Path:
        """Return the resolved config file path."""
        if self._config_path:
            return Path(self._config_path)
        return Path.home() / ".Exort" / "config.yaml"

    def _load_yaml_config(self, path: str | None = None) -> dict[str, Any]:
        """Load config from YAML file."""
        config_file = Path(path) if path else self.config_path
        if not config_file.exists():
            return {}

        try:
            import yaml
        except ImportError:
            # PyYAML not installed — try basic parsing
            return self._parse_simple_yaml(config_file)

        try:
            with open(config_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _parse_simple_yaml(self, path: Path) -> dict[str, Any]:
        """Minimal YAML parser for flat key-value configs."""
        config: dict[str, Any] = {}
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Type coercion
                    if value.lower() in ("true", "yes"):
                        config[key] = True
                    elif value.lower() in ("false", "no"):
                        config[key] = False
                    elif value.isdigit():
                        config[key] = int(value)
                    else:
                        try:
                            config[key] = float(value)
                        except ValueError:
                            config[key] = value
        except Exception:
            pass
        return config

    def _load_env_config(self) -> dict[str, Any]:
        """Load config from Exort_* environment variables."""
        config: dict[str, Any] = {}
        prefix = "Exort_"

        env_map = {
            f"{prefix}PROVIDER": ("provider", str),
            f"{prefix}MODEL": ("model", str),
            f"{prefix}TEMPERATURE": ("temperature", float),
            f"{prefix}MAX_TOKENS": ("max_tokens", int),
            f"{prefix}MAX_ITERATIONS": ("max_iterations", int),
            f"{prefix}MEMORY_DB": (["memory", "db_path"], str),
        }

        for env_var, (key, cast) in env_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    value = cast(value)
                except (ValueError, TypeError):
                    continue
                if isinstance(key, list):
                    # Nested key
                    d = config
                    for k in key[:-1]:
                        d = d.setdefault(k, {})
                    d[key[-1]] = value
                else:
                    config[key] = value

        return config

    def save(self, path: str | None = None) -> None:
        """Save current config to YAML file.

        Args:
            path: File path. Defaults to ``~/.Exort/config.yaml``.
        """
        save_path = Path(path) if path else self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import yaml
            content = yaml.dump(
                self._data, default_flow_style=False, sort_keys=True
            )
        except ImportError:
            # Fallback: simple key-value format
            lines = []
            for key, value in sorted(self._data.items()):
                if isinstance(value, dict):
                    lines.append(f"{key}:")
                    for k, v in sorted(value.items()):
                        lines.append(f"  {k}: {v}")
                else:
                    lines.append(f"{key}: {value}")
            content = "\n".join(lines) + "\n"

        save_path.write_text(content, encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-separated key.

        Args:
            key: Config key (e.g. ``"memory.enabled"``).
            default: Default value if key is not found.

        Returns:
            The config value.
        """
        keys = key.split(".")
        d = self._data
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                return default
        return d

    def set(self, key: str, value: Any) -> None:
        """Set a config value by dot-separated key.

        Args:
            key: Config key (e.g. ``"provider"``).
            value: Value to set.
        """
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def to_dict(self) -> dict[str, Any]:
        """Return a copy of the config as a dict."""
        return _deep_copy(self._data)

    def __repr__(self) -> str:
        return f"<Config provider={self._data.get('provider')!r}>"


def _deep_copy(d: dict[str, Any]) -> dict[str, Any]:
    """Deep copy a dict (no external deps)."""
    result: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy(v)
        else:
            result[k] = v
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Merge override into base (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
