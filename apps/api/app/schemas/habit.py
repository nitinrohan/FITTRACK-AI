"""Schemas for the habit endpoints — /api/v1/habits.

Validation rules enforced here (schema level):
  - name: 1-100 chars (trimmed, non-empty)
  - description / color length bounds
  - target_days_per_week: 1-7

Derived values (current_streak, longest_streak, weekly_adherence_pct, …) are
computed in the service layer and are clearly labelled as derived; they are
never accepted as input.

Note on Optional vs X | None:
  The completion schemas have a field named `date` which shadows the imported
  `date` type in the class body.  We use `from __future__ import annotations`
  (lazy string annotations) plus `Optional[X]` to avoid that shadowing issue,
  matching the convention used by the wellness schemas.
"""
# ruff: noqa: UP007

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# ── Habit requests ──────────────────────────────────────────────────────────────


class CreateHabitRequest(BaseModel):
    """Request body for POST /api/v1/habits."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None, max_length=20)
    target_days_per_week: int = Field(default=7, ge=1, le=7)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Habit name cannot be blank.")
        return trimmed

    @field_validator("description", "color")
    @classmethod
    def blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class UpdateHabitRequest(BaseModel):
    """Request body for PATCH /api/v1/habits/{id} (partial update)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None, max_length=20)
    target_days_per_week: Optional[int] = Field(default=None, ge=1, le=7)
    is_archived: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Habit name cannot be blank.")
        return trimmed


# ── Completion requests ─────────────────────────────────────────────────────────


class MarkCompletionRequest(BaseModel):
    """Request body for POST /api/v1/habits/{id}/completions.

    `date` defaults to today (in the user's local calendar date as sent by the
    client) when omitted.
    """

    date: Optional[date_type] = None


# ── Responses ───────────────────────────────────────────────────────────────────


class HabitResponse(BaseModel):
    """A habit plus its derived stats.

    `current_streak`, `longest_streak`, `completions_this_week` and
    `weekly_adherence_pct` are computed from completion history; they are
    derived figures, not stored values.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str]
    color: Optional[str]
    target_days_per_week: int
    is_archived: bool
    archived_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Derived stats
    completed_today: bool
    current_streak: int
    longest_streak: int
    completions_this_week: int
    weekly_adherence_pct: int

    model_config = {"from_attributes": True}


class HabitListResponse(BaseModel):
    """Paginated list of habits."""

    items: list[HabitResponse]
    total: int
    page: int
    page_size: int


class CompletionResponse(BaseModel):
    """A single completion record."""

    id: uuid.UUID
    habit_id: uuid.UUID
    date: date_type
    created_at: datetime

    model_config = {"from_attributes": True}


class HabitCompletionsResponse(BaseModel):
    """A habit's completion history (for a calendar / history view)."""

    habit_id: uuid.UUID
    items: list[CompletionResponse]
