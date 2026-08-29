from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from packages.python.clients.database import DatabaseClient
from packages.python.clients.repository_metadata import RepositoryMetadataResult
from packages.python.clients.storage import LocalStorageClient
from packages.python.common.errors import ConflictError
from packages.python.common.models import PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.settings import Settings
from packages.python.contracts.seeding import SeedSource
from services.content.models import Article
from services.content.repository import ContentRepository
from services.engagement.models import SponsorshipOption
from services.identity.models import Profile, ResumeVersion
from services.identity.repository import IdentityRepository
from services.identity.seeding import IdentitySeedData, IdentitySeeder
from services.portfolio.models import (
    ImpactMetric,
    Project,
    ProjectNature,
    RepositoryMetadataSnapshot,
)
from services.portfolio.models import (
    Testimonial as PortfolioTestimonial,
)
from services.portfolio.repository import PortfolioRepository
from services.portfolio.schemas import (
    MetricRead,
    MetricUpdate,
    RepositoryMetadataAdminRead,
)
from services.portfolio.schemas import (
    TestimonialRead as PortfolioTestimonialRead,
)
from services.portfolio.schemas import (
    TestimonialUpdate as PortfolioTestimonialUpdate,
)
from services.portfolio.service import PortfolioService

pytestmark = pytest.mark.integration


def _postgres_url() -> str:
    value = os.getenv("CORE_TEST_DATABASE_URL")
    if not value:
        pytest.skip("CORE_TEST_DATABASE_URL is not configured")
    if not value.startswith("postgresql+asyncpg://"):
        pytest.fail("CORE_TEST_DATABASE_URL must use PostgreSQL with asyncpg")
    return value


@pytest.fixture
async def postgres_session() -> AsyncIterator[AsyncSession]:
    database = DatabaseClient(_postgres_url(), pool_size=2, max_overflow=0)
    async with database.engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()
    await database.dispose()


@pytest.mark.asyncio
async def test_postgres_enforces_one_global_current_resume(
    postgres_session: AsyncSession,
) -> None:
    first_profile = Profile(
        full_name="First",
        headline="First profile",
        short_bio="First profile biography.",
        is_primary=True,
    )
    second_profile = Profile(
        full_name="Second",
        headline="Second profile",
        short_bio="Second profile biography.",
        is_primary=False,
    )
    PublicationPolicy.apply(first_profile, PublicationStatus.PUBLISHED)
    PublicationPolicy.apply(second_profile, PublicationStatus.PUBLISHED)
    postgres_session.add_all([first_profile, second_profile])
    await postgres_session.flush()
    postgres_session.add_all(
        [
            ResumeVersion(
                profile_id=first_profile.id,
                version_label="First",
                storage_key="postgres-test/first.pdf",
                original_filename="first.pdf",
                media_type="application/pdf",
                size_bytes=10,
                sha256="a" * 64,
                download_name="resume.pdf",
                is_current=True,
            ),
            ResumeVersion(
                profile_id=second_profile.id,
                version_label="Second",
                storage_key="postgres-test/second.pdf",
                original_filename="second.pdf",
                media_type="application/pdf",
                size_bytes=10,
                sha256="b" * 64,
                download_name="resume.pdf",
                is_current=True,
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        await postgres_session.flush()


@pytest.mark.asyncio
async def test_postgres_rejects_subjectless_metrics(
    postgres_session: AsyncSession,
) -> None:
    metric = ImpactMetric(
        label="Invalid",
        value="1",
        context="A metric without a subject must be rejected by the database.",
        is_approved=False,
    )
    PublicationPolicy.apply(metric, PublicationStatus.DRAFT)
    postgres_session.add(metric)
    with pytest.raises(IntegrityError):
        await postgres_session.flush()


@pytest.mark.asyncio
async def test_postgres_rejects_approval_without_audited_actor_and_timestamp(
    postgres_session: AsyncSession,
) -> None:
    metric = ImpactMetric(
        subject_label="Database approval invariant",
        label="Invalid approval",
        value="1",
        context="A hash alone must never make an evidence claim verified.",
        is_approved=True,
        approved_revision_hash="a" * 64,
    )
    PublicationPolicy.apply(metric, PublicationStatus.PUBLISHED)
    postgres_session.add(metric)
    with pytest.raises(IntegrityError):
        await postgres_session.flush()


@pytest.mark.asyncio
async def test_claim_edits_serialize_on_the_same_rows_as_approval_commands(
    tmp_path: Path,
) -> None:
    database = DatabaseClient(_postgres_url(), pool_size=4, max_overflow=0)
    metric_id: UUID | None = None
    testimonial_id: UUID | None = None
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=_postgres_url(),
        storage_root=tmp_path / "claim-lock-media",
        auth_secret="test-auth-secret-with-at-least-32-characters",
        privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
    )
    try:
        async with database.session_factory() as setup_session:
            metric = ImpactMetric(
                subject_label="Concurrent metric review",
                label="Reviewed throughput",
                value="1",
                context="The editor and approver serialize on this claim row.",
            )
            testimonial = PortfolioTestimonial(
                subject_label="Concurrent testimonial review",
                quote="Original reviewed quote.",
                attribution_name="Test reviewer",
            )
            PublicationPolicy.apply(metric, PublicationStatus.DRAFT)
            PublicationPolicy.apply(testimonial, PublicationStatus.DRAFT)
            setup_session.add_all((metric, testimonial))
            await setup_session.commit()
            metric_id = metric.id
            testimonial_id = testimonial.id

        async def assert_update_waits_for_subject_lock(
            model: type[ImpactMetric] | type[PortfolioTestimonial],
            subject_id: UUID,
        ) -> None:
            async with database.session_factory() as locking_session:
                locked = await locking_session.scalar(
                    select(model).where(model.id == subject_id).with_for_update(of=model)
                )
                assert locked is not None

                async with database.session_factory() as updating_session:
                    service = PortfolioService(
                        PortfolioRepository(updating_session),
                        SQLAlchemyTransactionManager(updating_session),
                        LocalStorageClient(settings.storage_root),
                        settings,
                    )
                    task: asyncio.Task[MetricRead | PortfolioTestimonialRead]
                    if model is ImpactMetric:
                        task = asyncio.create_task(
                            service.update_metric(
                                subject_id,
                                MetricUpdate(value="2"),
                            )
                        )
                    else:
                        task = asyncio.create_task(
                            service.update_testimonial(
                                subject_id,
                                PortfolioTestimonialUpdate(quote="Updated reviewed quote."),
                            )
                        )
                    try:
                        with pytest.raises(TimeoutError):
                            await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
                        await locking_session.rollback()
                        result = await asyncio.wait_for(task, timeout=5)
                        assert result.is_approved is False
                    finally:
                        if locking_session.in_transaction():
                            await locking_session.rollback()
                        if not task.done():
                            task.cancel()
                            with pytest.raises(asyncio.CancelledError):
                                await task

        await assert_update_waits_for_subject_lock(ImpactMetric, metric_id)
        await assert_update_waits_for_subject_lock(PortfolioTestimonial, testimonial_id)
    finally:
        if metric_id is not None or testimonial_id is not None:
            async with database.session_factory() as cleanup_session:
                if metric_id is not None:
                    await cleanup_session.execute(
                        delete(ImpactMetric).where(ImpactMetric.id == metric_id)
                    )
                if testimonial_id is not None:
                    await cleanup_session.execute(
                        delete(PortfolioTestimonial).where(
                            PortfolioTestimonial.id == testimonial_id
                        )
                    )
                await cleanup_session.commit()
        await database.dispose()


@pytest.mark.asyncio
async def test_postgres_rejects_incomplete_profile_cta_pair(
    postgres_session: AsyncSession,
) -> None:
    profile = Profile(
        full_name="Invalid CTA profile",
        headline="Database invariant",
        short_bio="Direct writes must obey the same public CTA contract.",
        primary_cta_label="Broken action",
        primary_cta_url=None,
        is_primary=False,
    )
    PublicationPolicy.apply(profile, PublicationStatus.DRAFT)
    postgres_session.add(profile)
    with pytest.raises(IntegrityError):
        await postgres_session.flush()


@pytest.mark.asyncio
async def test_postgres_featured_slot_is_partial_and_lock_query_is_valid(
    postgres_session: AsyncSession,
) -> None:
    first = Project(
        title="First slot candidate",
        slug="postgres-first-slot-candidate",
        summary="First PostgreSQL featured-slot candidate.",
        is_open_source=False,
        featured_rank=1,
    )
    second = Project(
        title="Second slot candidate",
        slug="postgres-second-slot-candidate",
        summary="Second PostgreSQL featured-slot candidate.",
        is_open_source=False,
        featured_rank=1,
    )
    PublicationPolicy.apply(first, PublicationStatus.DRAFT)
    PublicationPolicy.apply(second, PublicationStatus.DRAFT)
    postgres_session.add_all((first, second))
    await postgres_session.flush()

    PublicationPolicy.apply(first, PublicationStatus.PUBLISHED)
    await postgres_session.flush()
    locked = await PortfolioRepository(postgres_session).get_project_for_update(first.id)
    assert locked is not None
    assert locked.id == first.id

    PublicationPolicy.apply(second, PublicationStatus.PUBLISHED)
    with pytest.raises(IntegrityError):
        await postgres_session.flush()


@pytest.mark.asyncio
async def test_postgres_related_articles_use_jsonb_containment(
    postgres_session: AsyncSession,
) -> None:
    current = Article(
        title="Current PostgreSQL article",
        slug="postgres-current-article",
        excerpt="Current article used to verify PostgreSQL topic matching.",
        body_markdown="# Current\n\nPostgreSQL related-article verification.",
        topics=["postgresql", "contracts"],
    )
    related = Article(
        title="Related PostgreSQL article",
        slug="postgres-related-article",
        excerpt="Related article sharing one PostgreSQL topic.",
        body_markdown="# Related\n\nShared-topic verification.",
        topics=["postgresql"],
    )
    unrelated = Article(
        title="Unrelated PostgreSQL article",
        slug="postgres-unrelated-article",
        excerpt="Unrelated article that must not appear in the result.",
        body_markdown="# Unrelated\n\nNo shared topic.",
        topics=["accessibility"],
    )
    for article in (current, related, unrelated):
        PublicationPolicy.apply(article, PublicationStatus.PUBLISHED)
    postgres_session.add_all((current, related, unrelated))
    await postgres_session.flush()

    repository = ContentRepository(postgres_session)
    result = await repository.list_related_public_articles(current)

    assert [article.id for article in result] == [related.id]

    page, total = await repository.list_public_articles_page(
        limit=10,
        offset=0,
        topic="postgresql",
    )
    assert total == 2
    assert {article.id for article in page} == {current.id, related.id}


@pytest.mark.asyncio
async def test_concurrent_first_repository_refresh_observes_single_snapshot(
    tmp_path: Path,
) -> None:
    class BlockingRepositoryClient:
        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.release = asyncio.Event()
            self.calls = 0

        async def fetch(
            self, repository_url: str, *, etag: str | None = None
        ) -> RepositoryMetadataResult:
            del repository_url, etag
            self.calls += 1
            self.started.set()
            await self.release.wait()
            return RepositoryMetadataResult(
                provider="github",
                repository_identity="example/concurrent-refresh",
                fetched_at=datetime.now(UTC),
                language="Python",
                stars=7,
                forks=2,
                etag='"concurrent"',
            )

        async def close(self) -> None:
            return None

    database = DatabaseClient(_postgres_url(), pool_size=4, max_overflow=0)
    project_id: UUID | None = None
    first_task: asyncio.Task[RepositoryMetadataAdminRead] | None = None
    client = BlockingRepositoryClient()
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=_postgres_url(),
        storage_root=tmp_path / "media",
        auth_secret="test-auth-secret-with-at-least-32-characters",
        privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
    )
    try:
        async with database.session_factory() as setup_session:
            project = Project(
                title="Concurrent metadata refresh",
                slug=f"concurrent-metadata-refresh-{uuid4()}",
                summary="PostgreSQL first-refresh serialization test.",
                repository_url="https://github.com/example/concurrent-refresh",
                is_open_source=True,
                repository_metadata_refresh_enabled=True,
                nature=ProjectNature.SOFTWARE,
            )
            PublicationPolicy.apply(project, PublicationStatus.PUBLISHED)
            setup_session.add(project)
            await setup_session.commit()
            project_id = project.id

        async with database.session_factory() as first_session:
            first_service = PortfolioService(
                PortfolioRepository(first_session),
                SQLAlchemyTransactionManager(first_session),
                LocalStorageClient(settings.storage_root),
                settings,
                client,
            )
            first_task = asyncio.create_task(
                first_service.refresh_repository_metadata(project_id, force=True)
            )
            await asyncio.wait_for(client.started.wait(), timeout=5)

            async with database.session_factory() as second_session:
                second_service = PortfolioService(
                    PortfolioRepository(second_session),
                    SQLAlchemyTransactionManager(second_session),
                    LocalStorageClient(settings.storage_root),
                    settings,
                    client,
                )
                with pytest.raises(ConflictError, match="already being refreshed"):
                    await second_service.refresh_repository_metadata(project_id, force=True)

            client.release.set()
            first_result = await asyncio.wait_for(first_task, timeout=5)
            assert first_result.status.value == "fresh"
            assert client.calls == 1

        async with database.session_factory() as verify_session:
            snapshot_count = await verify_session.scalar(
                select(func.count())
                .select_from(RepositoryMetadataSnapshot)
                .where(RepositoryMetadataSnapshot.project_id == project_id)
            )
            assert snapshot_count == 1
    finally:
        client.release.set()
        if first_task is not None and not first_task.done():
            await first_task
        if project_id is not None:
            async with database.session_factory() as cleanup_session:
                await cleanup_session.execute(
                    delete(RepositoryMetadataSnapshot).where(
                        RepositoryMetadataSnapshot.project_id == project_id
                    )
                )
                await cleanup_session.execute(delete(Project).where(Project.id == project_id))
                await cleanup_session.commit()
        await database.dispose()


@pytest.mark.asyncio
async def test_postgres_enforces_sponsorship_amount_currency_pair(
    postgres_session: AsyncSession,
) -> None:
    postgres_session.add(
        SponsorshipOption(
            id="00000000-0000-0000-0000-000000000099",
            slug="invalid-price-pair",
            title="Invalid price pair",
            description="The database must reject an amount without a currency.",
            kind="external",
            cta_label="Open",
            destination_url="https://example.com/sponsor",
            amount_minor=2500,
            currency=None,
            recurrence="one_time",
            sort_order=0,
            is_published=False,
            is_archived=False,
            nofollow=True,
        )
    )
    with pytest.raises(IntegrityError):
        await postgres_session.flush()


@pytest.mark.asyncio
async def test_identity_seed_serializes_urls_for_asyncpg(
    postgres_session: AsyncSession,
    tmp_path: Path,
) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=_postgres_url(),
        storage_root=tmp_path / "media",
        auth_secret="test-auth-secret-with-at-least-32-characters",
        privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
    )
    data = IdentitySeedData.model_validate(
        {
            "profiles": [
                {
                    "seed_key": "postgres.profile.url",
                    "payload": {
                        "full_name": "PostgreSQL Seed Fixture",
                        "headline": "URL serialization verification",
                        "short_bio": "A transaction-scoped integration fixture.",
                        "primary_cta_label": "Review verification",
                        "primary_cta_url": "https://example.com/verification",
                        "status": "published",
                    },
                }
            ]
        }
    )

    report = await IdentitySeeder(
        IdentityRepository(postgres_session),
        SQLAlchemyTransactionManager(postgres_session),
        LocalStorageClient(settings.storage_root),
        settings,
    ).apply(data, source=SeedSource.CURATED, base_directory=tmp_path)

    assert report.created == 1
    stored = await IdentityRepository(postgres_session).get_profile_by_seed_key(
        "postgres.profile.url"
    )
    assert stored is not None
    assert stored.primary_cta_url == "https://example.com/verification"


def test_alembic_metadata_matches_postgres_head(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _postgres_url())
    command.check(Config("alembic.ini"))
