"""Recipe ORM models.

A Recipe is a user-owned, named combination of foods + exact quantities -
"log this exact combo again" without re-describing it or re-running AI
estimation. Recipes are logged via recipe_service.log_recipe(), which
creates ordinary FoodLog rows (with an optional scale factor for a
different portion size than saved) - a Recipe itself never appears in
progress/dashboard data directly.

Design notes:
- Recipe -> RecipeItem is a straightforward one-to-many, cascade-deleted:
  no other table references recipe_id (logging a recipe just creates plain
  FoodLog rows with no back-reference), so a hard delete is safe and there
  is no need for an archive/soft-delete flag like Food/Habit use.
- RecipeItem.food_id uses ondelete="RESTRICT" (same as FoodLog.food_id) so
  a food that's part of a saved recipe can't be silently deleted out from
  under it.
- `position` preserves the order items were added in for display.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.nutrition import Food
    from app.models.user import User


class Recipe(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-saved combination of foods + exact quantities."""

    __tablename__ = "recipes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="recipes")
    items: Mapped[list[RecipeItem]] = relationship(
        "RecipeItem",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeItem.position",
        lazy="selectin",
    )

    __table_args__ = (Index("ix_recipes_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<Recipe id={self.id} user={self.user_id} name={self.name!r}>"


class RecipeItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One food + quantity within a saved recipe."""

    __tablename__ = "recipe_items"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("foods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ──────────────────────────────────────────────────────
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="items")
    food: Mapped[Food] = relationship("Food")

    __table_args__ = (Index("ix_recipe_items_recipe_id", "recipe_id"),)

    def __repr__(self) -> str:
        return f"<RecipeItem recipe={self.recipe_id} food={self.food_id} qty={self.quantity_g}g>"
