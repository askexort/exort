"""
Provider registry — maps names to LLM backends.

Supported: groq (free), openai, ollama (local), anthropic,
           together, mistral, gemini, deepseek, perplexity,
           fireworks, cohere, replicate, xai, huggingface,
           moonshot, siliconflow, openrouter, custom,
           nvidia, cerebras, sambanova, novita, nous, minimax,
           stepfun, qwen, ollama-cloud, kimi, gmi, arcee, zai,
           volcengine, yi, zhipu, baichuan, cloudflare, deepinfra,
           lepton, writer, ai21, databricks, voyage, baseten,
           anyscale, lambda, textsynth, nebius, upstage
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
        # New providers (2026)
        "nvidia_provider", "cerebras_provider", "sambanova_provider",
        "novita_provider", "nous_provider", "minimax_provider",
        "stepfun_provider", "qwen_provider", "ollama_cloud_provider",
        "kimi_provider", "gmi_provider", "arcee_provider",
        "zai_provider", "volcengine_provider", "yi_provider",
        "zhipu_provider", "baichuan_provider", "cloudflare_provider",
        "deepinfra_provider", "lepton_provider", "writer_provider",
        "ai21_provider", "databricks_provider", "voyage_provider",
        "baseten_provider", "anyscale_provider", "lambda_provider",
        "textsynth_provider", "nebius_provider", "upstage_provider",
    ]:
        try:
            __import__(f"exort.providers.{mod_name}")
        except ImportError:
            pass

_boot()

# ── Aliases (provider name → canonical name) ──────────────────────
_aliases = {
    "xiaomi": "mimo",
    "xiaomi-mimo": "mimo",
}


def resolve_provider(name: str) -> str:
    """Resolve alias to canonical provider name."""
    return _aliases.get(name, name)


def get_provider(name: str, **kwargs) -> BaseProvider:
    name = resolve_provider(name)
    if name not in _registry:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_registry.keys())}")
    return _registry[name](**kwargs)


# Override get_provider in module scope
import exort.providers as _self
_self.get_provider = get_provider

__all__ = ["BaseProvider", "ProviderResponse", "get_provider", "register",
           "list_providers", "provider_info", "resolve_provider"]
