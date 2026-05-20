"""
Cohere provider — enterprise-grade AI, strong RAG capabilities.

Sign up: https://dashboard.cohere.com  (free trial)
Requires: pip install cohere
"""

from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class CohereProvider(BaseProvider):
    name = "cohere"
    needs_key = True

    def __init__(self, **kw):
        super().__init__(**kw)
        try:
            import cohere
            self._c = cohere.ClientV2(api_key=self.api_key or "x")
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install cohere")
        model = model or self.default_model or "command-r-plus"

        # Convert messages
        msgs = []
        system = ""
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                msgs.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                msgs.append({"role": "assistant", "content": m.get("content", "")})
            elif m["role"] == "tool":
                msgs.append({"role": "user", "content": f"Tool result: {m['content']}"})

        kw = dict(model=model, messages=msgs, temperature=temperature,
                  max_tokens=max_tokens)
        if system:
            kw["preamble"] = system

        r = self._c.chat(**kw)
        content = r.message.content[0].text if r.message.content else ""
        u = {}
        if r.usage:
            u = {
                "prompt_tokens": r.usage.tokens.input_tokens if r.usage.tokens else 0,
                "completion_tokens": r.usage.tokens.output_tokens if r.usage.tokens else 0,
                "total_tokens": (r.usage.tokens.input_tokens + r.usage.tokens.output_tokens) if r.usage.tokens else 0,
            }
        return ProviderResponse(content=content, tool_calls=[], usage=u,
                                model=model, finish_reason="complete")

    def ok(self):
        return bool(self._c and self.api_key)


register("cohere", CohereProvider)
