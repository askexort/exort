"""
Shell command execution tools.

Provides a tool for running shell commands with safety guards.
"""

from __future__ import annotations

import json
import subprocess
import shlex
from typing import Optional

from openmind.tools.base import tool

# Commands that are always blocked for safety
BLOCKED_COMMANDS = frozenset({
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:",
    "chmod -R 777 /", "shutdown", "reboot", "halt", "poweroff",
})


def _is_safe_command(command: str) -> bool:
    """Basic safety check for shell commands."""
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return False
    return True


@tool(
    name="run_shell",
    description="Execute a shell command and return stdout/stderr. Use with caution.",
)
def run_shell(
    command: str,
    timeout: int = 30,
    working_directory: Optional[str] = None,
) -> str:
    """Execute a shell command.

    Args:
        command: The shell command to execute.
        timeout: Timeout in seconds (default 30).
        working_directory: Working directory for the command.

    Returns:
        JSON with stdout, stderr, and return code.
    """
    if not _is_safe_command(command):
        return json.dumps({
            "error": "Command blocked for safety reasons.",
            "command": command,
        })

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_directory,
        )
        output = {
            "stdout": result.stdout[:50000],  # Cap output
            "stderr": result.stderr[:10000],
            "returncode": result.returncode,
            "command": command,
        }
        if result.returncode != 0:
            output["status"] = "error"
        else:
            output["status"] = "success"
        return json.dumps(output, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": f"Command timed out after {timeout}s",
            "command": command,
        })
    except Exception as exc:
        return json.dumps({
            "error": f"Failed to execute command: {exc}",
            "command": command,
        })
