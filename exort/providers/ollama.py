"""
Ollama local provider.

Connects to a locally running Ollama server for fully offline
LLM inference.
"""

from __future__ import annotations

import json
import os
from typing import Any

from Exort.providers.base import BaseProvider, ProviderResponse


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider.

    Args:
        base_url: Ollama server URL (default ``http://localhost:11434``).
        model: Model name (default ``llama3.1``).
    """

    name = "ollama"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        self.server_url = (
            self.base_url
            or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        ).rstrip("/")

    @property
    def default_model(self) -> str:
        return "llama3.1"

    def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Send a chat request to the Ollama API."""
        import urllib.request

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        url = f"{self.server_url}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.server_url}. "
                f"Is the server running? Error: {exc}"
            ) from exc

        message = result.get("message", {})
        tool_calls: list[dict[str, Any]] = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                tool_calls.append({
                    "id": f"call_{id(tc)}",
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "arguments": json.dumps(func.get("arguments", {})),
                    },
                })

        usage = {
            "prompt_tokens": result.get("prompt_eval_count", 0),
            "completion_tokens": result.get("eval_count", 0),
            "total_tokens": (
                result.get("prompt_eval_count", 0)
                + result.get("eval_count", 0)
            ),
        }

        return ProviderResponse(
            content=message.get("content", ""),
            tool_calls=tool_calls,
            usage=usage,
            raw=result,
            model=self.model,
            finish_reason="stop" if result.get("done") else "",
        )
