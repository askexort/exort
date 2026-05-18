"""
Built-in tools for the OpenMind agent.

Tools are registered via the :func:`~openmind.tools.base.tool` decorator
or by subclassing :class:`~openmind.tools.base.BaseTool`.
"""

from openmind.tools.base import ToolRegistry, BaseTool, tool

# Import built-in tools so they register via decorators
from openmind.tools import web as _web
from openmind.tools import file as _file
from openmind.tools import shell as _shell
from openmind.tools import code as _code

__all__ = ["ToolRegistry", "BaseTool", "tool"]
