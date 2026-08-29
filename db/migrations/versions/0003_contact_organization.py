"""Persist the optional organization supplied with a contact inquiry.

Revision ID: 0003_contact_organization
Revises: bf568d045965
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_contact_organization"
down_revision: str | None = "bf568d045965"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contact_submissions",
        sa.Column("organization", sa.String(length=160), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contact_submissions", "organization")
