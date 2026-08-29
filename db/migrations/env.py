from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from apps.api.auth.models import AdminSession, AdminUser, LoginAttempt  # noqa: F401
from packages.python.clients.database import normalize_async_database_url
from packages.python.common.models import Base
from packages.python.common.rate_limit import RateLimitBucket  # noqa: F401
from services.assistant.models import AssistantAuditEvent  # noqa: F401
from services.content.models import (  # noqa: F401
    Article,
    FeatureSetting,
    HomepageSection,
    MediaAsset,
    NavigationItem,
)
from services.engagement.models import ContactSubmission, SponsorshipOption  # noqa: F401
from services.identity.models import (  # noqa: F401
    PortraitAsset,
    Profile,
    ResumeVersion,
    SocialLink,
)
from services.portfolio.models import (  # noqa: F401
    Certification,
    Education,
    Experience,
    ImpactMetric,
    PortfolioApprovalEvent,
    PortfolioEvidence,
    ProfessionalCategory,
    Project,
    ProjectMedia,
    Sector,
    Skill,
    Testimonial,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = (
    os.getenv("PORTFOLIO_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)
if not database_url:
    raise RuntimeError("A database URL is required to run migrations")
config.set_main_option("sqlalchemy.url", normalize_async_database_url(database_url))
target_metadata = Base.metadata
_TYPE_BOUND_CHECKS = {
    "adminrole",
    "approvalaction",
    "evidencekind",
    "evidencevisibility",
    "homepagesectiontype",
    "navigationlocation",
    "projectnature",
    "publicationstatus",
    "repositorysnapshotstatus",
}


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Ignore reflected copies of SQLAlchemy Enum's type-bound CHECK constraints."""

    del object_, compare_to
    return not (type_ == "check_constraint" and reflected and name in _TYPE_BOUND_CHECKS)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
