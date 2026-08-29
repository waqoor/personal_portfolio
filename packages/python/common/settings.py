from __future__ import annotations

from pathlib import Path
from typing import Literal, Self
from urllib.parse import unquote, urlparse

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PORTFOLIO_",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    app_name: str = "Yazeed Hasan Portfolio API"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True
    json_logs: bool = True
    database_url: str = "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio"
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)
    db_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)

    auth_secret: SecretStr = SecretStr("development-only-secret-change-before-production")
    privacy_hash_secret: SecretStr = SecretStr(
        "development-privacy-secret-change-before-production"
    )
    session_cookie_name: str = "portfolio_admin_session"
    csrf_cookie_name: str = "portfolio_csrf"
    csrf_header_name: str = "X-CSRF-Token"
    session_ttl_seconds: int = Field(default=43_200, ge=900, le=2_592_000)
    cookie_secure: bool = False
    cookie_domain: str | None = None
    login_max_failures: int = Field(default=5, ge=2, le=50)
    login_window_seconds: int = Field(default=900, ge=60, le=86_400)
    login_account_delay_threshold: int = Field(default=3, ge=2, le=50)
    login_account_max_delay_seconds: int = Field(default=8, ge=1, le=300)
    admin_email: EmailStr | None = None
    admin_password: SecretStr | None = None

    public_base_url: str = "http://localhost:3000"
    api_public_url: str = "http://localhost:8000"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    content_security_policy: str = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    forwarded_allow_ips: str = "127.0.0.1"

    site_name: str = "Yazeed Hasan"
    site_owner_name: str = "Yazeed Hasan"
    site_owner_headline: str = "AI, Software, Data & Infrastructure Builder"
    site_default_title: str = "Yazeed Hasan — AI, Software, Data & Infrastructure"
    site_description: str = "Portfolio of AI, software, data, and infrastructure work."
    site_locale: str = "en_US"
    site_language: str = "en"
    site_social_image_url: str | None = None
    verified_same_as_urls: list[str] = Field(default_factory=list)

    storage_root: Path = Path("var/media")
    max_portrait_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)
    max_resume_bytes: int = Field(default=15 * 1024 * 1024, ge=1024)
    max_media_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    max_request_bytes: int = Field(default=55 * 1024 * 1024, ge=1024)

    featured_project_limit: int = Field(default=5, ge=1, le=5)
    repository_metadata_refresh_ttl_seconds: int = Field(default=86_400, ge=300, le=2_592_000)
    repository_metadata_timeout_seconds: float = Field(default=8.0, ge=1, le=30)
    github_api_token: SecretStr | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    contact_enabled: bool = True
    contact_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    contact_ip_limit: int = Field(default=8, ge=1, le=100)
    contact_email_limit: int = Field(default=5, ge=1, le=100)
    contact_max_links: int = Field(default=4, ge=0, le=20)
    contact_response_time_label: str = Field(
        default="Usually within 2-3 business days.", max_length=160
    )
    contact_notification_poll_seconds: int = Field(default=15, ge=1, le=300)
    contact_notification_batch_size: int = Field(default=50, ge=1, le=100)
    email_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65_535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: float = Field(default=8.0, ge=1, le=30)
    email_from_address: EmailStr | None = None
    contact_notification_to: EmailStr | None = None

    sponsorship_enabled: bool = True

    assistant_enabled: bool = False
    assistant_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    assistant_ip_limit: int = Field(default=20, ge=1, le=500)
    assistant_max_question_chars: int = Field(default=600, ge=100, le=2000)
    assistant_max_sources: int = Field(default=6, ge=1, le=12)
    assistant_max_context_chars: int = Field(default=12_000, ge=1000, le=30_000)
    assistant_max_output_tokens: int = Field(default=500, ge=64, le=1500)
    ai_provider_base_url: str = "https://api.openai.com/v1/"
    ai_provider_api_key: SecretStr | None = None
    ai_model: str | None = None
    ai_timeout_seconds: float = Field(default=15.0, ge=2, le=60)
    ai_max_retries: int = Field(default=1, ge=0, le=2)
    readiness_check_email: bool = False
    readiness_check_ai: bool = False

    @field_validator("api_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("api_prefix must start with '/' and must not end with '/'")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("at least one allowed origin is required")
        for value in values:
            parsed = urlparse(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
            ):
                raise ValueError(f"invalid CORS origin: {value}")
        return values

    @field_validator("allowed_hosts")
    @classmethod
    def validate_hosts(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("at least one allowed host is required")
        if any(
            not value.strip()
            or "://" in value
            or "/" in value
            or any(character.isspace() for character in value)
            for value in values
        ):
            raise ValueError("allowed_hosts must contain hostnames or supported host patterns")
        return values

    @field_validator("verified_same_as_urls")
    @classmethod
    def validate_verified_same_as(cls, values: list[str]) -> list[str]:
        for value in values:
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username:
                raise ValueError("verified sameAs URLs must be credential-free HTTPS URLs")
        return values

    @field_validator("site_social_image_url")
    @classmethod
    def validate_social_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        is_local = (
            value.startswith("/")
            and not value.startswith("//")
            and not parsed.query
            and not parsed.fragment
        )
        is_https = (
            parsed.scheme == "https"
            and bool(parsed.netloc)
            and not parsed.username
            and not parsed.password
        )
        if not (is_local or is_https):
            raise ValueError(
                "site_social_image_url must be a local path or credential-free HTTPS URL"
            )
        return value

    @model_validator(mode="after")
    def validate_production(self) -> Self:
        if self.environment != "test" and not self.database_url.startswith(
            ("postgresql+asyncpg://", "postgresql://")
        ):
            raise ValueError("PostgreSQL is required outside the test environment")
        secret = self.auth_secret.get_secret_value()
        privacy_secret = self.privacy_hash_secret.get_secret_value()
        if len(secret) < 32:
            raise ValueError("auth_secret must be at least 32 characters")
        if len(privacy_secret) < 32:
            raise ValueError("privacy_hash_secret must be at least 32 characters")
        if secret == privacy_secret:
            raise ValueError("auth_secret and privacy_hash_secret must be independent")
        if self.smtp_use_starttls and self.smtp_use_ssl:
            raise ValueError("SMTP STARTTLS and implicit TLS cannot both be enabled")
        if self.email_enabled and not all(
            (self.smtp_host, self.email_from_address, self.contact_notification_to)
        ):
            raise ValueError(
                "email delivery requires smtp_host, email_from_address, and contact_notification_to"
            )
        if self.assistant_enabled and (not self.ai_provider_api_key or not self.ai_model):
            raise ValueError("the assistant requires an AI provider key and model")
        parsed_api_url = urlparse(self.api_public_url)
        if (
            parsed_api_url.scheme not in {"http", "https"}
            or not parsed_api_url.netloc
            or parsed_api_url.username
            or parsed_api_url.password
            or parsed_api_url.query
            or parsed_api_url.fragment
        ):
            raise ValueError("api_public_url must be an absolute HTTP(S) URL")
        parsed_public_url = urlparse(self.public_base_url)
        if (
            parsed_public_url.scheme not in {"http", "https"}
            or not parsed_public_url.netloc
            or parsed_public_url.username
            or parsed_public_url.password
            or parsed_public_url.query
            or parsed_public_url.fragment
            or parsed_public_url.path not in {"", "/"}
        ):
            raise ValueError("public_base_url must be an absolute HTTP(S) origin")
        if (self.smtp_username is None) != (self.smtp_password is None):
            raise ValueError("SMTP username and password must be supplied together")
        if self.environment == "production":
            if "development-only" in secret or "change-before-production" in secret:
                raise ValueError("a unique production auth secret is required")
            if (
                "development-" in privacy_secret
                or "change-before-production" in privacy_secret
                or "change_me" in privacy_secret.casefold()
            ):
                raise ValueError("a unique production privacy hash secret is required")
            if not self.cookie_secure:
                raise ValueError("secure cookies are required in production")
            if not self.public_base_url.startswith("https://"):
                raise ValueError("public_base_url must use HTTPS in production")
            if not self.api_public_url.startswith("https://"):
                raise ValueError("api_public_url must use HTTPS in production")
            if "*" in self.allowed_origins or "*" in self.allowed_hosts:
                raise ValueError("wildcard CORS origins/hosts are forbidden in production")
            if "*" in {value.strip() for value in self.forwarded_allow_ips.split(",")}:
                raise ValueError("trusting forwarded headers from every address is forbidden")
            if not self.database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("the asyncpg PostgreSQL driver is required in production")
            parsed_database_url = urlparse(self.database_url)
            database_password = unquote(parsed_database_url.password or "")
            if (
                not parsed_database_url.username
                or not parsed_database_url.hostname
                or len(database_password) < 16
                or any(
                    marker in database_password.casefold()
                    for marker in ("change_me", "change-me", "changeme", "password")
                )
            ):
                raise ValueError("a strong, non-placeholder database credential is required")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("production CORS origins must use HTTPS")
            if self.email_enabled and not (self.smtp_use_starttls or self.smtp_use_ssl):
                raise ValueError("production email delivery must use TLS")
            if self.assistant_enabled:
                parsed_ai_url = urlparse(self.ai_provider_base_url)
                if (
                    parsed_ai_url.scheme != "https"
                    or not parsed_ai_url.netloc
                    or parsed_ai_url.username
                    or parsed_ai_url.password
                    or parsed_ai_url.query
                    or parsed_ai_url.fragment
                ):
                    raise ValueError("the production AI provider URL must be credential-free HTTPS")
            normalized_csp = self.content_security_policy.casefold()
            if "default-src" not in normalized_csp or "frame-ancestors" not in normalized_csp:
                raise ValueError("production content security policy is incomplete")
            if self.docs_enabled:
                raise ValueError("API documentation must be disabled in production")
        return self
