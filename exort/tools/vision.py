"""
Vision gear — prepare images for multimodal analysis.
"""

import base64
import os


def _load(image_path: str, prompt: str = "Describe this image.") -> dict:
    path = os.path.expanduser(image_path)
    if not os.path.exists(path):
        return {"error": f"Not found: {path}"}
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(path)[1].lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return {"base64_preview": b64[:80] + "...", "mime": mime, "path": path, "prompt": prompt,
                "hint": "Pass this to a vision-capable model for analysis."}
    except Exception as exc:
        return {"error": str(exc)}


def register(gearbox):
    gearbox.add(
        name="load_image",
        info="Load an image for analysis. Use with a vision model (gpt-4o, llama-3.2-vision).",
        params={
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to image file"},
                "prompt": {"type": "string", "description": "What to analyze", "default": "Describe this image."},
            },
            "required": ["image_path"],
        },
        handler=_load,
    )
