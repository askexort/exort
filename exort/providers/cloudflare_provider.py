"""
Cloudflare Workers AI provider — run models at the edge.

Sign up: https://dash.cloudflare.com
"""

import json
import os
from typing import Optional
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class CloudflareProvider(BaseProvider):
    name = "cloudflare"

    def __init__(self, **kw):
        super().__init__(**kw)
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        default_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
        self.base_url = self.base_url or default_url
        try:
            from openai import OpenAI
            self._c = OpenAI(api_key=self.api_key or "x", base_url=self.base_url)
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install openai")
        model = model or self.default_model or "@cf/meta/llama-3.3-70b-instruct"
        kw = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if tools:
            kw["tools"], kw["tool_choice"] = tools, "auto"
        if stream:
            return self._do_stream(**kw)
        r = self._c.chat.completions.create(**kw)
        ch = r.choices[0]
        tc = [{"id": t.id, "name": t.function.name, "arguments": json.loads(t.function.arguments)}
              for t in (ch.message.tool_calls or [])]
        u = {"prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens,
             "total_tokens": r.usage.total_tokens} if r.usage else {}
        return ProviderResponse(content=ch.message.content or "", tool_calls=tc,
                                usage=u, model=r.model, finish_reason=ch.finish_reason or "")

    def _do_stream(self, **kw):
        for chunk in self._c.chat.completions.create(**kw, stream=True):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def ok(self):
        return bool(self._c and self.api_key and os.environ.get("CLOUDFLARE_ACCOUNT_ID"))


register("cloudflare", CloudflareProvider)
