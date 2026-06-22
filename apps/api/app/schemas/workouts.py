"""Schemas for the workouts endpoints.

Covers:
  WorkoutTemplate  CRUD
  Workout          start / complete / get / list / delete
  WorkoutExercise  add / update / remove within a logged workout
  WorkoutSet       log / update / delete individual sets
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

# ── WorkoutTemplate ───────────────────────────────────────────────────────────


class TemplateExerciseIn(BaseModel):
    """An exercise slot inside a template create/update payload."""

    exercise_id: uuid.UUID
    order_index: int = Field(default=0, ge=0)
    default_sets: int | None = Field(default=None, ge=1, le=100)
    default_reps: int | None = Field(default=None, ge=1, le=10000)
    default_weight_kg: float | None = Field(default=None, ge=0)
    default_duration_seconds: int | None = Field(default=None, ge=1)
    default_distance_meters: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class TemplateExerciseResponse(BaseModel):
    """One exercise row returned inside a template response."""

    id: uuid.UUID
    exercise_id: uuid.UUID
    order_index: int
    default_sets: int | None
    default_reps: int | None
    default_weight_kg: float | None
    default_duration_seconds: int | None
    default_distance_meters: float | None
    notes: str | None

    # Denormalised exercise fields for convenient display
    exercise_name: str
    exercise_category: str | None

    model_config = {"from_attributes": True}


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    exercises: list[TemplateExerciseIn] = Field(default_factory=list)


class UpdateTemplateRequest(BaseModel):
    """All fields optional — send only what changed.

    If `exercises` is provided it fully replaces the existing exercise list.
    Omit `exercises` to leave the list unchanged.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    exercises: list[TemplateExerciseIn] | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    exercises: list[TemplateExerciseResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
    total: int


# ── WorkoutSet ────────────────────────────────────────────────────────────────


class LogSetRequest(BaseModel):
    """Log a single set for an exercise already in the workout."""

    set_number: int = Field(ge=1)
    reps: int | None = Field(default=None, ge=0, le=10000)
    weight_kg: float | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    rpe: float | None = Field(default=None, ge=1, le=10)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def at_least_one_metric(self) -> LogSetRequest:
        has_metric = any(
            v is not None
            for v in (self.reps, self.weight_kg, self.duration_seconds, self.distance_meters)
        )
        if not has_metric:
            raise ValueError(
                "At least one metric (reps, weight_kg, duration_seconds, "
                "distance_meters) must be provided."
            )
        return self


class UpdateSetRequest(BaseModel):
    """Partial update — send only changed fields."""

    reps: int | None = Field(default=None, ge=0, le=10000)
    weight_kg: float | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    rpe: float | None = Field(default=None, ge=1, le=10)
    completed_at: datetime | None = None


class SetResponse(BaseModel):
    id: uuid.UUID
    set_number: int
    reps: int | None
    weight_kg: float | None
    duration_seconds: int | None
    distance_meters: float | None
    rpe: float | None
    is_pr: bool
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ── WorkoutExercise ───────────────────────────────────────────────────────────


class AddExerciseRequest(BaseModel):
    """Add an exercise to an in-progress workout."""

    exercise_id: uuid.UUID
    order_index: int = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class WorkoutExerciseResponse(BaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    order_index: int
    notes: str | None
    exercise_name: str
    exercise_category: str | None
    sets: list[SetResponse]

    model_config = {"from_attributes": True}


# ── Workout ───────────────────────────────────────────────────────────────────


class StartWorkoutRequest(BaseModel):
    """Start a new workout session.

    Supply template_id to pre-populate exercises from that template.
    Omit template_id for an ad-hoc workout.
    name defaults to the template name (if used) or "Workout".
    """

    template_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=120)
    started_at: datetime | None = None  # defaults to server UTC now if omitted
    notes: str | None = Field(default=None, max_length=2000)


class CompleteWorkoutRequest(BaseModel):
    """Mark a workout as completed."""

    completed_at: datetime | None = None  # defaults to server UTC now if omitted
    notes: str | None = Field(default=None, max_length=2000)


class UpdateWorkoutRequest(BaseModel):
    """Lightweight metadata update (name / notes only)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = None


class WorkoutResponse(BaseModel):
    id: uuid.UUID
    name: str
    notes: str | None
    template_id: uuid.UUID | None
    template_name: str | None  # denormalised for display
    started_at: datetime
    completed_at: datetime | None
    total_volume_kg: float | None
    duration_seconds: int | None  # computed: completed_at - started_at
    exercises: list[WorkoutExerciseResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkoutSummary(BaseModel):
    """Lightweight row for list views — no nested exercises."""

    id: uuid.UUID
    name: str
    template_id: uuid.UUID | None
    template_name: str | None
    started_at: datetime
    completed_at: datetime | None
    total_volume_kg: float | None
    duration_seconds: int | None
    exercise_count: int
    set_count: int

    model_config = {"from_attributes": True}


class WorkoutListResponse(BaseModel):
    workouts: list[WorkoutSummary]
    total: int
    page: int
    page_size: int
