"""Tests for Exort built-in gear."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exort.tools.gear import GearBox


class TestFileGear:
    def setup_method(self):
        self.gb = GearBox()
        self.gb.discover()

    def test_write_read(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            p = f.name
        try:
            r = self.gb.run("write_file", {"path": p, "content": "hello"})
            assert r.get("ok") is True
            r = self.gb.run("read_file", {"path": p})
            assert "hello" in r["content"]
        finally:
            os.unlink(p)

    def test_listdir(self):
        r = self.gb.run("list_directory", {"path": "."})
        assert "entries" in r


class TestShellGear:
    def setup_method(self):
        self.gb = GearBox()
        self.gb.discover()

    def test_echo(self):
        r = self.gb.run("run_shell", {"command": "echo hi"})
        assert "hi" in r.get("stdout", "")


class TestCodeGear:
    def setup_method(self):
        self.gb = GearBox()
        self.gb.discover()

    def test_exec(self):
        r = self.gb.run("exec_python", {"code": "print(2+3)"})
        assert r["ok"] is True
        assert "5" in r["stdout"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
