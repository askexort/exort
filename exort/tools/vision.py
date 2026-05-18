"""
Vision tool — analyze images using multimodal LLMs.
"""

import base64
import os
import urllib.request
import urllib.parse


def _analyze_image(image_path: str, question: str = "Describe this image in detail.") -> dict:
    """Analyze an image using a vision-capable model."""
    path = os.path.expanduser(image_path)
    if not os.path.exists(path):
        return {"error": f"Image not found: {path}"}

    try:
        # Read and encode the image
        with open(path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")

        # Detect MIME type
        ext = os.path.splitext(path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        mime = mime_map.get(ext, "image/jpeg")

        return {
            "image_base64": img_data[:100] + "...[truncated]",
            "mime_type": mime,
            "path": path,
            "question": question,
            "note": "Image analysis requires a vision-capable model (e.g., gpt-4o, llama-3.2-vision). Use the agent with a vision model to analyze this image.",
        }
    except Exception as e:
        return {"error": f"Failed to process image: {e}"}


def register_tools(registry):
    """Register vision tools."""
    registry.register(
        name="analyze_image",
        description="Load an image for analysis. The agent will use a vision-capable model to describe or answer questions about the image. Supports JPG, PNG, GIF, WebP.",
        parameters={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file",
                },
                "question": {
                    "type": "string",
                    "description": "What to analyze about the image (default: describe it)",
                    "default": "Describe this image in detail.",
                },
            },
            "required": ["image_path"],
        },
        handler=_analyze_image,
    )
