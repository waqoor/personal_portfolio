from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from packages.python.clients.database import DatabaseClient
from packages.python.clients.email import (
    ContactNotification,
    EmailDeliveryResult,
    EmailProviderUnavailable,
    SystemEmail,
)
from packages.python.common.errors import ConflictError, RateLimitExceededError
from packages.python.common.rate_limit import DatabaseRateLimiter
from services.engagement.contracts import StoredContactSubmission
from services.engagement.discovery import EngagementDiscoveryProvider
from services.engagement.models import (
    ContactNotificationOutbox,
    ContactSubmission,
    SponsorshipOption,
)
from services.engagement.repository import SQLAlchemyEngagementRepository
from services.engagement.schemas import (
    ContactRequest,
    ContactStatusUpdate,
    SponsorshipOptionCreate,
    SponsorshipOptionUpdate,
)
from services.engagement.service import (
    ContactRequestContext,
    ContactService,
    ContactServiceConfig,
    EngagementAdminService,
    SponsorshipService,
)


class RecordingEmailClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.notifications: list[ContactNotification] = []

    async def send_contact_notification(
        self, notification: ContactNotification
    ) -> EmailDeliveryResult:
        self.notifications.append(notification)
        if self.fail:
            raise EmailProviderUnavailable("provider unavailable")
        return EmailDeliveryResult(provider_message_id="provider-123")

    async def send_system_email(self, message: SystemEmail) -> EmailDeliveryResult:
        del message
        return EmailDeliveryResult()

    async def health_check(self) -> bool:
        return not self.fail

    async def close(self) -> None:
        return None


class TimeoutAfterSendEmailClient(RecordingEmailClient):
    """Simulate an ambiguous provider timeout after accepting the delivery."""

    def __init__(self) -> None:
        super().__init__()
        self.accepted_by_delivery_key: dict[str, str] = {}

    async def send_contact_notification(
        self, notification: ContactNotification
    ) -> EmailDeliveryResult:
        self.notifications.append(notification)
        existing = self.accepted_by_delivery_key.get(notification.delivery_key)
        if existing is not None:
            return EmailDeliveryResult(provider_message_id=existing)
        provider_message_id = "provider-ambiguous-123"
        self.accepted_by_delivery_key[notification.delivery_key] = provider_message_id
        raise EmailProviderUnavailable("provider timed out after accepting delivery")


def _service(
    database: DatabaseClient,
    email: RecordingEmailClient,
    *,
    ip_limit: int = 8,
) -> ContactService:
    return ContactService(
        repository=SQLAlchemyEngagementRepository(database.session_factory),
        email_client=email,
        rate_limiter=DatabaseRateLimiter(database.session_factory),
        config=ContactServiceConfig(
            enabled=True,
            email_enabled=True,
            privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
            rate_limit_window_seconds=3600,
            ip_limit=ip_limit,
            email_limit=5,
            max_links=2,
        ),
    )


def _request(*, email: str = "visitor@example.com") -> ContactRequest:
    return ContactRequest(
        name="Portfolio Visitor",
        email=email,
        category="project",
        subject="A real project",
        message="I would like to discuss a concrete production project.",
        consent=True,
    )


@pytest.mark.asyncio
async def test_contact_is_committed_before_failed_notification(
    database_client: DatabaseClient,
) -> None:
    email = RecordingEmailClient(fail=True)
    receipt = await _service(database_client, email).submit(
        _request(),
        ContactRequestContext(client_ip="203.0.113.8", idempotency_key="request-key-0001"),
    )

    async with database_client.session_factory() as session:
        stored = await session.get(ContactSubmission, receipt.reference_id)

    assert stored is not None
    assert stored.notification_status == "retrying"
    assert stored.notification_error_code == "provider_unavailable"
    assert stored.ip_hash != "203.0.113.8"
    assert len(stored.ip_hash) == 64
    assert len(email.notifications) == 1
    async with database_client.session_factory() as session:
        outbox = (
            await session.execute(
                select(ContactNotificationOutbox).where(
                    ContactNotificationOutbox.submission_id == receipt.reference_id
                )
            )
        ).scalar_one()
    assert outbox.status == "retrying"
    assert outbox.attempt_count == 1
    assert outbox.next_attempt_at is not None


@pytest.mark.asyncio
async def test_contact_idempotency_key_is_bound_to_canonical_payload(
    database_client: DatabaseClient,
) -> None:
    service = _service(database_client, RecordingEmailClient())
    context = ContactRequestContext(client_ip="203.0.113.9", idempotency_key="payload-key-0001")
    await service.submit(_request(), context)

    changed = _request().model_copy(update={"message": "A different production request body."})
    with pytest.raises(ConflictError, match="different contact request"):
        await service.submit(changed, context)


@pytest.mark.asyncio
async def test_contact_idempotency_prevents_duplicate_write_and_notification(
    database_client: DatabaseClient,
) -> None:
    email = RecordingEmailClient()
    service = _service(database_client, email)
    context = ContactRequestContext(client_ip="203.0.113.9", idempotency_key="request-key-0002")

    first = await service.submit(_request(), context)
    second = await service.submit(_request(), context)

    async with database_client.session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ContactSubmission))
    assert first.reference_id == second.reference_id
    assert count == 1
    assert len(email.notifications) == 1


@pytest.mark.asyncio
async def test_contact_idempotency_race_does_not_repeat_notification(
    database_client: DatabaseClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = RecordingEmailClient()
    repository = SQLAlchemyEngagementRepository(database_client.session_factory)
    original_lookup = repository.get_contact_by_idempotency_hash
    lookup_count = 0

    async def simulate_stale_preflight(
        idempotency_hash: str,
    ) -> StoredContactSubmission | None:
        nonlocal lookup_count
        lookup_count += 1
        if lookup_count <= 2:
            return None
        return await original_lookup(idempotency_hash)

    monkeypatch.setattr(repository, "get_contact_by_idempotency_hash", simulate_stale_preflight)
    service = ContactService(
        repository=repository,
        email_client=email,
        rate_limiter=DatabaseRateLimiter(database_client.session_factory),
        config=ContactServiceConfig(
            enabled=True,
            email_enabled=True,
            privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
            rate_limit_window_seconds=3600,
            ip_limit=8,
            email_limit=5,
            max_links=2,
        ),
    )
    context = ContactRequestContext(client_ip="203.0.113.11", idempotency_key="race-key-0001")

    first = await service.submit(_request(), context)
    second = await service.submit(_request(), context)

    assert second.reference_id == first.reference_id
    assert len(email.notifications) == 1


@pytest.mark.asyncio
async def test_notification_retries_are_bounded_and_reuse_provider_key(
    database_client: DatabaseClient,
) -> None:
    email = RecordingEmailClient(fail=True)
    repository = SQLAlchemyEngagementRepository(database_client.session_factory)
    service = _service(database_client, email)
    admin = EngagementAdminService(repository, service)
    receipt = await service.submit(
        _request(),
        ContactRequestContext(client_ip="203.0.113.12", idempotency_key="retry-key-0001"),
    )

    for _ in range(4):
        await admin.retry_contact_notification(receipt.reference_id)

    terminal = await repository.get_contact_submission(receipt.reference_id)
    assert terminal is not None
    assert terminal.notification_status == "terminal"
    assert terminal.notification_attempt_count == 5
    assert len({item.delivery_key for item in email.notifications}) == 1

    email.fail = False
    recovered = await admin.retry_contact_notification(receipt.reference_id)
    assert recovered.notification_status == "sent"
    assert recovered.notification_attempt_count == 6


@pytest.mark.asyncio
async def test_due_worker_recovers_timeout_after_send_without_duplicate_delivery(
    database_client: DatabaseClient,
) -> None:
    email = TimeoutAfterSendEmailClient()
    repository = SQLAlchemyEngagementRepository(database_client.session_factory)
    service = _service(database_client, email)
    receipt = await service.submit(
        _request(),
        ContactRequestContext(client_ip="203.0.113.13", idempotency_key="worker-key-0001"),
    )
    failed = await repository.get_contact_submission(receipt.reference_id)
    assert failed is not None
    assert failed.notification_status == "retrying"
    await repository.reset_contact_notification(
        receipt.reference_id,
        next_attempt_at=datetime.now(UTC),
    )

    concurrent_results = await asyncio.gather(
        service.process_due_notifications(),
        service.process_due_notifications(),
    )
    repeated = await service.process_due_notifications()

    assert sum(result.sent_count for result in concurrent_results) == 1
    assert repeated.selected_count == 0
    assert len(email.notifications) == 2
    assert len({item.delivery_key for item in email.notifications}) == 1
    assert len(email.accepted_by_delivery_key) == 1
    stored = await repository.get_contact_submission(receipt.reference_id)
    assert stored is not None
    assert stored.notification_status == "sent"
    assert stored.notification_attempt_count == 2


@pytest.mark.asyncio
async def test_expired_notification_lease_rejects_stale_worker_completion(
    database_client: DatabaseClient,
) -> None:
    email = RecordingEmailClient(fail=True)
    repository = SQLAlchemyEngagementRepository(database_client.session_factory)
    service = _service(database_client, email)
    receipt = await service.submit(
        _request(),
        ContactRequestContext(client_ip="203.0.113.14", idempotency_key="lease-key-0001"),
    )
    await repository.reset_contact_notification(
        receipt.reference_id,
        next_attempt_at=datetime.now(UTC),
    )
    first = await repository.claim_notification(receipt.reference_id, now=datetime.now(UTC))
    assert first is not None
    async with database_client.session_factory() as session:
        outbox = (
            await session.execute(
                select(ContactNotificationOutbox).where(
                    ContactNotificationOutbox.submission_id == receipt.reference_id
                )
            )
        ).scalar_one()
        outbox.locked_at = datetime(2020, 1, 1, tzinfo=UTC)
        await session.commit()
    second = await repository.claim_notification(receipt.reference_id, now=datetime.now(UTC))
    assert second is not None
    assert second.attempt_count == first.attempt_count + 1

    stale_completion = await repository.complete_notification(
        receipt.reference_id,
        expected_attempt_count=first.attempt_count,
        provider_message_id="stale-provider-result",
        completed_at=datetime.now(UTC),
    )
    current_completion = await repository.complete_notification(
        receipt.reference_id,
        expected_attempt_count=second.attempt_count,
        provider_message_id="current-provider-result",
        completed_at=datetime.now(UTC),
    )

    assert stale_completion is False
    assert current_completion is True
    stored = await repository.get_contact_submission(receipt.reference_id)
    assert stored is not None
    assert stored.notification_status == "sent"


@pytest.mark.asyncio
async def test_contact_rate_limit_is_database_backed(database_client: DatabaseClient) -> None:
    service = _service(database_client, RecordingEmailClient(), ip_limit=1)
    await service.submit(
        _request(email="one@example.com"),
        ContactRequestContext(client_ip="203.0.113.10"),
    )

    with pytest.raises(RateLimitExceededError):
        await service.submit(
            _request(email="two@example.com"),
            ContactRequestContext(client_ip="203.0.113.10"),
        )


@pytest.mark.asyncio
async def test_honeypot_submission_is_not_persisted(database_client: DatabaseClient) -> None:
    request = _request().model_copy(update={"website": "https://spam.invalid"})
    await _service(database_client, RecordingEmailClient()).submit(
        request,
        ContactRequestContext(client_ip="198.51.100.2"),
    )

    async with database_client.session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ContactSubmission))
    assert count == 0


@pytest.mark.asyncio
async def test_sponsorship_lists_only_published_options(
    database_client: DatabaseClient,
) -> None:
    async with database_client.session_factory() as session:
        session.add_all(
            [
                SponsorshipOption(
                    id="00000000-0000-0000-0000-000000000001",
                    slug="github",
                    title="Sponsor open source",
                    description="Support ongoing public work.",
                    kind="external",
                    cta_label="Sponsor",
                    destination_url="https://github.com/sponsors/example",
                    sort_order=1,
                    is_published=True,
                    is_archived=False,
                    nofollow=True,
                    updated_at=datetime.now(UTC),
                ),
                SponsorshipOption(
                    id="00000000-0000-0000-0000-000000000002",
                    slug="draft",
                    title="Draft",
                    description="Not public.",
                    kind="external",
                    cta_label="Draft",
                    destination_url="https://example.com/draft",
                    sort_order=2,
                    is_published=False,
                    is_archived=False,
                    updated_at=datetime.now(UTC),
                ),
            ]
        )
        await session.commit()

    response = await SponsorshipService(
        repository=SQLAlchemyEngagementRepository(database_client.session_factory),
        enabled=True,
    ).list_public_options()

    assert [item.slug for item in response.items] == ["github"]
    assert response.items[0].rel == "sponsored nofollow noopener"


@pytest.mark.asyncio
async def test_sponsorship_database_rejects_an_unsafe_destination(
    database_client: DatabaseClient,
) -> None:
    async with database_client.session_factory() as session:
        session.add(
            SponsorshipOption(
                id="00000000-0000-0000-0000-000000000003",
                slug="unsafe",
                title="Unsafe",
                description="Invalid scheme.",
                kind="external",
                cta_label="Unsafe",
                destination_url="http://example.com",
                sort_order=3,
                is_published=True,
                is_archived=False,
                updated_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_discovery_exposes_only_available_engagement_routes(
    database_client: DatabaseClient,
) -> None:
    repository = SQLAlchemyEngagementRepository(database_client.session_factory)
    contact = _service(database_client, RecordingEmailClient())
    sponsorship = SponsorshipService(repository=repository, enabled=True)
    provider = EngagementDiscoveryProvider(
        contact=contact,
        sponsorship=sponsorship,
    )

    assert [document.path for document in await provider.list_for_discovery()] == [
        "/contact",
        "/sponsor",
    ]

    async with database_client.session_factory() as session:
        session.add(
            SponsorshipOption(
                id="00000000-0000-0000-0000-000000000004",
                slug="verified-sponsor",
                title="Sponsor the test portfolio",
                description="A published test-only sponsorship option.",
                kind="external",
                cta_label="Sponsor",
                destination_url="https://example.com/sponsor",
                sort_order=1,
                is_published=True,
                is_archived=False,
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    assert [document.path for document in await provider.list_for_discovery()] == [
        "/contact",
        "/sponsor",
    ]


@pytest.mark.asyncio
async def test_authenticated_engagement_management_uses_canonical_records(
    database_client: DatabaseClient,
) -> None:
    repository = SQLAlchemyEngagementRepository(database_client.session_factory)
    admin = EngagementAdminService(repository)
    contact = _service(database_client, RecordingEmailClient())
    receipt = await contact.submit(
        _request(),
        ContactRequestContext(client_ip="203.0.113.22"),
    )

    inbox = await admin.list_contacts(limit=20, offset=0)
    assert inbox.total == 1
    assert inbox.items[0].id == receipt.reference_id
    updated_contact = await admin.update_contact_status(
        receipt.reference_id,
        ContactStatusUpdate(status="read"),
    )
    assert updated_contact.status == "read"

    created = await admin.create_sponsorship(
        SponsorshipOptionCreate(
            slug="canonical-option",
            title="Canonical sponsorship",
            description="A test-only published sponsorship option.",
            kind="external",
            cta_label="Sponsor",
            destination_url="https://example.com/sponsor",
            is_published=True,
        )
    )
    assert (await admin.list_sponsorship(limit=20, offset=0)).total == 1
    assert [
        item.slug
        for item in (
            await SponsorshipService(repository=repository, enabled=True).list_public_options()
        ).items
    ] == ["canonical-option"]

    archived = await admin.archive_sponsorship(created.id)
    assert archived.is_archived is True
    assert (
        await SponsorshipService(repository=repository, enabled=True).list_public_options()
    ).items == []


def test_sponsorship_admin_rejects_non_https_destination() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        SponsorshipOptionCreate(
            slug="unsafe-option",
            title="Unsafe",
            description="This option must be rejected.",
            kind="external",
            cta_label="Open",
            destination_url="http://example.com/sponsor",
        )


def test_sponsorship_partial_amount_update_requires_currency_pair() -> None:
    with pytest.raises(ValueError, match="updated together"):
        SponsorshipOptionUpdate(amount_minor=2500)

    update = SponsorshipOptionUpdate(amount_minor=None, currency=None)
    assert update.model_dump(exclude_unset=True) == {
        "amount_minor": None,
        "currency": None,
    }
