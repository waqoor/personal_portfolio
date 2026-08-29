from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from packages.python.clients.database import DatabaseClient
from packages.python.clients.storage import LocalStorageClient
from packages.python.common.errors import ApplicationError, ConflictError
from packages.python.common.logging import configure_logging
from packages.python.common.models import PublicationStatus
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.schemas import APIModel
from packages.python.common.settings import Settings
from packages.python.contracts.seeding import SeedSource, SeedStats
from services.content.registry import HomepageSectionRegistry
from services.content.repository import ContentRepository
from services.content.seeding import ContentSeedData, ContentSeeder
from services.identity.repository import IdentityRepository
from services.identity.seeding import IdentitySeedData, IdentitySeeder
from services.portfolio.repository import PortfolioRepository
from services.portfolio.seeding import PortfolioSeedData, PortfolioSeeder

logger = logging.getLogger(__name__)
_MAX_MANIFEST_BYTES = 5 * 1024 * 1024


class SeedReviewMetadata(APIModel):
    importer: Literal["json_resume", "linkedin_export"]
    source_filename: str = Field(min_length=1, max_length=255)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    publication_policy: Literal["draft_review_required"]
    warnings: list[Annotated[str, Field(max_length=500)]] = Field(
        default_factory=list, max_length=200
    )


class SeedManifest(APIModel):
    schema_version: Literal[1]
    source: SeedSource
    review: SeedReviewMetadata | None = None
    identity: IdentitySeedData = Field(default_factory=IdentitySeedData)
    portfolio: PortfolioSeedData = Field(default_factory=PortfolioSeedData)
    content: ContentSeedData = Field(default_factory=ContentSeedData)

    @model_validator(mode="after")
    def reject_duplicate_identities(self) -> Self:
        expected_importer = {
            SeedSource.RESUME: "json_resume",
            SeedSource.LINKEDIN: "linkedin_export",
        }.get(self.source)
        if expected_importer and (self.review is None or self.review.importer != expected_importer):
            raise ValueError(
                f"{self.source.value} manifests require matching bounded importer provenance"
            )
        groups: dict[str, list[Any]] = {
            "identity.profiles": self.identity.profiles,
            "identity.social_links": self.identity.social_links,
            "identity.portraits": self.identity.portraits,
            "identity.resume_versions": self.identity.resume_versions,
            "portfolio.categories": self.portfolio.categories,
            "portfolio.sectors": self.portfolio.sectors,
            "portfolio.skills": self.portfolio.skills,
            "portfolio.projects": self.portfolio.projects,
            "portfolio.experiences": self.portfolio.experiences,
            "portfolio.education": self.portfolio.education,
            "portfolio.certifications": self.portfolio.certifications,
            "portfolio.metrics": self.portfolio.metrics,
            "portfolio.testimonials": self.portfolio.testimonials,
            "content.media": self.content.media,
            "content.articles": self.content.articles,
            "content.homepage_sections": self.content.homepage_sections,
            "content.navigation": self.content.navigation,
            "content.features": self.content.features,
        }
        for label, records in groups.items():
            self._assert_unique((record.seed_key for record in records), f"{label} seed_key")

        self._assert_unique(
            (record.payload.slug for record in self.portfolio.categories),
            "portfolio category slug",
        )
        self._assert_unique(
            (record.payload.slug for record in self.portfolio.sectors),
            "portfolio sector slug",
        )
        self._assert_unique(
            (record.payload.slug for record in self.portfolio.skills),
            "portfolio skill slug",
        )
        self._assert_unique(
            (record.payload.slug for record in self.portfolio.projects),
            "portfolio project slug",
        )
        self._assert_unique(
            (
                record.payload.featured_rank
                for record in self.portfolio.projects
                if record.payload.featured_rank is not None
            ),
            "portfolio featured rank",
        )
        self._assert_unique(
            (record.payload.slug for record in self.content.articles),
            "content article slug",
        )
        self._assert_unique(
            (record.payload.position for record in self.content.homepage_sections),
            "homepage section position",
        )
        self._assert_unique(
            ((record.payload.location, record.payload.href) for record in self.content.navigation),
            "navigation location and href",
        )
        self._assert_unique(
            (record.payload.key for record in self.content.features),
            "feature key",
        )
        if self.source in {SeedSource.RESUME, SeedSource.LINKEDIN}:
            publishable_records: list[Any] = [
                *self.identity.profiles,
                *self.portfolio.categories,
                *self.portfolio.sectors,
                *self.portfolio.skills,
                *self.portfolio.projects,
                *self.portfolio.experiences,
                *self.portfolio.education,
                *self.portfolio.certifications,
                *self.portfolio.metrics,
                *self.portfolio.testimonials,
                *self.content.media,
                *self.content.articles,
                *self.content.homepage_sections,
                *self.content.navigation,
            ]
            if any(
                getattr(record.payload, "status", PublicationStatus.DRAFT)
                is not PublicationStatus.DRAFT
                for record in publishable_records
            ) or any(
                item.status is not PublicationStatus.DRAFT or item.make_current
                for item in self.identity.resume_versions
            ):
                raise ValueError("resume and LinkedIn imports must remain draft until owner review")
        return self

    @staticmethod
    def _assert_unique(values: Any, label: str) -> None:
        seen: set[Any] = set()
        for value in values:
            if value in seen:
                raise ValueError(f"Duplicate {label}: {value}")
            seen.add(value)


class SeedReport(APIModel):
    identity: SeedStats
    portfolio: SeedStats
    content: SeedStats

    @property
    def total_created(self) -> int:
        return self.identity.created + self.portfolio.created + self.content.created

    @property
    def total_skipped(self) -> int:
        return self.identity.skipped + self.portfolio.skipped + self.content.skipped


def load_manifest(path: Path) -> SeedManifest:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError("Seed manifest file does not exist.")
    if resolved.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValueError("Seed manifest exceeds the 5 MiB safety limit.")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    raw = json.loads(resolved.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    return SeedManifest.model_validate(raw)


def manifest_template() -> dict[str, Any]:
    """Return the reviewed v1 starter; all public lifecycle state is draft."""

    return {
        "schema_version": 1,
        "source": "curated",
        "identity": {
            "profiles": [
                {
                    "seed_key": "profile.primary",
                    "payload": {
                        "full_name": "Replace with your public name",
                        "headline": "Replace with a factual professional headline",
                        "short_bio": "Replace with a concise, reviewed public biography.",
                        "is_primary": True,
                        "status": "draft",
                        "is_visible": True,
                        "noindex": True,
                    },
                }
            ],
            "social_links": [],
            "portraits": [],
            "resume_versions": [],
        },
        "portfolio": {},
        "content": {},
    }


def write_manifest_template(path: Path) -> None:
    write_manifest(path, manifest_template())


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    if resolved.exists():
        raise ValueError("Refusing to overwrite an existing manifest.")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


async def build_seed_plan(manifest: SeedManifest, *, settings: Settings) -> dict[str, Any]:
    """Inspect canonical seed identities without mutating database or storage."""

    from services.content.models import (
        Article,
        FeatureSetting,
        HomepageSection,
        MediaAsset,
        NavigationItem,
    )
    from services.identity.models import PortraitAsset, Profile, ResumeVersion, SocialLink
    from services.portfolio.models import (
        Certification,
        Education,
        Experience,
        ImpactMetric,
        ProfessionalCategory,
        Project,
        Sector,
        Skill,
        Testimonial,
    )

    database = DatabaseClient(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout_seconds=settings.db_pool_timeout_seconds,
    )
    groups: list[tuple[str, type[Any], list[Any]]] = [
        ("identity.profiles", Profile, manifest.identity.profiles),
        ("identity.social_links", SocialLink, manifest.identity.social_links),
        ("identity.portraits", PortraitAsset, manifest.identity.portraits),
        ("identity.resume_versions", ResumeVersion, manifest.identity.resume_versions),
        ("portfolio.categories", ProfessionalCategory, manifest.portfolio.categories),
        ("portfolio.sectors", Sector, manifest.portfolio.sectors),
        ("portfolio.skills", Skill, manifest.portfolio.skills),
        ("portfolio.projects", Project, manifest.portfolio.projects),
        ("portfolio.experiences", Experience, manifest.portfolio.experiences),
        ("portfolio.education", Education, manifest.portfolio.education),
        ("portfolio.certifications", Certification, manifest.portfolio.certifications),
        ("portfolio.metrics", ImpactMetric, manifest.portfolio.metrics),
        ("portfolio.testimonials", Testimonial, manifest.portfolio.testimonials),
        ("content.media", MediaAsset, manifest.content.media),
        ("content.articles", Article, manifest.content.articles),
        ("content.homepage_sections", HomepageSection, manifest.content.homepage_sections),
        ("content.navigation", NavigationItem, manifest.content.navigation),
        ("content.features", FeatureSetting, manifest.content.features),
    ]
    items: list[dict[str, Any]] = []
    try:
        async with database.session() as session:
            for resource, model, records in groups:
                for record in records:
                    exists = await session.scalar(
                        select(model.id).where(model.seed_key == record.seed_key).limit(1)
                    )
                    proposed = record.model_dump(mode="json")
                    items.append(
                        {
                            "resource": resource,
                            "seed_key": str(record.seed_key),
                            "action": (
                                "skip-preserve-admin-edits"
                                if exists
                                else "create-draft-or-declared-state"
                            ),
                            "provenance": manifest.source.value,
                            "proposed": proposed,
                        }
                    )
    finally:
        await database.dispose()
    return {
        "schema_version": manifest.schema_version,
        "source": manifest.source.value,
        "creates": sum(item["action"].startswith("create") for item in items),
        "skips": sum(item["action"].startswith("skip") for item in items),
        "items": items,
    }


async def run_seed(
    manifest: SeedManifest,
    *,
    manifest_directory: Path,
    settings: Settings,
) -> SeedReport:
    database = DatabaseClient(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout_seconds=settings.db_pool_timeout_seconds,
    )
    storage = LocalStorageClient(settings.storage_root)
    registry = HomepageSectionRegistry()
    try:
        async with database.session() as session:
            transaction = SQLAlchemyTransactionManager(session)
            try:
                identity = await IdentitySeeder(
                    IdentityRepository(session), transaction, storage, settings
                ).apply(
                    manifest.identity,
                    source=manifest.source,
                    base_directory=manifest_directory,
                )
                portfolio = await PortfolioSeeder(PortfolioRepository(session), transaction).apply(
                    manifest.portfolio, source=manifest.source
                )
                content = await ContentSeeder(
                    ContentRepository(session), transaction, storage, settings, registry
                ).apply(
                    manifest.content,
                    source=manifest.source,
                    base_directory=manifest_directory,
                )
                await transaction.commit()
            except IntegrityError as exc:
                await transaction.rollback()
                raise ConflictError("Seed data conflicts with existing canonical records.") from exc
            return SeedReport(identity=identity, portfolio=portfolio, content=content)
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize, validate, review, and apply versioned portfolio manifests."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="Create a safe draft-only v1 template")
    initialize.add_argument("--file", required=True, type=Path)
    json_resume = commands.add_parser(
        "import-json-resume",
        help="Convert a bounded JSON Resume document into a draft-only canonical manifest",
    )
    json_resume.add_argument("--input", required=True, type=Path)
    json_resume.add_argument("--file", required=True, type=Path)
    linkedin = commands.add_parser(
        "import-linkedin",
        help="Convert a bounded LinkedIn ZIP export into a draft-only canonical manifest",
    )
    linkedin.add_argument("--input", required=True, type=Path)
    linkedin.add_argument("--file", required=True, type=Path)
    validate = commands.add_parser("validate", help="Validate without database or storage writes")
    validate.add_argument("--file", required=True, type=Path)
    plan = commands.add_parser("dry-run", help="Show creates and preservation skips without writes")
    plan.add_argument("--file", required=True, type=Path)
    apply = commands.add_parser("apply", help="Apply a previously reviewed manifest")
    apply.add_argument("--file", required=True, type=Path)
    apply.add_argument(
        "--approve",
        action="store_true",
        help="Confirm that the dry-run and every requested public state were reviewed",
    )
    args = parser.parse_args()
    settings = Settings()
    configure_logging(level=settings.log_level, json_logs=settings.json_logs)
    try:
        if args.command == "init":
            write_manifest_template(args.file)
            print(json.dumps({"created": str(args.file.resolve()), "schema_version": 1}))
            return
        if args.command in {"import-json-resume", "import-linkedin"}:
            from apps.api.seed_importers import import_json_resume, import_linkedin_export

            imported = (
                import_json_resume(
                    args.input,
                    manifest_directory=args.file.resolve().parent,
                )
                if args.command == "import-json-resume"
                else import_linkedin_export(args.input)
            )
            manifest = SeedManifest.model_validate(imported.manifest)
            write_manifest(args.file, manifest.model_dump(mode="json", exclude_none=True))
            print(
                json.dumps(
                    {
                        "created": str(args.file.resolve()),
                        "schema_version": manifest.schema_version,
                        "source": manifest.source.value,
                        "publication_policy": "draft_review_required",
                        "warnings": list(imported.warnings),
                        "next": f"portfolio-seed validate --file {args.file}",
                    },
                    indent=2,
                )
            )
            return
        manifest = load_manifest(args.file)
        if args.command == "validate":
            print(
                json.dumps(
                    {
                        "valid": True,
                        "schema_version": manifest.schema_version,
                        "source": manifest.source.value,
                    }
                )
            )
            return
        if args.command == "dry-run":
            print(json.dumps(asyncio.run(build_seed_plan(manifest, settings=settings)), indent=2))
            return
        if not args.approve:
            raise ValueError("Apply requires --approve after reviewing `portfolio-seed dry-run`.")
        report = asyncio.run(
            run_seed(
                manifest,
                manifest_directory=args.file.resolve().parent,
                settings=settings,
            )
        )
    except PydanticValidationError as exc:
        logger.error("seed_manifest_validation_failed", extra={"error_count": exc.error_count()})
        raise SystemExit(2) from None
    except (ApplicationError, ValueError, OSError) as exc:
        logger.error("seed_failed", extra={"error_type": type(exc).__name__})
        raise SystemExit(1) from None
    logger.info(
        "seed_completed",
        extra={"created_count": report.total_created, "skipped_count": report.total_skipped},
    )


if __name__ == "__main__":
    main()
