from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import ClassVar

import httpx
import pytest
from sqlalchemy import select

from apps.api import manage, seed
from apps.api.auth.models import AdminRole, AdminUser
from apps.api.main import _run_contact_notification_worker, _safe_close, create_app
from apps.api.seed import SeedReport
from packages.python.clients.ai import (
    AIGenerationRequest,
    AIMessage,
    AIProviderUnavailable,
)
from packages.python.clients.database import DatabaseClient, normalize_async_database_url
from packages.python.clients.email import (
    ContactNotification,
    EmailProviderUnavailable,
    SystemEmail,
)
from packages.python.clients.openai_compatible_ai import OpenAICompatibleAIProviderClient
from packages.python.clients.smtp_email import SMTPEmailClient
from packages.python.common.errors import NotFoundError, ValidationError
from packages.python.common.rate_limit import (
    DatabaseRateLimiter,
    _as_aware,
)
from packages.python.common.repository import (
    SQLAlchemyRepository,
    SQLAlchemyTransactionManager,
)
from packages.python.common.settings import Settings
from packages.python.contracts.seeding import SeedStats
from services.content.models import FeatureSetting
from services.engagement.schemas import ContactNotificationBatchResult


class _FakeSMTP:
    instances: ClassVar[list[_FakeSMTP]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.ehlo_calls = 0
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.messages: list[EmailMessage] = []
        self.instances.append(self)

    def __enter__(self) -> _FakeSMTP:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def ehlo(self) -> None:
        self.ehlo_calls += 1

    def starttls(self, *, context: object) -> None:
        assert context is not None
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.messages.append(message)


class _UnhealthyExternalClient:
    def __init__(self) -> None:
        self.close_calls = 0

    async def health_check(self) -> bool:
        return False

    async def close(self) -> None:
        self.close_calls += 1


class _OneShotNotificationService:
    def __init__(self, stop_event: asyncio.Event, *, fail: bool = False) -> None:
        self.stop_event = stop_event
        self.fail = fail
        self.limits: list[int] = []

    async def process_due_notifications(self, *, limit: int) -> ContactNotificationBatchResult:
        self.limits.append(limit)
        self.stop_event.set()
        if self.fail:
            raise RuntimeError("injected outbox failure")
        return ContactNotificationBatchResult(
            selected_count=2,
            sent_count=1,
            not_sent_by_this_worker_count=1,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_contact_notification_worker_is_bounded_and_survives_batch_failure(
    fail: bool,
) -> None:
    stop_event = asyncio.Event()
    service = _OneShotNotificationService(stop_event, fail=fail)

    await _run_contact_notification_worker(
        service,
        stop_event=stop_event,
        poll_seconds=0,
        batch_size=37,
    )

    assert service.limits == [37]


@pytest.mark.asyncio
async def test_shutdown_continues_when_one_external_client_close_fails() -> None:
    async def failing_close() -> None:
        raise RuntimeError("injected close failure")

    await _safe_close("injected_client", failing_close)


@pytest.mark.asyncio
async def test_smtp_adapter_delivers_bounded_messages_and_checks_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeSMTP.instances.clear()
    monkeypatch.setattr("packages.python.clients.smtp_email.smtplib.SMTP", _FakeSMTP)
    client = SMTPEmailClient(
        host="smtp.example.com",
        port=587,
        from_address="sender@example.com",
        contact_recipient="owner@example.com",
        username="smtp-user",
        password="smtp-secret",
    )

    contact_result = await client.send_contact_notification(
        ContactNotification(
            submission_id="submission-1",
            delivery_key="contact-notification:submission-1",
            sender_name="Visitor",
            sender_email="visitor@example.com",
            category="project",
            subject=None,
            message="Please discuss a platform project.",
            submitted_at_iso="2026-08-27T12:00:00Z",
            organization="Example Org",
        )
    )
    system_result = await client.send_system_email(
        SystemEmail(
            recipient="operator@example.com",
            subject="Operational notice",
            plain_text="The operation completed.",
        )
    )
    assert await client.health_check() is True
    await client.close()

    assert contact_result.provider_message_id
    assert system_result.provider_message_id
    delivery = _FakeSMTP.instances[0]
    assert delivery.started_tls is True
    assert delivery.login_args == ("smtp-user", "smtp-secret")
    assert "Organization: Example Org" in delivery.messages[0].get_content()
    assert _FakeSMTP.instances[-1].ehlo_calls == 2
    assert _FakeSMTP.instances[-1].login_args == ("smtp-user", "smtp-secret")


@pytest.mark.asyncio
async def test_smtp_adapter_supports_implicit_tls_and_normalizes_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeSMTP.instances.clear()
    monkeypatch.setattr("packages.python.clients.smtp_email.smtplib.SMTP_SSL", _FakeSMTP)
    client = SMTPEmailClient(
        host="smtp.example.com",
        port=465,
        from_address="sender@example.com",
        contact_recipient="owner@example.com",
        use_starttls=False,
        use_ssl=True,
    )
    await client.send_system_email(
        SystemEmail(recipient="owner@example.com", subject="Notice", plain_text="Body")
    )
    assert "context" in _FakeSMTP.instances[0].kwargs

    def unavailable(message: EmailMessage) -> None:
        del message
        raise OSError("provider detail must be normalized")

    monkeypatch.setattr(client, "_send_sync", unavailable)
    with pytest.raises(EmailProviderUnavailable, match="provider is unavailable"):
        await client.send_system_email(
            SystemEmail(recipient="owner@example.com", subject="Notice", plain_text="Body")
        )

    def unhealthy() -> None:
        raise OSError("unavailable")

    monkeypatch.setattr(client, "_health_check_sync", unhealthy)
    assert await client.health_check() is False

    with pytest.raises(ValueError, match="cannot both"):
        SMTPEmailClient(
            host="smtp.example.com",
            port=465,
            from_address="sender@example.com",
            contact_recipient="owner@example.com",
            use_starttls=True,
            use_ssl=True,
        )
    with pytest.raises(ValueError, match="line breaks"):
        await client.send_system_email(
            SystemEmail(
                recipient="owner@example.com",
                subject="Injected\r\nBcc: attacker@example.com",
                plain_text="Body",
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected_message"),
    [
        (httpx.Response(503), "unavailable"),
        (httpx.Response(200, json={"choices": []}), "invalid response"),
        (httpx.Response(200, json={"choices": [{"message": {"content": " "}}]}), "empty"),
    ],
)
async def test_ai_adapter_normalizes_retryable_and_malformed_responses(
    response: httpx.Response,
    expected_message: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        response.request = request
        return response

    http_client = httpx.AsyncClient(
        base_url="https://provider.example/v1/",
        transport=httpx.MockTransport(handler),
    )
    adapter = OpenAICompatibleAIProviderClient(
        base_url="https://provider.example/v1/",
        api_key="secret",
        model="model",
        max_retries=0,
        client=http_client,
    )
    try:
        with pytest.raises(AIProviderUnavailable, match=expected_message):
            await adapter.generate(
                AIGenerationRequest(
                    messages=(AIMessage(role="user", content="Question"),),
                    max_output_tokens=64,
                )
            )
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_ai_adapter_normalizes_network_health_and_owned_client_cleanup() -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private provider detail", request=request)

    http_client = httpx.AsyncClient(
        base_url="https://provider.example/v1/",
        transport=httpx.MockTransport(unavailable),
    )
    adapter = OpenAICompatibleAIProviderClient(
        base_url="https://provider.example/v1/",
        api_key="secret",
        model="model",
        max_retries=0,
        client=http_client,
    )
    request = AIGenerationRequest(
        messages=(AIMessage(role="user", content="Question"),),
        max_output_tokens=64,
    )
    with pytest.raises(AIProviderUnavailable, match="provider is unavailable"):
        await adapter.generate(request)
    assert await adapter.health_check() is False
    await adapter.close()
    await http_client.aclose()

    owned = OpenAICompatibleAIProviderClient(
        base_url="https://provider.example/v1/",
        api_key="secret",
        model="model",
    )
    await owned.close()
    assert owned._client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize(("status_code", "expected"), [(200, True), (401, False), (503, False)])
async def test_ai_adapter_health_requires_a_successful_provider_response(
    status_code: int,
    expected: bool,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    http_client = httpx.AsyncClient(
        base_url="https://provider.example/v1/",
        transport=httpx.MockTransport(handler),
    )
    adapter = OpenAICompatibleAIProviderClient(
        base_url="https://provider.example/v1/",
        api_key="secret",
        model="model",
        client=http_client,
    )
    try:
        assert await adapter.health_check() is expected
    finally:
        await http_client.aclose()


def _test_settings(database_url: str, storage_root: Path | None = None) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=database_url,
        storage_root=storage_root or Path("var/test-media"),
        auth_secret="test-auth-secret-with-at-least-32-characters",
        privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
    )


@pytest.mark.asyncio
async def test_admin_creation_command_uses_composition_boundaries(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _test_settings(str(database_client.engine.url), tmp_path / "media")
    await manage.create_admin(
        settings=settings,
        email="cli-owner@example.com",
        display_name="CLI Owner",
        password="Correct-Horse-42!",
        role=AdminRole.OWNER,
    )
    async with database_client.session_factory() as session:
        owner = await session.scalar(
            select(AdminUser).where(AdminUser.email == "cli-owner@example.com")
        )
    assert owner is not None
    assert owner.display_name == "CLI Owner"

    await manage.update_admin(
        settings=settings,
        current_email="cli-owner@example.com",
        email="updated-owner@example.com",
        display_name="Updated CLI Owner",
        password="Updated-Horse-84!",
    )
    async with database_client.session_factory() as session:
        previous_owner = await session.scalar(
            select(AdminUser).where(AdminUser.email == "cli-owner@example.com")
        )
        updated_owner = await session.scalar(
            select(AdminUser).where(AdminUser.email == "updated-owner@example.com")
        )
    assert previous_owner is None
    assert updated_owner is not None
    assert updated_owner.display_name == "Updated CLI Owner"
    assert manage.PasswordService().verify(updated_owner.password_hash, "Updated-Horse-84!")


def test_admin_cli_reads_password_securely_and_reports_command_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORTFOLIO_ADMIN_PASSWORD", "Correct-Horse-42!")
    assert manage._password_from_secure_input(Settings(_env_file=None)) == "Correct-Horse-42!"

    captured: dict[str, object] = {}

    async def fake_create_admin(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(manage, "create_admin", fake_create_admin)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "portfolio-admin",
            "create-admin",
            "--email",
            "owner@example.com",
            "--display-name",
            "Owner",
        ],
    )
    manage.main()
    assert captured["email"] == "owner@example.com"

    monkeypatch.setenv("PORTFOLIO_ADMIN_EMAIL", "environment-owner@example.com")
    captured.clear()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "portfolio-admin",
            "create-admin",
            "--display-name",
            "Environment Owner",
        ],
    )
    manage.main()
    assert captured["email"] == "environment-owner@example.com"

    monkeypatch.delenv("PORTFOLIO_ADMIN_PASSWORD")
    monkeypatch.setattr(manage, "Settings", lambda: Settings(_env_file=None))
    prompts: Iterator[str] = iter(("first", "second"))
    monkeypatch.setattr("apps.api.manage.getpass.getpass", lambda _: next(prompts))
    with pytest.raises(SystemExit) as caught:
        manage.main()
    assert caught.value.code == 1


def test_seed_manifest_loader_and_cli_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = tmp_path / "seed.json"
    valid.write_text('{"schema_version":1,"source":"curated"}', encoding="utf-8")
    assert seed.load_manifest(valid).schema_version == 1

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":1,"schema_version":1,"source":"curated"}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        seed.load_manifest(duplicate)
    with pytest.raises(ValueError, match="does not exist"):
        seed.load_manifest(tmp_path / "missing.json")

    async def fake_seed(*args: object, **kwargs: object) -> SeedReport:
        del args, kwargs
        return SeedReport(
            identity=SeedStats(created=1, skipped=0),
            portfolio=SeedStats(created=0, skipped=1),
            content=SeedStats(created=0, skipped=0),
        )

    monkeypatch.setattr(seed, "run_seed", fake_seed)
    monkeypatch.setattr(sys, "argv", ["portfolio-seed", "validate", "--file", str(valid)])
    seed.main()

    monkeypatch.setattr(sys, "argv", ["portfolio-seed", "--file", str(valid)])
    with pytest.raises(SystemExit) as legacy_exit:
        seed.main()
    assert legacy_exit.value.code == 2

    monkeypatch.setattr(sys, "argv", ["portfolio-seed", "apply", "--file", str(valid)])
    with pytest.raises(SystemExit) as review_exit:
        seed.main()
    assert review_exit.value.code == 1

    monkeypatch.setattr(
        sys,
        "argv",
        ["portfolio-seed", "apply", "--file", str(valid), "--approve"],
    )
    seed.main()

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"schema_version":2,"source":"curated"}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["portfolio-seed", "validate", "--file", str(invalid)])
    with pytest.raises(SystemExit) as validation_exit:
        seed.main()
    assert validation_exit.value.code == 2

    monkeypatch.setattr(sys, "argv", ["portfolio-seed", "validate", "--file", str(duplicate)])
    with pytest.raises(SystemExit) as failure_exit:
        seed.main()
    assert failure_exit.value.code == 1


class _FeatureRepository(SQLAlchemyRepository[FeatureSetting]):
    model = FeatureSetting


@pytest.mark.asyncio
async def test_generic_repository_transaction_and_database_utilities(
    database_client: DatabaseClient,
) -> None:
    assert normalize_async_database_url("postgresql://u:p@db/name").startswith(
        "postgresql+asyncpg://"
    )
    assert normalize_async_database_url("postgres://u:p@db/name").startswith(
        "postgresql+asyncpg://"
    )
    assert normalize_async_database_url("sqlite+aiosqlite://") == "sqlite+aiosqlite://"
    assert await database_client.health_check() is True

    async with database_client.session_factory() as session:
        repository = _FeatureRepository(session)
        transaction = SQLAlchemyTransactionManager(session)
        feature = repository.add(FeatureSetting(key="core.test", enabled=True))
        await transaction.commit()

        assert await repository.get(feature.id) is feature
        statement = select(FeatureSetting).where(FeatureSetting.enabled.is_(True))
        assert await repository.count(statement) == 1
        assert list(await repository.list_query(statement, limit=10, offset=0)) == [feature]
        feature_id = feature.id
        await repository.delete(feature)
        await transaction.rollback()
        assert await repository.get(feature_id) is not None


@pytest.mark.asyncio
async def test_rate_limiter_empty_batch_and_storage_missing_file(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    from packages.python.clients.storage import LocalStorageClient

    limiter = DatabaseRateLimiter(database_client.session_factory)
    assert await limiter.consume(()) is True
    assert _as_aware(datetime.now(UTC)).tzinfo is UTC
    assert _as_aware(datetime(2026, 1, 1)).tzinfo is UTC

    storage = LocalStorageClient(tmp_path / "media")
    with pytest.raises(NotFoundError):
        await storage.read("missing/file.bin")
    with pytest.raises(ValidationError):
        await storage.read("/absolute/file.bin")


@pytest.mark.asyncio
async def test_readiness_reports_optional_dependencies_and_lifespan_closes_clients(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _test_settings(
        str(database_client.engine.url),
        tmp_path / "readiness-media",
    ).model_copy(
        update={
            "email_enabled": True,
            "assistant_enabled": True,
            "readiness_check_email": True,
            "readiness_check_ai": True,
        }
    )
    external = _UnhealthyExternalClient()
    app = create_app(
        settings,
        database_client=database_client,
        email_client=external,  # type: ignore[arg-type]
        ai_provider_client=external,  # type: ignore[arg-type]
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client,
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json()["checks"] == {
        "database": True,
        "email": False,
        "ai": False,
    }
    assert external.close_calls == 2
