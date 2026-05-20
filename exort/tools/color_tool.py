"""
Color gear — convert between color formats.
"""


def _color_convert(color: str, to_format: str = "hex") -> dict:
    """Convert color between formats (hex, rgb, hsl)."""
    try:
        # Parse input
        if color.startswith("#"):
            hex_color = color.lstrip("#")
            if len(hex_color) == 3:
                hex_color = "".join(c * 2 for c in hex_color)
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        elif color.startswith("rgb"):
            parts = color.replace("rgb(", "").replace("rgba(", "").replace(")", "").split(",")
            r, g, b = int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
        else:
            return {"error": f"Unsupported format: {color}. Use #hex or rgb(r,g,b)"}

        # Convert
        hex_val = f"#{r:02x}{g:02x}{b:02x}"
        rgb_val = f"rgb({r}, {g}, {b})"

        # HSL conversion
        r_n, g_n, b_n = r / 255, g / 255, b / 255
        cmax = max(r_n, g_n, b_n)
        cmin = min(r_n, g_n, b_n)
        delta = cmax - cmin
        l = (cmax + cmin) / 2
        if delta == 0:
            h = s = 0
        else:
            s = delta / (1 - abs(2 * l - 1))
            if cmax == r_n:
                h = 60 * (((g_n - b_n) / delta) % 6)
            elif cmax == g_n:
                h = 60 * ((b_n - r_n) / delta + 2)
            else:
                h = 60 * ((r_n - g_n) / delta + 4)

        return {
            "hex": hex_val,
            "rgb": rgb_val,
            "hsl": f"hsl({h:.0f}, {s*100:.0f}%, {l*100:.0f}%)",
            "r": r, "g": g, "b": b,
            "h": round(h), "s": round(s * 100), "l": round(l * 100),
        }
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="color_convert",
        info="Convert colors between hex (#ff0000), rgb (rgb(255,0,0)), and hsl formats.",
        params={
            "type": "object",
            "properties": {
                "color": {"type": "string", "description": "Input color (hex #ff0000 or rgb(255,0,0))"},
                "to_format": {"type": "string", "description": "Target format", "default": "hex",
                              "enum": ["hex", "rgb", "hsl"]},
            },
            "required": ["color"],
        },
        handler=_color_convert,
    )
