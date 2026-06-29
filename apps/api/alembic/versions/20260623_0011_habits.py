"""Add habits and habit_completions tables.

Revision ID: 20260623_0011
Revises: 20260619_0010
Create Date: 2026-06-23

Phase 12 - Habit tracking.  Adds the `habits` table (recurring behaviours
with a weekly target) and `habit_completions` (one check-off per habit per
day, enforced by a unique constraint).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260623_0011"
down_revision = "20260619_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── habits ─────────────────────────────────────────────────────────────────
    op.create_table(
        "habits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column(
            "target_days_per_week",
            sa.Integer,
            nullable=False,
            server_default="7",
        ),
        sa.Column(
            "is_archived",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_habits_user_id_is_archived",
        "habits",
        ["user_id", "is_archived"],
    )
    op.create_index("ix_habits_user_id", "habits", ["user_id"])

    # ── habit_completions ──────────────────────────────────────────────────────
    op.create_table(
        "habit_completions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "habit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("habits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "habit_id", "date", name="uq_habit_completion_habit_date"
        ),
    )
    op.create_index("ix_habit_completions_habit_id", "habit_completions", ["habit_id"])
    op.create_index("ix_habit_completions_user_id", "habit_completions", ["user_id"])
    op.create_index(
        "ix_habit_completions_user_id_date",
        "habit_completions",
        ["user_id", "date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_habit_completions_user_id_date", table_name="habit_completions"
    )
    op.drop_index("ix_habit_completions_user_id", table_name="habit_completions")
    op.drop_index("ix_habit_completions_habit_id", table_name="habit_completions")
    op.drop_table("habit_completions")

    op.drop_index("ix_habits_user_id", table_name="habits")
    op.drop_index("ix_habits_user_id_is_archived", table_name="habits")
    op.drop_table("habits")
