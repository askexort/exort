"""
Hash gear — generate hashes, encode/decode.
"""

import hashlib
import base64
import json


def _hash(text: str, algorithm: str = "sha256") -> dict:
    """Hash text with specified algorithm."""
    try:
        h = hashlib.new(algorithm)
        h.update(text.encode("utf-8"))
        return {"algorithm": algorithm, "hash": h.hexdigest(), "input_length": len(text)}
    except Exception as e:
        return {"error": str(e)}


def _base64_encode(text: str) -> dict:
    """Base64 encode text."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return {"encoded": encoded, "original_length": len(text)}


def _base64_decode(encoded: str) -> dict:
    """Base64 decode text."""
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        return {"decoded": decoded}
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="hash",
        info="Generate a hash of text. Supports: md5, sha1, sha256, sha512, sha3_256, blake2b.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to hash"},
                "algorithm": {"type": "string", "description": "Hash algorithm", "default": "sha256",
                              "enum": ["md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b"]},
            },
            "required": ["text"],
        },
        handler=_hash,
    )
    gearbox.add(
        name="base64_encode",
        info="Encode text to Base64.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to encode"},
            },
            "required": ["text"],
        },
        handler=_base64_encode,
    )
    gearbox.add(
        name="base64_decode",
        info="Decode Base64 text.",
        params={
            "type": "object",
            "properties": {
                "encoded": {"type": "string", "description": "Base64 string to decode"},
            },
            "required": ["encoded"],
        },
        handler=_base64_decode,
    )
