"""Add statement workflow statuses used by the application model.

Revision ID: a04c2d7f901b
Revises: create_statement_rows
"""

from alembic import op


revision = "a04c2d7f901b"
down_revision = "create_statement_rows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL enum labels cannot be removed safely during downgrade.
    for value in ("VALIDATING", "REVIEW_REQUIRED", "CONFIRMED", "ANALYZED", "CANCELLED"):
        op.execute(
            f"ALTER TYPE public.statementstatus ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    pass
