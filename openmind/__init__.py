"""
OpenMind - Open-source AI Agent Framework
==========================================

A modular, extensible AI agent framework with multi-provider support,
tool execution, and conversation memory.

Usage::

    from openmind import Agent
    agent = Agent(provider="groq")
    agent.chat("Hello, world!")

Or via CLI::

    openmind chat --provider groq
"""

__version__ = "0.1.0"
__author__ = "OpenMind Contributors"
__license__ = "MIT"

from openmind.agent import Agent
from openmind.config import Config
from openmind.memory.store import MemoryStore
from openmind.tools.base import ToolRegistry

__all__ = ["Agent", "Config", "MemoryStore", "ToolRegistry", "__version__"]
