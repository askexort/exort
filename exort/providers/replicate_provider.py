"""
Replicate provider — run any open model in the cloud.

Sign up: https://replicate.com  (free tier available)
Requires: pip install replicate
"""

from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class ReplicateProvider(BaseProvider):
    name = "replicate"
    needs_key = True

    def __init__(self, **kw):
        super().__init__(**kw)
        try:
            import replicate
            self._replicate = replicate
            if self.api_key:
                import os
                os.environ["REPLICATE_API_TOKEN"] = self.api_key
        except ImportError:
            self._replicate = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._replicate:
            raise RuntimeError("pip install replicate")
        model = model or self.default_model or "meta/meta-llama-3.1-405b-instruct"

        # Build prompt from messages
        prompt_parts = []
        for m in messages:
            role = m["role"]
            if role == "system":
                prompt_parts.append(f"System: {m['content']}")
            elif role == "user":
                prompt_parts.append(f"User: {m['content']}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {m.get('content', '')}")

        prompt = "\n".join(prompt_parts)

        try:
            output = self._replicate.run(
                model,
                input={"prompt": prompt, "max_new_tokens": max_tokens, "temperature": temperature}
            )
            content = "".join(str(chunk) for chunk in output)
            return ProviderResponse(content=content, tool_calls=[], usage={},
                                    model=model, finish_reason="stop")
        except Exception as e:
            return ProviderResponse(content=f"Replicate error: {e}")

    def ok(self):
        return bool(self._replicate and self.api_key)


register("replicate", ReplicateProvider)
