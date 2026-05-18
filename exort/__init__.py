"""
Exort — AI Agent for Everyone

An open-source AI agent framework with tool use, memory, skills,
and multi-provider support. Built for developers and non-developers alike.

Quick Start:
    from exort import Agent
    agent = Agent()
    response = agent.chat("Hello, what can you do?")
    print(response)

CLI:
    exort chat              # Interactive REPL
    exort chat "question"   # Single question
    exort serve             # Telegram bot
    exort config show       # Show configuration
"""

__version__ = "1.0.0"
__author__ = "Exort"

from exort.agent import Agent
from exort.config import Config
from exort.memory.store import MemoryStore
from exort.tools.registry import ToolRegistry

__all__ = ["Agent", "Config", "MemoryStore", "ToolRegistry"]
