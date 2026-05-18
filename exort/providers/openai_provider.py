"""
OpenAI / OpenAI-compatible provider.

Works with OpenAI, together.ai, fireworks.ai, groq, or any
OpenAI-compatible API endpoint.
"""

import json
from typing import Generator, Optional

from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register_provider


class OpenAIProvider(BaseProvider):
    name = "openai"
    requires_api_key = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key or "dummy",
                base_url=self.base_url,
            )
        except ImportError:
            self._client = None

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ):
        if not self._client:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        model = model or self.default_model or "gpt-4o-mini"
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        if stream:
            return self._stream(**kwargs)

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
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
            model=response.model,
            finish_reason=choice.finish_reason or "",
        )

    def _stream(self, **kwargs):
        """Streaming generator."""
        stream = self._client.chat.completions.create(**kwargs, stream=True)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def validate(self) -> bool:
        if not self._client:
            return False
        if not self.api_key:
            return False
        return True


# Register with provider name variants
register_provider("openai", OpenAIProvider)
