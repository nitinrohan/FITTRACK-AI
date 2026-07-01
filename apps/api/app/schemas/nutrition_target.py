"""Schemas for user-configurable daily nutrition targets.

GET returns the user's current targets (any unset field is null - never a
guessed default). PUT replaces the whole set of targets in one call; send
null for a field to clear it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NutritionTargetResponse(BaseModel):
    calorie_target_kcal: float | None
    protein_target_g: float | None
    carbs_target_g: float | None
    fat_target_g: float | None
    fiber_target_g: float | None
    is_set: bool  # True if at least one target has been configured
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class UpdateNutritionTargetRequest(BaseModel):
    calorie_target_kcal: float | None = Field(default=None, ge=0, le=20_000)
    protein_target_g: float | None = Field(default=None, ge=0, le=1000)
    carbs_target_g: float | None = Field(default=None, ge=0, le=2000)
    fat_target_g: float | None = Field(default=None, ge=0, le=1000)
    fiber_target_g: float | None = Field(default=None, ge=0, le=500)
