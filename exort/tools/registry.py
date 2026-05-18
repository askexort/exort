"""
Tool registry — discovers and manages tools.

Tools self-register by calling registry.register() at module import time.
The agent imports all tool modules on startup to populate the registry.
"""

import importlib
import inspect
from typing import Any, Callable, Optional


class ToolSchema:
    """OpenAI-compatible function tool schema."""

    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters

    def to_openai(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Tool:
    """Registered tool with schema and handler."""

    def __init__(self, schema: ToolSchema, handler: Callable, dangerous: bool = False):
        self.schema = schema
        self.handler = handler
        self.dangerous = dangerous

    def __repr__(self):
        return f"Tool({self.schema.name})"


class ToolRegistry:
    """
    Central registry of all available tools.

    Usage:
        registry = ToolRegistry()
        registry.discover()  # Auto-discover built-in tools

        # Get tools for the LLM
        schemas = registry.get_schemas()

        # Execute a tool
        result = registry.call("web_search", {"query": "hello"})
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
        dangerous: bool = False,
    ):
        """Register a tool."""
        schema = ToolSchema(name, description, parameters)
        self._tools[name] = Tool(schema, handler, dangerous)

    def discover(self):
        """Auto-discover and register all built-in tools."""
        modules = [
            "exort.tools.web",
            "exort.tools.file_ops",
            "exort.tools.shell",
            "exort.tools.code",
            "exort.tools.vision",
        ]
        for mod_name in modules:
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "register_tools"):
                    mod.register_tools(self)
            except ImportError as e:
                pass  # Tool not available (missing deps)

    def get_schemas(self) -> list[dict]:
        """Get OpenAI-compatible tool schemas for the LLM."""
        return [tool.schema.to_openai() for tool in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def call(self, name: str, arguments: dict) -> Any:
        """Execute a tool by name with arguments."""
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        tool = self._tools[name]
        try:
            result = tool.handler(**arguments)
            if isinstance(result, str):
                return result
            return result
        except TypeError as e:
            return {"error": f"Invalid arguments for {name}: {e}"}
        except Exception as e:
            return {"error": f"Tool {name} failed: {e}"}

    def is_dangerous(self, name: str) -> bool:
        if name in self._tools:
            return self._tools[name].dangerous
        return False

    def __len__(self):
        return len(self._tools)

    def __contains__(self, name: str):
        return name in self._tools

    def __repr__(self):
        names = ", ".join(self._tools.keys())
        return f"ToolRegistry({len(self._tools)} tools: {names})"
