"""Bounded term extraction for public catalog search."""

from __future__ import annotations

import re

_WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.-]{1,}", re.IGNORECASE)
_STOP_WORDS = frozenset(
    {
        "about",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "or",
        "owner",
        "please",
        "portfolio",
        "tell",
        "that",
        "the",
        "their",
        "them",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


def extract_search_terms(query: str, *, max_terms: int = 12) -> tuple[str, ...]:
    """Return ordered, deduplicated terms suitable for bounded SQL filtering."""

    if max_terms < 1:
        return ()

    terms: list[str] = []
    seen: set[str] = set()
    for match in _WORD_PATTERN.findall(query):
        term = match.casefold()
        if term in _STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) == max_terms:
            break
    return tuple(terms)
