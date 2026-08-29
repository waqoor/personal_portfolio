"""Fail-closed aggregation of public content supplied by domain contracts."""

from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

from services.assistant.contracts import PublishedContentDocument, PublishedContentProvider

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


class PublishedContentRegistry:
    """Composition-owned registry; providers retain ownership of source queries."""

    def __init__(self, providers: tuple[PublishedContentProvider, ...] = ()) -> None:
        self._providers = list(providers)

    def register(self, provider: PublishedContentProvider) -> None:
        self._providers.append(provider)

    async def search(self, query: str, *, limit: int) -> list[PublishedContentDocument]:
        candidates: list[PublishedContentDocument] = []
        for provider in self._providers:
            documents = await provider.search_published(query, limit=limit)
            candidates.extend(document for document in documents if _is_authorized(document))

        deduplicated: dict[str, PublishedContentDocument] = {}
        for document in candidates:
            sanitized = PublishedContentDocument(
                source_id=document.source_id[:160],
                content_type=document.content_type[:40],
                title=_plain_text(document.title, 200),
                excerpt=_plain_text(document.excerpt, 2400),
                canonical_url=document.canonical_url,
                relevance=document.relevance,
                published_at=document.published_at,
            )
            current = deduplicated.get(sanitized.canonical_url)
            if current is None or sanitized.relevance > current.relevance:
                deduplicated[sanitized.canonical_url] = sanitized
        return sorted(
            deduplicated.values(),
            key=lambda document: (document.relevance, document.published_at is not None),
            reverse=True,
        )[:limit]


def _is_authorized(document: PublishedContentDocument) -> bool:
    parsed = urlsplit(document.canonical_url)
    return bool(
        document.is_published
        and document.is_public
        and not document.is_hidden
        and not document.is_archived
        and document.is_approved
        and document.is_indexable
        and document.allow_ai
        and parsed.scheme in {"http", "https"}
        and parsed.netloc
    )


def _plain_text(value: str, max_chars: int) -> str:
    without_tags = _HTML_TAG.sub(" ", html.unescape(value))
    normalized = _WHITESPACE.sub(" ", without_tags).strip()
    # Prevent source text from closing the prompt delimiter used by the orchestrator.
    normalized = normalized.replace("</source>", "&lt;/source&gt;")
    return normalized[:max_chars]
