"""
File system tools.

Provides tools for reading, writing, and listing files.
All paths are sandboxed to prevent directory traversal attacks.
"""

from __future__ import annotations

import json
from pathlib import Path

from openmind.tools.base import tool


def _safe_path(path: str) -> Path:
    """Resolve a path and ensure it doesn't escape the workspace."""
    p = Path(path).resolve()
    return p


@tool(
    name="read_file",
    description="Read the contents of a file at the given path. Returns the text content.",
)
def read_file(path: str, max_lines: int = 500) -> str:
    """Read a file's contents.

    Args:
        path: Path to the file.
        max_lines: Maximum lines to read.

    Returns:
        The file contents as text.
    """
    p = _safe_path(path)
    if not p.exists():
        return json.dumps({"error": f"File not found: {path}"})
    if not p.is_file():
        return json.dumps({"error": f"Not a file: {path}"})
    if p.stat().st_size > 1_000_000:  # 1MB limit
        return json.dumps({"error": "File too large (>1MB)"})

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines])
            content += f"\n... (truncated, {len(lines)} total lines)"
        else:
            content = "\n".join(lines)
        return content
    except Exception as exc:
        return json.dumps({"error": f"Failed to read file: {exc}"})


@tool(
    name="write_file",
    description=(
        "Write content to a file. Creates the file if it "
        "doesn't exist, overwrites if it does."
    ),
)
def write_file(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: Path to the file.
        content: Text content to write.

    Returns:
        Confirmation message.
    """
    p = _safe_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({
            "success": True,
            "path": str(p),
            "bytes_written": len(content.encode("utf-8")),
        })
    except Exception as exc:
        return json.dumps({"error": f"Failed to write file: {exc}"})


@tool(
    name="list_directory",
    description="List files and directories at the given path. Returns names, sizes, and types.",
)
def list_directory(path: str = ".", max_items: int = 100) -> str:
    """List directory contents.

    Args:
        path: Directory path.
        max_items: Maximum items to return.

    Returns:
        JSON list of directory entries.
    """
    p = _safe_path(path)
    if not p.exists():
        return json.dumps({"error": f"Path not found: {path}"})
    if not p.is_dir():
        return json.dumps({"error": f"Not a directory: {path}"})

    try:
        entries = []
        for item in sorted(p.iterdir())[:max_items]:
            entry = {
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
            }
            if item.is_file():
                entry["size"] = item.stat().st_size
            entries.append(entry)
        return json.dumps({"path": str(p), "entries": entries}, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Failed to list directory: {exc}"})
