from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from apps.api.auth.models import AdminRole, AdminSession, AdminUser
from apps.api.auth.repository import AuthRepository
from apps.api.auth.schemas import AdminCredentialsUpdate, CreateAdminInput
from packages.python.common.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
)
from packages.python.common.errors import UnauthorizedError as AuthenticationError
from packages.python.common.rate_limit import DatabaseRateLimiter, RateLimitRequest
from packages.python.common.repository import TransactionManager
from packages.python.common.security import (
    PasswordService,
    generate_token,
    hash_token,
    keyed_digest,
)
from packages.python.common.settings import Settings

logger = logging.getLogger(__name__)
_IP_FAILURE_NAMESPACE = "auth-ip-failure"
_ACCOUNT_FAILURE_NAMESPACE = "auth-account-failure"


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: AdminUser
    session: AdminSession
    session_token: str
    csrf_token: str


@dataclass(frozen=True, slots=True)
class CurrentAdmin:
    user: AdminUser
    session: AdminSession


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        transaction: TransactionManager,
        settings: Settings,
        password_service: PasswordService,
        rate_limiter: DatabaseRateLimiter | None = None,
    ) -> None:
        self.repository = repository
        self.transaction = transaction
        self.settings = settings
        self.password_service = password_service
        self.rate_limiter = rate_limiter

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().casefold()

    async def login(self, email: str, password: str, client_ip: str) -> AuthenticatedSession:
        now = datetime.now(UTC)
        normalized_email = self.normalize_email(email)
        secret = self.settings.auth_secret.get_secret_value()
        identifier_digest = keyed_digest(normalized_email, secret)
        ip_digest = keyed_digest(client_ip, secret)
        window = timedelta(seconds=self.settings.login_window_seconds)
        cutoff = now - window
        ip_failure_count = await self.repository.count_recent_ip_failures(ip_digest, cutoff)
        if ip_failure_count >= self.settings.login_max_failures:
            raise RateLimitError(self.settings.login_window_seconds)

        user = await self.repository.get_user_by_email(normalized_email)
        valid = self.password_service.verify(user.password_hash if user else None, password)
        if not valid or user is None or not user.is_active:
            account_failure_count = await self.repository.count_recent_identifier_failures(
                identifier_digest, cutoff
            )
            ip_bucket_allowed = True
            account_bucket_allowed = True
            if self.rate_limiter is not None:
                ip_bucket_allowed = await self.rate_limiter.consume(
                    (
                        RateLimitRequest(
                            namespace=_IP_FAILURE_NAMESPACE,
                            identity_hash=ip_digest,
                            limit=self.settings.login_max_failures,
                            window_seconds=self.settings.login_window_seconds,
                        ),
                    )
                )
                account_bucket_allowed = await self.rate_limiter.consume(
                    (
                        RateLimitRequest(
                            namespace=_ACCOUNT_FAILURE_NAMESPACE,
                            identity_hash=identifier_digest,
                            limit=max(1, self.settings.login_account_delay_threshold - 1),
                            window_seconds=self.settings.login_window_seconds,
                        ),
                    )
                )
            self.repository.add_attempt(identifier_digest, ip_digest, succeeded=False)
            await self.transaction.commit()
            if not ip_bucket_allowed:
                raise RateLimitError(self.settings.login_window_seconds)
            if account_failure_count + 1 >= self.settings.login_account_delay_threshold:
                exponent = min(
                    account_failure_count + 1 - self.settings.login_account_delay_threshold,
                    10,
                )
                retry_after = min(
                    2**exponent,
                    self.settings.login_account_max_delay_seconds,
                )
                raise RateLimitError(retry_after)
            if not account_bucket_allowed:
                raise RateLimitError(1)
            raise AuthenticationError("Invalid email or password.")

        session_token = generate_token()
        csrf_token = generate_token()
        expires_at = now + timedelta(seconds=self.settings.session_ttl_seconds)
        admin_session = AdminSession(
            admin_user_id=user.id,
            token_hash=hash_token(session_token),
            csrf_hash=hash_token(csrf_token),
            expires_at=expires_at,
            last_seen_at=now,
        )
        if self.password_service.needs_rehash(user.password_hash):
            user.password_hash = self.password_service.hash(password)
        user.last_login_at = now
        self.repository.add_session(admin_session)
        await self.repository.clear_identifier_failures(identifier_digest)
        self.repository.add_attempt(identifier_digest, ip_digest, succeeded=True)
        await self.repository.purge_attempts_before(now - timedelta(days=7))
        await self.transaction.commit()
        if self.rate_limiter is not None:
            try:
                await self.rate_limiter.reset(
                    namespace=_ACCOUNT_FAILURE_NAMESPACE,
                    identity_hash=identifier_digest,
                )
            except Exception:
                logger.warning("login_account_bucket_reset_failed", exc_info=False)
        return AuthenticatedSession(user, admin_session, session_token, csrf_token)

    async def authenticate(
        self, session_token: str | None, csrf_token: str | None = None
    ) -> CurrentAdmin:
        if not session_token:
            raise AuthenticationError()
        admin_session = await self.repository.get_session_by_token_hash(hash_token(session_token))
        now = datetime.now(UTC)
        expires_at = admin_session.expires_at if admin_session is not None else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            admin_session is None
            or admin_session.revoked_at is not None
            or expires_at is None
            or expires_at <= now
            or not admin_session.user.is_active
        ):
            raise AuthenticationError()
        if csrf_token is not None and not hmac.compare_digest(
            admin_session.csrf_hash, hash_token(csrf_token)
        ):
            raise ForbiddenError("CSRF validation failed.")
        return CurrentAdmin(admin_session.user, admin_session)

    async def logout(self, current: CurrentAdmin) -> None:
        await self.repository.revoke_session(current.session.id, datetime.now(UTC))
        await self.transaction.commit()

    async def create_admin(self, data: CreateAdminInput) -> AdminUser:
        normalized_email = self.normalize_email(str(data.email))
        if await self.repository.get_user_by_email(normalized_email):
            raise ConflictError("An admin with this email already exists.")
        user = AdminUser(
            email=normalized_email,
            display_name=data.display_name,
            password_hash=self.password_service.hash(data.password),
            role=data.role,
        )
        self.repository.add_user(user)
        try:
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError("An admin with this email already exists.") from exc
        return user

    async def update_admin_credentials(
        self,
        current_email: str,
        data: AdminCredentialsUpdate,
    ) -> AdminUser:
        user = await self.repository.get_user_by_email(self.normalize_email(current_email))
        if user is None:
            raise NotFoundError("The administrator account does not exist.")

        normalized_email = self.normalize_email(str(data.email))
        conflicting_user = await self.repository.get_user_by_email(normalized_email)
        if conflicting_user is not None and conflicting_user.id != user.id:
            raise ConflictError("An admin with this email already exists.")

        user.email = normalized_email
        user.password_hash = self.password_service.hash(data.password)
        if data.display_name is not None:
            user.display_name = data.display_name
        await self.repository.revoke_all_user_sessions(user.id, datetime.now(UTC))
        try:
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError("An admin with this email already exists.") from exc
        return user

    @staticmethod
    def require_owner(current: CurrentAdmin) -> None:
        if current.user.role is not AdminRole.OWNER:
            raise ForbiddenError("Owner access is required.")
