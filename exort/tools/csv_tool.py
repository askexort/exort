"""
CSV gear — read, write, and analyze CSV data.
"""

import csv
import io
import json


def _csv_read(file_path: str, max_rows: int = 100) -> dict:
    """Read a CSV file and return as list of dicts."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for i, row in enumerate(reader) if i < max_rows]
        return {"rows": rows, "count": len(rows), "columns": list(rows[0].keys()) if rows else []}
    except Exception as e:
        return {"error": str(e)}


def _csv_parse(text: str, delimiter: str = ",") -> dict:
    """Parse CSV text into structured data."""
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        return {"rows": rows, "count": len(rows), "columns": list(rows[0].keys()) if rows else []}
    except Exception as e:
        return {"error": str(e)}


def _csv_from_json(json_data: str, file_path: str = None) -> dict:
    """Convert JSON array of objects to CSV."""
    try:
        data = json.loads(json_data)
        if not data:
            return {"error": "Empty data"}
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        csv_text = output.getvalue()
        if file_path:
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                f.write(csv_text)
            return {"saved": file_path, "rows": len(data), "preview": csv_text[:500]}
        return {"csv": csv_text, "rows": len(data)}
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="csv_read",
        info="Read a CSV file and return structured data with column names.",
        params={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to CSV file"},
                "max_rows": {"type": "integer", "description": "Max rows to read", "default": 100},
            },
            "required": ["file_path"],
        },
        handler=_csv_read,
    )
    gearbox.add(
        name="csv_parse",
        info="Parse CSV text into structured data.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "CSV text to parse"},
                "delimiter": {"type": "string", "description": "Column delimiter", "default": ","},
            },
            "required": ["text"],
        },
        handler=_csv_parse,
    )
    gearbox.add(
        name="csv_from_json",
        info="Convert a JSON array of objects to CSV format. Optionally save to file.",
        params={
            "type": "object",
            "properties": {
                "json_data": {"type": "string", "description": "JSON array of objects"},
                "file_path": {"type": "string", "description": "Optional path to save CSV"},
            },
            "required": ["json_data"],
        },
        handler=_csv_from_json,
    )
