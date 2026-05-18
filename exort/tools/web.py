"""
Web gear — search the internet and read web pages.

DuckDuckGo search (no API key required).
Plain HTTP fetch for page content.
"""

import re
import urllib.parse
import urllib.request


_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return structured results."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        hits = []
        blocks = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]*)">(.*?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL,
        )
        for href, title, snippet in blocks[:max_results]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            if "uddg=" in href:
                href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            hits.append({"title": title, "url": href, "snippet": snippet})
        return hits or [{"note": "No results found."}]
    except Exception as exc:
        return [{"error": str(exc)}]


def _fetch(url: str, max_chars: int = 10000) -> str:
    """Fetch a URL and return cleaned text content."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r'<script.*?</script>', '', raw, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars] if len(text) > max_chars else text
    except Exception as exc:
        return f"Fetch failed: {exc}"


def register(gearbox):
    """Register web gear."""
    gearbox.add(
        name="web_search",
        info="Search the web via DuckDuckGo. Returns titles, URLs, and snippets. Use for any factual question about current events, definitions, or topics you are unsure about.",
        params={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default 5)", "default": 5},
            },
            "required": ["query"],
        },
        handler=lambda query, max_results=5: _search(query, int(max_results)),
    )
    gearbox.add(
        name="fetch_url",
        info="Download a web page and return its text content. Use to read articles, docs, or any URL.",
        params={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_chars": {"type": "integer", "description": "Max characters (default 10000)", "default": 10000},
            },
            "required": ["url"],
        },
        handler=lambda url, max_chars=10000: _fetch(url, int(max_chars)),
    )
