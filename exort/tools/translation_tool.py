"""
Translation tools — language detection and text statistics.
"""

import json
import re


def _detect_language(text: str) -> str:
    """Simple language detection based on character patterns."""
    # Check for CJK characters
    if re.search(r'[\u4e00-\u9fff]', text):
        return "Chinese (zh)"
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "Japanese (ja)"
    if re.search(r'[\uac00-\ud7af]', text):
        return "Korean (ko)"
    if re.search(r'[\u0600-\u06ff]', text):
        return "Arabic (ar)"
    if re.search(r'[\u0400-\u04ff]', text):
        return "Russian (ru)"
    # Latin-based: check common words
    lower = text.lower()
    if any(w in lower for w in ['the', 'is', 'and', 'of', 'to', 'in']):
        return "English (en)"
    if any(w in lower for w in ['le', 'la', 'les', 'de', 'et', 'est']):
        return "French (fr)"
    if any(w in lower for w in ['der', 'die', 'das', 'und', 'ist', 'ein']):
        return "German (de)"
    if any(w in lower for w in ['el', 'la', 'los', 'las', 'de', 'es', 'en']):
        return "Spanish (es)"
    return "Unknown"


def _word_count(text: str) -> str:
    """Count words, characters, lines, and sentences."""
    words = len(text.split())
    chars = len(text)
    chars_no_space = len(text.replace(' ', '').replace('\n', ''))
    lines = len(text.split('\n'))
    sentences = len([s for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()])
    return json.dumps({
        "words": words,
        "characters": chars,
        "characters_no_spaces": chars_no_space,
        "lines": lines,
        "sentences": sentences,
        "avg_word_length": round(sum(len(w) for w in text.split()) / max(words, 1), 1),
    }, indent=2)


def register(gearbox):
    gearbox.add(
        name="detect_language",
        info="Detect the language of a text based on character patterns and common words.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to detect the language of"},
            },
            "required": ["text"],
        },
        handler=_detect_language,
    )
    gearbox.add(
        name="word_count",
        info="Count words, characters, lines, sentences, and average word length in text.",
        params={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"},
            },
            "required": ["text"],
        },
        handler=_word_count,
    )
