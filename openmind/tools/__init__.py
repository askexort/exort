"""
Built-in tools for the OpenMind agent.

Tools are registered via the :func:`~openmind.tools.base.tool` decorator
or by subclassing :class:`~openmind.tools.base.BaseTool`.
"""

from openmind.tools import code as _code  # noqa: F401
from openmind.tools import file as _file  # noqa: F401
from openmind.tools import shell as _shell  # noqa: F401

# Import built-in tools so they register via decorators
from openmind.tools import web as _web  # noqa: F401
from openmind.tools.base import BaseTool, ToolRegistry, tool

__all__ = ["ToolRegistry", "BaseTool", "tool"]
