"""NutritionTarget ORM model.

One row per user (like UserPreference) holding optional daily macro/calorie
targets. These are the numbers "compared to your goals" features (e.g. the
AI daily nutrition insight) measure progress against.

Design notes:
- All fields are nullable and independent - a user can set just a protein
  target without setting the others. Comparisons only run for fields that
  are actually set; the app must never invent a target the user hasn't
  entered (see AI Assistant Rules: never invent goals/data).
- Values are stored in canonical units: kcal for energy, grams for macros.
- This is deliberately separate from the general-purpose Goal model - Goal
  covers open-ended, dated fitness goals with a status lifecycle; nutrition
  targets are a simple daily settings row with no lifecycle of their own.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class NutritionTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's optional daily nutrition targets."""

    __tablename__ = "nutrition_targets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    calorie_target_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_target_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_target_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_target_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_target_g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Relationship ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="nutrition_target")

    __table_args__ = (Index("ix_nutrition_targets_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<NutritionTarget user_id={self.user_id}>"
