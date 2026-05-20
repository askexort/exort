"""
Diff gear — compare texts and files.
"""

import difflib


def _text_diff(text1: str, text2: str, context: int = 3) -> dict:
    """Compare two texts and show differences."""
    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)
    diff = list(difflib.unified_diff(lines1, lines2, fromfile="text1", tofile="text2", n=context))
    if not diff:
        return {"identical": True, "message": "Texts are identical"}
    return {
        "identical": False,
        "diff": "".join(diff)[:5000],
        "lines_added": sum(1 for l in diff if l.startswith("+") and not l.startswith("+++")),
        "lines_removed": sum(1 for l in diff if l.startswith("-") and not l.startswith("---")),
    }


def _file_diff(file1: str, file2: str, context: int = 3) -> dict:
    """Compare two files and show differences."""
    try:
        with open(file1, "r", encoding="utf-8") as f:
            lines1 = f.readlines()
        with open(file2, "r", encoding="utf-8") as f:
            lines2 = f.readlines()
        diff = list(difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2, n=context))
        if not diff:
            return {"identical": True, "message": "Files are identical"}
        return {
            "identical": False,
            "diff": "".join(diff)[:5000],
            "lines_added": sum(1 for l in diff if l.startswith("+") and not l.startswith("+++")),
            "lines_removed": sum(1 for l in diff if l.startswith("-") and not l.startswith("---")),
        }
    except Exception as e:
        return {"error": str(e)}


def _similarity(text1: str, text2: str) -> dict:
    """Calculate similarity ratio between two texts."""
    ratio = difflib.SequenceMatcher(None, text1, text2).ratio()
    return {
        "similarity": round(ratio, 4),
        "percentage": f"{ratio * 100:.1f}%",
        "text1_length": len(text1),
        "text2_length": len(text2),
    }


def register(gearbox):
    gearbox.add(
        name="text_diff",
        info="Compare two texts and show differences in unified diff format.",
        params={
            "type": "object",
            "properties": {
                "text1": {"type": "string", "description": "First text"},
                "text2": {"type": "string", "description": "Second text"},
                "context": {"type": "integer", "description": "Context lines around changes", "default": 3},
            },
            "required": ["text1", "text2"],
        },
        handler=_text_diff,
    )
    gearbox.add(
        name="file_diff",
        info="Compare two files and show differences in unified diff format.",
        params={
            "type": "object",
            "properties": {
                "file1": {"type": "string", "description": "Path to first file"},
                "file2": {"type": "string", "description": "Path to second file"},
                "context": {"type": "integer", "description": "Context lines", "default": 3},
            },
            "required": ["file1", "file2"],
        },
        handler=_file_diff,
    )
    gearbox.add(
        name="text_similarity",
        info="Calculate how similar two texts are (0.0 to 1.0 ratio).",
        params={
            "type": "object",
            "properties": {
                "text1": {"type": "string", "description": "First text"},
                "text2": {"type": "string", "description": "Second text"},
            },
            "required": ["text1", "text2"],
        },
        handler=_similarity,
    )
