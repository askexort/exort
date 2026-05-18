"""
Groq cloud provider.

Uses Groq's fast inference API with a generous free tier.
Ideal for getting started without spending money.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openmind.providers.base import BaseProvider, ProviderResponse


class GroqProvider(BaseProvider):
    """Groq cloud LLM provider.

    Args:
        api_key: Groq API key. Falls back to ``GROQ_API_KEY`` env var.
        model: Model name (default ``llama-3.1-8b-instant``).
    """

    name = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "The 'groq' package is required. Install it with: "
                "pip install groq"
            )
        self.client = Groq(
            api_key=self.api_key or os.environ.get("GROQ_API_KEY"),
        )

    @property
    def default_model(self) -> str:
        return "llama-3.1-8b-instant"

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Send a chat completion request to the Groq API."""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**params)
        choice = response.choices[0]

        tool_calls: List[Dict[str, Any]] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return ProviderResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
            model=response.model,
            finish_reason=choice.finish_reason or "",
        )

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ):
        """Stream chat completion tokens from the Groq API."""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        stream = self.client.chat.completions.create(**params)

        collected_content = ""
        collected_tool_calls: Dict[int, Dict[str, Any]] = {}

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                collected_content += delta.content
                yield ProviderResponse(
                    content=collected_content,
                    model=chunk.model,
                )

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in collected_tool_calls:
                        collected_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                        tc = collected_tool_calls[idx]
                        if tc_delta.id:
                            tc["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tc["function"]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tc["function"]["arguments"] += tc_delta.function.arguments

        if collected_tool_calls:
            yield ProviderResponse(
                content=collected_content,
                tool_calls=[collected_tool_calls[k] for k in sorted(collected_tool_calls)],
                model=self.model,
                finish_reason="tool_calls",
            )
