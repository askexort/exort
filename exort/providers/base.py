"""
Base provider — abstract interface for LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator, Optional


@dataclass
class ProviderResponse:
    """Response from an LLM provider."""
    content: str = ""
    tool_calls: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""
    finish_reason: str = ""
    raw: dict = field(default_factory=dict)


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement chat() which sends messages to an LLM
    and returns a ProviderResponse.
    """

    name: str = ""
    requires_api_key: bool = True

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 default_model: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> ProviderResponse | Generator[str, None, None]:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: OpenAI-format message list [{"role": ..., "content": ...}]
            model: Model override (uses default_model if None)
            tools: OpenAI-format tool schemas
            temperature: Sampling temperature
            max_tokens: Max response tokens
            stream: If True, yields chunk strings

        Returns:
            ProviderResponse (non-streaming) or generator of strings (streaming)
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Check if the provider is properly configured (API key, etc.)."""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(model={self.default_model})"
