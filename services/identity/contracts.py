from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from services.identity.schemas import ProfileRead, PublicResumeRead


class IdentityPublicReader(Protocol):
    async def get_public_profile(self) -> ProfileRead | None: ...

    async def get_public_current_resume(self) -> PublicResumeRead | None: ...


IdentityPublicReaderFactory = Callable[[], AbstractAsyncContextManager[IdentityPublicReader]]
