"""
Exort utilities — terminal formatting, IDs, helpers.
"""

import os
import uuid
from datetime import datetime


# ── ANSI palette ──────────────────────────────────────────
# Exort uses a warm amber/cyan palette — distinct identity.

class C:
    """Color codes."""
    RST = "\033[0m"
    B   = "\033[1m"
    DIM = "\033[2m"
    UND = "\033[4m"

    # Foreground
    BLK = "\033[30m"
    RED = "\033[31m"
    GRN = "\033[32m"
    YEL = "\033[33m"
    BLU = "\033[34m"
    MAG = "\033[35m"
    CYN = "\033[36m"
    WHT = "\033[37m"

    # Exort accent colors
    ACC = "\033[38;5;208m"   # orange — Exort's signature
    HI  = "\033[97m"         # bright white

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


def banner():
    """Print the Exort banner."""
    print(f"""
{C.ACC}{C.B}  ▓█████  ██╗  ██╗  ██████  ██████  ████████╗
  ▓█   ▀  ╚██╗██╝  ██╔═══██╗██╔══██╗╚══██╔══╝
  ██████╗  ╚███╝   ██║   ██║██████╔╝   ██║
  ▓█   ▀  ██╔██╗  ██║   ██║██╔══██╗   ██║
  ██████╗ ██╔╝ ██╗ ╚██████╔╝██║  ██║   ██║
  ╚═════╝ ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝{C.RST}
  {C.DIM}The Open Agent Engine  ·  v2.0.0  ·  Free AI for Everyone{C.RST}
""")


def confirm(msg: str, default: bool = False) -> bool:
    tag = "[Y/n]" if default else "[y/N]"
    try:
        r = input(f"{msg} {tag} ").strip().lower()
        return default if not r else r in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return default
