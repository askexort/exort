"""Tests for Exort built-in tools."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exort.tools.registry import ToolRegistry


class TestFileTools:
    """Test file operation tools."""

    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.discover()

    def test_write_and_read_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name

        try:
            result = self.registry.call("write_file", {"path": path, "content": "Hello World"})
            assert result.get("success") is True

            result = self.registry.call("read_file", {"path": path})
            assert "Hello World" in result["content"]
        finally:
            os.unlink(path)

    def test_list_directory(self):
        result = self.registry.call("list_directory", {"path": "."})
        assert "entries" in result

    def test_read_nonexistent(self):
        result = self.registry.call("read_file", {"path": "/nonexistent/file.txt"})
        assert "error" in result


class TestShellTool:
    """Test shell execution tool."""

    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.discover()

    def test_run_shell_echo(self):
        result = self.registry.call("run_shell", {"command": "echo hello"})
        assert "hello" in result.get("stdout", "")

    def test_run_shell_exit_code(self):
        result = self.registry.call("run_shell", {"command": "exit 0"})
        assert result.get("returncode") == 0


class TestCodeTool:
    """Test code execution tool."""

    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.discover()

    def test_execute_python(self):
        result = self.registry.call("execute_python", {"code": "print(2 + 3)"})
        assert result["success"] is True
        assert "5" in result["stdout"]

    def test_execute_python_error(self):
        result = self.registry.call("execute_python", {"code": "raise ValueError('test')"})
        assert result["success"] is False
        assert "ValueError" in result["stderr"]


class TestWebTools:
    """Test web tools (requires network)."""

    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.discover()

    def test_web_search(self):
        result = self.registry.call("web_search", {"query": "Python programming", "max_results": 3})
        assert isinstance(result, list)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
