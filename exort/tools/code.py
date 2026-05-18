"""
Code execution tools — run Python code safely.
"""

import io
import sys
import traceback


def _execute_python(code: str, timeout: int = 30) -> dict:
    """Execute Python code and capture output."""
    # Redirect stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Execute in isolated namespace
        namespace = {"__builtins__": __builtins__}
        exec(code, namespace)

        stdout_val = stdout_capture.getvalue()
        stderr_val = stderr_capture.getvalue()

        if len(stdout_val) > 5000:
            stdout_val = stdout_val[:5000] + "\n...[truncated]"

        return {
            "stdout": stdout_val,
            "stderr": stderr_val[:2000] if stderr_val else "",
            "success": True,
        }
    except Exception:
        stderr_val = traceback.format_exc()
        if len(stderr_val) > 3000:
            stderr_val = stderr_val[:3000] + "\n...[truncated]"
        return {
            "stdout": stdout_capture.getvalue()[:2000],
            "stderr": stderr_val,
            "success": False,
        }
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def register_tools(registry):
    """Register code execution tools."""
    registry.register(
        name="execute_python",
        description="Execute Python code and return the output. Use this for calculations, data processing, prototyping, or any Python task. The code runs in an isolated namespace.",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
            },
            "required": ["code"],
        },
        handler=_execute_python,
        dangerous=True,
    )
