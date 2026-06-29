"""WeightEntry ORM model.

Stores a single body-weight measurement for a user.  All numeric values are
stored in canonical SI units - weight in kg, body fat as a percentage (0-100),
muscle mass in kg.  The frontend converts to the user's preferred unit system
at display time.

Design notes:
- measured_at is stored as a plain date (not datetime) because users typically
  log weight once per day.  If a user logs twice on the same day the second
  entry is accepted - the service layer surfaces this as a note, not an error.
  The most-recent entry per day is used for charting.
- body_fat_pct and muscle_mass_kg are fully optional.  Many users only track
  scale weight.
- notes is a short free-text field for the user's own context (e.g. "after
  morning run", "holiday week").
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class WeightEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One body-weight measurement logged by a user."""

    __tablename__ = "weight_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Measurements (canonical units) ────────────────────────────────────
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional body-composition fields
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Timeline ───────────────────────────────────────────────────────────
    # Stored as a date - time-of-day is not relevant for weight trends.
    measured_at: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Context ────────────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Display unit hint ──────────────────────────────────────────────────
    # The unit the user entered the value in, for round-trip display without
    # visible precision loss.  "kg" or "lbs".  Does NOT affect stored value.
    display_unit: Mapped[str] = mapped_column(String(4), nullable=False, default="kg")

    # ── Relationship ───────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="weight_entries")

    __table_args__ = (
        # Primary query pattern: user's entries ordered by date.
        Index("ix_weight_entries_user_id_measured_at", "user_id", "measured_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<WeightEntry user_id={self.user_id} " f"date={self.measured_at} kg={self.weight_kg}>"
        )
