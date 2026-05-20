"""
HTTP gear — make HTTP requests (GET, POST, PUT, DELETE).
"""

import json
import urllib.request
import urllib.parse
import urllib.error


def _http_request(url: str, method: str = "GET", body: str = None,
                  headers: str = None, timeout: int = 15) -> dict:
    """Make an HTTP request."""
    try:
        hdrs = {"User-Agent": "Exort/2.0"}
        if headers:
            hdrs.update(json.loads(headers))
        if body and method in ("POST", "PUT", "PATCH"):
            if "Content-Type" not in hdrs:
                hdrs["Content-Type"] = "application/json"

        data = body.encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(content)
                return {"status": resp.status, "data": parsed, "url": url}
            except json.JSONDecodeError:
                return {"status": resp.status, "text": content[:5000], "url": url}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:2000]
        return {"status": e.code, "error": str(e), "body": body_text, "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


def register(gearbox):
    gearbox.add(
        name="http_request",
        info="Make an HTTP request. Use for API calls, webhooks, REST APIs. Supports GET/POST/PUT/DELETE/PATCH.",
        params={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to request"},
                "method": {"type": "string", "description": "HTTP method", "default": "GET", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]},
                "body": {"type": "string", "description": "Request body (JSON string for POST/PUT)"},
                "headers": {"type": "string", "description": "JSON string of headers"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 15},
            },
            "required": ["url"],
        },
        handler=_http_request,
    )
