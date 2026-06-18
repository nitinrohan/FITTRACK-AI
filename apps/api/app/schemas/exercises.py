"""Pydantic schemas for the exercise library.

ExerciseCategory and Equipment are string enums validated at the API boundary.
muscle_groups is exposed as list[str] in responses; stored as CSV internally.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ExerciseCategory(str, Enum):
    strength = "strength"
    cardio = "cardio"
    flexibility = "flexibility"
    balance = "balance"
    sports = "sports"
    other = "other"


class Equipment(str, Enum):
    barbell = "barbell"
    dumbbell = "dumbbell"
    bodyweight = "bodyweight"
    machine = "machine"
    cable = "cable"
    kettlebell = "kettlebell"
    resistance_band = "resistance_band"
    ez_bar = "ez_bar"
    plate = "plate"
    other = "other"
    none = "none"


# ── Requests ─────────────────────────────────────────────────────────────────

class CreateExerciseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    instructions: str | None = Field(default=None, max_length=5000)
    category: ExerciseCategory = ExerciseCategory.strength
    muscle_groups: list[str] = Field(default_factory=list, max_length=20)
    equipment: Equipment = Equipment.none

    @field_validator("muscle_groups", mode="before")
    @classmethod
    def validate_muscle_groups(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        if isinstance(v, list | tuple):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class UpdateExerciseRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    instructions: str | None = None
    category: ExerciseCategory | None = None
    muscle_groups: list[str] | None = None
    equipment: Equipment | None = None

    @field_validator("muscle_groups", mode="before")
    @classmethod
    def validate_muscle_groups(cls, v: object) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        if isinstance(v, list | tuple):
            return [str(item).strip() for item in v if str(item).strip()]
        return []


# ── Responses ─────────────────────────────────────────────────────────────────

class ExerciseResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    instructions: str | None
    category: str
    muscle_groups: list[str]
    equipment: str
    is_system: bool
    user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_groups(cls, obj: object) -> ExerciseResponse:
        """Build response, converting CSV muscle_groups to list."""
        from app.models.exercise import Exercise as ExerciseModel

        e: ExerciseModel = obj  # type: ignore[assignment]
        raw = e.muscle_groups or ""
        groups = [m.strip() for m in raw.split(",") if m.strip()]
        return cls(
            id=e.id,
            name=e.name,
            description=e.description,
            instructions=e.instructions,
            category=e.category,
            muscle_groups=groups,
            equipment=e.equipment,
            is_system=e.is_system,
            user_id=e.user_id,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class ExerciseListResponse(BaseModel):
    items: list[ExerciseResponse]
    total: int
    page: int
    page_size: int
    pages: int
