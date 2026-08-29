from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from packages.python.common.errors import NotFoundError, StorageError, ValidationError


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    size_bytes: int
    sha256: str


class StorageClient(Protocol):
    async def save(self, key: str, content: bytes) -> StoredObject: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def exists(self, key: str) -> bool: ...

    def iter_bytes(
        self, key: str, *, start: int = 0, end: int | None = None, chunk_size: int = 64 * 1024
    ) -> AsyncIterator[bytes]: ...


class LocalStorageClient:
    """Atomic, path-contained adapter for a persistent local media volume."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        candidate = PurePosixPath(key)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValidationError("Invalid storage key.")
        resolved = self._root.joinpath(*candidate.parts).resolve()
        if not resolved.is_relative_to(self._root):
            raise ValidationError("Invalid storage key.")
        return resolved

    async def save(self, key: str, content: bytes) -> StoredObject:
        destination = self._resolve(key)
        digest = hashlib.sha256(content).hexdigest()

        def _write() -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".upload-", dir=destination.parent)
            temporary_path = Path(temporary)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, destination)
            except OSError as exc:
                temporary_path.unlink(missing_ok=True)
                raise StorageError() from exc

        await asyncio.to_thread(_write)
        return StoredObject(key=key, size_bytes=len(content), sha256=digest)

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise NotFoundError("The managed file was not found.") from exc
        except OSError as exc:
            raise StorageError() from exc

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as exc:
            raise StorageError() from exc

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._resolve(key).is_file)

    async def iter_bytes(
        self, key: str, *, start: int = 0, end: int | None = None, chunk_size: int = 64 * 1024
    ) -> AsyncIterator[bytes]:
        path = self._resolve(key)
        try:
            handle = await asyncio.to_thread(path.open, "rb")
        except FileNotFoundError as exc:
            raise NotFoundError("The managed file was not found.") from exc
        try:
            await asyncio.to_thread(handle.seek, start)
            remaining = None if end is None else end - start + 1
            while remaining is None or remaining > 0:
                read_size = chunk_size if remaining is None else min(chunk_size, remaining)
                chunk = await asyncio.to_thread(handle.read, read_size)
                if not chunk:
                    break
                if remaining is not None:
                    remaining -= len(chunk)
                yield chunk
        except OSError as exc:
            raise StorageError() from exc
        finally:
            await asyncio.to_thread(handle.close)
