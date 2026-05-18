"""
LLM provider implementations.

Supported providers:

- **openai** - OpenAI API and compatible endpoints
- **ollama** - Local Ollama server
- **groq** - Groq cloud (free tier available)
"""

from openmind.providers.base import BaseProvider, ProviderResponse
from openmind.providers.openai import OpenAIProvider
from openmind.providers.ollama import OllamaProvider
from openmind.providers.groq import GroqProvider

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
