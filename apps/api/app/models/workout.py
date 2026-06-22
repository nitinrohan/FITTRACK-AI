"""Workout ORM models.

Domain model for workout templates and logged workout sessions.

Hierarchy:
  WorkoutTemplate
    └─ WorkoutTemplateExercise  (ordered exercises in a template)

  Workout  (a logged session — may start from a template or be ad-hoc)
    └─ WorkoutExercise  (exercises performed in the session)
         └─ WorkoutSet  (individual sets: reps, weight, duration, distance)

Design notes:
- All weights stored in kg, distances in metres, durations in seconds (canonical units).
- WorkoutSet.is_pr is set by the service layer when a new personal-record is detected
  for that exercise+metric combination for the user.
- Workout.total_volume_kg is computed at completion time:
  sum(weight_kg * reps) across all sets where both values are present.
- completed_at=None means the workout is still in progress.
- template_id on Workout is nullable: ad-hoc workouts have no template.
- order_index on WorkoutTemplateExercise and WorkoutExercise controls display order.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.user import User


# ── Workout Template ───────────────────────────────────────────────────────────


class WorkoutTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reusable blueprint for a workout session.

    Users create templates once and then start workouts from them.
    System templates (is_system=True, user_id=None) may be seeded as
    starter plans — currently unused in the MVP but reserved for the future.
    """

    __tablename__ = "workout_templates"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # True for built-in system templates; False for user-created templates.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped[User | None] = relationship("User", back_populates="workout_templates")
    template_exercises: Mapped[list[WorkoutTemplateExercise]] = relationship(
        "WorkoutTemplateExercise",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="WorkoutTemplateExercise.order_index",
    )
    workouts: Mapped[list[Workout]] = relationship(
        "Workout",
        back_populates="template",
    )

    __table_args__ = (Index("ix_workout_templates_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<WorkoutTemplate id={self.id} name={self.name!r}>"


class WorkoutTemplateExercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An exercise slot inside a WorkoutTemplate, with optional defaults."""

    __tablename__ = "workout_template_exercises"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Display order within the template (0-based)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional defaults — pre-fill the logging form but the user can override
    default_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    template: Mapped[WorkoutTemplate] = relationship(
        "WorkoutTemplate", back_populates="template_exercises"
    )
    exercise: Mapped[Exercise] = relationship("Exercise")

    def __repr__(self) -> str:
        return (
            f"<WorkoutTemplateExercise template={self.template_id} "
            f"exercise={self.exercise_id} order={self.order_index}>"
        )


# ── Logged Workout Session ────────────────────────────────────────────────────


class Workout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single logged workout session.

    A workout begins when the user starts it (started_at) and ends when
    they complete it (completed_at).  While in progress, completed_at is
    None.  The application should surface in-progress workouts and offer
    to resume or discard them.
    """

    __tablename__ = "workouts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Null for ad-hoc workouts started without a template
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # UTC timestamps for the actual session
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    # Derived at completion: sum(weight_kg * reps) where both are present
    total_volume_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="workouts")
    template: Mapped[WorkoutTemplate | None] = relationship(
        "WorkoutTemplate", back_populates="workouts"
    )
    exercises: Mapped[list[WorkoutExercise]] = relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )

    __table_args__ = (
        # Common query: list a user's workouts ordered by date
        Index("ix_workouts_user_id_started_at", "user_id", "started_at"),
    )

    def __repr__(self) -> str:
        status = "in-progress" if self.completed_at is None else "completed"
        return f"<Workout id={self.id} name={self.name!r} status={status}>"


class WorkoutExercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An exercise performed within a logged workout session."""

    __tablename__ = "workout_exercises"

    workout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    workout: Mapped[Workout] = relationship("Workout", back_populates="exercises")
    exercise: Mapped[Exercise] = relationship("Exercise")
    sets: Mapped[list[WorkoutSet]] = relationship(
        "WorkoutSet",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )

    def __repr__(self) -> str:
        return (
            f"<WorkoutExercise workout={self.workout_id} "
            f"exercise={self.exercise_id} order={self.order_index}>"
        )


class WorkoutSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single set logged within a WorkoutExercise.

    Metric fields:
    - reps + weight_kg  → strength exercises (bench press, squat, …)
    - duration_seconds  → time-based exercises (plank, rest, …)
    - distance_meters   → cardio exercises (run, row, …)

    Fields are nullable because not every exercise type uses all metrics.
    At least one metric should be present for a meaningful set, but this
    is enforced at the service layer, not the DB layer, to keep the schema
    flexible.

    is_pr is set to True by the service layer when this set establishes a
    new personal record for the user on this exercise+metric combination.
    """

    __tablename__ = "workout_sets"

    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position within the exercise (1-based for display)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Strength metrics
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Time-based metrics
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cardio metrics
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Subjective effort (Rate of Perceived Exertion, 1-10 scale)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Personal record flag set by service layer at log time
    is_pr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # When this set was completed (UTC); defaults to row creation time
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    workout_exercise: Mapped[WorkoutExercise] = relationship(
        "WorkoutExercise", back_populates="sets"
    )

    __table_args__ = (
        # Look up all sets for a workout_exercise in order
        Index(
            "ix_workout_sets_workout_exercise_id_set_number",
            "workout_exercise_id",
            "set_number",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkoutSet we={self.workout_exercise_id} "
            f"set={self.set_number} reps={self.reps} kg={self.weight_kg}>"
        )
