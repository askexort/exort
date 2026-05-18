"""
Web search and HTTP tools.

Provides tools for searching the web and fetching URLs.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from Exort.tools.base import tool


@tool(
    name="web_search",
    description=(
        "Search the web using DuckDuckGo. Returns a list of "
        "search results with titles, URLs, and snippets."
    ),
)
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo's HTML API.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        JSON-formatted search results.
    """
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Simple HTML parsing (no external deps)
        results = []
        parts = html.split('result__a')
        for part in parts[1 : max_results + 1]:
            # Extract title
            title = ""
            if 'result__title' in part:
                title_start = part.find('>') + 1
                title_end = part.find('</a>', title_start)
                if title_start > 0 and title_end > title_start:
                    title = part[title_start:title_end].strip()
                    title = title.replace("<b>", "").replace("</b>", "")

            # Extract URL
            result_url = ""
            if 'href="' in part:
                href_start = part.find('href="') + 6
                href_end = part.find('"', href_start)
                if href_start > 5 and href_end > href_start:
                    result_url = part[href_start:href_end]

            # Extract snippet
            snippet = ""
            if 'result__snippet' in part:
                snip_start = part.find('result__snippet')
                snip_start = part.find('>', snip_start) + 1
                snip_end = part.find('</a>', snip_start)
                if snip_start > 0 and snip_end > snip_start:
                    snippet = part[snip_start:snip_end].strip()
                    snippet = snippet.replace("<b>", "").replace("</b>", "")

            if title or result_url:
                results.append({
                    "title": title,
                    "url": result_url,
                    "snippet": snippet,
                })

        if not results:
            return json.dumps({"query": query, "results": [], "note": "No results found."})

        return json.dumps({"query": query, "results": results}, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc), "query": query})


@tool(
    name="fetch_url",
    description="Fetch the content of a URL and return the text. Useful for reading web pages.",
)
def fetch_url(url: str, max_chars: int = 10000) -> str:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch.
        max_chars: Maximum characters to return.

    Returns:
        The text content of the page.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Exort/0.1 (AI Agent Framework)",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Strip HTML tags for basic text extraction
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > max_chars:
            text = text[:max_chars] + "\n... (truncated)"

        return text

    except Exception as exc:
        return f"Error fetching URL: {exc}"
