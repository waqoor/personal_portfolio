from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

import httpx

from packages.python.clients.repository_metadata import (
    RepositoryMetadataProviderError,
    RepositoryMetadataResult,
)


class GitHubRepositoryMetadataClient:
    """Bounded adapter for GitHub's public repository source of record."""

    def __init__(
        self,
        *,
        token: str | None = None,
        timeout_seconds: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "portfolio-repository-metadata/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )
        self._owns_client = client is None

    async def fetch(
        self, repository_url: str, *, etag: str | None = None
    ) -> RepositoryMetadataResult:
        identity = _github_identity(repository_url)
        headers = {"If-None-Match": etag} if etag else None
        try:
            response = await self._client.get(
                f"/repos/{quote(identity, safe='/')}", headers=headers
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RepositoryMetadataProviderError("provider_unavailable") from exc

        if response.status_code == 304:
            return RepositoryMetadataResult(
                provider="github",
                repository_identity=identity,
                fetched_at=datetime.now(UTC),
                etag=etag,
                not_modified=True,
            )
        if response.status_code in {403, 429}:
            raise RepositoryMetadataProviderError(
                "rate_limited",
                retry_after_seconds=_retry_after(response.headers.get("Retry-After")),
            )
        if response.status_code == 404:
            raise RepositoryMetadataProviderError("not_found_or_private")
        if response.status_code != 200:
            raise RepositoryMetadataProviderError("provider_unavailable")

        try:
            payload = response.json()
            resolved_identity = str(payload["full_name"])
            language_value = payload.get("language")
            language = str(language_value) if language_value else None
            stars = int(payload["stargazers_count"])
            forks = int(payload["forks_count"])
            private = bool(payload["private"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RepositoryMetadataProviderError("invalid_provider_response") from exc
        if private:
            raise RepositoryMetadataProviderError("not_found_or_private")
        if stars < 0 or forks < 0:
            raise RepositoryMetadataProviderError("invalid_provider_response")
        return RepositoryMetadataResult(
            provider="github",
            repository_identity=resolved_identity,
            fetched_at=datetime.now(UTC),
            language=language,
            stars=stars,
            forks=forks,
            etag=response.headers.get("ETag"),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _github_identity(repository_url: str) -> str:
    parsed = urlsplit(repository_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise RepositoryMetadataProviderError("unsupported_repository_url")
    segments = [segment for segment in parsed.path.strip("/").split("/") if segment]
    if len(segments) != 2:
        raise RepositoryMetadataProviderError("unsupported_repository_url")
    owner, repository = segments
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository or any(value in {".", ".."} for value in (owner, repository)):
        raise RepositoryMetadataProviderError("unsupported_repository_url")
    return f"{owner}/{repository}"


def _retry_after(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return max(0, min(int(value), 86_400))
    except ValueError:
        return None
