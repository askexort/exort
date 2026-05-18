"""Tests for the tool system."""

import json
import os
import tempfile

import pytest

from Exort.tools.base import BaseTool, ToolRegistry, tool


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_tool(self):
        registry = ToolRegistry()

        class MyTool(BaseTool):
            name = "my_tool"
            description = "A test tool"

            def execute(self, query: str = "test") -> str:
                return f"Result: {query}"

        registry.register(MyTool())
        assert "my_tool" in registry
        assert len(registry) == 1

    def test_register_function(self):
        registry = ToolRegistry()

        def my_func(name: str) -> str:
            return f"Hello, {name}!"

        registry.register_function(my_func, name="greet", description="Greet someone")
        assert "greet" in registry
        result = registry.execute("greet", {"name": "World"})
        assert result == "Hello, World!"

    def test_tool_decorator(self):
        @tool(name="calc", description="Calculate something")
        def calc(a: int, b: int) -> str:
            """Add two numbers."""
            return str(a + b)

        assert hasattr(calc, "_Exort_tool")
        t = calc._Exort_tool
        assert t.name == "calc"
        assert t.execute(a=2, b=3) == "5"

    def test_get_tool_definitions(self):
        registry = ToolRegistry()

        class MyTool(BaseTool):
            name = "search"
            description = "Search for something"

            def execute(self, query: str) -> str:
                return f"Results for {query}"

        registry.register(MyTool())
        defs = registry.get_tool_definitions()
        assert len(defs) == 1
        assert defs[0]["type"] == "function"
        assert defs[0]["function"]["name"] == "search"

    def test_execute_nonexistent_tool(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError):
            registry.execute("nonexistent", {})

    def test_list_tools(self):
        registry = ToolRegistry()

        class ToolA(BaseTool):
            name = "alpha"
            description = "Alpha tool"

            def execute(self) -> str:
                return "alpha"

        class ToolB(BaseTool):
            name = "beta"
            description = "Beta tool"

            def execute(self) -> str:
                return "beta"

        registry.register(ToolA())
        registry.register(ToolB())
        assert registry.list_tools() == ["alpha", "beta"]

    def test_auto_discover(self):
        registry = ToolRegistry()
        registry.auto_discover()
        # Should find the built-in tools
        assert len(registry) > 0
        assert "web_search" in registry or "run_shell" in registry


class TestBuiltinTools:
    """Tests for built-in tools."""

    def test_read_file(self):
        from Exort.tools.file import read_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!")
            f.flush()
            result = read_file(f.name)
            assert "Hello, World!" in result

        os.unlink(f.name)

    def test_write_file(self):
        from Exort.tools.file import write_file

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            result = write_file(path, "Hello!")
            parsed = json.loads(result)
            assert parsed["success"] is True

    def test_list_directory(self):
        from Exort.tools.file import list_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            open(os.path.join(tmpdir, "a.txt"), "w").close()
            open(os.path.join(tmpdir, "b.txt"), "w").close()
            result = list_directory(tmpdir)
            parsed = json.loads(result)
            assert len(parsed["entries"]) == 2

    def test_execute_python(self):
        from Exort.tools.code import execute_python

        result = execute_python("result = 2 + 2")
        parsed = json.loads(result)
        assert parsed["status"] == "success"
        assert "4" in parsed.get("result", "")

    def test_execute_python_with_output(self):
        from Exort.tools.code import execute_python

        result = execute_python("print('hello')")
        parsed = json.loads(result)
        assert parsed["status"] == "success"
        assert "hello" in parsed.get("stdout", "")
