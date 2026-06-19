"""Add sleep_logs, daily_steps, and wellness_logs tables.

Revision ID: 20260618_0009
Revises: 20260616_0008
Create Date: 2026-06-18

Phase 11 — Water, sleep, steps, and wellness tracking.
Water already exists (water_logs in migration 0006).
This migration adds the three new tables.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260618_0009"
down_revision = "20260616_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sleep_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "sleep_logs",
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
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("bedtime", sa.DateTime(timezone=False), nullable=True),
        sa.Column("wake_time", sa.DateTime(timezone=False), nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("quality", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
        "ix_sleep_logs_user_id_date",
        "sleep_logs",
        ["user_id", "date"],
    )

    # ── daily_steps ────────────────────────────────────────────────────────────
    op.create_table(
        "daily_steps",
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
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("steps", sa.Integer, nullable=False),
        sa.Column("active_minutes", sa.Integer, nullable=True),
        sa.Column("distance_m", sa.Float, nullable=True),
        sa.Column("calories_burned", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
        "ix_daily_steps_user_id_date",
        "daily_steps",
        ["user_id", "date"],
    )

    # ── wellness_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "wellness_logs",
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
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("mood", sa.Integer, nullable=True),
        sa.Column("energy", sa.Integer, nullable=True),
        sa.Column("stress", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
        "ix_wellness_logs_user_id_date",
        "wellness_logs",
        ["user_id", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_wellness_logs_user_id_date", table_name="wellness_logs")
    op.drop_table("wellness_logs")

    op.drop_index("ix_daily_steps_user_id_date", table_name="daily_steps")
    op.drop_table("daily_steps")

    op.drop_index("ix_sleep_logs_user_id_date", table_name="sleep_logs")
    op.drop_table("sleep_logs")
