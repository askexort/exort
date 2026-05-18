"""
The Exort Engine — autonomous reasoning core.

The engine drives a cycle:

    PERCEIVE  →  read user input + tool results
    REASON    →  LLM decides what to do next
    ACT       →  call a tool / return final answer
    REFLECT   →  observe the result, loop or finish

This is the "brain" of Exort.  It is provider-agnostic — any LLM
that speaks the OpenAI tool-calling protocol works.

Usage:
    from exort import Engine

    e = Engine()
    print(e.talk("Summarize the latest Python 3.13 changes"))

    # Streaming
    for chunk in e.talk("Tell me a story", stream=True):
        print(chunk, end="", flush=True)

    # Persistent conversation
    e.open("my project")
    e.talk("Build a REST API")
    e.talk("Now add auth")           # remembers context
    e.close()
"""

import json
import time
from typing import Generator, Optional

from exort.config import Config
from exort.memory.store import ConversationStore
from exort.providers import get_provider
from exort.providers.base import ProviderResponse
from exort.tools.gear import GearBox

# ── Built-in system prompt ────────────────────────────────
_SYSTEM = """You are Exort, an open-source AI agent engine.

You have access to gear (tools) that let you take real actions:
{gear_catalog}

HOW TO WORK:
- Read the user\'s request carefully.
- If you need information, USE YOUR GEAR — don\'t guess.
- Think step-by-step for complex tasks.
- When writing code, test it by running it.
- Be direct and useful. No filler.
- If a tool errors, try a different approach.

You are honest: if you don\'t know, say so."""


class Engine:
    """
    The Exort reasoning engine.

    Wraps an LLM provider with tool execution in a perceive → reason → act loop.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[Config] = None,
        memory: Optional[ConversationStore] = None,
        gear: Optional[GearBox] = None,
        persona: Optional[str] = None,
        verbose: bool = False,
    ):
        self.cfg = config or Config()
        self.mem = memory or ConversationStore()
        self.gear = gear or GearBox()
        self.gear.discover()

        # Provider
        self._prov_name = provider or self.cfg.get("engine.provider", "groq")
        self._model = model or self.cfg.get("engine.model")
        pcfg = self.cfg.provider_conf(self._prov_name)
        self.provider = get_provider(
            self._prov_name,
            api_key=self.cfg.api_key(self._prov_name),
            base_url=pcfg.get("endpoint"),
            default_model=self._model or pcfg.get("model"),
        )

        # Tuning
        self._max_rounds = self.cfg.get("engine.max_rounds", 20)
        self._max_tokens = self.cfg.get("engine.max_tokens", 4096)
        self._temperature = self.cfg.get("engine.temperature", 0.7)
        self._verbose = verbose

        # System prompt (with optional persona override)
        self._system = persona or self.cfg.get("engine.persona") or self._build_system()

        # Session state
        self._session: Optional[str] = None
        self._history: list[dict] = []
        self._stats = {"prompt_tok": 0, "completion_tok": 0, "total_tok": 0, "gear_calls": 0, "turns": 0}

    # ── System prompt ─────────────────────────────────────

    def _build_system(self) -> str:
        catalog = []
        for g in self.gear._gear.values():
            props = g.spec.params.get("properties", {})
            req = g.spec.params.get("required", [])
            lines = []
            for pname, pinfo in props.items():
                tag = " *" if pname in req else ""
                lines.append(f"      {pname}{tag}: {pinfo.get(\"description\", pinfo.get(\"type\", \"\"))}")
            param_block = "\n".join(lines) or "      (none)"
            catalog.append(f"  [{g.spec.name}]\n    {g.spec.info}\n    Params:\n{param_block}")
        return _SYSTEM.format(gear_catalog="\n\n".join(catalog))

    # ── Session management ────────────────────────────────

    def open(self, title: str = "New session") -> str:
        """Start a persistent conversation."""
        self._session = self.mem.create(title)
        self._history = []
        self._stats = {"prompt_tok": 0, "completion_tok": 0, "total_tok": 0, "gear_calls": 0, "turns": 0}
        return self._session

    def close(self):
        """End the current session."""
        self._session = None
        self._history = []

    def resume(self, session_id: str):
        """Load a previous session."""
        self._session = session_id
        self._history = self.mem.messages(session_id)

    # ── Main entry point ──────────────────────────────────

    def talk(self, text: str, stream: bool = False) -> str | Generator[str, None, None]:
        """
        Send a message and get a response.

        The engine will reason, call tools as needed, and return
        a final answer.  Pass stream=True to get chunk-by-chunk output.
        """
        if not self._session:
            self.open(text[:60])

        self._history.append({"role": "user", "content": text})
        self.mem.add(self._session, "user", text)

        messages = [{"role": "system", "content": self._system}] + self._history
        schemas = self.gear.schemas() if self.cfg.get("gear.enabled") else None

        if stream:
            return self._cycle_stream(messages, schemas)
        return self._cycle_sync(messages, schemas)

    # ── Synchronous cycle ─────────────────────────────────

    def _cycle_sync(self, messages: list[dict], schemas: list[dict]) -> str:
        rounds = 0
        while rounds < self._max_rounds:
            rounds += 1
            try:
                resp = self.provider.chat(
                    messages=messages, model=self._model,
                    tools=schemas, temperature=self._temperature,
                    max_tokens=self._max_tokens, stream=False,
                )
            except Exception as exc:
                return f"[Engine error: {exc}]"

            self._track(resp.usage)

            if not resp.tool_calls:
                answer = resp.content
                self._history.append({"role": "assistant", "content": answer})
                if self._session:
                    self.mem.add(self._session, "assistant", answer,
                                 tokens=resp.usage.get("completion_tokens", 0))
                self._stats["turns"] += 1
                return answer

            messages = self._run_gear(resp, messages)

        return "[Max reasoning rounds reached — try a more specific request.]"

    # ── Streaming cycle ───────────────────────────────────

    def _cycle_stream(self, messages: list[dict], schemas: list[dict]):
        rounds = 0
        while rounds < self._max_rounds:
            rounds += 1
            try:
                resp = self.provider.chat(
                    messages=messages, model=self._model,
                    tools=schemas, temperature=self._temperature,
                    max_tokens=self._max_tokens, stream=False,
                )
            except Exception as exc:
                yield f"\n[Engine error: {exc}]"
                return

            self._track(resp.usage)

            if not resp.tool_calls:
                answer = resp.content
                self._history.append({"role": "assistant", "content": answer})
                if self._session:
                    self.mem.add(self._session, "assistant", answer,
                                 tokens=resp.usage.get("completion_tokens", 0))
                self._stats["turns"] += 1
                for i in range(0, len(answer), 4):
                    yield answer[i:i+4]
                    time.sleep(0.008)
                return

            messages = self._run_gear(resp, messages)
            for g in (resp.tool_calls or []):
                yield f"\n  [{g[\'name\']}] running...\n"

        yield "\n[Max rounds reached]"

    # ── Gear execution ────────────────────────────────────

    def _run_gear(self, resp: ProviderResponse, messages: list[dict]) -> list[dict]:
        """Execute tool calls and append results to message chain."""
        assistant_msg = {"role": "assistant", "content": resp.content or "", "tool_calls": []}
        messages.append(assistant_msg)

        for tc in resp.tool_calls:
            name, args, tid = tc["name"], tc["arguments"], tc["id"]

            if self._verbose or self.cfg.get("display.show_gear_calls"):
                brief = json.dumps(args, default=str)[:80]
                print(f"  [{name}] {brief}")

            result = self.gear.run(name, args)
            result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
            if len(result_str) > 8000:
                result_str = result_str[:8000] + "\n...[truncated]"

            assistant_msg["tool_calls"].append({
                "id": tid, "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, default=str)},
            })
            messages.append({"role": "tool", "tool_call_id": tid, "content": result_str})
            self._stats["gear_calls"] += 1

        return messages

    # ── Stats ─────────────────────────────────────────────

    def _track(self, usage: dict):
        if usage:
            self._stats["prompt_tok"] += usage.get("prompt_tokens", 0)
            self._stats["completion_tok"] += usage.get("completion_tokens", 0)
            self._stats["total_tok"] += usage.get("total_tokens", 0)

    @property
    def stats(self) -> dict:
        return self._stats.copy()

    def status(self) -> dict:
        return {
            "provider": self._prov_name,
            "model": self._model or self.provider.default_model,
            "session": self._session,
            "turns": self._stats["turns"],
            "gear_calls": self._stats["gear_calls"],
            "tokens": {k: self._stats[k] for k in ("prompt_tok", "completion_tok", "total_tok")},
            "gear_count": len(self.gear),
        }

    def reset(self):
        self._history.clear()
        self._stats = {"prompt_tok": 0, "completion_tok": 0, "total_tok": 0, "gear_calls": 0, "turns": 0}

    def __repr__(self):
        return f"Engine({self._prov_name}/{self._model}, gear={len(self.gear)})"
