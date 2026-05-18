"""
LLM provider implementations.

Supported providers:

- **openai** - OpenAI API and compatible endpoints
- **ollama** - Local Ollama server
- **groq** - Groq cloud (free tier available)
"""

from Exort.providers.base import BaseProvider, ProviderResponse
from Exort.providers.groq import GroqProvider
from Exort.providers.ollama import OllamaProvider
from Exort.providers.openai import OpenAIProvider

PROVIDERS = {
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "groq": GroqProvider,
}


def get_provider(name: str, **kwargs) -> BaseProvider:
    """Factory function to get a provider by name.

    Args:
        name: Provider name (openai, ollama, groq).
        **kwargs: Provider-specific configuration.

    Returns:
        An initialized BaseProvider instance.

    Raises:
        ValueError: If the provider name is unknown.
    """
    name = name.lower().strip()
    if name not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS.keys()))
        raise ValueError(
            f"Unknown provider '{name}'. Available: {available}"
        )
    return PROVIDERS[name](**kwargs)


__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "OpenAIProvider",
    "OllamaProvider",
    "GroqProvider",
    "get_provider",
    "PROVIDERS",
]
