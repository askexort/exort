"""
URL gear — parse, encode, decode, and build URLs.
"""

import urllib.parse


def _url_parse(url: str) -> dict:
    """Parse a URL into components."""
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        return {
            "scheme": parsed.scheme,
            "netloc": parsed.netloc,
            "path": parsed.path,
            "params": parsed.params,
            "query": parsed.query,
            "query_params": {k: v[0] if len(v) == 1 else v for k, v in params.items()},
            "fragment": parsed.fragment,
            "port": parsed.port,
            "hostname": parsed.hostname,
        }
    except Exception as e:
        return {"error": str(e)}


def _url_encode(text: str) -> dict:
    """URL-encode a string."""
    return {"encoded": urllib.parse.quote_plus(text), "original": text}


def _url_decode(text: str) -> dict:
    """URL-decode a string."""
    return {"decoded": urllib.parse.unquote_plus(text), "encoded": text}


def _url_build(scheme: str = "https", host: str = "", path: str = "",
               params: str = None, fragment: str = None) -> dict:
    """Build a URL from components. Pass params as JSON string."""
    try:
        query = ""
        if params:
            d = urllib.parse.urlencode(eval(params) if isinstance(params, str) else params)
            query = d
        url = urllib.parse.urlunparse((scheme, host, path, "", query, fragment or ""))
        return {"url": url}
    except Exception as e:
        return {"error": str(e)}


def register(gearbox):
    gearbox.add(
        name="url_parse",
        info="Parse a URL into its components (scheme, host, path, query params, fragment).",
        params={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to parse"},
            },
            "required": ["url"],
        },
        handler=_url_parse,
    )
    gearbox.add(
        name="url_encode",
        info="URL-encode a string (percent-encoding).",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to encode"},
            },
            "required": ["text"],
        },
        handler=_url_encode,
    )
    gearbox.add(
        name="url_decode",
        info="URL-decode a percent-encoded string.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Percent-encoded text to decode"},
            },
            "required": ["text"],
        },
        handler=_url_decode,
    )
    gearbox.add(
        name="url_build",
        info="Build a URL from components (scheme, host, path, query params, fragment).",
        params={
            "type": "object",
            "properties": {
                "scheme": {"type": "string", "description": "Protocol (http/https)", "default": "https"},
                "host": {"type": "string", "description": "Hostname"},
                "path": {"type": "string", "description": "URL path", "default": ""},
                "params": {"type": "string", "description": "Query params as JSON dict string"},
                "fragment": {"type": "string", "description": "URL fragment"},
            },
            "required": ["host"],
        },
        handler=_url_build,
    )
