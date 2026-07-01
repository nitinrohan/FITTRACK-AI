"""Add nutrition_targets table.

Revision ID: 20260630_0013
Revises: 20260626_0012
Create Date: 2026-06-30

Nutrition targets - one optional row per user holding daily calorie/macro
targets (calorie_target_kcal, protein_target_g, carbs_target_g,
fat_target_g, fiber_target_g). All fields nullable; a missing row or a
null field means "not set", never a default the app invented. Used by the
daily nutrition insight feature to compare logged intake against real
user-set targets instead of guessing.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260630_0013"
down_revision = "20260626_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nutrition_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("calorie_target_kcal", sa.Float, nullable=True),
        sa.Column("protein_target_g", sa.Float, nullable=True),
        sa.Column("carbs_target_g", sa.Float, nullable=True),
        sa.Column("fat_target_g", sa.Float, nullable=True),
        sa.Column("fiber_target_g", sa.Float, nullable=True),
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
        "ix_nutrition_targets_user_id", "nutrition_targets", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_nutrition_targets_user_id", table_name="nutrition_targets")
    op.drop_table("nutrition_targets")
