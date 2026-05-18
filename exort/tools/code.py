"""
Code gear — execute Python in a sandboxed namespace.
"""

import io
import sys
import traceback


def _exec(code: str) -> dict:
    old_out, old_err = sys.stdout, sys.stderr
    cap_out, cap_err = io.StringIO(), io.StringIO()
    try:
        sys.stdout, sys.stderr = cap_out, cap_err
        exec(code, {"__builtins__": __builtins__})
        return {"stdout": cap_out.getvalue()[:5000], "stderr": cap_err.getvalue()[:2000], "ok": True}
    except Exception:
        return {"stdout": cap_out.getvalue()[:2000], "stderr": traceback.format_exc()[:3000], "ok": False}
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def register(gearbox):
    gearbox.add(
        name="exec_python",
        info="Run Python code and capture output. Good for calculations, data transforms, prototyping.",
        params={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
            },
            "required": ["code"],
        },
        handler=_exec,
        unsafe=True,
    )
