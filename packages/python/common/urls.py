from __future__ import annotations

from urllib.parse import quote, unquote, urlsplit


class CanonicalUrlPolicy:
    """Build same-origin canonical URLs from untrusted local paths."""

    def __init__(self, public_site_url: str) -> None:
        parsed = urlsplit(public_site_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Public site URL must be absolute")
        self._origin = f"{parsed.scheme}://{parsed.netloc}"

    @property
    def origin(self) -> str:
        return self._origin

    def build(self, path: str) -> str:
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("Canonical paths must be local and contain no query or fragment")
        raw_segments = parsed.path.replace("\\", "/").split("/")
        decoded_segments = [unquote(segment) for segment in raw_segments]
        if any(segment == ".." for segment in decoded_segments):
            raise ValueError("Canonical paths cannot traverse parent segments")
        segments = [
            quote(segment, safe="-._~") for segment in decoded_segments if segment not in {"", "."}
        ]
        normalized_path = "/" + "/".join(segments)
        if normalized_path != "/" and parsed.path.endswith("/"):
            normalized_path = normalized_path.rstrip("/")
        return self._origin + normalized_path

    def is_same_origin_url(self, value: str) -> bool:
        parsed = urlsplit(value)
        return f"{parsed.scheme}://{parsed.netloc}" == self._origin
