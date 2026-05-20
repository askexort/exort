"""
UUID gear — generate and validate UUIDs.
"""

import uuid


def _generate(count: int = 1, version: int = 4) -> dict:
    """Generate UUID(s)."""
    try:
        uuids = []
        for _ in range(min(count, 100)):
            if version == 1:
                uuids.append(str(uuid.uuid1()))
            elif version == 4:
                uuids.append(str(uuid.uuid4()))
            else:
                uuids.append(str(uuid.uuid4()))
        return {"uuids": uuids, "count": len(uuids), "version": version}
    except Exception as e:
        return {"error": str(e)}


def _validate(uuid_string: str) -> dict:
    """Validate a UUID string."""
    try:
        u = uuid.UUID(uuid_string)
        return {"valid": True, "uuid": str(u), "version": u.version,
                "hex": u.hex, "bytes": len(u.bytes)}
    except ValueError as e:
        return {"valid": False, "error": str(e)}


def register(gearbox):
    gearbox.add(
        name="uuid_generate",
        info="Generate one or more UUIDs. Supports v1 (time-based) and v4 (random).",
        params={
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of UUIDs to generate (max 100)", "default": 1},
                "version": {"type": "integer", "description": "UUID version (1 or 4)", "default": 4},
            },
            "required": [],
        },
        handler=_generate,
    )
    gearbox.add(
        name="uuid_validate",
        info="Validate a UUID string and return its properties.",
        params={
            "type": "object",
            "properties": {
                "uuid_string": {"type": "string", "description": "UUID to validate"},
            },
            "required": ["uuid_string"],
        },
        handler=_validate,
    )
