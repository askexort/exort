"""
Shell execution tools — run shell commands safely.
"""

import os
import subprocess
import sys


def _run_shell(command: str, timeout: int = 30, cwd: str = None) -> dict:
    """Run a shell command and capture output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        if len(output) > 5000:
            output = output[:5000] + "\n...[truncated]"
        return {
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000] if result.stderr else "",
            "returncode": result.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s", "command": command}
    except Exception as e:
        return {"error": f"Failed to run command: {e}", "command": command}


def register_tools(registry):
    """Register shell tools."""
    registry.register(
        name="run_shell",
        description="Execute a shell command and return the output. Use this for system commands, git operations, package management, etc. Commands timeout after 30 seconds.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                    "default": 30,
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory (optional, defaults to current dir)",
                },
            },
            "required": ["command"],
        },
        handler=_run_shell,
        dangerous=True,
    )
