"""
Anthropic provider — Claude models.

Requires: pip install anthropic
"""

import json
from typing import Optional
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, **kw):
        super().__init__(**kw)
        try:
            import anthropic
            self._c = anthropic.Anthropic(api_key=self.api_key or "x")
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install anthropic")
        model = model or self.default_model or "claude-sonnet-4-20250514"
        sys = ""
        msgs = []
        for m in messages:
            if m["role"] == "system":
                sys = m["content"]
            else:
                msgs.append(m)
        kw = dict(model=model, messages=msgs, max_tokens=max_tokens, temperature=temperature)
        if sys:
            kw["system"] = sys
        if tools:
            kw["tools"] = [{"name": t["function"]["name"], "description": t["function"]["description"],
                             "input_schema": t["function"]["parameters"]} for t in tools]
        r = self._c.messages.create(**kw)
        content, tc = "", []
        for b in r.content:
            if b.type == "text":
                content += b.text
            elif b.type == "tool_use":
                tc.append({"id": b.id, "name": b.name, "arguments": b.input})
        u = {"prompt_tokens": r.usage.input_tokens, "completion_tokens": r.usage.output_tokens,
             "total_tokens": r.usage.input_tokens + r.usage.output_tokens} if r.usage else {}
        return ProviderResponse(content=content, tool_calls=tc, usage=u,
                                model=r.model, finish_reason=r.stop_reason or "")

    def ok(self):
        return bool(self._c and self.api_key)


register("anthropic", AnthropicProvider)
