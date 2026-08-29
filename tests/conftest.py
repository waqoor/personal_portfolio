from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from packages.python.clients.database import DatabaseClient
from packages.python.common.models import Base


@pytest.fixture
def png_bytes() -> bytes:
    """A complete 1x1 PNG with valid chunks and checksums."""

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )


@pytest.fixture
async def database_client(tmp_path: Path) -> AsyncIterator[DatabaseClient]:
    database_path = (tmp_path / "test.db").as_posix()
    client = DatabaseClient(f"sqlite+aiosqlite:///{database_path}")
    async with client.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield client
    finally:
        await client.dispose()
