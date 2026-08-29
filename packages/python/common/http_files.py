from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.responses import Response, StreamingResponse

from packages.python.clients.storage import StorageClient


def _parse_range(value: str | None, size: int) -> tuple[int, int] | None:
    if value is None:
        return None
    if not value.startswith("bytes=") or "," in value:
        raise ValueError
    start_text, separator, end_text = value[6:].partition("-")
    if not separator:
        raise ValueError
    if not start_text:
        suffix = int(end_text)
        if suffix <= 0:
            raise ValueError
        return max(0, size - suffix), size - 1
    start = int(start_text)
    end = int(end_text) if end_text else size - 1
    if start < 0 or start >= size or end < start:
        raise ValueError
    return start, min(end, size - 1)


def _etag_matches(value: str | None, etag: str) -> bool:
    if value is None:
        return False
    expected = f'"{etag}"'
    for candidate in value.split(","):
        candidate = candidate.strip()
        if candidate == "*":
            return True
        if candidate.startswith("W/"):
            candidate = candidate[2:].strip()
        if candidate == expected:
            return True
    return False


async def storage_file_response(
    *,
    storage: StorageClient,
    key: str,
    size: int,
    media_type: str,
    etag: str,
    range_header: str | None,
    cache_control: str,
    disposition: str | None = None,
    if_none_match: str | None = None,
) -> Response:
    headers = {
        "ETag": f'"{etag}"',
        "Cache-Control": cache_control,
        "Accept-Ranges": "bytes",
    }
    if _etag_matches(if_none_match, etag):
        return Response(status_code=304, headers=headers)

    try:
        byte_range = _parse_range(range_header, size)
    except (ValueError, TypeError):
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"},
        )

    if disposition:
        headers["Content-Disposition"] = disposition
    if byte_range is None:
        start, end, status_code = 0, size - 1, 200
    else:
        start, end = byte_range
        status_code = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    headers["Content-Length"] = str(max(0, end - start + 1))

    iterator: AsyncIterator[bytes] = storage.iter_bytes(key, start=start, end=end)
    return StreamingResponse(
        iterator,
        status_code=status_code,
        media_type=media_type,
        headers=headers,
    )
