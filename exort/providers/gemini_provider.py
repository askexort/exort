"""
Google Gemini provider — multimodal, long context.

Sign up: https://aistudio.google.com  (free tier available)
Requires: pip install google-genai
"""

import json
from exort.providers.base import BaseProvider, ProviderResponse
from exort.providers import register


class GeminiProvider(BaseProvider):
    name = "gemini"
    needs_key = True

    def __init__(self, **kw):
        super().__init__(**kw)
        try:
            from google import genai
            self._c = genai.Client(api_key=self.api_key or "x")
        except ImportError:
            self._c = None

    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False):
        if not self._c:
            raise RuntimeError("pip install google-genai")
        model = model or self.default_model or "gemini-2.0-flash"

        # Convert OpenAI messages to Gemini format
        system = ""
        contents = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif m["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.get("content", "")}]})
            elif m["role"] == "tool":
                contents.append({"role": "user", "parts": [{"text": f"Tool result: {m['content']}"}]})

        config = {"temperature": temperature, "max_output_tokens": max_tokens}
        if system:
            config["system_instruction"] = system

        try:
            from google.genai import types
            genai_tools = []
            if tools:
                for t in tools:
                    fn = t["function"]
                    genai_tools.append(types.Tool(
                        function_declarations=[types.FunctionDeclaration(
                            name=fn["name"],
                            description=fn["description"],
                            parameters=fn["parameters"],
                        )]
                    ))
                config["tools"] = genai_tools

            r = self._c.models.generate_content(
                model=model, contents=contents, config=types.GenerateContentConfig(**config)
            )
        except Exception as e:
            return ProviderResponse(content=f"Gemini error: {e}")

        content = ""
        tc = []
        if r.candidates:
            for part in r.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    content += part.text
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tc.append({
                        "id": f"call_{fc.name}",
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })

        u = {}
        if r.usage_metadata:
            u = {
                "prompt_tokens": r.usage_metadata.prompt_token_count or 0,
                "completion_tokens": r.usage_metadata.candidates_token_count or 0,
                "total_tokens": (r.usage_metadata.prompt_token_count or 0) + (r.usage_metadata.candidates_token_count or 0),
            }
        return ProviderResponse(content=content, tool_calls=tc, usage=u,
                                model=model, finish_reason="stop")

    def ok(self):
        return bool(self._c and self.api_key)


register("gemini", GeminiProvider)
