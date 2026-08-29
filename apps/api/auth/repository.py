from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.models import AdminSession, AdminUser, LoginAttempt


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_email(self, email: str) -> AdminUser | None:
        return cast(
            AdminUser | None,
            await self.session.scalar(select(AdminUser).where(AdminUser.email == email)),
        )

    async def get_user(self, user_id: UUID) -> AdminUser | None:
        return await self.session.get(AdminUser, user_id)

    def add_user(self, user: AdminUser) -> AdminUser:
        self.session.add(user)
        return user

    async def get_session_by_token_hash(self, token_hash: str) -> AdminSession | None:
        return cast(
            AdminSession | None,
            await self.session.scalar(
                select(AdminSession).where(AdminSession.token_hash == token_hash)
            ),
        )

    def add_session(self, admin_session: AdminSession) -> AdminSession:
        self.session.add(admin_session)
        return admin_session

    async def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        await self.session.execute(
            update(AdminSession)
            .where(AdminSession.id == session_id, AdminSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

    async def revoke_all_user_sessions(self, user_id: UUID, revoked_at: datetime) -> None:
        await self.session.execute(
            update(AdminSession)
            .where(AdminSession.admin_user_id == user_id, AdminSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

    async def count_recent_identifier_failures(
        self, identifier_digest: str, since: datetime
    ) -> int:
        statement = select(func.count(LoginAttempt.id)).where(
            LoginAttempt.identifier_digest == identifier_digest,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.occurred_at >= since,
        )
        return int((await self.session.scalar(statement)) or 0)

    async def count_recent_ip_failures(self, ip_digest: str, since: datetime) -> int:
        statement = select(func.count(LoginAttempt.id)).where(
            LoginAttempt.ip_digest == ip_digest,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.occurred_at >= since,
        )
        return int((await self.session.scalar(statement)) or 0)

    def add_attempt(
        self, identifier_digest: str, ip_digest: str, *, succeeded: bool
    ) -> LoginAttempt:
        attempt = LoginAttempt(
            identifier_digest=identifier_digest,
            ip_digest=ip_digest,
            succeeded=succeeded,
        )
        self.session.add(attempt)
        return attempt

    async def clear_identifier_failures(self, identifier_digest: str) -> None:
        await self.session.execute(
            delete(LoginAttempt).where(
                LoginAttempt.identifier_digest == identifier_digest,
                LoginAttempt.succeeded.is_(False),
            )
        )

    async def purge_attempts_before(self, cutoff: datetime) -> None:
        await self.session.execute(delete(LoginAttempt).where(LoginAttempt.occurred_at < cutoff))
