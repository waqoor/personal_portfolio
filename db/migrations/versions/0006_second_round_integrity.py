"""Enforce second-round approval and public CTA invariants.

Revision ID: 0006_second_round_integrity
Revises: 0005_issues001_integrity
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_second_round_integrity"
down_revision: str | None = "0005_issues001_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Preserve usable URLs and remove labels that cannot perform an action before
    # making the pair invariant authoritative for every write path.
    op.execute(
        "UPDATE profiles SET primary_cta_label = 'Learn more' "
        "WHERE primary_cta_url IS NOT NULL "
        "AND (primary_cta_label IS NULL OR length(trim(primary_cta_label)) = 0)"
    )
    op.execute(
        "UPDATE profiles SET primary_cta_label = NULL "
        "WHERE primary_cta_url IS NULL AND primary_cta_label IS NOT NULL"
    )
    op.execute(
        "UPDATE profiles SET secondary_cta_label = 'Learn more' "
        "WHERE secondary_cta_url IS NOT NULL "
        "AND (secondary_cta_label IS NULL OR length(trim(secondary_cta_label)) = 0)"
    )
    op.execute(
        "UPDATE profiles SET secondary_cta_label = NULL "
        "WHERE secondary_cta_url IS NULL AND secondary_cta_label IS NOT NULL"
    )
    op.create_check_constraint(
        "ck_profile_primary_cta_pair",
        "profiles",
        "(primary_cta_label IS NULL AND primary_cta_url IS NULL) OR "
        "(primary_cta_label IS NOT NULL AND length(trim(primary_cta_label)) > 0 "
        "AND primary_cta_url IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_profile_secondary_cta_pair",
        "profiles",
        "(secondary_cta_label IS NULL AND secondary_cta_url IS NULL) OR "
        "(secondary_cta_label IS NOT NULL AND length(trim(secondary_cta_label)) > 0 "
        "AND secondary_cta_url IS NOT NULL)",
    )

    for table_name, constraint_name in (
        ("impact_metrics", "ck_metric_approval_revision"),
        ("testimonials", "ck_testimonial_approval_revision"),
    ):
        op.drop_constraint(constraint_name, table_name, type_="check")
        op.create_check_constraint(
            constraint_name,
            table_name,
            "NOT is_approved OR (approved_revision_hash IS NOT NULL "
            "AND length(approved_revision_hash) = 64 AND approved_at IS NOT NULL "
            "AND approved_by_admin_id IS NOT NULL)",
        )


def downgrade() -> None:
    for table_name, constraint_name in (
        ("impact_metrics", "ck_metric_approval_revision"),
        ("testimonials", "ck_testimonial_approval_revision"),
    ):
        op.drop_constraint(constraint_name, table_name, type_="check")
        op.create_check_constraint(
            constraint_name,
            table_name,
            "NOT is_approved OR (approved_revision_hash IS NOT NULL "
            "AND length(approved_revision_hash) = 64)",
        )
    op.drop_constraint("ck_profile_secondary_cta_pair", "profiles", type_="check")
    op.drop_constraint("ck_profile_primary_cta_pair", "profiles", type_="check")
