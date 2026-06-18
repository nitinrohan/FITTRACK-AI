"""Nutrition ORM models.

Domain model for food tracking, meal logging, and water intake.

Hierarchy:
  Food  (a food item with macro data — system or user-created)
  FoodLog  (a logged portion of a Food for a specific meal + date)
  WaterLog  (a logged water intake entry for a specific date)

Design notes:
- All macro values stored per 100 g of food (canonical unit).
  FoodLog.quantity_g stores how much the user actually ate.
  Displayed calories/macros = stored_per_100g * quantity_g / 100.
- Calories are stored as kcal.
- Dates stored as plain date (not datetime) — nutrition is tracked per day.
- meal_type uses a string enum (breakfast/lunch/dinner/snack/other) so new
  types can be added without a migration.
- WaterLog stores amount_ml (millilitres, canonical unit). The frontend
  converts to cups/fl oz for users who prefer imperial.
- is_system on Food marks built-in entries visible to all users.
  User-created foods are private (user_id set, is_system=False).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Meal type literal values ───────────────────────────────────────────────────

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack", "other")


# ── Food ──────────────────────────────────────────────────────────────────────


class Food(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A food item in the database with macro-nutrient information.

    All macro values are per 100 g of food.  quantity_g on FoodLog records
    how much was eaten; displayed values are scaled proportionally.

    is_system=True entries are seeded at startup and visible to all users.
    User-created entries have is_system=False and are private.
    """

    __tablename__ = "foods"

    # Null for system foods; set for user-created foods.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Macros per 100 g ──────────────────────────────────────────────────
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Serving suggestion ────────────────────────────────────────────────
    # Optional defaults shown on the log form; user can override quantity.
    serving_size_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    serving_unit: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "cup", "slice", "medium"

    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Soft-delete flag — deactivated foods are hidden from search.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped[User | None] = relationship("User", back_populates="foods")
    food_logs: Mapped[list[FoodLog]] = relationship(
        "FoodLog",
        back_populates="food",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_foods_user_id", "user_id"),
        # Full-text search via LIKE on name — a dedicated search index
        # (e.g. GIN tsvector) can replace this in a future phase.
        Index("ix_foods_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Food id={self.id} name={self.name!r} kcal/100g={self.calories_per_100g}>"


# ── FoodLog ───────────────────────────────────────────────────────────────────


class FoodLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single food entry in a user's meal diary.

    Links a user to a Food item for a specific date + meal slot.
    quantity_g is how many grams were eaten; displayed calories/macros
    are scaled: value = food.calories_per_100g * quantity_g / 100.
    """

    __tablename__ = "food_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("foods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── When / which meal ─────────────────────────────────────────────────
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    # breakfast | lunch | dinner | snack | other
    meal_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="other"
    )

    # ── Amount ────────────────────────────────────────────────────────────
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="food_logs")
    food: Mapped[Food] = relationship("Food", back_populates="food_logs")

    __table_args__ = (
        # Primary query: user's entries for a specific date.
        Index("ix_food_logs_user_id_logged_date", "user_id", "logged_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<FoodLog user={self.user_id} date={self.logged_date} "
            f"meal={self.meal_type} food={self.food_id} qty={self.quantity_g}g>"
        )


# ── WaterLog ──────────────────────────────────────────────────────────────────


class WaterLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single water intake entry for a user on a specific date.

    Multiple entries per day are allowed (e.g. one per glass).
    The service layer aggregates them for the daily total.
    amount_ml is stored in millilitres (canonical SI unit).
    """

    __tablename__ = "water_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="water_logs")

    __table_args__ = (
        Index("ix_water_logs_user_id_logged_date", "user_id", "logged_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<WaterLog user={self.user_id} date={self.logged_date} "
            f"ml={self.amount_ml}>"
        )
