"""Close publication, evidence, delivery, media, and repository integrity gaps.

Revision ID: 0005_issues001_integrity
Revises: 0004_engagement_constraints
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_issues001_integrity"
down_revision: str | None = "0004_engagement_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _value_enum(name: str, *values: str, length: int) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
    )


def upgrade() -> None:
    op.add_column(
        "contact_submissions",
        sa.Column("payload_digest", sa.String(length=64), nullable=True),
    )
    for table_name in ("impact_metrics", "testimonials"):
        op.add_column(
            table_name,
            sa.Column("approved_revision_hash", sa.String(length=64), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        )
    for table_name in ("media_assets", "project_media"):
        op.add_column(
            table_name,
            sa.Column(
                "is_decorative",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
        op.add_column(
            table_name,
            sa.Column("page_count", sa.Integer(), nullable=True),
        )
    op.add_column(
        "projects",
        sa.Column(
            "repository_metadata_refresh_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "nature",
            _value_enum(
                "projectnature",
                "case_study",
                "product",
                "software",
                length=24,
            ),
            server_default="case_study",
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE projects SET nature = 'software' "
        "WHERE is_open_source = true AND repository_url IS NOT NULL"
    )

    op.create_table(
        "portfolio_approval_events",
        sa.Column("subject_type", sa.String(length=16), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            _value_enum(
                "approvalaction",
                "approved",
                "revoked",
                "auto_revoked",
                length=24,
            ),
            nullable=False,
        ),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("revision_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "subject_type IN ('metric', 'testimonial')",
            name="ck_portfolio_approval_event_subject_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_portfolio_approval_events_subject",
        "portfolio_approval_events",
        ["subject_type", "subject_id", "created_at"],
    )

    op.create_table(
        "contact_notification_outbox",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("provider_idempotency_key", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_contact_outbox_attempts"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'retrying', 'sent', 'terminal', 'disabled')",
            name="ck_contact_outbox_status",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["contact_submissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_idempotency_key",
            name="uq_contact_notification_outbox_provider_idempotency_key",
        ),
        sa.UniqueConstraint(
            "submission_id",
            name="uq_contact_notification_outbox_submission_id",
        ),
    )
    op.create_index(
        "ix_contact_notification_outbox_next_attempt_at",
        "contact_notification_outbox",
        ["next_attempt_at"],
    )
    op.create_index(
        "ix_contact_outbox_due",
        "contact_notification_outbox",
        ["status", "next_attempt_at"],
    )

    op.create_table(
        "repository_metadata_snapshots",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=40),
            server_default="github",
            nullable=False,
        ),
        sa.Column("repository_identity", sa.String(length=300), nullable=True),
        sa.Column("language", sa.String(length=120), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=True),
        sa.Column("forks", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_etag", sa.String(length=300), nullable=True),
        sa.Column(
            "status",
            _value_enum(
                "repositorysnapshotstatus",
                "fresh",
                "stale",
                "refreshing",
                "rate_limited",
                "unavailable",
                length=24,
            ),
            server_default="stale",
            nullable=False,
        ),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_token", sa.String(length=36), nullable=True),
        sa.Column("refresh_lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "forks IS NULL OR forks >= 0",
            name="ck_repository_metadata_forks",
        ),
        sa.CheckConstraint(
            "stars IS NULL OR stars >= 0",
            name="ck_repository_metadata_stars",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_repository_metadata_project"),
    )
    op.create_index(
        "ix_repository_metadata_refresh",
        "repository_metadata_snapshots",
        ["status", "stale_after"],
    )
    op.create_index(
        "ix_repository_metadata_snapshots_project_id",
        "repository_metadata_snapshots",
        ["project_id"],
    )

    op.create_table(
        "portfolio_evidence",
        sa.Column("impact_metric_id", sa.Uuid(), nullable=True),
        sa.Column("testimonial_id", sa.Uuid(), nullable=True),
        sa.Column(
            "kind",
            _value_enum(
                "evidencekind",
                "public_url",
                "managed_media",
                "document_reference",
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            _value_enum(
                "evidencevisibility",
                "private_review",
                "public",
                length=24,
            ),
            server_default="private_review",
            nullable=False,
        ),
        sa.Column("reference_url", sa.String(length=2048), nullable=True),
        sa.Column("managed_media_id", sa.Uuid(), nullable=True),
        sa.Column("reference_text", sa.String(length=2048), nullable=True),
        sa.Column("public_label", sa.String(length=160), nullable=True),
        sa.Column("provenance", sa.String(length=500), nullable=False),
        sa.Column("captured_at", sa.Date(), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(kind = 'public_url' AND reference_url IS NOT NULL "
            "AND managed_media_id IS NULL AND reference_text IS NULL) OR "
            "(kind = 'managed_media' AND reference_url IS NULL "
            "AND managed_media_id IS NOT NULL AND reference_text IS NULL) OR "
            "(kind = 'document_reference' AND reference_url IS NULL "
            "AND managed_media_id IS NULL AND reference_text IS NOT NULL)",
            name="ck_portfolio_evidence_locator",
        ),
        sa.CheckConstraint(
            "visibility != 'public' OR "
            "(public_label IS NOT NULL AND length(trim(public_label)) >= 3)",
            name="ck_portfolio_evidence_public_label",
        ),
        sa.CheckConstraint("revision > 0", name="ck_portfolio_evidence_revision"),
        sa.CheckConstraint(
            "(impact_metric_id IS NOT NULL AND testimonial_id IS NULL) OR "
            "(impact_metric_id IS NULL AND testimonial_id IS NOT NULL)",
            name="ck_portfolio_evidence_single_subject",
        ),
        sa.ForeignKeyConstraint(
            ["impact_metric_id"],
            ["impact_metrics.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["managed_media_id"],
            ["project_media.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["testimonial_id"],
            ["testimonials.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("impact_metric_id", name="uq_portfolio_evidence_metric"),
        sa.UniqueConstraint("testimonial_id", name="uq_portfolio_evidence_testimonial"),
    )
    op.create_index(
        "ix_portfolio_evidence_media",
        "portfolio_evidence",
        ["managed_media_id"],
    )

    # Preserve old free-text references as private, explicitly unreviewed evidence.
    op.execute(
        """
        INSERT INTO portfolio_evidence (
            id, impact_metric_id, kind, visibility, reference_text, provenance,
            captured_at, revision, created_at, updated_at
        )
        SELECT gen_random_uuid(), id, 'document_reference', 'private_review',
               trim(evidence_reference),
               'Migrated legacy free-text reference; independent review required',
               COALESCE(updated_at::date, CURRENT_DATE), 1, now(), now()
        FROM impact_metrics
        WHERE evidence_reference IS NOT NULL AND length(trim(evidence_reference)) > 0
        """
    )
    op.execute(
        """
        INSERT INTO portfolio_evidence (
            id, testimonial_id, kind, visibility, reference_text, provenance,
            captured_at, revision, created_at, updated_at
        )
        SELECT gen_random_uuid(), id, 'document_reference', 'private_review',
               trim(source_reference),
               'Migrated legacy free-text reference; independent review required',
               COALESCE(updated_at::date, CURRENT_DATE), 1, now(), now()
        FROM testimonials
        WHERE source_reference IS NOT NULL AND length(trim(source_reference)) > 0
        """
    )
    for table_name, subject_type in (
        ("impact_metrics", "metric"),
        ("testimonials", "testimonial"),
    ):
        op.execute(
            sa.text(
                f"""
                INSERT INTO portfolio_approval_events (
                    id, subject_type, subject_id, action, actor_admin_id,
                    revision_hash, created_at
                )
                SELECT gen_random_uuid(), :subject_type, id, 'auto_revoked',
                       approved_by_admin_id, NULL, now()
                FROM {table_name}
                WHERE is_approved = true
                """
            ).bindparams(subject_type=subject_type)
        )
        op.execute(
            f"UPDATE {table_name} SET is_approved = false, approved_at = NULL, "
            "approved_by_admin_id = NULL, approved_revision_hash = NULL "
            "WHERE is_approved = true"
        )

    op.drop_constraint("ck_metric_approval_evidence", "impact_metrics", type_="check")
    op.create_check_constraint(
        "ck_metric_approval_revision",
        "impact_metrics",
        "NOT is_approved OR (approved_revision_hash IS NOT NULL "
        "AND length(approved_revision_hash) = 64)",
    )
    op.drop_constraint("ck_testimonial_approval_source", "testimonials", type_="check")
    op.create_check_constraint(
        "ck_testimonial_approval_revision",
        "testimonials",
        "NOT is_approved OR (approved_revision_hash IS NOT NULL "
        "AND length(approved_revision_hash) = 64)",
    )
    op.drop_column("impact_metrics", "evidence_reference")
    op.drop_column("testimonials", "source_reference")

    # Existing unsent notifications join the durable lifecycle without being lost.
    op.execute(
        """
        INSERT INTO contact_notification_outbox (
            id, submission_id, provider_idempotency_key, status, attempt_count,
            next_attempt_at, last_error_code, created_at, updated_at
        )
        SELECT gen_random_uuid()::text, id, 'contact-notification:' || id,
               CASE WHEN notification_status = 'failed' THEN 'retrying' ELSE 'pending' END,
               CASE WHEN notification_status = 'failed' THEN 1 ELSE 0 END,
               now(), notification_error_code, now(), now()
        FROM contact_submissions
        WHERE notification_status IN ('pending', 'failed')
        """
    )
    op.execute(
        "UPDATE contact_submissions SET notification_status = 'retrying' "
        "WHERE notification_status = 'failed'"
    )
    op.drop_constraint(
        "ck_contact_notification_status",
        "contact_submissions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_contact_notification_status",
        "contact_submissions",
        "notification_status IN "
        "('pending', 'disabled', 'sent', 'failed', 'retrying', 'terminal')",
    )

    op.execute(
        "UPDATE navigation_items SET location = 'header' "
        "WHERE location NOT IN ('header', 'footer')"
    )
    op.alter_column(
        "navigation_items",
        "location",
        existing_type=sa.String(length=40),
        type_=sa.String(length=16),
        existing_nullable=False,
        existing_server_default="header",
    )
    op.create_check_constraint(
        "navigationlocation",
        "navigation_items",
        "location IN ('header', 'footer')",
    )

    op.drop_constraint("projects_featured_rank_key", "projects", type_="unique")
    op.create_index(
        "uq_projects_active_featured_rank",
        "projects",
        ["featured_rank"],
        unique=True,
        postgresql_where=sa.text(
            "featured_rank IS NOT NULL AND status = 'published' "
            "AND is_visible = true AND archived_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_projects_active_featured_rank", table_name="projects")
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY featured_rank
                       ORDER BY CASE WHEN status = 'published' AND is_visible = true
                                          AND archived_at IS NULL THEN 0 ELSE 1 END,
                                updated_at DESC,
                                id
                   ) AS duplicate_order
            FROM projects
            WHERE featured_rank IS NOT NULL
        )
        UPDATE projects
        SET featured_rank = NULL
        FROM ranked
        WHERE projects.id = ranked.id AND ranked.duplicate_order > 1
        """
    )
    op.create_unique_constraint(
        "projects_featured_rank_key",
        "projects",
        ["featured_rank"],
    )

    op.drop_constraint("navigationlocation", "navigation_items", type_="check")
    op.alter_column(
        "navigation_items",
        "location",
        existing_type=sa.String(length=16),
        type_=sa.String(length=40),
        existing_nullable=False,
        existing_server_default="header",
    )

    op.drop_constraint(
        "ck_contact_notification_status",
        "contact_submissions",
        type_="check",
    )
    op.execute(
        "UPDATE contact_submissions SET notification_status = 'failed' "
        "WHERE notification_status IN ('retrying', 'terminal')"
    )
    op.create_check_constraint(
        "ck_contact_notification_status",
        "contact_submissions",
        "notification_status IN ('pending', 'disabled', 'sent', 'failed')",
    )

    op.add_column(
        "impact_metrics",
        sa.Column("evidence_reference", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "testimonials",
        sa.Column("source_reference", sa.String(length=2048), nullable=True),
    )
    op.execute(
        """
        UPDATE impact_metrics AS metric
        SET evidence_reference = COALESCE(
            evidence.reference_url,
            evidence.reference_text,
            'managed-media:' || evidence.managed_media_id::text
        )
        FROM portfolio_evidence AS evidence
        WHERE evidence.impact_metric_id = metric.id
        """
    )
    op.execute(
        """
        UPDATE testimonials AS testimonial
        SET source_reference = COALESCE(
            evidence.reference_url,
            evidence.reference_text,
            'managed-media:' || evidence.managed_media_id::text
        )
        FROM portfolio_evidence AS evidence
        WHERE evidence.testimonial_id = testimonial.id
        """
    )
    op.drop_constraint("ck_metric_approval_revision", "impact_metrics", type_="check")
    op.create_check_constraint(
        "ck_metric_approval_evidence",
        "impact_metrics",
        "NOT is_approved OR (evidence_reference IS NOT NULL "
        "AND length(trim(evidence_reference)) > 0)",
    )
    op.drop_constraint(
        "ck_testimonial_approval_revision",
        "testimonials",
        type_="check",
    )
    op.create_check_constraint(
        "ck_testimonial_approval_source",
        "testimonials",
        "NOT is_approved OR (source_reference IS NOT NULL "
        "AND length(trim(source_reference)) > 0)",
    )

    op.drop_index("ix_portfolio_evidence_media", table_name="portfolio_evidence")
    op.drop_table("portfolio_evidence")
    op.drop_index(
        "ix_repository_metadata_snapshots_project_id",
        table_name="repository_metadata_snapshots",
    )
    op.drop_index(
        "ix_repository_metadata_refresh",
        table_name="repository_metadata_snapshots",
    )
    op.drop_table("repository_metadata_snapshots")
    op.drop_index("ix_contact_outbox_due", table_name="contact_notification_outbox")
    op.drop_index(
        "ix_contact_notification_outbox_next_attempt_at",
        table_name="contact_notification_outbox",
    )
    op.drop_table("contact_notification_outbox")
    op.drop_index(
        "ix_portfolio_approval_events_subject",
        table_name="portfolio_approval_events",
    )
    op.drop_table("portfolio_approval_events")

    op.drop_column("testimonials", "created_by_admin_id")
    op.drop_column("testimonials", "approved_revision_hash")
    op.drop_column("impact_metrics", "created_by_admin_id")
    op.drop_column("impact_metrics", "approved_revision_hash")
    op.drop_column("projects", "nature")
    op.drop_column("projects", "repository_metadata_refresh_enabled")
    for table_name in ("project_media", "media_assets"):
        op.drop_column(table_name, "page_count")
        op.drop_column(table_name, "is_decorative")
    op.drop_column("contact_submissions", "payload_digest")
