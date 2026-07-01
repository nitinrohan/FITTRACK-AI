"""StressLog ORM model - point-in-time stress readings (0-100).

This is a finer-grained, multi-reading-per-day metric, distinct from the
subjective 1-5 `stress` field on WellnessLog (a once-or-twice daily check-in).
Stress readings are self-reported in the MVP; `source` is an extension point
for wearable-provided readings later.

Storage:
- level is an integer 0-100 (validated at the API boundary).
- recorded_at is stored in UTC (naive), like all timestamps in this codebase.
- Daily highest/lowest/average are derived at query time, never stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class StressLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single stress reading on a 0-100 scale."""

    __tablename__ = "stress_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 0 (very calm) .. 100 (very stressed). Higher = more stress.
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    # When the reading was taken (UTC, naive). Multiple readings per day allowed.
    recorded_at: Mapped[datetime] = mapped_column(nullable=False)

    # "manual" today; extension point for "wearable" etc. later.
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="stress_logs")

    __table_args__ = (
        Index("ix_stress_logs_user_id_recorded_at", "user_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<StressLog user_id={self.user_id} level={self.level} at={self.recorded_at}>"
