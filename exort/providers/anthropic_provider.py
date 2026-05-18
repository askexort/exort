"""
Anthropic provider — Claude models.

Requires: pip install anthropic
"""

import json
from typing import Generator, Optional

from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register_provider


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    requires_api_key = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key or "dummy")
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
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        model = model or self.default_model or "claude-sonnet-4-20250514"

        # Extract system message (Anthropic uses separate system param)
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                # Convert OpenAI format to Anthropic format
                chat_messages.append(msg)

        kwargs = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            # Convert OpenAI tools to Anthropic format
            anthropic_tools = []
            for t in tools:
                func = t.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                })
            kwargs["tools"] = anthropic_tools

        if stream:
            return self._stream(**kwargs)

        response = self._client.messages.create(**kwargs)

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason or "",
        )

    def _stream(self, **kwargs):
        with self._client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def validate(self) -> bool:
        return bool(self._client and self.api_key)


register_provider("anthropic", AnthropicProvider)
