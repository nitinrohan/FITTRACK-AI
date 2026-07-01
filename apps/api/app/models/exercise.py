"""Exercise ORM model.

Design notes:
- System exercises (is_system=True, user_id=None) are the built-in library
  seeded at startup. All users can browse and use them.
- Custom exercises (is_system=False, user_id=<uuid>) are created by individual
  users and are only visible to their owner.
- muscle_groups stored as a comma-separated string (simple, avoids JSON column
  portability issues; parsed to a list at the service layer).
- Canonical equipment values are enforced at the API boundary (Pydantic enum).
- category is a free-form string validated by Pydantic; keeping it as a plain
  column avoids a separate lookup table for MVP.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Exercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An exercise that can be performed in a workout.

    System exercises are global; custom exercises belong to one user.
    """

    __tablename__ = "exercises"

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    # Values: "strength" | "cardio" | "flexibility" | "balance" | "sports" | "other"
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="strength")

    # Comma-separated canonical muscle group names, e.g. "chest,triceps,shoulders"
    # Parsed to list[str] at the service layer.
    muscle_groups: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Values: "barbell" | "dumbbell" | "bodyweight" | "machine" | "cable" |
    #         "kettlebell" | "resistance_band" | "ez_bar" | "plate" | "other" | "none"
    equipment: Mapped[str] = mapped_column(String(50), nullable=False, default="none")

    # Whether this is a built-in system exercise or user-created
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Null for system exercises; set for custom user exercises
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationship - only present for custom exercises
    user: Mapped[User | None] = relationship("User", back_populates="exercises")

    __table_args__ = (
        # Fast lookup by name (case-insensitive search done in Python/DB layer)
        Index("ix_exercises_name", "name"),
        # Filter system exercises quickly
        Index("ix_exercises_is_system", "is_system"),
        # Filter custom exercises by owner
        Index("ix_exercises_user_id", "user_id"),
        # Filter by category
        Index("ix_exercises_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<Exercise id={self.id} name={self.name!r} system={self.is_system}>"
