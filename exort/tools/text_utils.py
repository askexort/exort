"""
Text utilities gear — word count, case conversion, extraction, etc.
"""

import re
import collections


def _word_count(text: str) -> dict:
    """Count words, characters, sentences, paragraphs."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    return {
        "words": len(words),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "lines": text.count("\n") + 1,
        "avg_word_length": round(sum(len(w) for w in words) / len(words), 1) if words else 0,
    }


def _case_convert(text: str, case: str = "upper") -> dict:
    """Convert text case."""
    converters = {
        "upper": text.upper,
        "lower": text.lower,
        "title": text.title,
        "capitalize": text.capitalize,
        "swap": text.swapcase,
        "snake": lambda: re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower(),
        "camel": lambda: ''.join(w.capitalize() for w in re.split(r'[_\s-]+', text)),
        "kebab": lambda: re.sub(r'(?<!^)(?=[A-Z])', '-', text).lower().replace(' ', '-'),
    }
    fn = converters.get(case)
    if fn:
        result = fn() if callable(fn) else fn
        return {"original": text, "converted": result, "case": case}
    return {"error": f"Unknown case: {case}. Available: {list(converters.keys())}"}


def _extract_emails(text: str) -> dict:
    """Extract email addresses from text."""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return {"emails": list(set(emails)), "count": len(set(emails))}


def _extract_urls(text: str) -> dict:
    """Extract URLs from text."""
    urls = re.findall(r'https?://[^\s<>"\'\)\]]+', text)
    return {"urls": list(set(urls)), "count": len(set(urls))}


def _frequency(text: str, top_n: int = 10) -> dict:
    """Get word frequency analysis."""
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    counter = collections.Counter(words)
    top = counter.most_common(top_n)
    return {"total_words": len(words), "unique_words": len(counter),
            "top": [{"word": w, "count": c} for w, c in top]}


def register(gearbox):
    gearbox.add(
        name="word_count",
        info="Count words, characters, sentences, paragraphs, and lines in text.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"},
            },
            "required": ["text"],
        },
        handler=_word_count,
    )
    gearbox.add(
        name="case_convert",
        info="Convert text case: upper, lower, title, capitalize, swap, snake, camel, kebab.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert"},
                "case": {"type": "string", "description": "Target case", "default": "upper",
                         "enum": ["upper", "lower", "title", "capitalize", "swap", "snake", "camel", "kebab"]},
            },
            "required": ["text"],
        },
        handler=_case_convert,
    )
    gearbox.add(
        name="extract_emails",
        info="Extract all email addresses from text.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to scan for emails"},
            },
            "required": ["text"],
        },
        handler=_extract_emails,
    )
    gearbox.add(
        name="extract_urls",
        info="Extract all URLs from text.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to scan for URLs"},
            },
            "required": ["text"],
        },
        handler=_extract_urls,
    )
    gearbox.add(
        name="word_frequency",
        info="Analyze word frequency in text. Returns most common words.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"},
                "top_n": {"type": "integer", "description": "Number of top words to return", "default": 10},
            },
            "required": ["text"],
        },
        handler=_frequency,
    )
