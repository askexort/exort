"""
Utility functions for Exort Agent.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Any


# ── ANSI Colors ──
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[40m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def disable():
        """Disable all colors (for non-terminal output)."""
        for attr in dir(Colors):
            if attr.isupper() and not attr.startswith("_"):
                setattr(Colors, attr, "")


def colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{Colors.RESET}"


def generate_id() -> str:
    """Generate a short unique ID."""
    return uuid.uuid4().hex[:12]


def timestamp() -> str:
    """Current timestamp in ISO format."""
    return datetime.now().isoformat()


def truncate(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def safe_json(obj: Any) -> str:
    """Safely serialize to JSON."""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


def format_tokens(usage: dict) -> str:
    """Format token usage info."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", prompt + completion)
    return f"[{prompt} in / {completion} out / {total} total]"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.0f}s"


def get_terminal_width() -> int:
    """Get terminal width, default 80."""
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80


def print_banner():
    """Print the Exort welcome banner."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
  ███████╗██╗  ██╗ ██████╗ ██████╗ ████████╗
  ██╔════╝╚██╗██╔╝██╔═══██╗██╔══██╗╚══██╔══╝
  █████╗   ╚███╔╝ ██║   ██║██████╔╝   ██║
  ██╔══╝   ██╔██╗ ██║   ██║██╔══██╗   ██║
  ███████╗██╔╝ ██╗╚██████╔╝██║  ██║   ██║
  ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝
{Colors.RESET}{Colors.DIM}  AI Agent for Everyone — v1.0.0{Colors.RESET}
"""
    print(banner)


def confirm(message: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        response = input(f"{message}{suffix}").strip().lower()
        if not response:
            return default
        return response in ("y", "yes", "true", "1")
    except (EOFError, KeyboardInterrupt):
        return False
