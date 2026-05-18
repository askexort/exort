"""
Exort Agent — the core AI agent with tool use, memory, and multi-provider support.

This is the brain of Exort. It implements a think → act → observe loop
where the LLM can use tools to accomplish tasks.

Usage:
    from exort import Agent

    # Simple usage
    agent = Agent()
    print(agent.chat("What is the weather in Tokyo?"))

    # With streaming
    for chunk in agent.chat("Tell me a story", stream=True):
        print(chunk, end="", flush=True)

    # With a specific provider
    agent = Agent(provider="ollama", model="llama3.1")
    print(agent.chat("Hello!"))

    # Interactive session (auto-saves to memory)
    agent.start_session("My Project")
    print(agent.chat("Help me build a web scraper"))
    print(agent.chat("Now add error handling"))  # Remembers previous context
    agent.end_session()
"""

import json
import sys
import time
from typing import Generator, Optional

from exort.config import Config
from exort.memory.store import MemoryStore
from exort.providers import get_provider
from exort.providers.base import ProviderResponse
from exort.tools.registry import ToolRegistry


SYSTEM_PROMPT = """You are Exort, an AI assistant that can use tools to help users.

You have access to the following tools:
{tool_descriptions}

IMPORTANT GUIDELINES:
- Think step by step before answering complex questions
- Use tools when they can help — don't guess when you can look things up
- When writing code, test it by running it
- Be concise but thorough
- If a tool returns an error, try a different approach
- Always tell the user what you're doing when using tools

You are helpful, honest, and harmless. If you don't know something, say so."""


class Agent:
    """
    The Exort AI Agent.

    Implements the core think → act → observe loop with:
    - Multi-provider LLM support (Groq, OpenAI, Ollama, Anthropic)
    - Tool use (web search, file ops, shell, code execution, vision)
    - Conversation memory (SQLite-backed, persistent)
    - Streaming responses
    - Token tracking and cost estimation
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[Config] = None,
        memory: Optional[MemoryStore] = None,
        tools: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        verbose: bool = False,
    ):
        self.config = config or Config()
        self.memory = memory or MemoryStore()
        self.tools = tools or ToolRegistry()

        # Discover and register tools
        self.tools.discover()

        # Provider setup
        self._provider_name = provider or self.config.get("provider", "groq")
        self._model = model or self.config.get("model")
        provider_cfg = self.config.get_provider_config(self._provider_name)
        api_key = self.config.get_api_key(self._provider_name)
        self.provider = get_provider(
            self._provider_name,
            api_key=api_key,
            base_url=provider_cfg.get("base_url"),
            default_model=self._model or provider_cfg.get("default_model"),
        )

        # Agent settings
        self._max_iterations = self.config.get("agent.max_iterations", 25)
        self._max_tokens = self.config.get("agent.max_tokens", 4096)
        self._temperature = self.config.get("agent.temperature", 0.7)
        self._streaming = self.config.get("display.streaming", True)
        self._verbose = verbose

        # System prompt
        self._system_prompt = system_prompt or self.config.get("agent.system_prompt") or self._build_system_prompt()

        # Session state
        self._conversation_id: Optional[str] = None
        self._messages: list[dict] = []
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._total_tool_calls = 0
        self._turn_count = 0

    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions."""
        tool_descs = []
        for tool in self.tools._tools.values():
            params = []
            props = tool.schema.parameters.get("properties", {})
            required = tool.schema.parameters.get("required", [])
            for name, info in props.items():
                req = " (required)" if name in required else ""
                params.append(f"    - {name}: {info.get('description', info.get('type', ''))}{req}")
            param_str = "\n".join(params) if params else "    (no parameters)"
            tool_descs.append(f"• {tool.schema.name}\n  {tool.schema.description}\n  Parameters:\n{param_str}")

        return SYSTEM_PROMPT.format(tool_descriptions="\n\n".join(tool_descs))

    def start_session(self, title: str = "New Chat") -> str:
        """Start a new conversation session with memory persistence."""
        self._conversation_id = self.memory.create_conversation(title)
        self._messages = []
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._total_tool_calls = 0
        self._turn_count = 0
        if self._verbose:
            print(f"[Session started: {self._conversation_id}]")
        return self._conversation_id

    def end_session(self):
        """End the current session."""
        if self._conversation_id and self._messages:
            # Save final state
            pass
        self._conversation_id = None
        self._messages = []

    def load_session(self, conversation_id: str):
        """Load an existing conversation from memory."""
        self._conversation_id = conversation_id
        self._messages = self.memory.get_history(conversation_id)

    def chat(self, user_input: str, stream: bool = False) -> str | Generator[str, None, None]:
        """
        Send a message to the agent and get a response.

        This is the main entry point. The agent will:
        1. Add your message to the conversation
        2. Send everything to the LLM
        3. If the LLM wants to use tools, execute them and loop
        4. Return the final response

        Args:
            user_input: The user's message
            stream: If True, yields response chunks

        Returns:
            The agent's response string, or a generator if streaming
        """
        # Auto-start session if needed
        if not self._conversation_id:
            self.start_session(title=user_input[:50])

        # Add user message
        self._messages.append({"role": "user", "content": user_input})
        if self._conversation_id:
            self.memory.add_message(self._conversation_id, "user", user_input)

        # Prepare messages for API
        api_messages = [{"role": "system", "content": self._system_prompt}] + self._messages

        # Get tool schemas
        tool_schemas = self.tools.get_schemas() if self.config.get("tools.enabled", True) else None

        # Agent loop: think → act → observe
        if stream:
            return self._stream_loop(api_messages, tool_schemas)
        else:
            return self._sync_loop(api_messages, tool_schemas)

    def _sync_loop(self, api_messages: list[dict], tool_schemas: list[dict]) -> str:
        """Synchronous agent loop."""
        iterations = 0
        start_time = time.time()

        while iterations < self._max_iterations:
            iterations += 1
            try:
                response = self.provider.chat(
                    messages=api_messages,
                    model=self._model,
                    tools=tool_schemas,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    stream=False,
                )
            except Exception as e:
                error_msg = f"API error: {e}"
                return error_msg

            # Track usage
            self._track_usage(response.usage)

            # If no tool calls, we're done
            if not response.tool_calls:
                final_response = response.content
                self._messages.append({"role": "assistant", "content": final_response})
                if self._conversation_id:
                    self.memory.add_message(
                        self._conversation_id, "assistant", final_response,
                        token_count=response.usage.get("completion_tokens", 0),
                    )
                self._turn_count += 1
                return final_response

            # Execute tool calls
            assistant_msg = {"role": "assistant", "content": response.content or "", "tool_calls": []}
            api_messages.append(assistant_msg)

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                if self._verbose or self.config.get("display.show_tool_calls"):
                    print(f"  ⚡ {tool_name}({json.dumps(tool_args, default=str)[:100]})")

                # Execute tool
                result = self.tools.call(tool_name, tool_args)
                result_str = json.dumps(result, default=str) if not isinstance(result, str) else result

                if len(result_str) > 8000:
                    result_str = result_str[:8000] + "\n...[truncated]"

                # Add tool result to messages
                assistant_msg["tool_calls"].append({
                    "id": tool_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(tool_args, default=str)},
                })
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result_str,
                })

                self._total_tool_calls += 1

        return "Max iterations reached. Please try a more specific request."

    def _stream_loop(self, api_messages: list[dict], tool_schemas: list[dict]):
        """Streaming agent loop — yields text chunks."""
        iterations = 0

        while iterations < self._max_iterations:
            iterations += 1

            # Check if there were tool calls in the last iteration
            # We need to make a non-streaming call if tools might be used
            # For simplicity, do a non-streaming call first, then stream if no tools
            try:
                response = self.provider.chat(
                    messages=api_messages,
                    model=self._model,
                    tools=tool_schemas,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    stream=False,
                )
            except Exception as e:
                yield f"\n[Error: {e}]"
                return

            self._track_usage(response.usage)

            if not response.tool_calls:
                # Stream the final response
                final = response.content
                self._messages.append({"role": "assistant", "content": final})
                if self._conversation_id:
                    self.memory.add_message(
                        self._conversation_id, "assistant", final,
                        token_count=response.usage.get("completion_tokens", 0),
                    )
                self._turn_count += 1
                # Yield in chunks for streaming effect
                chunk_size = 4
                for i in range(0, len(final), chunk_size):
                    yield final[i:i+chunk_size]
                    time.sleep(0.01)
                return

            # Execute tools
            assistant_msg = {"role": "assistant", "content": response.content or "", "tool_calls": []}
            api_messages.append(assistant_msg)

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                yield f"\n⚡ {tool_name}...\n"

                result = self.tools.call(tool_name, tool_args)
                result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
                if len(result_str) > 8000:
                    result_str = result_str[:8000] + "\n...[truncated]"

                assistant_msg["tool_calls"].append({
                    "id": tool_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(tool_args, default=str)},
                })
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result_str,
                })
                self._total_tool_calls += 1

        yield "\n[Max iterations reached]"

    def _track_usage(self, usage: dict):
        """Track token usage across turns."""
        if usage:
            self._total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            self._total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            self._total_usage["total_tokens"] += usage.get("total_tokens", 0)

    @property
    def usage(self) -> dict:
        """Get cumulative token usage."""
        return self._total_usage.copy()

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def tool_call_count(self) -> int:
        return self._total_tool_calls

    def get_status(self) -> dict:
        """Get current agent status."""
        return {
            "provider": self._provider_name,
            "model": self._model or self.provider.default_model,
            "conversation_id": self._conversation_id,
            "turns": self._turn_count,
            "tool_calls": self._total_tool_calls,
            "usage": self._total_usage,
            "tools_available": len(self.tools),
        }

    def reset(self):
        """Reset conversation state (keeps session)."""
        self._messages = []
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._total_tool_calls = 0
        self._turn_count = 0

    def __repr__(self):
        return f"Agent(provider={self._provider_name}, model={self._model}, tools={len(self.tools)})"
