"""
Provider registry — maps provider names to implementations.

Supported providers:
  - groq: Groq Cloud (free tier available, very fast)
  - openai: OpenAI / any OpenAI-compatible API
  - ollama: Local models via Ollama
  - anthropic: Anthropic Claude models
"""

from typing import Optional

from exort.providers.base import BaseProvider, ProviderResponse


_providers = {}


def register_provider(name: str, provider_class: type):
    """Register a provider class."""
    _providers[name] = provider_class


def get_provider(name: str, **kwargs) -> BaseProvider:
    """Get a provider instance by name."""
    if name not in _providers:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_providers.keys())}")
    return _providers[name](**kwargs)


def list_providers() -> list[str]:
    """List available provider names."""
    return list(_providers.keys())


# Auto-register providers
def _discover():
    """Import provider modules to trigger registration."""
    from exort.providers import groq_provider, openai_provider, ollama_provider
    try:
        from exort.providers import anthropic_provider
    except ImportError:
        pass  # anthropic SDK not installed


_discover()

__all__ = ["BaseProvider", "ProviderResponse", "get_provider", "register_provider", "list_providers"]
