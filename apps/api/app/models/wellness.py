"""Wellness ORM models - sleep, daily steps, and wellness check-in.

Phase 11 adds three lightweight daily-logging tables:

  SleepLog    - one or more sleep entries per day (naps are valid).
                Canonical unit: duration_minutes (integer).
                bedtime / wake_time are optional UTC datetimes; when both
                are provided the service computes duration_minutes from them.

  DailySteps  - step-count log for a calendar date.
                Canonical unit: steps (integer), distance in metres.
                Multiple entries per day are accepted (app syncs, manual
                entry); the latest entry for a date is used for display.

  WellnessLog - subjective daily check-in: mood, energy, stress on a 1-5
                scale.  At least one metric must be provided (validated in
                the service layer).  One entry per day is the norm but the
                DB allows multiple.

All values use date (not datetime) as the primary time axis so that
entries are day-aligned regardless of time zone.  UTC datetimes are used
only where time-of-day is meaningful (bedtime, wake_time).

Canonical unit summary:
  sleep duration  → minutes (integer)
  distance        → metres  (float)
  mood / energy / stress → integer 1-5 (1=lowest, 5=highest)
                           stress is inverted at display time (1=very calm)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── SleepLog ──────────────────────────────────────────────────────────────────


class SleepLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One sleep session logged by a user.

    The `date` field is the calendar date the sleep "belongs to" - typically
    the wake-up date, so a session from 23:00 Mon → 07:00 Tue is logged as
    Tuesday.

    duration_minutes is the canonical stored value.  When both bedtime and
    wake_time are provided the service computes it; when only duration is
    provided bedtime/wake_time are left null.
    """

    __tablename__ = "sleep_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Date ─────────────────────────────────────────────────────────────────
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Times (optional - may log duration directly) ──────────────────────────
    bedtime: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    wake_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    # ── Duration (canonical) ──────────────────────────────────────────────────
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Subjective quality (1 = very poor, 5 = excellent) ─────────────────────
    quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="sleep_logs")

    __table_args__ = (Index("ix_sleep_logs_user_id_date", "user_id", "date"),)

    def __repr__(self) -> str:
        return (
            f"<SleepLog user={self.user_id} date={self.date} " f"minutes={self.duration_minutes}>"
        )


# ── DailySteps ────────────────────────────────────────────────────────────────


class DailySteps(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Daily step count and activity metrics for a user.

    Multiple entries per date are accepted (wearable syncs may push
    incremental updates).  The service returns the latest entry per date
    for display and aggregation.

    distance_m stores distance in metres (canonical SI unit).
    """

    __tablename__ = "daily_steps"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Core metric ───────────────────────────────────────────────────────────
    steps: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Optional supplementary metrics ───────────────────────────────────────
    active_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="daily_steps")

    __table_args__ = (Index("ix_daily_steps_user_id_date", "user_id", "date"),)

    def __repr__(self) -> str:
        return f"<DailySteps user={self.user_id} date={self.date} " f"steps={self.steps}>"


# ── WellnessLog ───────────────────────────────────────────────────────────────


class WellnessLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Subjective daily wellness check-in.

    All three rating fields are optional; at least one must be provided
    (enforced in the service layer).

    Rating scale:
      mood    - 1 (very low) … 5 (excellent)
      energy  - 1 (exhausted) … 5 (high energy)
      stress  - 1 (very calm) … 5 (very stressed)
                (inverted at display time: higher stress = worse)

    Multiple entries per date are accepted (e.g. morning + evening check).
    The service surfaces the latest entry per date for dashboards.
    """

    __tablename__ = "wellness_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Subjective ratings (1-5) ──────────────────────────────────────────────
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="wellness_logs")

    __table_args__ = (Index("ix_wellness_logs_user_id_date", "user_id", "date"),)

    def __repr__(self) -> str:
        return (
            f"<WellnessLog user={self.user_id} date={self.date} "
            f"mood={self.mood} energy={self.energy} stress={self.stress}>"
        )
