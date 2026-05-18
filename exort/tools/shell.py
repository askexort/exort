"""
Shell gear — run system commands.
"""

import subprocess
import os


def _run(command: str, timeout: int = 30, cwd: str = None) -> dict:
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd or os.getcwd(),
        )
        return {
            "stdout": r.stdout[:5000],
            "stderr": r.stderr[:2000],
            "exit_code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timed out after {timeout}s"}
    except Exception as exc:
        return {"error": str(exc)}


def register(gearbox):
    gearbox.add(
        name="run_shell",
        info="Execute a shell command. Returns stdout, stderr, and exit code. 30s timeout.",
        params={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
                "timeout": {"type": "integer", "description": "Seconds (default 30)", "default": 30},
                "cwd": {"type": "string", "description": "Working directory"},
            },
            "required": ["command"],
        },
        handler=_run,
        unsafe=True,
    )
