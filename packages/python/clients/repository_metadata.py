from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RepositoryMetadataResult:
    provider: str
    repository_identity: str
    fetched_at: datetime
    language: str | None = None
    stars: int | None = None
    forks: int | None = None
    etag: str | None = None
    not_modified: bool = False


class RepositoryMetadataProviderError(Exception):
    def __init__(self, code: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


class RepositoryMetadataClient(Protocol):
    async def fetch(
        self, repository_url: str, *, etag: str | None = None
    ) -> RepositoryMetadataResult: ...

    async def close(self) -> None: ...
