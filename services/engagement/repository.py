"""SQLAlchemy persistence adapter for engagement behavior."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload

from packages.python.common.errors import ConflictError
from services.engagement.contracts import (
    AdminContactSubmission,
    AdminSponsorshipOption,
    ClaimedContactNotification,
    ContactCreateResult,
    NewContactSubmission,
    PublicSponsorshipOption,
    StoredContactSubmission,
)
from services.engagement.models import (
    ContactNotificationOutbox,
    ContactSubmission,
    SponsorshipOption,
)


class SQLAlchemyEngagementRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_contact_by_idempotency_hash(
        self, idempotency_hash: str
    ) -> StoredContactSubmission | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContactSubmission).where(
                    ContactSubmission.idempotency_hash == idempotency_hash
                )
            )
            model = result.scalar_one_or_none()
        return _to_stored_contact(model) if model is not None else None

    async def create_contact(self, submission: NewContactSubmission) -> ContactCreateResult:
        model = ContactSubmission(
            id=submission.id,
            name=submission.name,
            email=submission.email,
            organization=submission.organization,
            category=submission.category,
            subject=submission.subject,
            message=submission.message,
            consent=submission.consent,
            notification_status=submission.notification_status,
            ip_hash=submission.ip_hash,
            email_hash=submission.email_hash,
            idempotency_hash=submission.idempotency_hash,
            payload_digest=submission.payload_digest,
            created_at=submission.created_at,
        )
        outbox = ContactNotificationOutbox(
            id=str(uuid.uuid4()),
            submission_id=submission.id,
            provider_idempotency_key=f"contact-notification:{submission.id}",
            status=("pending" if submission.notification_status == "pending" else "disabled"),
            next_attempt_at=(
                submission.created_at if submission.notification_status == "pending" else None
            ),
            created_at=submission.created_at,
            updated_at=submission.created_at,
        )
        async with self._session_factory() as session:
            session.add(model)
            session.add(outbox)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                if submission.idempotency_hash is None:
                    raise
                existing = await self.get_contact_by_idempotency_hash(submission.idempotency_hash)
                if existing is None:
                    raise
                return ContactCreateResult(submission=existing, created=False)
        return ContactCreateResult(submission=_to_stored_contact(model), created=True)

    async def list_due_notification_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[str]:
        """Return a bounded candidate batch; claiming remains the concurrency authority."""

        stale_before = now - timedelta(minutes=15)
        async with self._session_factory() as session:
            return list(
                (
                    await session.scalars(
                        select(ContactNotificationOutbox.submission_id)
                        .where(
                            or_(
                                and_(
                                    ContactNotificationOutbox.status.in_(("pending", "retrying")),
                                    or_(
                                        ContactNotificationOutbox.next_attempt_at.is_(None),
                                        ContactNotificationOutbox.next_attempt_at <= now,
                                    ),
                                ),
                                and_(
                                    ContactNotificationOutbox.status == "processing",
                                    or_(
                                        ContactNotificationOutbox.locked_at.is_(None),
                                        ContactNotificationOutbox.locked_at <= stale_before,
                                    ),
                                ),
                            )
                        )
                        .order_by(
                            ContactNotificationOutbox.next_attempt_at.asc().nullsfirst(),
                            ContactNotificationOutbox.created_at.asc(),
                        )
                        .limit(limit)
                    )
                ).all()
            )

    async def claim_notification(
        self,
        submission_id: str,
        *,
        now: datetime,
        force: bool = False,
    ) -> ClaimedContactNotification | None:
        stale_before = now - timedelta(minutes=15)
        async with self._session_factory() as session:
            eligible = or_(
                and_(
                    ContactNotificationOutbox.status.in_(("pending", "retrying")),
                    or_(
                        ContactNotificationOutbox.next_attempt_at.is_(None),
                        ContactNotificationOutbox.next_attempt_at <= now,
                    ),
                ),
                and_(
                    ContactNotificationOutbox.status == "processing",
                    or_(
                        ContactNotificationOutbox.locked_at.is_(None),
                        ContactNotificationOutbox.locked_at <= stale_before,
                    ),
                ),
            )
            if force:
                eligible = or_(eligible, ContactNotificationOutbox.status == "terminal")

            # A conditional write is the claim authority. SELECT FOR UPDATE is ignored by
            # SQLite and can also leave a read/write race in alternative SQL backends.
            # The compare-and-swap predicate guarantees that at most one worker advances
            # a due lease, while the attempt counter fences stale completions.
            claimed = (
                await session.execute(
                    update(ContactNotificationOutbox)
                    .where(
                        ContactNotificationOutbox.submission_id == submission_id,
                        eligible,
                    )
                    .values(
                        status="processing",
                        attempt_count=ContactNotificationOutbox.attempt_count + 1,
                        last_attempt_at=now,
                        locked_at=now,
                        updated_at=now,
                    )
                    .returning(
                        ContactNotificationOutbox.provider_idempotency_key,
                        ContactNotificationOutbox.attempt_count,
                    )
                )
            ).one_or_none()
            if claimed is None:
                await session.rollback()
                return None
            delivery_key, attempt_count = claimed
            await session.execute(
                update(ContactSubmission)
                .where(ContactSubmission.id == submission_id)
                .values(notification_status="pending", notification_updated_at=now)
            )
            submission = await session.scalar(
                select(ContactSubmission).where(ContactSubmission.id == submission_id)
            )
            if submission is None:
                await session.rollback()
                return None
            await session.commit()
            return ClaimedContactNotification(
                submission=_to_stored_contact(submission),
                delivery_key=delivery_key,
                attempt_count=attempt_count,
            )

    async def complete_notification(
        self,
        submission_id: str,
        *,
        expected_attempt_count: int,
        provider_message_id: str | None,
        completed_at: datetime,
    ) -> bool:
        async with self._session_factory() as session:
            updated_id = (
                await session.execute(
                    update(ContactNotificationOutbox)
                    .where(
                        ContactNotificationOutbox.submission_id == submission_id,
                        ContactNotificationOutbox.status == "processing",
                        ContactNotificationOutbox.attempt_count == expected_attempt_count,
                    )
                    .values(
                        status="sent",
                        next_attempt_at=None,
                        locked_at=None,
                        last_error_code=None,
                        provider_message_id=provider_message_id,
                        updated_at=completed_at,
                    )
                    .returning(ContactNotificationOutbox.id)
                )
            ).scalar_one_or_none()
            if updated_id is None:
                await session.rollback()
                return False
            await session.execute(
                update(ContactSubmission)
                .where(ContactSubmission.id == submission_id)
                .values(
                    notification_status="sent",
                    provider_message_id=provider_message_id,
                    notification_error_code=None,
                    notification_updated_at=completed_at,
                )
            )
            await session.commit()
            return True

    async def retry_notification(
        self,
        submission_id: str,
        *,
        expected_attempt_count: int,
        error_code: str,
        next_attempt_at: datetime | None,
        terminal: bool,
        updated_at: datetime,
    ) -> bool:
        status = "terminal" if terminal else "retrying"
        async with self._session_factory() as session:
            updated_id = (
                await session.execute(
                    update(ContactNotificationOutbox)
                    .where(
                        ContactNotificationOutbox.submission_id == submission_id,
                        ContactNotificationOutbox.status == "processing",
                        ContactNotificationOutbox.attempt_count == expected_attempt_count,
                    )
                    .values(
                        status=status,
                        next_attempt_at=next_attempt_at,
                        locked_at=None,
                        last_error_code=error_code,
                        updated_at=updated_at,
                    )
                    .returning(ContactNotificationOutbox.id)
                )
            ).scalar_one_or_none()
            if updated_id is None:
                await session.rollback()
                return False
            await session.execute(
                update(ContactSubmission)
                .where(ContactSubmission.id == submission_id)
                .values(
                    notification_status=status,
                    notification_error_code=error_code,
                    notification_updated_at=updated_at,
                )
            )
            await session.commit()
            return True

    async def list_public_sponsorship_options(self) -> list[PublicSponsorshipOption]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SponsorshipOption)
                .where(
                    SponsorshipOption.is_published.is_(True),
                    SponsorshipOption.is_archived.is_(False),
                )
                .order_by(SponsorshipOption.sort_order, SponsorshipOption.title)
            )
            models = result.scalars().all()
        return [
            PublicSponsorshipOption(
                slug=model.slug,
                title=model.title,
                description=model.description,
                kind=model.kind,
                cta_label=model.cta_label,
                destination_url=model.destination_url,
                amount_minor=model.amount_minor,
                currency=model.currency,
                recurrence=model.recurrence,
                nofollow=model.nofollow,
            )
            for model in models
        ]

    async def list_contact_submissions(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdminContactSubmission], int]:
        async with self._session_factory() as session:
            statement = select(ContactSubmission).options(
                joinedload(ContactSubmission.notification_outbox)
            )
            if status:
                statement = statement.where(ContactSubmission.status == status)
            if search:
                pattern = f"%{search.strip()}%"
                statement = statement.where(
                    or_(
                        ContactSubmission.name.ilike(pattern),
                        ContactSubmission.email.ilike(pattern),
                        ContactSubmission.organization.ilike(pattern),
                        ContactSubmission.subject.ilike(pattern),
                        ContactSubmission.message.ilike(pattern),
                    )
                )
            total = int(
                (
                    await session.scalar(
                        select(func.count()).select_from(statement.order_by(None).subquery())
                    )
                )
                or 0
            )
            models = (
                await session.scalars(
                    statement.order_by(ContactSubmission.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        return [_to_admin_contact(model) for model in models], total

    async def get_contact_submission(self, submission_id: str) -> AdminContactSubmission | None:
        async with self._session_factory() as session:
            model = await session.get(
                ContactSubmission,
                submission_id,
                options=(joinedload(ContactSubmission.notification_outbox),),
            )
        return _to_admin_contact(model) if model is not None else None

    async def update_contact_status(
        self, submission_id: str, status: str
    ) -> AdminContactSubmission | None:
        async with self._session_factory() as session:
            model = await session.get(
                ContactSubmission,
                submission_id,
                options=(joinedload(ContactSubmission.notification_outbox),),
            )
            if model is None:
                return None
            model.status = status
            model.notification_updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(model)
        return _to_admin_contact(model)

    async def reset_contact_notification(
        self, submission_id: str, *, next_attempt_at: datetime
    ) -> AdminContactSubmission | None:
        async with self._session_factory() as session:
            model = await session.get(
                ContactSubmission,
                submission_id,
                options=(joinedload(ContactSubmission.notification_outbox),),
            )
            if model is None or model.notification_outbox is None:
                return None
            outbox = model.notification_outbox
            if outbox.status in {"sent", "disabled"}:
                return _to_admin_contact(model)
            outbox.status = "retrying"
            outbox.next_attempt_at = next_attempt_at
            outbox.locked_at = None
            outbox.last_error_code = None
            outbox.updated_at = next_attempt_at
            model.notification_status = "retrying"
            model.notification_error_code = None
            model.notification_updated_at = next_attempt_at
            await session.commit()
            return _to_admin_contact(model)

    async def list_sponsorship_options(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdminSponsorshipOption], int]:
        async with self._session_factory() as session:
            statement = select(SponsorshipOption)
            if status == "published":
                statement = statement.where(
                    SponsorshipOption.is_published.is_(True),
                    SponsorshipOption.is_archived.is_(False),
                )
            elif status in {"draft", "hidden"}:
                statement = statement.where(
                    SponsorshipOption.is_published.is_(False),
                    SponsorshipOption.is_archived.is_(False),
                )
            elif status == "archived":
                statement = statement.where(SponsorshipOption.is_archived.is_(True))
            if search:
                pattern = f"%{search.strip()}%"
                statement = statement.where(
                    or_(
                        SponsorshipOption.title.ilike(pattern),
                        SponsorshipOption.slug.ilike(pattern),
                        SponsorshipOption.description.ilike(pattern),
                    )
                )
            total = int(
                (
                    await session.scalar(
                        select(func.count()).select_from(statement.order_by(None).subquery())
                    )
                )
                or 0
            )
            models = (
                await session.scalars(
                    statement.order_by(SponsorshipOption.sort_order, SponsorshipOption.title)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        return [_to_admin_sponsorship(model) for model in models], total

    async def create_sponsorship_option(
        self, values: Mapping[str, object]
    ) -> AdminSponsorshipOption:
        model = SponsorshipOption(**dict(values))
        async with self._session_factory() as session:
            session.add(model)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("A sponsorship option with this slug already exists.") from exc
            await session.refresh(model)
        return _to_admin_sponsorship(model)

    async def update_sponsorship_option(
        self, option_id: str, changes: Mapping[str, object]
    ) -> AdminSponsorshipOption | None:
        async with self._session_factory() as session:
            model = await session.get(SponsorshipOption, option_id)
            if model is None:
                return None
            for key, value in changes.items():
                setattr(model, key, value)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("A sponsorship option with this slug already exists.") from exc
            await session.refresh(model)
        return _to_admin_sponsorship(model)


def _to_stored_contact(model: ContactSubmission) -> StoredContactSubmission:
    return StoredContactSubmission(
        id=model.id,
        name=model.name,
        email=model.email,
        organization=model.organization,
        category=model.category,
        subject=model.subject,
        message=model.message,
        payload_digest=model.payload_digest,
        created_at=model.created_at,
    )


def _to_admin_contact(model: ContactSubmission) -> AdminContactSubmission:
    outbox = model.notification_outbox
    return AdminContactSubmission(
        id=model.id,
        name=model.name,
        email=model.email,
        organization=model.organization,
        category=model.category,
        subject=model.subject,
        message=model.message,
        consent=model.consent,
        status=model.status,
        notification_status=model.notification_status,
        notification_error_code=model.notification_error_code,
        notification_attempt_count=outbox.attempt_count if outbox else 0,
        notification_next_attempt_at=outbox.next_attempt_at if outbox else None,
        created_at=model.created_at,
        updated_at=model.notification_updated_at or model.created_at,
    )


def _to_admin_sponsorship(model: SponsorshipOption) -> AdminSponsorshipOption:
    return AdminSponsorshipOption(
        id=model.id,
        slug=model.slug,
        title=model.title,
        description=model.description,
        kind=model.kind,
        cta_label=model.cta_label,
        destination_url=model.destination_url,
        amount_minor=model.amount_minor,
        currency=model.currency,
        recurrence=model.recurrence,
        sort_order=model.sort_order,
        is_published=model.is_published,
        is_archived=model.is_archived,
        nofollow=model.nofollow,
        updated_at=model.updated_at,
    )
