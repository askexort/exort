"""
Image tools — analyze image file metadata and format.
"""

import json
import os
import struct


def _human_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f}{unit}" if unit != 'B' else f"{n}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _describe_image_format(file_path: str) -> str:
    """Get image metadata without loading the full image."""
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    size = os.path.getsize(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    info = {"file": file_path, "size_bytes": size, "size_human": _human_size(size), "format": ext}

    # Try to read dimensions from headers
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)

            if ext in ('.png',) and header[:8] == b'\x89PNG\r\n\x1a\n':
                w = struct.unpack('>I', header[16:20])[0]
                h = struct.unpack('>I', header[20:24])[0]
                info["width"], info["height"] = w, h

            elif ext in ('.jpg', '.jpeg') and header[:2] == b'\xff\xd8':
                info["format"] = "JPEG"
                info["note"] = "JPEG detected. Use PIL for dimensions."

            elif ext in ('.gif',) and header[:3] == b'GIF':
                w = struct.unpack('<H', header[6:8])[0]
                h = struct.unpack('<H', header[8:10])[0]
                info["width"], info["height"] = w, h

            elif ext in ('.webp',) and header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                info["format"] = "WebP"
    except Exception:
        pass

    return json.dumps(info, indent=2)


def register(gearbox):
    gearbox.add(
        name="describe_image_format",
        info="Analyze image file metadata (size, dimensions, format) without loading the full image. Supports PNG, JPEG, GIF, WebP.",
        params={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the image file to analyze"},
            },
            "required": ["file_path"],
        },
        handler=_describe_image_format,
    )
