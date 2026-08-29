"""Create engagement, assistant audit, and abuse-limit persistence.

Revision ID: 0001_cross_cutting
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_cross_cutting"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("bucket_key", sa.String(length=160), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("request_count > 0", name="ck_rate_limit_request_count_positive"),
        sa.PrimaryKeyConstraint("bucket_key"),
    )
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("consent", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="new", nullable=False),
        sa.Column(
            "notification_status", sa.String(length=24), server_default="pending", nullable=False
        ),
        sa.Column("notification_error_code", sa.String(length=64), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("idempotency_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_hash"),
    )
    op.create_index("ix_contact_submissions_created_at", "contact_submissions", ["created_at"])
    op.create_index(
        "ix_contact_submissions_email_hash_created",
        "contact_submissions",
        ["email_hash", "created_at"],
    )
    op.create_index(
        "ix_contact_submissions_status_created",
        "contact_submissions",
        ["status", "created_at"],
    )
    op.create_table(
        "sponsorship_options",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("cta_label", sa.String(length=80), nullable=False),
        sa.Column("destination_url", sa.String(length=2048), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("recurrence", sa.String(length=20), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("nofollow", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "amount_minor IS NULL OR amount_minor >= 0",
            name="ck_sponsorship_amount_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_sponsorship_options_public_order",
        "sponsorship_options",
        ["is_published", "is_archived", "sort_order"],
    )
    op.create_table(
        "assistant_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("question_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("contained_redacted_pii", sa.Boolean(), nullable=False),
        sa.Column("provider_request_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_count >= 0", name="ck_assistant_source_count_nonnegative"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_assistant_duration_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_audit_events_created", "assistant_audit_events", ["created_at"])
    op.create_index(
        "ix_assistant_audit_events_status_created",
        "assistant_audit_events",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_audit_events_status_created", table_name="assistant_audit_events")
    op.drop_index("ix_assistant_audit_events_created", table_name="assistant_audit_events")
    op.drop_table("assistant_audit_events")
    op.drop_index("ix_sponsorship_options_public_order", table_name="sponsorship_options")
    op.drop_table("sponsorship_options")
    op.drop_index("ix_contact_submissions_status_created", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_email_hash_created", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_created_at", table_name="contact_submissions")
    op.drop_table("contact_submissions")
    op.drop_table("rate_limit_buckets")
