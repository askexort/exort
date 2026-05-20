"""
Exort utilities — terminal formatting, IDs, helpers.
Futuristic UI with gold/amber palette.
"""

import os
import sys
import uuid
import time
import shutil
from datetime import datetime


# ── ANSI palette ──────────────────────────────────────────
# Exort uses a warm amber/gold palette — distinct identity.

class C:
    """Color codes."""
    RST = "\033[0m"
    B   = "\033[1m"
    DIM = "\033[2m"
    UND = "\033[4m"
    BLK = "\033[30m"
    RED = "\033[31m"
    GRN = "\033[32m"
    YEL = "\033[33m"
    BLU = "\033[34m"
    MAG = "\033[35m"
    CYN = "\033[36m"
    WHT = "\033[37m"

    # 256-color palette
    ACC  = "\033[38;5;220m"   # gold — Exort's signature
    ACC2 = "\033[38;5;214m"   # amber
    HI   = "\033[97m"         # bright white
    GRY   = "\033[38;5;240m"  # subtle gray
    GRY2  = "\033[38;5;245m"  # medium gray
    GOLD  = "\033[38;5;220m"  # alias
    CYAN  = "\033[38;5;51m"   # neon cyan
    PURP  = "\033[38;5;141m"  # purple

    @staticmethod
    def off():
        for a in dir(C):
            if a.isupper() and not a.startswith("_"):
                setattr(C, a, "")


def uid() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now().isoformat()


def fmt_tokens(u: dict) -> str:
    return f"[{u.get('prompt_tok',0)} in / {u.get('completion_tok',0)} out / {u.get('total_tok',0)} total]"


def fmt_time(sec: float) -> str:
    if sec < 1:
        return f"{sec*1000:.0f}ms"
    return f"{sec:.1f}s" if sec < 60 else f"{int(sec//60)}m {sec%60:.0f}s"


def get_terminal_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def box_line(text: str, width: int = 60, align: str = "left") -> str:
    """Create a box line with borders."""
    if align == "center":
        text = text.center(width - 4)
    elif align == "right":
        text = text.rjust(width - 4)
    else:
        text = text.ljust(width - 4)
    return f"  {C.GRY}│{C.RST} {text} {C.GRY}│{C.RST}"


def separator(char: str = "─", width: int = 60, color: str = "") -> str:
    """Create a separator line."""
    c = color or C.GRY
    return f"  {c}{char * width}{C.RST}"


def glow_text(text: str) -> str:
    """Create a glowing gold text effect."""
    return f"{C.ACC}{C.B}{text}{C.RST}"


def banner():
    """Print the futuristic Exort banner."""
    w = get_terminal_width()
    bw = min(62, w - 4)

    # Top border
    top = f"  {C.ACC}┌{'─' * (bw - 2)}┐{C.RST}"
    bot = f"  {C.ACC}└{'─' * (bw - 2)}┘{C.RST}"
    mid = f"  {C.ACC}├{'─' * (bw - 2)}┤{C.RST}"

    # ASCII art
    art = [
        "  ███████╗██╗  ██╗ ██████╗ ██████╗ ████████╗",
        "  ██╔════╝╚██╗██╝ ██╔═══██╗██╔══██╗╚══██╔══╝",
        "  █████╗   ╚███╝  ██║   ██║██████╔╝   ██║   ",
        "  ██╔══╝   ██╔██╗ ██║   ██║██╔══██╗   ██║   ",
        "  ███████╗██╔╝ ██╗╚██████╔╝██║  ██║   ██║   ",
        "  ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ",
    ]

    print()
    print(top)
    for line in art:
        padded = line.ljust(bw + 26)  # account for ANSI codes
        print(f"  {C.ACC}│{C.RST}{C.ACC}{C.B}{line}{C.RST}{' ' * max(0, bw - 48)}{C.ACC}│{C.RST}")
    print(mid)

    # Info lines
    version = "v2.1.0"
    tagline = "The Open Agent Engine"
    subtitle = "Free AI for Everyone"

    print(f"  {C.ACC}│{C.RST}  {C.HI}{C.B}{tagline.center(bw - 4)}{C.RST}  {C.ACC}│{C.RST}")
    print(f"  {C.ACC}│{C.RST}  {C.GRY2}{version.center(bw - 4)}{C.RST}  {C.ACC}│{C.RST}")
    print(f"  {C.ACC}│{C.RST}  {C.ACC}{subtitle.center(bw - 4)}{C.RST}  {C.ACC}│{C.RST}")
    print(bot)
    print()


def splash_screen(provider: str, model: str, gear_count: int, session_id: str = None):
    """Print a detailed startup info screen."""
    w = get_terminal_width()
    bw = min(62, w - 4)

    banner()

    # Status box
    top = f"  {C.GRY}┌{'─' * (bw - 2)}┐{C.RST}"
    bot = f"  {C.GRY}└{'─' * (bw - 2)}┘{C.RST}"
    mid = f"  {C.GRY}├{'─' * (bw - 2)}┤{C.RST}"

    print(top)
    print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ SYSTEM STATUS{C.RST}{' ' * (bw - 19)}{C.GRY}│{C.RST}")
    print(mid)

    # Status rows
    rows = [
        ("Provider", f"{C.CYN}{provider}{C.RST}"),
        ("Model", f"{C.HI}{model}{C.RST}"),
        ("Gear", f"{C.GRN}{gear_count} tools loaded{C.RST}"),
        ("Session", f"{C.GRY2}{session_id or 'auto'}{C.RST}"),
    ]

    for label, value in rows:
        # Calculate visible length (without ANSI codes)
        raw = f"  {label:<12} {value}"
        # We can't easily calculate, so just print
        print(f"  {C.GRY}│{C.RST}  {C.GRY2}{label:<12}{C.RST} {value}{' ' * max(1, bw - len(label) - 16)}{C.GRY}│{C.RST}")

    print(mid)

    # Quick commands hint
    cmds = [
        f"{C.CYN}:help{C.RST} commands",
        f"{C.CYN}:status{C.RST} info",
        f"{C.CYN}:providers{C.RST} list",
        f"{C.CYN}:quit{C.RST} exit",
    ]
    hint = "  ·  ".join(cmds)
    # Pad to fit
    print(f"  {C.GRY}│{C.RST}  {hint}{' ' * max(1, bw - 50)}{C.GRY}│{C.RST}")
    print(bot)
    print()


def loading_animation(text: str = "Initializing", duration: float = 1.5):
    """Show a loading animation."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        frame = frames[i % len(frames)]
        sys.stdout.write(f"\r  {C.ACC}{frame}{C.RST} {C.GRY2}{text}...{C.RST}")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write(f"\r  {C.GRN}✓{C.RST} {C.GRY2}{text}... done{C.RST}\n")
    sys.stdout.flush()


def progress_bar(current: int, total: int, width: int = 30, prefix: str = "") -> str:
    """Create a progress bar."""
    if total == 0:
        return ""
    pct = current / total
    filled = int(width * pct)
    bar = f"{C.ACC}{'█' * filled}{C.GRY}{'░' * (width - filled)}{C.RST}"
    return f"  {prefix} {bar} {C.ACC}{pct*100:.0f}%{C.RST}"


def tool_call_display(name: str, args_summary: str, status: str = "running"):
    """Display a tool call with status."""
    if status == "running":
        icon = f"{C.ACC}⟳{C.RST}"
        st = f"{C.ACC}running{C.RST}"
    elif status == "done":
        icon = f"{C.GRN}✓{C.RST}"
        st = f"{C.GRN}done{C.RST}"
    elif status == "error":
        icon = f"{C.RED}✗{C.RST}"
        st = f"{C.RED}error{C.RST}"
    else:
        icon = f"{C.GRY}○{C.RST}"
        st = f"{C.GRY}{status}{C.RST}"

    return f"  {icon} {C.CYN}{name}{C.RST} {C.GRY}({args_summary[:50]}){C.RST} {st}"


def response_header(provider: str, model: str):
    """Show a response header."""
    return f"  {C.GRN}▸{C.RST} {C.GRY2}{provider}/{model}{C.RST}"


def stats_line(elapsed: float, tokens: dict, gear_calls: int) -> str:
    """Create a stats display line."""
    parts = []
    parts.append(f"{C.GRY2}{fmt_time(elapsed)}{C.RST}")
    if tokens.get("total_tok"):
        parts.append(f"{C.GRY2}{tokens['total_tok']} tokens{C.RST}")
    if gear_calls:
        parts.append(f"{C.GRY2}{gear_calls} tools{C.RST}")
    return f"  {C.GRY}└─ {' · '.join(parts)}{C.RST}"


def confirm(msg: str, default: bool = False) -> bool:
    tag = "[Y/n]" if default else "[y/N]"
    try:
        r = input(f"{msg} {tag} ").strip().lower()
        return default if not r else r in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return default
