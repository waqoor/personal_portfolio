"""Composition registry for public discovery DTO providers."""

from __future__ import annotations

from services.discovery.contracts import DiscoveryContentProvider, DiscoveryDocument
from services.discovery.policies import PublicationIndexPolicy


class DiscoveryContentRegistry:
    def __init__(self, providers: tuple[DiscoveryContentProvider, ...] = ()) -> None:
        self._providers = list(providers)
        self._publication_policy = PublicationIndexPolicy()

    def register(self, provider: DiscoveryContentProvider) -> None:
        self._providers.append(provider)

    async def list_public(self) -> list[DiscoveryDocument]:
        documents: list[DiscoveryDocument] = []
        for provider in self._providers:
            provided = await provider.list_for_discovery()
            documents.extend(
                document
                for document in provided
                if self._publication_policy.is_publicly_renderable(document)
            )
        by_path: dict[str, DiscoveryDocument] = {}
        for document in documents:
            existing = by_path.get(document.path)
            if existing is None or _modified_sort_key(document) > _modified_sort_key(existing):
                by_path[document.path] = document
        return sorted(by_path.values(), key=lambda document: document.path)

    async def get_public(self, path: str) -> DiscoveryDocument | None:
        documents = await self.list_public()
        normalized = "/" + path.strip().strip("/") if path.strip("/") else "/"
        return next(
            (
                document
                for document in documents
                if "/" + document.path.strip().strip("/") == normalized
            ),
            None,
        )


def _modified_sort_key(document: DiscoveryDocument) -> float:
    value = document.modified_at or document.published_at
    return value.timestamp() if value else 0.0
