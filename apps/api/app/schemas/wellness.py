"""Schemas for sleep, steps, and wellness endpoints.

Unit conventions:
  sleep duration  - minutes (integer)
  distance        - metres  (float); frontend converts to km / miles
  ratings         - integers 1-5 (validated here and in service)

Validation rules enforced here (schema level):
  - quality, mood, energy, stress must be 1-5 when provided
  - steps must be >= 0
  - duration_minutes must be > 0 when provided
  - active_minutes must be >= 0 when provided

Service-level validation:
  - SleepLog: must supply duration_minutes OR (bedtime AND wake_time)
  - WellnessLog: at least one of mood / energy / stress must be provided

Note on Optional vs X | None:
  Fields named 'date', 'steps' etc. shadow built-in type names in the class
  body.  Python 3.10 bytecode evaluates the default value BEFORE the annotation,
  so `date: Optional[date] = None` would resolve `date` to None at annotation time.
  We use `from __future__ import annotations` (lazy string annotations) and
  `Optional[X]` to avoid both that shadowing issue and Pydantic's backport
  evaluator rejecting the `X | Y` union syntax.
"""
# ruff: noqa: UP007

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Shared validators ─────────────────────────────────────────────────────────


def _validate_rating(v: Optional[int], field_name: str) -> int | None:
    if v is not None and not (1 <= v <= 5):
        raise ValueError(f"{field_name} must be between 1 and 5.")
    return v


# ── Sleep ─────────────────────────────────────────────────────────────────────


class LogSleepRequest(BaseModel):
    """Request body for POST /api/v1/sleep."""

    date: date
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    quality: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: Optional[int]) -> int | None:
        return _validate_rating(v, "quality")

    @model_validator(mode="after")
    def require_duration_or_times(self) -> LogSleepRequest:
        has_duration = self.duration_minutes is not None
        has_times = self.bedtime is not None and self.wake_time is not None
        if not has_duration and not has_times:
            raise ValueError("Provide either duration_minutes or both bedtime and wake_time.")
        if self.bedtime and self.wake_time and self.wake_time <= self.bedtime:
            raise ValueError("wake_time must be after bedtime.")
        return self


class UpdateSleepRequest(BaseModel):
    """Request body for PATCH /api/v1/sleep/{id}."""

    date: Optional[date] = None
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    quality: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: Optional[int]) -> int | None:
        return _validate_rating(v, "quality")


class SleepLogResponse(BaseModel):
    """Response for a single sleep log entry."""

    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    bedtime: Optional[datetime]
    wake_time: Optional[datetime]
    duration_minutes: Optional[int]
    quality: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SleepListResponse(BaseModel):
    """Paginated list of sleep log entries."""

    items: list[SleepLogResponse]
    total: int
    page: int
    page_size: int


# ── Steps ─────────────────────────────────────────────────────────────────────


class LogStepsRequest(BaseModel):
    """Request body for POST /api/v1/steps."""

    date: date
    steps: int = Field(ge=0, le=100_000)
    active_minutes: Optional[int] = Field(default=None, ge=0, le=1440)
    distance_m: Optional[float] = Field(default=None, ge=0)
    calories_burned: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


class UpdateStepsRequest(BaseModel):
    """Request body for PATCH /api/v1/steps/{id}."""

    date: Optional[date] = None
    steps: Optional[int] = Field(default=None, ge=0, le=100_000)
    active_minutes: Optional[int] = Field(default=None, ge=0, le=1440)
    distance_m: Optional[float] = Field(default=None, ge=0)
    calories_burned: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


class StepsLogResponse(BaseModel):
    """Response for a single daily-steps entry."""

    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    steps: int
    active_minutes: Optional[int]
    distance_m: Optional[float]
    calories_burned: Optional[float]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepsListResponse(BaseModel):
    """Paginated list of daily-steps entries."""

    items: list[StepsLogResponse]
    total: int
    page: int
    page_size: int


# ── Wellness ──────────────────────────────────────────────────────────────────


class LogWellnessRequest(BaseModel):
    """Request body for POST /api/v1/wellness."""

    date: date
    mood: Optional[int] = None
    energy: Optional[int] = None
    stress: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("mood", "energy", "stress")
    @classmethod
    def validate_rating(cls, v: Optional[int]) -> int | None:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5.")
        return v

    @model_validator(mode="after")
    def at_least_one_metric(self) -> LogWellnessRequest:
        if self.mood is None and self.energy is None and self.stress is None:
            raise ValueError("Provide at least one of mood, energy, or stress.")
        return self


class UpdateWellnessRequest(BaseModel):
    """Request body for PATCH /api/v1/wellness/{id}."""

    date: Optional[date] = None
    mood: Optional[int] = None
    energy: Optional[int] = None
    stress: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("mood", "energy", "stress")
    @classmethod
    def validate_rating(cls, v: Optional[int]) -> int | None:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5.")
        return v


class WellnessLogResponse(BaseModel):
    """Response for a single wellness check-in entry."""

    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    mood: Optional[int]
    energy: Optional[int]
    stress: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WellnessListResponse(BaseModel):
    """Paginated list of wellness check-in entries."""

    items: list[WellnessLogResponse]
    total: int
    page: int
    page_size: int


# ── Daily snapshot ────────────────────────────────────────────────────────────


class DailyWellnessSnapshot(BaseModel):
    """Combined daily wellness snapshot for the given date.

    Returns the latest entry per domain for the requested date.
    Fields are null when no entry exists for that date.
    water_total_ml comes from the nutrition domain (water_logs table).
    """

    date: date
    sleep: Optional[SleepLogResponse] = None
    steps: Optional[StepsLogResponse] = None
    wellness: Optional[WellnessLogResponse] = None
    water_total_ml: int = 0
