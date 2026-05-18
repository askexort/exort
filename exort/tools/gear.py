"""
GearBox — the tool system for Exort.

Exort calls its tools "gear" — each piece of gear gives the agent
a new capability.  Gear self-registers via a simple convention:

    # In any file under exort/tools/:
    def register(gearbox: GearBox):
        gearbox.add(
            name="my_gear",
            info="What it does",
            params={...},
            handler=my_function,
        )

The engine discovers gear at startup by importing each module
and calling its register() function.
"""

import importlib
import json
from typing import Any, Callable, Optional


class GearSpec:
    """Schema for a single piece of gear (OpenAI-compatible)."""

    __slots__ = ("name", "info", "params")

    def __init__(self, name: str, info: str, params: dict):
        self.name = name
        self.info = info
        self.params = params

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.info,
                "parameters": self.params,
            },
        }


class Gear:
    """A registered piece of gear: spec + handler + metadata."""

    __slots__ = ("spec", "handler", "unsafe")

    def __init__(self, spec: GearSpec, handler: Callable, unsafe: bool = False):
        self.spec = spec
        self.handler = handler
        self.unsafe = unsafe


# Modules to scan for gear on startup
_BUILTIN_MODULES = [
    "exort.tools.web",
    "exort.tools.file_ops",
    "exort.tools.shell",
    "exort.tools.code",
    "exort.tools.vision",
]


class GearBox:
    """
    Central collection of all registered gear.

        gb = GearBox()
        gb.discover()                          # load built-in gear
        schemas = gb.schemas()                 # for the LLM
        result = gb.run("web_search", {"query": "hello"})
    """

    def __init__(self):
        self._gear: dict[str, Gear] = {}

    # ── Registration ──────────────────────────────────────

    def add(
        self,
        name: str,
        info: str,
        params: dict,
        handler: Callable,
        unsafe: bool = False,
    ):
        """Register a piece of gear."""
        spec = GearSpec(name, info, params)
        self._gear[name] = Gear(spec, handler, unsafe)

    def discover(self):
        """Import built-in tool modules so they register themselves."""
        for mod_name in _BUILTIN_MODULES:
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "register"):
                    mod.register(self)
            except ImportError:
                pass  # optional dependency not installed

    # ── Query ─────────────────────────────────────────────

    def schemas(self) -> list[dict]:
        """Return OpenAI-compatible tool schemas for the LLM."""
        return [g.spec.to_schema() for g in self._gear.values()]

    def names(self) -> list[str]:
        return list(self._gear.keys())

    def has(self, name: str) -> bool:
        return name in self._gear

    def is_unsafe(self, name: str) -> bool:
        g = self._gear.get(name)
        return g.unsafe if g else False

    # ── Execution ─────────────────────────────────────────

    def run(self, name: str, args: dict) -> Any:
        """Execute a piece of gear by name."""
        if name not in self._gear:
            return {"error": f"Unknown gear: {name}"}
        gear = self._gear[name]
        try:
            result = gear.handler(**args)
            return result if isinstance(result, (str, dict, list)) else str(result)
        except TypeError as exc:
            return {"error": f"Bad arguments for {name}: {exc}"}
        except Exception as exc:
            return {"error": f"{name} failed: {exc}"}

    # ── Dunder ────────────────────────────────────────────

    def __len__(self):
        return len(self._gear)

    def __contains__(self, name: str):
        return name in self._gear

    def __repr__(self):
        return f"GearBox({len(self._gear)} pieces)"
