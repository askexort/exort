"""
Markdown tools — render and convert markdown text.
"""

import re


def _markdown_render(text: str) -> str:
    """Convert markdown to terminal-friendly text."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\033[1m\1\033[0m', text)  # bold
    text = re.sub(r'\*(.*?)\*', r'\033[3m\1\033[0m', text)  # italic
    text = re.sub(r'`(.*?)`', r'\033[93m\1\033[0m', text)  # code
    text = re.sub(r'~~(.*?)~~', r'\033[9m\1\033[0m', text)  # strikethrough
    text = re.sub(r'^#{1}\s+', '\u25a0 ', text, flags=re.MULTILINE)  # h1
    text = re.sub(r'^#{2}\s+', '  \u25a0 ', text, flags=re.MULTILINE)  # h2
    text = re.sub(r'^#{3}\s+', '    \u25a0 ', text, flags=re.MULTILINE)  # h3
    text = re.sub(r'^[-*]\s+', '  \u2022 ', text, flags=re.MULTILINE)  # lists
    text = re.sub(r'^\d+\.\s+', lambda m: f'  {m.group()}', text, flags=re.MULTILINE)  # numbered
    return text


def _markdown_to_html(text: str) -> str:
    """Convert markdown to basic HTML."""
    html = text
    html = re.sub(r'^#{1}\s+(.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{2}\s+(.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{3}\s+(.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'^[-*]\s+(.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    return f"<div>{html}</div>"


def register(gearbox):
    gearbox.add(
        name="markdown_render",
        info="Render markdown text to terminal-friendly output with ANSI formatting (bold, italic, headers, lists).",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Markdown text to render for terminal display"},
            },
            "required": ["text"],
        },
        handler=_markdown_render,
    )
    gearbox.add(
        name="markdown_to_html",
        info="Convert markdown text to basic HTML.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Markdown text to convert to HTML"},
            },
            "required": ["text"],
        },
        handler=_markdown_to_html,
    )
