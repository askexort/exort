"""
Web tools — search the internet and fetch web page content.

Uses DuckDuckGo for search (no API key required) and basic HTTP for fetching.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo via the HTML API (no API key needed)."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Parse results from HTML
        results = []
        # Find result blocks
        snippets = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]*)">(.*?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        for href, title, snippet in snippets[:max_results]:
            # Clean HTML tags
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            # Decode DuckDuckGo redirect URL
            if "uddg=" in href:
                href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            results.append({
                "title": title,
                "url": href,
                "snippet": snippet,
            })
        return results
    except Exception as e:
        return [{"error": f"Search failed: {e}"}]


def _fetch_url(url: str, max_chars: int = 10000) -> str:
    """Fetch a URL and return its text content."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Exort/1.0)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Strip HTML tags for plain text
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"
        return text
    except Exception as e:
        return f"Failed to fetch URL: {e}"


def register_tools(registry):
    """Register web tools."""
    registry.register(
        name="web_search",
        description="Search the web using DuckDuckGo. Returns titles, URLs, and snippets. Use this to find current information on any topic.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        handler=lambda query, max_results=5: _ddg_search(query, int(max_results)),
    )

    registry.register(
        name="fetch_url",
        description="Fetch and read the content of a web page URL. Returns the page text content. Use this to read articles, documentation, or any web page.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return (default: 10000)",
                    "default": 10000,
                },
            },
            "required": ["url"],
        },
        handler=lambda url, max_chars=10000: _fetch_url(url, int(max_chars)),
    )
