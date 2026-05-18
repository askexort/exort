"""
Utility functions for OpenMind.

Contains helpers for formatting, logging, and common operations.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any


# ANSI color codes
class Colors:
    """ANSI terminal color codes."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @classmethod
    def disable(cls) -> None:
        """Disable all colors."""
        for attr in dir(cls):
            if attr.isupper() and not attr.startswith("_"):
                setattr(cls, attr, "")


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Apply ANSI color to text.

    Args:
        text: Text to colorize.
        color: ANSI color code (from Colors class).
        bold: Whether to make text bold.

    Returns:
        Colorized text string.
    """
    prefix = Colors.BOLD if bold else ""
    return f"{prefix}{color}{text}{Colors.RESET}"


def print_colored(text: str, color: str, bold: bool = False, file=None) -> None:
    """Print colorized text to a file (default stderr)."""
    print(colorize(text, color, bold), file=file or sys.stderr)


def format_tool_call(name: str, arguments: dict[str, Any], color: bool = True) -> str:
    """Format a tool call for display.

    Args:
        name: Tool name.
        arguments: Tool arguments.
        color: Whether to use ANSI colors.

    Returns:
        Formatted string.
    """
    args_str = json.dumps(arguments, indent=2)
    if color:
        return (
            f"  {Colors.CYAN}⚡ {name}{Colors.RESET}\n"
            f"  {Colors.DIM}{args_str}{Colors.RESET}"
        )
    return f"  ⚡ {name}\n  {args_str}"


def format_tool_result(result: str, color: bool = True) -> str:
    """Format a tool result for display.

    Args:
        result: Tool result string.
        color: Whether to use ANSI colors.

    Returns:
        Formatted string.
    """
    # Truncate very long results
    display = result[:2000]
    if len(result) > 2000:
        display += f"\n... ({len(result) - 2000} chars truncated)"

    if color:
        return f"  {Colors.GREEN}📋 Result:{Colors.RESET}\n  {display}"
    return f"  📋 Result:\n  {display}"


def format_token_usage(usage: dict[str, int], color: bool = True) -> str:
    """Format token usage for display.

    Args:
        usage: Token usage dict.
        color: Whether to use ANSI colors.

    Returns:
        Formatted string.
    """
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", prompt + completion)

    text = f"tokens: {total} (prompt: {prompt}, completion: {completion})"
    if color:
        return f"  {Colors.DIM}📊 {text}{Colors.RESET}"
    return f"  📊 {text}"


def generate_id(prefix: str = "conv") -> str:
    """Generate a unique ID with prefix.

    Args:
        prefix: ID prefix string.

    Returns:
        Unique identifier string.
    """
    return f"{prefix}_{int(time.time() * 1000)}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def safe_json_parse(text: str) -> dict[str, Any] | None:
    """Safely parse JSON, returning None on failure.

    Args:
        text: JSON string to parse.

    Returns:
        Parsed dict or None.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def estimate_tokens(text: str) -> int:
    """Rough token count estimate.

    Uses a simple heuristic of ~4 characters per token.

    Args:
        text: Text to estimate.

    Returns:
        Estimated token count.
    """
    return len(text) // 4
