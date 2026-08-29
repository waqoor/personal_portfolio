from __future__ import annotations

import argparse
import asyncio
import getpass
import logging

from pydantic import ValidationError as PydanticValidationError

from apps.api.auth.models import AdminRole
from apps.api.auth.repository import AuthRepository
from apps.api.auth.schemas import AdminCredentialsUpdate, CreateAdminInput
from apps.api.auth.service import AuthService
from packages.python.clients.database import DatabaseClient
from packages.python.common.errors import ApplicationError, NotFoundError
from packages.python.common.logging import configure_logging
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.security import PasswordService
from packages.python.common.settings import Settings

logger = logging.getLogger(__name__)


async def create_admin(
    *,
    settings: Settings,
    email: str,
    display_name: str,
    password: str,
    role: AdminRole,
) -> None:
    database = DatabaseClient(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout_seconds=settings.db_pool_timeout_seconds,
    )
    try:
        async with database.session() as session:
            service = AuthService(
                AuthRepository(session),
                SQLAlchemyTransactionManager(session),
                settings,
                PasswordService(),
            )
            await service.create_admin(
                CreateAdminInput(
                    email=email,
                    display_name=display_name,
                    password=password,
                    role=role,
                )
            )
    finally:
        await database.dispose()


async def update_admin(
    *,
    settings: Settings,
    current_email: str,
    email: str,
    password: str,
    display_name: str | None,
) -> None:
    database = DatabaseClient(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout_seconds=settings.db_pool_timeout_seconds,
    )
    try:
        async with database.session() as session:
            service = AuthService(
                AuthRepository(session),
                SQLAlchemyTransactionManager(session),
                settings,
                PasswordService(),
            )
            await service.update_admin_credentials(
                current_email,
                AdminCredentialsUpdate(
                    email=email,
                    password=password,
                    display_name=display_name,
                ),
            )
    finally:
        await database.dispose()


def _password_from_secure_input(settings: Settings) -> str:
    if settings.admin_password is not None:
        return settings.admin_password.get_secret_value()
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


def _email_from_argument_or_settings(value: str | None, settings: Settings) -> str:
    email = value or settings.admin_email
    if not email:
        raise ValueError("Admin email is required via --email or PORTFOLIO_ADMIN_EMAIL.")
    return email


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage portfolio platform administrators.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-admin", help="Create an administrator")
    create.add_argument("--email")
    create.add_argument("--display-name", required=True)
    create.add_argument("--role", choices=[role.value for role in AdminRole], default="owner")
    update = subparsers.add_parser(
        "update-admin",
        help="Rotate an administrator's email and password and revoke active sessions",
    )
    update.add_argument("--current-email", required=True)
    update.add_argument("--email")
    update.add_argument("--display-name")
    args = parser.parse_args()
    settings = Settings()
    configure_logging(level=settings.log_level, json_logs=settings.json_logs)
    try:
        if args.command == "create-admin":
            asyncio.run(
                create_admin(
                    settings=settings,
                    email=str(_email_from_argument_or_settings(args.email, settings)),
                    display_name=args.display_name,
                    password=_password_from_secure_input(settings),
                    role=AdminRole(args.role),
                )
            )
        elif args.command == "update-admin":
            asyncio.run(
                update_admin(
                    settings=settings,
                    current_email=args.current_email,
                    email=str(_email_from_argument_or_settings(args.email, settings)),
                    display_name=args.display_name,
                    password=_password_from_secure_input(settings),
                )
            )
    except PydanticValidationError as exc:
        logger.error("admin_input_invalid", extra={"error_count": exc.error_count()})
        raise SystemExit(2) from None
    except (ApplicationError, NotFoundError, ValueError) as exc:
        logger.error("admin_command_failed", extra={"error_type": type(exc).__name__})
        raise SystemExit(1) from None
    logger.info("admin_command_completed", extra={"command": args.command})


if __name__ == "__main__":
    main()
