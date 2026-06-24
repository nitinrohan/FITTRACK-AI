"""User, UserProfile, and UserPreference ORM models.

Design notes:
- User stores only auth-critical fields. Personal and preference data lives in
  separate tables so they can evolve independently and the User table stays slim.
- height_cm stored as a float in centimetres (canonical unit).
- date_of_birth stored as a plain date (no time component needed).
- unit_system and language are stored as strings so new values can be added
  without a migration; validation happens at the API boundary (Pydantic).
- All tables use UUIDPrimaryKeyMixin + TimestampMixin from base.py.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.goal import Goal
    from app.models.habit import Habit
    from app.models.measurement import BodyMeasurement
    from app.models.nutrition import Food, FoodLog, WaterLog
    from app.models.weight_entry import WeightEntry
    from app.models.wellness import DailySteps, SleepLog, WellnessLog
    from app.models.workout import Workout, WorkoutTemplate


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Core authentication record. One row per registered account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Account state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Future role-based access control extension point.
    # "user" is the only role used in the MVP.
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)

    # Relationships (loaded lazily by default)
    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    preferences: Mapped[UserPreference | None] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    goals: Mapped[list[Goal]] = relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    weight_entries: Mapped[list[WeightEntry]] = relationship(
        "WeightEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    exercises: Mapped[list[Exercise]] = relationship(
        "Exercise",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    workout_templates: Mapped[list[WorkoutTemplate]] = relationship(
        "WorkoutTemplate",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    workouts: Mapped[list[Workout]] = relationship(
        "Workout",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    foods: Mapped[list[Food]] = relationship(
        "Food",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    food_logs: Mapped[list[FoodLog]] = relationship(
        "FoodLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    water_logs: Mapped[list[WaterLog]] = relationship(
        "WaterLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    body_measurements: Mapped[list[BodyMeasurement]] = relationship(
        "BodyMeasurement",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    sleep_logs: Mapped[list[SleepLog]] = relationship(
        "SleepLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    daily_steps: Mapped[list[DailySteps]] = relationship(
        "DailySteps",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    wellness_logs: Mapped[list[WellnessLog]] = relationship(
        "WellnessLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    habits: Mapped[list[Habit]] = relationship(
        "Habit",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Personal profile information — separate from auth credentials.

    All fields are optional so users can complete them progressively
    during onboarding without being forced to provide everything at
    registration.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Display
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Physical — stored in canonical units (cm, no weight here; weight is logged separately)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float(precision=1), nullable=True)

    # Demographic — optional, used only for formulas that genuinely require it
    # (e.g. Mifflin-St Jeor BMR). Never used for profiling or targeting.
    # Stored as a free-form string so users can self-describe; see onboarding docs.
    biological_sex: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Fitness context
    experience_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "beginner" | "intermediate" | "advanced"

    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    # ISO 3166-1 alpha-2

    # Onboarding
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_step: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="profile")

    __table_args__ = (Index("ix_user_profiles_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} name={self.display_name!r}>"


class UserPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-configurable application preferences.

    Defaults are applied when the row is created (at registration).
    Each field can be updated independently via PATCH /api/v1/preferences.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Measurement system — affects display only; canonical storage is always SI.
    # "metric" | "imperial"
    unit_system: Mapped[str] = mapped_column(String(20), default="metric", nullable=False)

    # IANA time zone string, e.g. "America/New_York", "Europe/London", "Asia/Tokyo"
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)

    # ISO 639-1 language code, e.g. "en", "es", "fr"
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Display preferences
    first_day_of_week: Mapped[int] = mapped_column(default=1, nullable=False)
    # 0=Sunday, 1=Monday (ISO default)

    # Notification opt-ins (individual channels controlled via NotificationPreference — Phase 7)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # AI features opt-in (required before sending data to an external model)
    ai_features_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="preferences")

    __table_args__ = (Index("ix_user_preferences_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id} units={self.unit_system!r}>"
