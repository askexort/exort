"""
File gear — read, write, list, and search files on disk.
"""

import os
import glob as glob_mod


def _read(path: str, offset: int = 1, limit: int = 500) -> dict:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return {"error": f"Not found: {path}"}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start = max(0, offset - 1)
        end = min(len(lines), start + limit)
        numbered = "".join(f"{i+1:4d} | {lines[i]}" for i in range(start, end))
        return {"content": numbered, "total_lines": len(lines), "path": path}
    except Exception as exc:
        return {"error": str(exc)}


def _write(path: str, content: str) -> dict:
    path = os.path.expanduser(path)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": path, "bytes": len(content.encode())}
    except Exception as exc:
        return {"error": str(exc)}


def _listdir(path: str = ".", limit: int = 100) -> dict:
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return {"error": f"Not a directory: {path}"}
    try:
        entries = []
        for name in sorted(os.listdir(path))[:limit]:
            full = os.path.join(path, name)
            e = {"name": name, "type": "dir" if os.path.isdir(full) else "file"}
            if e["type"] == "file":
                e["size"] = os.path.getsize(full)
            entries.append(e)
        return {"path": path, "entries": entries}
    except Exception as exc:
        return {"error": str(exc)}


def _search(pattern: str, path: str = ".", glob: str = None, limit: int = 20) -> dict:
    path = os.path.expanduser(path)
    try:
        if glob:
            matches = []
            for fp in glob_mod.glob(os.path.join(path, "**", glob), recursive=True):
                if not os.path.isfile(fp):
                    continue
                try:
                    with open(fp, encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                matches.append({"file": fp, "line": i, "text": line.strip()[:200]})
                                if len(matches) >= limit:
                                    return {"matches": matches}
                except Exception:
                    continue
            return {"matches": matches}
        else:
            hits = []
            for fp in glob_mod.glob(os.path.join(path, "**", f"*{pattern}*"), recursive=True):
                hits.append({"path": fp, "type": "dir" if os.path.isdir(fp) else "file"})
                if len(hits) >= limit:
                    break
            return {"matches": hits}
    except Exception as exc:
        return {"error": str(exc)}


def register(gearbox):
    """Register file gear."""
    gearbox.add(
        name="read_file",
        info="Read a text file with line numbers. Supports offset/limit for large files.",
        params={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "offset": {"type": "integer", "description": "Start line (1-indexed)", "default": 1},
                "limit": {"type": "integer", "description": "Max lines", "default": 500},
            },
            "required": ["path"],
        },
        handler=_read,
    )
    gearbox.add(
        name="write_file",
        info="Write content to a file. Creates parent dirs. OVERWRITES existing file.",
        params={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        handler=_write,
    )
    gearbox.add(
        name="list_directory",
        info="List files and directories with sizes.",
        params={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path", "default": "."},
                "limit": {"type": "integer", "description": "Max entries", "default": 100},
            },
            "required": [],
        },
        handler=_listdir,
    )
    gearbox.add(
        name="search_files",
        info="Find files by name or search inside file contents.",
        params={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search term"},
                "path": {"type": "string", "description": "Root dir", "default": "."},
                "glob": {"type": "string", "description": "File filter (e.g. *.py)"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
            "required": ["pattern"],
        },
        handler=_search,
    )
