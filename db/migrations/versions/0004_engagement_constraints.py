"""Enforce engagement lifecycle and sponsorship integrity in PostgreSQL.

Revision ID: 0004_engagement_constraints
Revises: 0003_contact_organization
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_engagement_constraints"
down_revision: str | None = "0003_contact_organization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_contact_submission_category",
        "contact_submissions",
        "category IN ('general', 'project', 'collaboration', 'speaking', 'sponsorship', 'other')",
    )
    op.create_check_constraint(
        "ck_contact_submission_status",
        "contact_submissions",
        "status IN ('new', 'read', 'closed', 'spam')",
    )
    op.create_check_constraint(
        "ck_contact_notification_status",
        "contact_submissions",
        "notification_status IN ('pending', 'disabled', 'sent', 'failed')",
    )
    op.create_check_constraint(
        "ck_contact_submission_consent",
        "contact_submissions",
        "consent = true",
    )
    op.create_check_constraint(
        "ck_sponsorship_amount_currency_pair",
        "sponsorship_options",
        "(amount_minor IS NULL AND currency IS NULL) OR "
        "(amount_minor IS NOT NULL AND currency IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_sponsorship_recurrence",
        "sponsorship_options",
        "recurrence IS NULL OR recurrence IN ('one_time', 'monthly', 'yearly')",
    )
    op.create_check_constraint(
        "ck_sponsorship_sort_order_nonnegative",
        "sponsorship_options",
        "sort_order >= 0",
    )
    op.create_check_constraint(
        "ck_sponsorship_destination_https",
        "sponsorship_options",
        "destination_url LIKE 'https://%'",
    )


def downgrade() -> None:
    for name, table in (
        ("ck_sponsorship_destination_https", "sponsorship_options"),
        ("ck_sponsorship_sort_order_nonnegative", "sponsorship_options"),
        ("ck_sponsorship_recurrence", "sponsorship_options"),
        ("ck_sponsorship_amount_currency_pair", "sponsorship_options"),
        ("ck_contact_submission_consent", "contact_submissions"),
        ("ck_contact_notification_status", "contact_submissions"),
        ("ck_contact_submission_status", "contact_submissions"),
        ("ck_contact_submission_category", "contact_submissions"),
    ):
        op.drop_constraint(name, table, type_="check")
