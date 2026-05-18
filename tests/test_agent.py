"""Tests for the Agent class."""

from unittest.mock import MagicMock, patch

import pytest

from Exort.agent import Agent
from Exort.config import Config
from Exort.providers.base import BaseProvider, ProviderResponse


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    name = "mock"

    @property
    def default_model(self):
        return "mock-model"

    def generate(self, messages, tools=None, temperature=0.7, max_tokens=4096, **kwargs):
        return ProviderResponse(
            content="Hello! I'm a mock response.",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            model="mock-model",
            finish_reason="stop",
        )


class MockToolProvider(BaseProvider):
    """Mock provider that makes a tool call then responds."""

    name = "mock-tool"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._call_count = 0

    @property
    def default_model(self):
        return "mock-model"

    def generate(self, messages, tools=None, temperature=0.7, max_tokens=4096, **kwargs):
        self._call_count += 1
        if self._call_count == 1:
            # First call: make a tool call
            return ProviderResponse(
                content="",
                tool_calls=[{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "arguments": '{"query": "test"}',
                    },
                }],
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                model="mock-model",
                finish_reason="tool_calls",
            )
        else:
            # Second call: final response
            return ProviderResponse(
                content="Tool result processed successfully.",
                usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                model="mock-model",
                finish_reason="stop",
            )


class TestAgent:
    """Tests for Agent initialization and basic operations."""

    def test_agent_creation(self):
        agent = Agent(provider=MockProvider())
        assert agent.provider.name == "mock"
        assert agent.provider.model == "mock-model"

    def test_agent_chat(self):
        agent = Agent(provider=MockProvider())
        response = agent.chat("Hello")
        assert response == "Hello! I'm a mock response."

    def test_agent_chat_with_conversation_id(self):
        agent = Agent(provider=MockProvider())
        response = agent.chat("Hello", conversation_id="test-conv")
        assert response == "Hello! I'm a mock response."
        assert agent.conversation_id is None  # Not auto-set

    def test_agent_reset(self):
        agent = Agent(provider=MockProvider())
        agent.chat("Hello")
        assert agent.conversation_id is not None
        agent.reset()
        assert agent.conversation_id is None

    def test_agent_stats(self):
        agent = Agent(provider=MockProvider())
        agent.chat("Hello")
        stats = agent.get_stats()
        assert stats["total_tokens"] == 15
        assert stats["provider"] == "mock"
        assert stats["model"] == "mock-model"

    def test_agent_tool_loop(self):
        """Test the agentic loop with tool calls."""
        from Exort.tools.base import ToolRegistry, tool

        registry = ToolRegistry()

        @tool(name="test_tool", description="A test tool")
        def test_tool(query: str) -> str:
            return f"Result for {query}"

        registry.register(test_tool._Exort_tool)

        agent = Agent(provider=MockToolProvider(), tools=registry)
        response = agent.chat("Use the tool")
        assert response == "Tool result processed successfully."

    def test_agent_repr(self):
        agent = Agent(provider=MockProvider())
        repr_str = repr(agent)
        assert "mock" in repr_str
        assert "mock-model" in repr_str


class TestAgentConfig:
    """Tests for Agent with custom config."""

    def test_custom_config(self):
        config = Config(overrides={"temperature": 0.5, "max_tokens": 1000})
        agent = Agent(provider=MockProvider(), config=config)
        assert agent.config.get("temperature") == 0.5
        assert agent.config.get("max_tokens") == 1000
