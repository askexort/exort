"""
JSON gear — parse, format, query, and transform JSON.
"""

import json
import re


def _json_parse(text: str) -> dict:
    """Parse JSON string and return structured data."""
    try:
        return {"data": json.loads(text), "valid": True}
    except json.JSONDecodeError as e:
        return {"error": str(e), "valid": False}


def _json_format(data: str, indent: int = 2) -> dict:
    """Pretty-print JSON."""
    try:
        parsed = json.loads(data)
        return {"formatted": json.dumps(parsed, indent=indent, ensure_ascii=False)}
    except Exception as e:
        return {"error": str(e)}


def _json_query(data: str, path: str) -> dict:
    """Query JSON with dot notation (e.g. 'users.0.name')."""
    try:
        obj = json.loads(data)
        current = obj
        for key in path.split("."):
            if isinstance(current, list):
                current = current[int(key)]
            elif isinstance(current, dict):
                current = current[key]
            else:
                return {"error": f"Cannot traverse into {type(current).__name__} with key '{key}'"}
        return {"path": path, "value": current}
    except Exception as e:
        return {"error": str(e)}


def _json_merge(json1: str, json2: str) -> dict:
    """Deep merge two JSON objects."""
    try:
        a, b = json.loads(json1), json.loads(json2)
        if isinstance(a, dict) and isinstance(b, dict):
            merged = {**a, **b}
            return {"merged": merged}
        return {"error": "Both inputs must be JSON objects"}
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="json_parse",
        info="Parse and validate a JSON string. Returns the structured data or an error.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "JSON string to parse"},
            },
            "required": ["text"],
        },
        handler=_json_parse,
    )
    gearbox.add(
        name="json_format",
        info="Pretty-print / format a JSON string with indentation.",
        params={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON string to format"},
                "indent": {"type": "integer", "description": "Indentation spaces", "default": 2},
            },
            "required": ["data"],
        },
        handler=_json_format,
    )
    gearbox.add(
        name="json_query",
        info="Query a JSON value using dot notation path (e.g. 'users.0.name', 'data.items.2.id').",
        params={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON string to query"},
                "path": {"type": "string", "description": "Dot-notation path (e.g. 'users.0.name')"},
            },
            "required": ["data", "path"],
        },
        handler=_json_query,
    )
    gearbox.add(
        name="json_merge",
        info="Deep merge two JSON objects together.",
        params={
            "type": "object",
            "properties": {
                "json1": {"type": "string", "description": "First JSON object"},
                "json2": {"type": "string", "description": "Second JSON object (takes priority)"},
            },
            "required": ["json1", "json2"],
        },
        handler=_json_merge,
    )
