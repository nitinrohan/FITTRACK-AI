"""Add body_measurements table.

Revision ID: 20260612_0007
Revises: 20260612_0006
Create Date: 2026-06-12

Adds the body_measurements table which stores circumference measurements
(waist, chest, hips, arms, thighs, calves, neck, etc.) in centimetres.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260612_0007"
down_revision = "20260612_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "body_measurements",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        # ── Ownership ─────────────────────────────────────────────────────
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # ── Date ──────────────────────────────────────────────────────────
        sa.Column("measured_at", sa.Date, nullable=False),
        # ── Trunk (cm) ────────────────────────────────────────────────────
        sa.Column("waist_cm", sa.Float, nullable=True),
        sa.Column("chest_cm", sa.Float, nullable=True),
        sa.Column("hips_cm", sa.Float, nullable=True),
        sa.Column("shoulders_cm", sa.Float, nullable=True),
        sa.Column("abdomen_cm", sa.Float, nullable=True),
        # ── Upper body (cm) ───────────────────────────────────────────────
        sa.Column("left_arm_cm", sa.Float, nullable=True),
        sa.Column("right_arm_cm", sa.Float, nullable=True),
        sa.Column("left_forearm_cm", sa.Float, nullable=True),
        sa.Column("right_forearm_cm", sa.Float, nullable=True),
        # ── Lower body (cm) ───────────────────────────────────────────────
        sa.Column("left_thigh_cm", sa.Float, nullable=True),
        sa.Column("right_thigh_cm", sa.Float, nullable=True),
        sa.Column("left_calf_cm", sa.Float, nullable=True),
        sa.Column("right_calf_cm", sa.Float, nullable=True),
        # ── Neck ──────────────────────────────────────────────────────────
        sa.Column("neck_cm", sa.Float, nullable=True),
        # ── Notes ─────────────────────────────────────────────────────────
        sa.Column("notes", sa.Text, nullable=True),
        # ── Timestamps ────────────────────────────────────────────────────
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
        "ix_body_measurements_user_id_measured_at",
        "body_measurements",
        ["user_id", "measured_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_body_measurements_user_id_measured_at",
        table_name="body_measurements",
    )
    op.drop_table("body_measurements")
