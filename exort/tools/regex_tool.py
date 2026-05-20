"""
Regex gear — pattern matching and text extraction.
"""

import re
import json


def _regex_match(text: str, pattern: str, flags: str = "") -> dict:
    """Find all matches of a regex pattern in text."""
    try:
        f = 0
        if "i" in flags.lower():
            f |= re.IGNORECASE
        if "m" in flags.lower():
            f |= re.MULTILINE
        if "s" in flags.lower():
            f |= re.DOTALL

        matches = re.findall(pattern, text, f)
        if isinstance(matches[0], tuple) if matches else False:
            matches = [list(m) for m in matches]
        return {"matches": matches[:100], "count": len(matches), "pattern": pattern}
    except Exception as e:
        return {"error": str(e)}


def _regex_replace(text: str, pattern: str, replacement: str, flags: str = "") -> dict:
    """Replace all matches of a regex pattern."""
    try:
        f = 0
        if "i" in flags.lower():
            f |= re.IGNORECASE
        if "m" in flags.lower():
            f |= re.MULTILINE
        if "s" in flags.lower():
            f |= re.DOTALL
        result = re.sub(pattern, replacement, text, flags=f)
        return {"result": result, "replacements": len(re.findall(pattern, text, f))}
    except Exception as e:
        return {"error": str(e)}


def _regex_split(text: str, pattern: str) -> dict:
    """Split text by a regex pattern."""
    try:
        parts = re.split(pattern, text)
        return {"parts": parts, "count": len(parts)}
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="regex_match",
        info="Find all matches of a regex pattern in text. Supports flags: i (ignorecase), m (multiline), s (dotall).",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to search in"},
                "pattern": {"type": "string", "description": "Regex pattern"},
                "flags": {"type": "string", "description": "Flags: i=ignorecase, m=multiline, s=dotall", "default": ""},
            },
            "required": ["text", "pattern"],
        },
        handler=_regex_match,
    )
    gearbox.add(
        name="regex_replace",
        info="Replace all matches of a regex pattern with replacement text.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to modify"},
                "pattern": {"type": "string", "description": "Regex pattern to match"},
                "replacement": {"type": "string", "description": "Replacement text"},
                "flags": {"type": "string", "description": "Flags", "default": ""},
            },
            "required": ["text", "pattern", "replacement"],
        },
        handler=_regex_replace,
    )
    gearbox.add(
        name="regex_split",
        info="Split text by a regex pattern into parts.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to split"},
                "pattern": {"type": "string", "description": "Regex pattern to split on"},
            },
            "required": ["text", "pattern"],
        },
        handler=_regex_split,
    )
