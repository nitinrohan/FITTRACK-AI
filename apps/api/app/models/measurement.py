"""BodyMeasurement ORM model.

Stores a single set of body circumference measurements for a user.
All values are stored in canonical SI units (centimetres).
The frontend converts to inches at display time when the user prefers
imperial units.

Design notes:
- Every field except user_id and measured_at is optional so users can
  record only the measurements they care about (e.g. just waist + hips).
- measured_at is a plain date - time-of-day is not meaningful.
- Multiple entries on the same date are accepted; the most-recent per date
  is used for progress charts.
- left/right variants are stored separately for users who track limb
  asymmetry (e.g. after injury). Single-value tracking works by just
  populating the left side.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class BodyMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One set of body circumference measurements logged by a user."""

    __tablename__ = "body_measurements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Date ──────────────────────────────────────────────────────────────
    measured_at: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Trunk (cm) ────────────────────────────────────────────────────────
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    chest_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hips_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    shoulders_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    abdomen_cm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Upper body - left / right (cm) ────────────────────────────────────
    # Store left + right separately to support asymmetry tracking.
    left_arm_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_arm_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    left_forearm_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_forearm_cm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Lower body - left / right (cm) ────────────────────────────────────
    left_thigh_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_thigh_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    left_calf_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_calf_cm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Neck ──────────────────────────────────────────────────────────────
    neck_cm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="body_measurements")

    __table_args__ = (
        Index(
            "ix_body_measurements_user_id_measured_at",
            "user_id",
            "measured_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<BodyMeasurement user_id={self.user_id} " f"date={self.measured_at}>"
