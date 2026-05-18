"""
File operation tools — read, write, edit, and search files.
"""

import os
import glob as glob_module
from pathlib import Path


def _read_file(path: str, offset: int = 1, limit: int = 500) -> dict:
    """Read a file with line numbers."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        start = max(0, offset - 1)
        end = min(total, start + limit)
        content = ""
        for i in range(start, end):
            content += f"{i+1:4d} | {lines[i]}"
        return {"content": content, "total_lines": total, "path": path}
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}


def _write_file(path: str, content: str) -> dict:
    """Write content to a file, creating directories if needed."""
    path = os.path.expanduser(path)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path, "bytes_written": len(content.encode())}
    except Exception as e:
        return {"error": f"Failed to write file: {e}"}


def _list_directory(path: str = ".", max_items: int = 100) -> dict:
    """List files and directories."""
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return {"error": f"Not a directory: {path}"}
    try:
        entries = []
        for name in sorted(os.listdir(path))[:max_items]:
            full = os.path.join(path, name)
            entry = {
                "name": name,
                "type": "directory" if os.path.isdir(full) else "file",
            }
            if os.path.isfile(full):
                entry["size"] = os.path.getsize(full)
            entries.append(entry)
        return {"path": path, "entries": entries, "count": len(entries)}
    except Exception as e:
        return {"error": f"Failed to list directory: {e}"}


def _search_files(pattern: str, path: str = ".", file_glob: str = None, limit: int = 20) -> dict:
    """Search for files matching a glob pattern or search file contents."""
    path = os.path.expanduser(path)
    try:
        if file_glob:
            # Content search within files matching glob
            matches = []
            for filepath in glob_module.glob(os.path.join(path, "**", file_glob), recursive=True):
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, 1):
                                if pattern.lower() in line.lower():
                                    matches.append({
                                        "file": filepath,
                                        "line": i,
                                        "content": line.strip()[:200],
                                    })
                                    if len(matches) >= limit:
                                        return {"matches": matches, "count": len(matches)}
                    except Exception:
                        continue
            return {"matches": matches, "count": len(matches)}
        else:
            # File name search
            matches = []
            for filepath in glob_module.glob(os.path.join(path, "**", f"*{pattern}*"), recursive=True):
                matches.append({"path": filepath, "type": "directory" if os.path.isdir(filepath) else "file"})
                if len(matches) >= limit:
                    break
            return {"matches": matches, "count": len(matches)}
    except Exception as e:
        return {"error": f"Search failed: {e}"}


def register_tools(registry):
    """Register file operation tools."""
    registry.register(
        name="read_file",
        description="Read a text file with line numbers. Use this to view source code, configs, or any text file.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "offset": {"type": "integer", "description": "Line number to start from (1-indexed, default: 1)", "default": 1},
                "limit": {"type": "integer", "description": "Max lines to read (default: 500)", "default": 500},
            },
            "required": ["path"],
        },
        handler=_read_file,
    )

    registry.register(
        name="write_file",
        description="Write content to a file. Creates the file and parent directories if they don't exist. OVERWRITES existing content completely.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        handler=_write_file,
    )

    registry.register(
        name="list_directory",
        description="List files and directories in a path. Shows file sizes and types.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: current directory)", "default": "."},
                "max_items": {"type": "integer", "description": "Max entries to return (default: 100)", "default": 100},
            },
            "required": [],
        },
        handler=_list_directory,
    )

    registry.register(
        name="search_files",
        description="Search for files by name or search inside file contents. Returns matching files and line numbers.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern (filename or text)"},
                "path": {"type": "string", "description": "Directory to search in (default: current)", "default": "."},
                "file_glob": {"type": "string", "description": "Glob pattern to filter files for content search (e.g. '*.py')"},
                "limit": {"type": "integer", "description": "Max results (default: 20)", "default": 20},
            },
            "required": ["pattern"],
        },
        handler=_search_files,
    )
