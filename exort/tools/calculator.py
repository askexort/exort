"""
Calculator gear — evaluate math expressions safely.
"""

import math
import operator


_SAFE_OPS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "pow": pow, "int": int, "float": float,
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "floor": math.floor, "ceil": math.ceil, "factorial": math.factorial,
    "pi": math.pi, "e": math.e, "tau": math.tau,
    "inf": math.inf, "nan": math.nan,
    "radians": math.radians, "degrees": math.degrees,
    "hypot": math.hypot, "gcd": math.gcd,
}


def _calc(expression: str) -> dict:
    """Evaluate a math expression safely."""
    try:
        result = eval(expression, {"__builtins__": {}}, _SAFE_OPS)
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e), "expression": expression}


def register(gearbox):
    gearbox.add(
        name="calculator",
        info="Evaluate mathematical expressions. Supports: +, -, *, /, //, %, **, sin, cos, tan, sqrt, log, pow, factorial, pi, e, etc. Use for ANY math computation.",
        params={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate (e.g. 'sqrt(144)', '2**10', 'sin(pi/2)')"},
            },
            "required": ["expression"],
        },
        handler=_calc,
    )
