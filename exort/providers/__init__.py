"""
Provider registry — maps names to LLM backends.

Supported: groq (free), openai, ollama (local), anthropic
"""

from typing import Optional
from exort.providers.base import BaseProvider, ProviderResponse

_registry = {}


def register(name: str, cls: type):
    _registry[name] = cls


def get_provider(name: str, **kwargs) -> BaseProvider:
    if name not in _registry:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_registry.keys())}")
    return _registry[name](**kwargs)


def list_providers() -> list[str]:
    return list(_registry.keys())


# Auto-register
def _boot():
    from exort.providers import groq_provider, openai_provider, ollama_provider
    try:
        from exort.providers import anthropic_provider
    except ImportError:
        pass

_boot()

__all__ = ["BaseProvider", "ProviderResponse", "get_provider", "register", "list_providers"]
