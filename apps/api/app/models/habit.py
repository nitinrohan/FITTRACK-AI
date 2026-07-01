"""Habit ORM models - habits and their daily completions.

Phase 12 adds two tables for the habit-tracking feature:

  Habit            - a recurring behaviour the user wants to build, e.g.
                     "Drink 2L of water" or "Read 10 pages".  MVP habits are
                     daily check-offs with a configurable weekly target
                     (target_days_per_week, 1-7).  Habits are archived rather
                     than hard-deleted so historical completions are preserved.

  HabitCompletion  - one check-off of a habit on a calendar date.  A unique
                     (habit_id, date) constraint guarantees at most one
                     completion per habit per day, which makes the "mark done"
                     endpoint naturally idempotent.

Design notes:
- `date` (not datetime) is the time axis: a habit is "done for a day"
  regardless of the time of day, which keeps it timezone-robust.  The client
  sends the user's local calendar date.
- HabitCompletion carries user_id (denormalised from the parent habit) so the
  repository can filter completions by owner directly and as defence-in-depth
  for data isolation.
- Streak and adherence are derived values computed in the service layer; they
  are never stored.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Habit ─────────────────────────────────────────────────────────────────────


class Habit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A recurring habit the user is tracking."""

    __tablename__ = "habits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional UI accent (hex string or palette token); purely presentational.
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # How many days per week the user aims to complete this habit (1-7).
    target_days_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    # Archived habits are hidden from the active list but keep their history.
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="habits")
    completions: Mapped[list[HabitCompletion]] = relationship(
        "HabitCompletion",
        back_populates="habit",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_habits_user_id_is_archived", "user_id", "is_archived"),
    )

    def __repr__(self) -> str:
        return f"<Habit user={self.user_id} name={self.name!r} archived={self.is_archived}>"


# ── HabitCompletion ───────────────────────────────────────────────────────────


class HabitCompletion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single completion of a habit on a calendar date."""

    __tablename__ = "habit_completions"

    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised owner for direct, ownership-scoped queries.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    habit: Mapped[Habit] = relationship("Habit", back_populates="completions")

    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_completion_habit_date"),
        Index("ix_habit_completions_user_id_date", "user_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<HabitCompletion habit={self.habit_id} date={self.date}>"
