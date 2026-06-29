"""Goal ORM model.

A Goal represents a user-defined fitness target with optional numeric tracking.
Goals can be purely qualitative (title + description) or quantitative
(starting_value → target_value with a current_value that tracks progress).

Internal unit strategy:
  target_unit and current_unit store the *display* unit chosen by the user
  (e.g. "kg", "lb", "%", "reps").  The numeric values are stored exactly as
  entered - no server-side unit conversion for goals because goal values are
  personal targets the user sets, not measured physiological data.
  When the user changes their unit preference the goal values stay as-is;
  the frontend displays them with whatever unit was recorded on the goal.

Status lifecycle:
  active → completed   (user manually marks done, or target reached)
  active → paused      (user suspends the goal temporarily)
  active → cancelled   (user gives up on the goal)
  paused → active      (user resumes)
  completed/cancelled  → terminal (no further transitions expected)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

GOAL_TYPE_CHOICES = (
    "weight_loss",
    "weight_gain",
    "body_fat",
    "strength",
    "endurance",
    "habit",
    "custom",
)

GOAL_STATUS_CHOICES = ("active", "completed", "paused", "cancelled")


class Goal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity ───────────────────────────────────────────────────────────
    goal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Numeric tracking (optional) ────────────────────────────────────────
    # Store values as floats with the user's chosen unit label.
    # Both value and unit must be set together if either is set.
    starting_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── Timeline ───────────────────────────────────────────────────────────
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Status ─────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # ── Privacy ────────────────────────────────────────────────────────────
    # Goals are private by default; public sharing is a future feature.
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="goals")

    __table_args__ = (
        # Efficient listing of a user's goals ordered by creation time.
        Index("ix_goals_user_id_created_at", "user_id", "created_at"),
        # Filter by status is common (e.g. show only active goals).
        Index("ix_goals_user_id_status", "user_id", "status"),
    )
