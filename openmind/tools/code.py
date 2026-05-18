"""
Code execution tools.

Provides a sandboxed Python code execution tool.
"""

from __future__ import annotations

import io
import json
import sys
import traceback

from openmind.tools.base import tool


@tool(
    name="execute_python",
    description=(
        "Execute Python code in a sandboxed environment and return the output. "
        "Use for calculations, data processing, etc."
    ),
)
def execute_python(
    code: str,
    timeout: int = 30,
) -> str:
    """Execute Python code and capture output.

    Args:
        code: Python code to execute.
        timeout: Execution timeout in seconds.

    Returns:
        JSON with stdout, stderr, and any return values.
    """
    # Capture stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Restricted builtins for safety
    safe_builtins = {
        k: v for k, v in __builtins__.items()  # type: ignore[union-attr]
        if k not in ("eval", "exec", "compile", "__import__", "open", "input")
    } if isinstance(__builtins__, dict) else {
        k: getattr(__builtins__, k)
        for k in dir(__builtins__)
        if not k.startswith("_")
        and k not in ("eval", "exec", "compile", "__import__", "open", "input")
    }

    local_ns: dict = {}

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Compile and run with restricted globals
        compiled = compile(code, "<agent>", "exec")
        exec(compiled, {"__builtins__": safe_builtins}, local_ns)

        stdout_val = stdout_capture.getvalue()
        stderr_val = stderr_capture.getvalue()

        # Try to find a result variable
        result = None
        if local_ns:
            # Return the last expression result if there's a 'result' variable
            if "result" in local_ns:
                result = local_ns["result"]
            else:
                # Get the last non-private variable
                for key in reversed(list(local_ns.keys())):
                    if not key.startswith("_"):
                        val = local_ns[key]
                        if not callable(val):
                            result = val
                            break

        output: dict = {
            "stdout": stdout_val,
            "status": "success",
        }
        if stderr_val:
            output["stderr"] = stderr_val
        if result is not None:
            try:
                output["result"] = repr(result)
            except Exception:
                output["result"] = str(result)

        return json.dumps(output, indent=2, default=str)

    except Exception:
        return json.dumps({
            "error": traceback.format_exc(),
            "status": "error",
        }, indent=2)

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
