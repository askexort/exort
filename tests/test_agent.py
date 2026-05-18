"""Tests for the Exort Agent."""

import os
import sys
import json
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exort.config import Config
from exort.tools.registry import ToolRegistry
from exort.memory.store import MemoryStore
from exort.providers.base import ProviderResponse


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    def chat(self, messages, model=None, tools=None, temperature=0.7, max_tokens=4096, stream=False):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return ProviderResponse(content="No more mock responses.", model="mock")

    def validate(self):
        return True

    @property
    def default_model(self):
        return "mock-model"


class TestToolRegistry:
    """Test the tool registry."""

    def test_create_registry(self):
        registry = ToolRegistry()
        assert len(registry) == 0

    def test_register_tool(self):
        registry = ToolRegistry()
        registry.register(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"q": {"type": "string"}}},
            handler=lambda q="": f"result: {q}",
        )
        assert "test_tool" in registry
        assert len(registry) == 1

    def test_call_tool(self):
        registry = ToolRegistry()
        registry.register(
            name="echo",
            description="Echo tool",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
            handler=lambda text="": f"echo: {text}",
        )
        result = registry.call("echo", {"text": "hello"})
        assert result == "echo: hello"

    def test_call_unknown_tool(self):
        registry = ToolRegistry()
        result = registry.call("nonexistent", {})
        assert "error" in result

    def test_get_schemas(self):
        registry = ToolRegistry()
        registry.register(
            name="my_tool",
            description="Test",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "ok",
        )
        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "my_tool"

    def test_discover(self):
        registry = ToolRegistry()
        registry.discover()
        assert len(registry) > 0
        assert "web_search" in registry
        assert "read_file" in registry
        assert "run_shell" in registry
        assert "execute_python" in registry


class TestConfig:
    """Test the config system."""

    def test_default_config(self):
        config = Config(path="/tmp/test_exort_config.yaml")
        assert config.get("provider") == "groq"
        assert config.get("model") == "llama-3.3-70b-versatile"
        assert config.get("agent.max_iterations") == 25

    def test_set_and_get(self):
        config = Config(path="/tmp/test_exort_config.yaml")
        config.set("provider", "openai")
        assert config.get("provider") == "openai"

    def test_nested_set(self):
        config = Config(path="/tmp/test_exort_config.yaml")
        config.set("agent.temperature", 0.5)
        assert config.get("agent.temperature") == 0.5

    def test_provider_config(self):
        config = Config(path="/tmp/test_exort_config.yaml")
        groq_cfg = config.get_provider_config("groq")
        assert "base_url" in groq_cfg
        assert "api_key_env" in groq_cfg


class TestMemoryStore:
    """Test the memory store."""

    def test_create_conversation(self):
        store = MemoryStore(db_path="/tmp/test_exort_memory.db")
        conv_id = store.create_conversation("Test Chat")
        assert conv_id is not None
        store.close()

    def test_add_and_get_messages(self):
        store = MemoryStore(db_path="/tmp/test_exort_memory_2.db")
        conv_id = store.create_conversation("Test")
        store.add_message(conv_id, "user", "Hello!")
        store.add_message(conv_id, "assistant", "Hi there!")

        history = store.get_history(conv_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello!"
        assert history[1]["role"] == "assistant"
        store.close()

    def test_search_messages(self):
        store = MemoryStore(db_path="/tmp/test_exort_memory_3.db")
        conv_id = store.create_conversation("Search Test")
        store.add_message(conv_id, "user", "Python is a great programming language")
        store.add_message(conv_id, "assistant", "Yes, Python is very versatile!")

        results = store.search_messages("Python")
        assert len(results) > 0
        store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
