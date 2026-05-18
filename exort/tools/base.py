"""
Tool registry and base classes.

Provides the plugin system for registering and invoking tools.
Tools can be created by subclassing :class:`BaseTool` or by using
the :func:`tool` decorator.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any


class BaseTool:
    """Abstract base class for tools.

    Subclasses must set ``name`` and ``description`` class attributes
    and implement :meth:`execute`.

    Example::

        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does something useful"

            def execute(self, query: str) -> str:
                return f"Result for {query}"
    """

    name: str = ""
    description: str = ""

    def get_parameters_schema(self) -> dict[str, Any]:
        """Return an OpenAI-compatible parameters JSON schema.

        Override for custom schemas. Default implementation inspects
        the ``execute`` method signature.
        """
        sig = inspect.signature(self.execute)
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            prop: dict[str, Any] = {"type": "string"}
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                }
                prop["type"] = type_map.get(param.annotation, "string")
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            properties[param_name] = prop

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    def to_openai_tool(self) -> dict[str, Any]:
        """Return the tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema(),
            },
        }

    def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given arguments.

        Returns:
            A string result to feed back to the LLM.
        """
        raise NotImplementedError


class ToolDecoratorTool(BaseTool):
    """Wrapper that turns a decorated function into a BaseTool."""

    def __init__(self, func: Callable[..., str], name: str, description: str) -> None:
        self._func = func
        self.name = name
        self.description = description

    def execute(self, **kwargs: Any) -> str:
        return self._func(**kwargs)


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable:
    """Decorator to register a function as a tool.

    Example::

        @tool(name="greet", description="Greet someone")
        def greet(name: str) -> str:
            return f"Hello, {name}!"
    """

    def decorator(func: Callable[..., str]) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]
        wrapper = ToolDecoratorTool(func, tool_name, tool_desc)
        # Attach metadata so the registry can discover it
        wrapper._is_Exort_tool = True  # type: ignore[attr-defined]
        func._Exort_tool = wrapper  # type: ignore[attr-defined]
        return func

    return decorator


class ToolRegistry:
    """Registry that manages all available tools.

    Example::

        registry = ToolRegistry()
        registry.register(MyTool())
        registry.register_function(my_func, name="my_func")

        # Get OpenAI-format tool definitions
        definitions = registry.get_tool_definitions()

        # Execute a tool call
        result = registry.execute("my_func", {"query": "hello"})
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool_instance: BaseTool) -> None:
        """Register a tool instance."""
        if not tool_instance.name:
            raise ValueError("Tool must have a 'name' attribute")
        self._tools[tool_instance.name] = tool_instance

    def register_function(
        self,
        func: Callable[..., str],
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Register a plain function as a tool."""
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]
        wrapper = ToolDecoratorTool(func, tool_name, tool_desc)
        self._tools[tool_name] = wrapper

    def auto_discover(self) -> None:
        """Discover and register all ``@tool``-decorated functions
        that have been imported."""
        # This scans tool modules for decorated functions
        for module_name in ("web", "file", "shell", "code"):
            try:
                mod = __import__(f"Exort.tools.{module_name}", fromlist=[module_name])
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if callable(attr) and hasattr(attr, "_Exort_tool"):
                        t = attr._Exort_tool
                        if t.name not in self._tools:
                            self._tools[t.name] = t
            except ImportError:
                pass

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return all tools in OpenAI function-calling format."""
        return [t.to_openai_tool() for t in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name.

        Args:
            name: Tool name.
            arguments: Keyword arguments for the tool.

        Returns:
            The tool's string result.

        Raises:
            KeyError: If the tool is not registered.
        """
        tool_inst = self._tools.get(name)
        if tool_inst is None:
            available = ", ".join(sorted(self._tools.keys()))
            raise KeyError(
                f"Tool '{name}' not found. Available: {available}"
            )
        try:
            return tool_inst.execute(**arguments)
        except Exception as exc:
            return f"Error executing tool '{name}': {exc}"

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.list_tools()}>"
