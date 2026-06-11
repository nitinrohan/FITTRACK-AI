"""Schemas for the goals endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

GoalType = Literal[
    "weight_loss",
    "weight_gain",
    "body_fat",
    "strength",
    "endurance",
    "habit",
    "custom",
]

GoalStatus = Literal["active", "completed", "paused", "cancelled"]


# ── Requests ──────────────────────────────────────────────────────────────────

class CreateGoalRequest(BaseModel):
    goal_type: GoalType
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    # Numeric tracking — all optional.  If any numeric field is provided,
    # target_unit should also be provided (validated below).
    starting_value: float | None = Field(default=None, ge=0)
    target_value: float | None = Field(default=None, ge=0)
    current_value: float | None = Field(default=None, ge=0)
    target_unit: str | None = Field(default=None, max_length=32)

    deadline: date | None = None

    @model_validator(mode="after")
    def numeric_fields_consistent(self) -> CreateGoalRequest:
        has_value = any(
            v is not None
            for v in (self.starting_value, self.target_value, self.current_value)
        )
        if has_value and not self.target_unit:
            raise ValueError(
                "target_unit is required when any numeric value is provided"
            )
        return self


class UpdateGoalRequest(BaseModel):
    """All fields optional — send only what changed."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    goal_type: GoalType | None = None
    starting_value: float | None = Field(default=None, ge=0)
    target_value: float | None = Field(default=None, ge=0)
    current_value: float | None = Field(default=None, ge=0)
    target_unit: str | None = Field(default=None, max_length=32)
    deadline: date | None = None
    status: GoalStatus | None = None


# ── Response ──────────────────────────────────────────────────────────────────

class GoalResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    goal_type: str
    title: str
    description: str | None
    starting_value: float | None
    target_value: float | None
    current_value: float | None
    target_unit: str | None
    deadline: date | None
    status: str
    completed_at: datetime | None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    # Computed — not stored in DB.
    progress_pct: float | None = None


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
