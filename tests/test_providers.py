"""Tests for LLM providers."""

import pytest

from openmind.providers.base import BaseProvider, ProviderResponse
from openmind.providers import get_provider, PROVIDERS


class TestBaseProvider:
    """Tests for the base provider interface."""

    def test_provider_response_defaults(self):
        resp = ProviderResponse()
        assert resp.content == ""
        assert resp.tool_calls == []
        assert resp.usage == {}
        assert resp.model == ""
        assert resp.finish_reason == ""

    def test_provider_response_with_data(self):
        resp = ProviderResponse(
            content="Hello!",
            usage={"total_tokens": 100},
            model="test-model",
        )
        assert resp.content == "Hello!"
        assert resp.usage["total_tokens"] == 100


class TestProviderFactory:
    """Tests for provider factory function."""

    def test_get_provider_unknown(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")

    def test_providers_registry(self):
        assert "openai" in PROVIDERS
        assert "ollama" in PROVIDERS
        assert "groq" in PROVIDERS

    def test_provider_count(self):
        assert len(PROVIDERS) == 3


class TestProviderClasses:
    """Tests for provider class attributes."""

    def test_openai_provider_class(self):
        from openmind.providers.openai import OpenAIProvider
        assert OpenAIProvider.name == "openai"
        p = OpenAIProvider()
        assert p.default_model == "gpt-4o-mini"

    def test_ollama_provider_class(self):
        from openmind.providers.ollama import OllamaProvider
        assert OllamaProvider.name == "ollama"
        p = OllamaProvider()
        assert p.default_model == "llama3.1"

    def test_groq_provider_class(self):
        from openmind.providers.groq import GroqProvider
        assert GroqProvider.name == "groq"
        p = GroqProvider()
        assert p.default_model == "llama-3.1-8b-instant"
