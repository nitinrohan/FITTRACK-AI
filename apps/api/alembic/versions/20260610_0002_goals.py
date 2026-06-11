"""Add goals table.

Revision ID: 20260610_0002
Revises: 20260610_0001
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260610_0002"
down_revision: str | None = "20260610_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Identity
        sa.Column("goal_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Numeric tracking
        sa.Column("starting_value", sa.Float, nullable=True),
        sa.Column("target_value", sa.Float, nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("target_unit", sa.String(32), nullable=True),
        # Timeline
        sa.Column("deadline", sa.Date, nullable=True),
        # Status
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        # Privacy
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    # Indexes for efficient per-user queries.
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index(
        "ix_goals_user_id_created_at", "goals", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_goals_user_id_status", "goals", ["user_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_goals_user_id_status", table_name="goals")
    op.drop_index("ix_goals_user_id_created_at", table_name="goals")
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")
