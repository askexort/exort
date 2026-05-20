"""
DateTime gear — date and time operations.
"""

from datetime import datetime, timedelta, timezone
import time as _time


def _now(timezone_offset: str = "UTC") -> dict:
    """Get current date/time."""
    if timezone_offset == "UTC":
        dt = datetime.now(timezone.utc)
    else:
        try:
            offset = int(timezone_offset)
            tz = timezone(timedelta(hours=offset))
            dt = datetime.now(tz)
        except ValueError:
            dt = datetime.now()
    return {
        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
        "unix": int(dt.timestamp()),
        "day_of_week": dt.strftime("%A"),
        "iso": dt.isoformat(),
    }


def _convert(timestamp: int = None, date_string: str = None, to_format: str = "%Y-%m-%d") -> dict:
    """Convert between formats."""
    try:
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            return {"input": timestamp, "formatted": dt.strftime(to_format), "iso": dt.isoformat()}
        elif date_string:
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y"]:
                try:
                    dt = datetime.strptime(date_string, fmt)
                    return {"input": date_string, "formatted": dt.strftime(to_format),
                            "unix": int(dt.timestamp()), "iso": dt.isoformat()}
                except ValueError:
                    continue
            return {"error": f"Could not parse date: {date_string}"}
        return {"error": "Provide timestamp or date_string"}
    except Exception as e:
        return {"error": str(e)}


def _diff(date1: str, date2: str) -> dict:
    """Calculate difference between two dates."""
    try:
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
            try:
                d1 = datetime.strptime(date1, fmt)
                break
            except ValueError:
                continue
        else:
            return {"error": f"Cannot parse: {date1}"}
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
            try:
                d2 = datetime.strptime(date2, fmt)
                break
            except ValueError:
                continue
        else:
            return {"error": f"Cannot parse: {date2}"}
        delta = d2 - d1
        return {
            "days": delta.days,
            "seconds": delta.total_seconds(),
            "weeks": delta.days // 7,
            "human": f"{abs(delta.days)} days {'later' if delta.days >= 0 else 'earlier'}",
        }
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="datetime_now",
        info="Get current date, time, unix timestamp, and day of week. Use timezone_offset for local time (e.g. '-5' for EST).",
        params={
            "type": "object",
            "properties": {
                "timezone_offset": {"type": "string", "description": "Hours from UTC (e.g. '5', '-8') or 'UTC'", "default": "UTC"},
            },
            "required": [],
        },
        handler=_now,
    )
    gearbox.add(
        name="datetime_convert",
        info="Convert between date formats. Parse dates to unix timestamps or format timestamps to dates.",
        params={
            "type": "object",
            "properties": {
                "timestamp": {"type": "integer", "description": "Unix timestamp to convert"},
                "date_string": {"type": "string", "description": "Date string to parse (e.g. '2024-01-15')"},
                "to_format": {"type": "string", "description": "Output format (strftime)", "default": "%Y-%m-%d"},
            },
            "required": [],
        },
        handler=_convert,
    )
    gearbox.add(
        name="datetime_diff",
        info="Calculate the difference between two dates in days, weeks, and seconds.",
        params={
            "type": "object",
            "properties": {
                "date1": {"type": "string", "description": "First date (e.g. '2024-01-01')"},
                "date2": {"type": "string", "description": "Second date (e.g. '2024-12-31')"},
            },
            "required": ["date1", "date2"],
        },
        handler=_diff,
    )
