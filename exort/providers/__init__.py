"""
Provider registry — maps names to LLM backends.

Supported: groq (free), openai, ollama (local), anthropic,
           together, mistral, gemini, deepseek, perplexity,
           fireworks, cohere, replicate, xai, huggingface,
           moonshot, siliconflow, openrouter, custom
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
    return sorted(_registry.keys())


def provider_info() -> list[dict]:
    """Return info about all registered providers."""
    info = []
    for name, cls in sorted(_registry.items()):
        info.append({
            "name": name,
            "class": cls.__name__,
            "needs_key": getattr(cls, "needs_key", True),
        })
    return info


# Auto-register all providers
def _boot():
    # Core providers (always available)
    from exort.providers import groq_provider, openai_provider, ollama_provider
    from exort.providers import custom_provider

    # New providers (graceful import)
    for mod_name in [
        "anthropic_provider", "together_provider", "mistral_provider",
        "mimo_provider",
        "gemini_provider", "deepseek_provider", "perplexity_provider",
        "fireworks_provider", "cohere_provider", "replicate_provider",
        "xai_provider", "huggingface_provider", "moonshot_provider",
        "siliconflow_provider", "openrouter_provider",
    ]:
        try:
            __import__(f"exort.providers.{mod_name}")
        except ImportError:
            pass

_boot()

__all__ = ["BaseProvider", "ProviderResponse", "get_provider", "register",
           "list_providers", "provider_info"]
