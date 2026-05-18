"""
Exort - Open-source AI Agent Framework
==========================================

A modular, extensible AI agent framework with multi-provider support,
tool execution, and conversation memory.

Usage::

    from Exort import Agent
    agent = Agent(provider="groq")
    agent.chat("Hello, world!")

Or via CLI::

    Exort chat --provider groq
"""

__version__ = "0.1.0"
__author__ = "Exort Contributors"
__license__ = "MIT"

from Exort.agent import Agent
from Exort.config import Config
from Exort.memory.store import MemoryStore
from Exort.tools.base import ToolRegistry

__all__ = ["Agent", "Config", "MemoryStore", "ToolRegistry", "__version__"]
