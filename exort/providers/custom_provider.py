"""
Custom provider — bring your own LLM API.

Works with any OpenAI-compatible endpoint:
  Together AI, Fireworks, DeepSeek, Mistral, Groq, OpenRouter,
  LM Studio, Ollama, vLLM, text-generation-inference, etc.

Usage:
  from exort.providers.custom_provider import CustomProvider
  p = CustomProvider(api_key="sk-...", base_url="https://api.together.xyz/v1",
                     default_model="meta-llama/Llama-3-70b-chat-hf")
  resp = p.chat([{"role": "user", "content": "hello"}])
"""

import json
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class CustomProvider(BaseProvider):
    name = "custom"

    def __init__(self, **kw):
        super().__init__(**kw)
        if not self.base_url:
            raise ValueError("Custom provider requires base_url (the API endpoint)")
        try:
            from openai import OpenAI
            self._c = OpenAI(api_key=self.api_key or "not-needed", base_url=self.base_url)
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install openai")
        model = model or self.default_model
        if not model:
            raise ValueError("No model specified. Set default_model or pass model= kwarg")
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
        return bool(self._c and self.base_url)


# Register under "custom" — also used for user-added providers
register("custom", CustomProvider)
