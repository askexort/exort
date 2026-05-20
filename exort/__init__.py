"""
╔═══════════════════════════════════════════════════════════╗
║  EXORT — The Open Agent Engine                            ║
║  Free AI for Everyone                                     ║
╚═══════════════════════════════════════════════════════════╝

Exort is an autonomous agent engine that reasons, acts, and
learns through direct tool interaction. No paid dependencies
required — runs on free-tier APIs or fully offline with Ollama.

Quick Start:
    from exort import Engine
    engine = Engine()
    engine.talk("What can you do?")

Or from the terminal:
    exort                    # launch interactive shell
    exort ask "hello"        # one-shot question
    exort bot                # start Telegram bot
"""

__version__ = "2.1.0"
__author__ = "Exort Contributors"
__license__ = "MIT"

from exort.engine import Engine
from exort.config import Config
from exort.memory.store import ConversationStore
from exort.tools.gear import GearBox

__all__ = ["Engine", "Config", "ConversationStore", "GearBox"]
