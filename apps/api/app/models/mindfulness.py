"""Mindfulness ORM models - a curated session library and minute logs.

MindfulnessSession is content (system-provided rows plus optional user-created
ones), modelled like the exercise library: system rows have user_id = NULL and
is_system = True. external_url is an optional link to a track/playlist; there is
no embedded audio in the MVP.

MindfulnessLog records mindful minutes, optionally tied to a session. Daily
totals and the mindful-day streak are derived at query time, never stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class MindfulnessSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A mindfulness/breathing session in the library."""

    __tablename__ = "mindfulness_sessions"

    # NULL for system library rows; set for user-created custom sessions.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # "breathing" | "meditation" | "sleep" | "focus"
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="meditation")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional external link (e.g. a Spotify/YouTube track). May be empty.
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped[User | None] = relationship("User", back_populates="mindfulness_sessions")

    __table_args__ = (Index("ix_mindfulness_sessions_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<MindfulnessSession title={self.title!r} category={self.category}>"


class MindfulnessLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A logged stretch of mindful minutes."""

    __tablename__ = "mindfulness_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to the session practised. SET NULL so deleting a custom
    # session does not erase the user's minute history.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mindfulness_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="mindfulness_logs")
    session: Mapped[MindfulnessSession | None] = relationship("MindfulnessSession")

    __table_args__ = (
        Index("ix_mindfulness_logs_user_id_recorded_at", "user_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<MindfulnessLog user_id={self.user_id} minutes={self.duration_minutes}>"
