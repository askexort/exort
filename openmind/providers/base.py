"""
Abstract base class for LLM providers.

All providers must implement the ``generate`` method to produce
responses from a list of conversation messages.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    """Standardized response from any LLM provider.

    Attributes:
        content: The generated text content.
        tool_calls: Parsed tool calls, if any.
        usage: Token usage dict with keys ``prompt_tokens``,
            ``completion_tokens``, ``total_tokens``.
        raw: The raw API response object for advanced use.
        model: The model identifier used for generation.
        finish_reason: Why generation stopped (e.g. "stop", "tool_calls").
    """

    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None
    model: str = ""
    finish_reason: str = ""


class BaseProvider(abc.ABC):
    """Abstract base class for LLM providers.

    Subclasses must implement :meth:`generate`.  They may also
    override :meth:`generate_stream` for streaming support.

    Args:
        api_key: API key for the provider (if required).
        model: Model identifier to use.
        base_url: Optional override for the API base URL.
        **kwargs: Additional provider-specific settings.
    """

    # Subclasses should set this to the provider's human-readable name.
    name: str = "base"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = base_url
        self.extra = kwargs

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Return the default model identifier for this provider."""

    @abc.abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Generate a response from the LLM.

        Args:
            messages: Conversation messages in OpenAI format.
                Each dict has ``role`` (system/user/assistant/tool)
                and ``content`` keys.
            tools: Optional tool definitions in OpenAI function-calling format.
            temperature: Sampling temperature (0.0–2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            A :class:`ProviderResponse` with the generated content.
        """

    def generate_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ):
        """Generate a streaming response (optional).

        Default implementation yields a single chunk from :meth:`generate`.
        Subclasses may override for true streaming.

        Yields:
            Partial :class:`ProviderResponse` objects.
        """
        yield self.generate(
            messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model!r}>"
