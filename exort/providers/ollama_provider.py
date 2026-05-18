"""
Ollama provider — 100% local inference.

Install: https://ollama.ai
Pull a model: ollama pull llama3.1
"""

import json
from typing import Optional
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class OllamaProvider(BaseProvider):
    name = "ollama"
    needs_key = False

    def __init__(self, **kw):
        super().__init__(**kw)
        self.base_url = self.base_url or "http://localhost:11434/v1"
        try:
            from openai import OpenAI
            self._c = OpenAI(api_key="ollama", base_url=self.base_url)
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install openai")
        model = model or self.default_model or "llama3.1"
        kw = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if tools:
            kw["tools"] = tools
        r = self._c.chat.completions.create(**kw)
        ch = r.choices[0]
        tc = [{"id": t.id, "name": t.function.name, "arguments": json.loads(t.function.arguments)}
              for t in (ch.message.tool_calls or [])] if ch.message.tool_calls else []
        u = {"prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens,
             "total_tokens": r.usage.total_tokens} if r.usage else {}
        return ProviderResponse(content=ch.message.content or "", tool_calls=tc,
                                usage=u, model=r.model, finish_reason=ch.finish_reason or "")

    def ok(self):
        return bool(self._c)


register("ollama", OllamaProvider)
