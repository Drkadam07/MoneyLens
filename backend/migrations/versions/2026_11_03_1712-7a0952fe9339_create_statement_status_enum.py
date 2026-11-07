# backend/migrations/versions/2026_11_03_1712-7a0952fe9339_create_statement_status_enum.py
"""Create statement status enum and migrate statements.status.

Revision ID: 7a0952fe9339
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7a0952fe9339"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IMPORTANT:
    # Keep these values synchronized with StatementStatus
    # in app/modules/statements/models.py.
    status_enum = postgresql.ENUM(
        "QUEUED",
        "PROCESSING",
        "COMPLETED",
        "FAILED",
        name="statementstatus",
        schema="public",
        create_type=False,
    )

    # Create PostgreSQL enum before altering the column.
    status_enum.create(op.get_bind(), checkfirst=True)

    # Convert existing VARCHAR status column to PostgreSQL ENUM.
    op.alter_column(
        "statements",
        "status",
        existing_type=sa.String(length=50),
        type_=status_enum,
        existing_nullable=False,
        postgresql_using="status::text::public.statementstatus",
    )


def downgrade() -> None:
    # Convert enum back to VARCHAR.
    op.alter_column(
        "statements",
        "status",
        existing_type=postgresql.ENUM(
            "QUEUED",
            "PROCESSING",
            "COMPLETED",
            "FAILED",
            name="statementstatus",
            schema="public",
            create_type=False,
        ),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="status::text",
    )

    # Drop enum after converting the column.
    op.execute("DROP TYPE IF EXISTS public.statementstatus")
