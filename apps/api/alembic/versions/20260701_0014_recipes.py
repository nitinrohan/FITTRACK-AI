"""Add recipes and recipe_items tables.

Revision ID: 20260701_0014
Revises: 20260630_0013
Create Date: 2026-07-01

Recipes let a user save a named combination of foods + exact quantities
and re-log the whole thing later (optionally scaled) without re-describing
it or re-running AI estimation. recipe_items.food_id is RESTRICT (matches
food_logs) so a food referenced by a saved recipe can't be deleted out
from under it. Recipes are hard-deleted (with items cascading) since
nothing else references recipe_id.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260701_0014"
down_revision = "20260630_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_recipes_user_id", "recipes", ["user_id"])

    op.create_table(
        "recipe_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity_g", sa.Float, nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_recipe_items_recipe_id", "recipe_items", ["recipe_id"])
    op.create_index("ix_recipe_items_food_id", "recipe_items", ["food_id"])


def downgrade() -> None:
    op.drop_index("ix_recipe_items_food_id", table_name="recipe_items")
    op.drop_index("ix_recipe_items_recipe_id", table_name="recipe_items")
    op.drop_table("recipe_items")

    op.drop_index("ix_recipes_user_id", table_name="recipes")
    op.drop_table("recipes")
