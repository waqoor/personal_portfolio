"""Canonical URL and indexability policies reused by every discovery surface."""

from __future__ import annotations

from dataclasses import dataclass

from packages.python.common.urls import CanonicalUrlPolicy
from services.discovery.contracts import DiscoveryDocument


@dataclass(frozen=True, slots=True)
class IndexDecision:
    index: bool
    follow: bool
    directive: str


class PublicationIndexPolicy:
    def decide(self, document: DiscoveryDocument) -> IndexDecision:
        index = bool(
            document.is_published
            and document.is_public
            and not document.is_hidden
            and not document.is_archived
            and not document.noindex
        )
        return IndexDecision(
            index=index,
            follow=index,
            directive=(
                "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
                if index
                else "noindex, nofollow"
            ),
        )

    def is_publicly_renderable(self, document: DiscoveryDocument) -> bool:
        return bool(
            document.is_published
            and document.is_public
            and not document.is_hidden
            and not document.is_archived
        )


__all__ = ["CanonicalUrlPolicy", "IndexDecision", "PublicationIndexPolicy"]
