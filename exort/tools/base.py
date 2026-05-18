"""
Base tool class and @tool decorator for creating new tools.

Usage (decorator style):
    from exort.tools.base import tool

    @tool(
        name="my_tool",
        description="Does something useful",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The input"},
            },
            "required": ["query"],
        },
    )
    def my_tool(query: str) -> str:
        return f"Result for {query}"

Usage (class style):
    from exort.tools.base import BaseTool

    class MyTool(BaseTool):
        name = "my_tool"
        description = "Does something useful"
        parameters = {...}

        def run(self, query: str) -> str:
            return f"Result for {query}"
"""

from typing import Any, Callable, Optional


def tool(
    name: str,
    description: str,
    parameters: dict,
    dangerous: bool = False,
):
    """Decorator to register a function as an Exort tool."""

    def decorator(func: Callable):
        func._exort_tool = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "dangerous": dangerous,
        }
        return func

    return decorator


class BaseTool:
    """Base class for tools. Subclass and implement run()."""

    name: str = ""
    description: str = ""
    parameters: dict = {}
    dangerous: bool = False

    def run(self, **kwargs) -> Any:
        raise NotImplementedError

    def __call__(self, **kwargs) -> Any:
        return self.run(**kwargs)
