"""
Perplexity provider — search-augmented AI with real-time web access.

Sign up: https://www.perplexity.ai
"""

import json
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class PerplexityProvider(BaseProvider):
    name = "perplexity"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.base_url = self.base_url or "https://api.perplexity.ai"
        try:
            from openai import OpenAI
            self._c = OpenAI(api_key=self.api_key or "x", base_url=self.base_url)
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install openai")
        model = model or self.default_model or "sonar-pro"
        kw = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if stream:
            return self._do_stream(**kw)
        r = self._c.chat.completions.create(**kw)
        ch = r.choices[0]
        u = {"prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens,
             "total_tokens": r.usage.total_tokens} if r.usage else {}
        return ProviderResponse(content=ch.message.content or "", tool_calls=[],
                                usage=u, model=r.model, finish_reason=ch.finish_reason or "")

    def _do_stream(self, **kw):
        for chunk in self._c.chat.completions.create(**kw, stream=True):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def ok(self):
        return bool(self._c and self.api_key)


register("perplexity", PerplexityProvider)
