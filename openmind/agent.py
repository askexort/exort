"""
Core agent implementation.

The Agent class implements the agentic loop:

    think → act → observe → repeat

It orchestrates LLM providers, tools, and memory to create
autonomous AI agents that can reason, use tools, and learn.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Generator
from typing import Any

from openmind.config import Config
from openmind.memory.store import MemoryStore
from openmind.providers import get_provider
from openmind.providers.base import BaseProvider
from openmind.tools.base import ToolRegistry
from openmind.utils import (
    generate_id,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools. Use them when needed.

When you need to perform actions or get information, use the available tools.
Think step by step and explain your reasoning.
If you don't need tools, just respond directly.

Be concise but thorough. Always strive for accuracy."""


class Agent:
    """OpenMind AI Agent.

    Implements the think → act → observe loop for autonomous
    AI interactions with tool use.

    Args:
        provider: LLM provider name ("openai", "ollama", "groq") or
            a BaseProvider instance.
        model: Model name (uses provider default if not specified).
        config: Config instance (creates default if not specified).
        system_prompt: Custom system prompt.
        tools: ToolRegistry instance (creates default if not specified).
        memory: MemoryStore instance (creates default if not specified).
        on_thought: Callback for agent thoughts.
        on_action: Callback for tool calls.
        on_observation: Callback for tool results.
        on_response: Callback for final responses.

    Example::

        agent = Agent(provider="groq")
        response = agent.chat("What's the weather in Tokyo?")

        # Streaming
        for chunk in agent.chat_stream("Tell me a story"):
            print(chunk, end="")
    """

    def __init__(
        self,
        provider: str | BaseProvider = "groq",
        model: str | None = None,
        config: Config | None = None,
        system_prompt: str | None = None,
        tools: ToolRegistry | None = None,
        memory: MemoryStore | None = None,
        on_thought: Callable[[str], None] | None = None,
        on_action: Callable[[str, dict], None] | None = None,
        on_observation: Callable[[str], None] | None = None,
        on_response: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config or Config()

        # Initialize provider
        if isinstance(provider, str):
            self.provider = get_provider(
                provider,
                model=model,
            )
        else:
            self.provider = provider

        # Initialize tools
        self.tools = tools or ToolRegistry()
        if self.config.get("tools.auto_discover", True):
            self.tools.auto_discover()

        # Initialize memory
        self.memory = memory or MemoryStore(
            db_path=self.config.get("memory.db_path")
        )

        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.conversation_id: str | None = None
        self.max_iterations = self.config.get("max_iterations", 10)

        # Callbacks
        self._on_thought = on_thought
        self._on_action = on_action
        self._on_observation = on_observation
        self._on_response = on_response

        # State
        self._total_tokens = 0
        self._iteration_count = 0

    def _build_messages(
        self,
        user_message: str,
        conversation_id: str | None = None,
        include_history: bool = True,
    ) -> list[dict[str, str]]:
        """Build the message list for the LLM.

        Args:
            user_message: The user's message.
            conversation_id: Conversation ID for history retrieval.
            include_history: Whether to include past messages.

        Returns:
            List of message dicts in OpenAI format.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Add conversation history
        if include_history and conversation_id:
            history = self.memory.get_history(conversation_id)
            # Exclude system messages (we already added ours)
            history = [m for m in history if m["role"] != "system"]
            messages.extend(history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _handle_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Execute tool calls and add results to messages.

        Args:
            tool_calls: List of tool call dicts from the LLM.
            messages: Message list to append results to.

        Returns:
            Updated message list with tool results.
        """
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args_str = func.get("arguments", "{}")

            # Parse arguments
            try:
                arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                arguments = {}

            # Callbacks
            if self._on_action:
                self._on_action(name, arguments)

            logger.debug("Executing tool: %s(%s)", name, arguments)

            # Execute the tool
            result = self.tools.execute(name, arguments)

            # Callback
            if self._on_observation:
                self._on_observation(result)

            logger.debug("Tool result: %s", result[:200])

            # Add assistant tool call message
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tc],
            })

            # Add tool result message
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

        return messages

    def chat(
        self,
        message: str,
        conversation_id: str | None = None,
        stream: bool | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a message and get a response.

        Implements the full agentic loop: think → act → observe → repeat.

        Args:
            message: User message text.
            conversation_id: Conversation ID (auto-generated if not provided).
            stream: Whether to stream the response.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Returns:
            The assistant's response text.
        """
        if conversation_id is None:
            if self.conversation_id is None:
                self.conversation_id = generate_id()
                self.memory.create_conversation(
                    self.conversation_id,
                    provider=self.provider.name,
                    model=self.provider.model,
                )
            conversation_id = self.conversation_id

        # Save user message to memory
        self.memory.add_message(conversation_id, "user", message)

        # Build messages
        messages = self._build_messages(message, conversation_id)

        # Get tool definitions
        tool_defs = self.tools.get_tool_definitions() if self.tools else None

        temp = temperature or self.config.get("temperature", 0.7)
        tokens = max_tokens or self.config.get("max_tokens", 4096)

        # Agentic loop
        final_content = ""
        for iteration in range(self.max_iterations):
            self._iteration_count += 1

            response = self.provider.generate(
                messages=messages,
                tools=tool_defs if tool_defs else None,
                temperature=temp,
                max_tokens=tokens,
            )

            # Track tokens
            if response.usage:
                self._total_tokens += response.usage.get("total_tokens", 0)

            # If there are tool calls, handle them
            if response.tool_calls:
                # Callback
                if self._on_thought:
                    self._on_thought(
                        f"Iteration {iteration + 1}: Using tools..."
                    )

                messages = self._handle_tool_calls(response.tool_calls, messages)
                continue  # Loop back for the next LLM call

            # No tool calls — we have a final response
            final_content = response.content
            break
        else:
            final_content = (
                "I've reached the maximum number of tool use iterations. "
                "Here's what I have so far:\n\n" + (response.content if response else "")
            )

        # Save assistant response to memory
        self.memory.add_message(
            conversation_id,
            "assistant",
            final_content,
            token_count=response.usage.get("completion_tokens", 0) if response else 0,
        )

        # Callback
        if self._on_response:
            self._on_response(final_content)

        return final_content

    def chat_stream(
        self,
        message: str,
        conversation_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Stream a chat response token by token.

        Args:
            message: User message text.
            conversation_id: Conversation ID.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Yields:
            Partial response text chunks.
        """
        if conversation_id is None:
            if self.conversation_id is None:
                self.conversation_id = generate_id()
                self.memory.create_conversation(
                    self.conversation_id,
                    provider=self.provider.name,
                    model=self.provider.model,
                )
            conversation_id = self.conversation_id

        self.memory.add_message(conversation_id, "user", message)
        messages = self._build_messages(message, conversation_id)
        tool_defs = self.tools.get_tool_definitions() if self.tools else None

        temp = temperature or self.config.get("temperature", 0.7)
        tokens = max_tokens or self.config.get("max_tokens", 4096)

        # For streaming, we handle tool calls non-streaming
        for _iteration in range(self.max_iterations):
            last_response = None
            for chunk in self.provider.generate_stream(
                messages=messages,
                tools=tool_defs if tool_defs else None,
                temperature=temp,
                max_tokens=tokens,
            ):
                last_response = chunk
                if chunk.content and not chunk.tool_calls:
                    yield chunk.content

            if last_response is None:
                break

            if last_response.tool_calls:
                messages = self._handle_tool_calls(last_response.tool_calls, messages)
                continue

            # Save final response
            self.memory.add_message(
                conversation_id,
                "assistant",
                last_response.content,
                token_count=(
                    last_response.usage.get("completion_tokens", 0)
                    if last_response.usage else 0
                ),
            )
            break

    def reset(self) -> None:
        """Reset agent state for a new conversation."""
        self.conversation_id = None
        self._total_tokens = 0
        self._iteration_count = 0

    def get_stats(self) -> dict[str, Any]:
        """Get agent usage statistics.

        Returns:
            Dict with token usage, iteration count, etc.
        """
        return {
            "total_tokens": self._total_tokens,
            "iteration_count": self._iteration_count,
            "conversation_id": self.conversation_id,
            "provider": self.provider.name,
            "model": self.provider.model,
            "tools_registered": len(self.tools),
        }

    def __repr__(self) -> str:
        return (
            f"<Agent provider={self.provider.name!r} "
            f"model={self.provider.model!r} "
            f"tools={len(self.tools)}>"
        )
