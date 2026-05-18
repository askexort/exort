"""Tests for the Exort Engine."""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exort.config import Config
from exort.tools.gear import GearBox
from exort.memory.store import ConversationStore
from exort.providers.base import ProviderResponse


class MockProvider:
    """Mock LLM for testing."""
    def __init__(self, responses=None):
        self.responses = responses or []
        self._i = 0
    def chat(self, messages, model=None, tools=None, temperature=0.7, max_tokens=4096, stream=False):
        if self._i < len(self.responses):
            r = self.responses[self._i]; self._i += 1; return r
        return ProviderResponse(content="done.", model="mock")
    def ok(self): return True
    @property
    def default_model(self): return "mock"


class TestGearBox:
    def test_empty(self):
        gb = GearBox()
        assert len(gb) == 0

    def test_register(self):
        gb = GearBox()
        gb.add("echo", "echo text", {"type": "object", "properties": {"t": {"type": "string"}}}, lambda t="": t)
        assert "echo" in gb
        assert len(gb) == 1

    def test_run(self):
        gb = GearBox()
        gb.add("add", "add", {"type": "object", "properties": {}}, lambda: 42)
        assert gb.run("add", {}) == 42

    def test_unknown(self):
        gb = GearBox()
        assert "error" in gb.run("nope", {})

    def test_schemas(self):
        gb = GearBox()
        gb.add("x", "test", {"type": "object", "properties": {}}, lambda: None)
        s = gb.schemas()
        assert s[0]["type"] == "function"
        assert s[0]["function"]["name"] == "x"

    def test_discover(self):
        gb = GearBox()
        gb.discover()
        assert len(gb) > 0
        assert "web_search" in gb
        assert "run_shell" in gb


class TestConfig:
    def test_defaults(self):
        cfg = Config(path="/tmp/test_exort_cfg.yaml")
        assert cfg.get("engine.provider") == "groq"
        assert cfg.get("engine.max_rounds") == 20

    def test_set_get(self):
        cfg = Config(path="/tmp/test_exort_cfg.yaml")
        cfg.set("engine.temperature", 0.3)
        assert cfg.get("engine.temperature") == 0.3

    def test_provider_conf(self):
        cfg = Config(path="/tmp/test_exort_cfg.yaml")
        gc = cfg.provider_conf("groq")
        assert "endpoint" in gc


class TestConversationStore:
    def test_crud(self):
        s = ConversationStore(path="/tmp/test_exort_conv.db")
        sid = s.create("test")
        s.add(sid, "user", "hello")
        s.add(sid, "assistant", "hi!")
        h = s.messages(sid)
        assert len(h) == 2
        assert h[0]["content"] == "hello"
        s.close()

    def test_search(self):
        s = ConversationStore(path="/tmp/test_exort_conv2.db")
        sid = s.create("search")
        s.add(sid, "user", "Python is great")
        r = s.search("Python")
        assert len(r) > 0
        s.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
