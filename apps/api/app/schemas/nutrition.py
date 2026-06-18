"""Schemas for the nutrition endpoints.

Covers:
  Food          CRUD (create custom food, list/search, get, update, delete)
  FoodLog       log a food entry, list by date, update, delete
  WaterLog      log water, list by date, update, delete
  DailyNutrition  aggregated daily summary (totals + per-meal breakdown)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Meal type ─────────────────────────────────────────────────────────────────

MealType = Literal["breakfast", "lunch", "dinner", "snack", "other"]

MEAL_TYPE_ORDER: list[MealType] = ["breakfast", "lunch", "dinner", "snack", "other"]


# ── Food ──────────────────────────────────────────────────────────────────────


class CreateFoodRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    # All macros per 100 g
    calories_per_100g: float = Field(ge=0)
    protein_per_100g: float = Field(default=0.0, ge=0)
    carbs_per_100g: float = Field(default=0.0, ge=0)
    fat_per_100g: float = Field(default=0.0, ge=0)
    fiber_per_100g: float | None = Field(default=None, ge=0)
    sugar_per_100g: float | None = Field(default=None, ge=0)
    sodium_per_100g: float | None = Field(default=None, ge=0)

    serving_size_g: float | None = Field(default=None, gt=0)
    serving_unit: str | None = Field(default=None, max_length=50)


class UpdateFoodRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = None
    description: str | None = None
    calories_per_100g: float | None = Field(default=None, ge=0)
    protein_per_100g: float | None = Field(default=None, ge=0)
    carbs_per_100g: float | None = Field(default=None, ge=0)
    fat_per_100g: float | None = Field(default=None, ge=0)
    fiber_per_100g: float | None = Field(default=None, ge=0)
    sugar_per_100g: float | None = Field(default=None, ge=0)
    sodium_per_100g: float | None = Field(default=None, ge=0)
    serving_size_g: float | None = Field(default=None, gt=0)
    serving_unit: str | None = None


class FoodResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    brand: str | None
    description: str | None
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: float | None
    sugar_per_100g: float | None
    sodium_per_100g: float | None
    serving_size_g: float | None
    serving_unit: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FoodListResponse(BaseModel):
    foods: list[FoodResponse]
    total: int
    page: int
    page_size: int


# ── FoodLog ───────────────────────────────────────────────────────────────────


class LogFoodRequest(BaseModel):
    food_id: uuid.UUID
    logged_date: date
    meal_type: MealType = "other"
    quantity_g: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)


class UpdateFoodLogRequest(BaseModel):
    meal_type: MealType | None = None
    quantity_g: float | None = Field(default=None, gt=0)
    notes: str | None = None


class FoodLogResponse(BaseModel):
    id: uuid.UUID
    food_id: uuid.UUID
    logged_date: date
    meal_type: str
    quantity_g: float
    notes: str | None

    # Computed macros for this log entry (scaled from per-100g values)
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None

    # Denormalised food info for display
    food_name: str
    food_brand: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── WaterLog ──────────────────────────────────────────────────────────────────


class LogWaterRequest(BaseModel):
    logged_date: date
    amount_ml: int = Field(gt=0, le=10_000)
    notes: str | None = Field(default=None, max_length=500)


class UpdateWaterLogRequest(BaseModel):
    amount_ml: int | None = Field(default=None, gt=0, le=10_000)
    notes: str | None = None


class WaterLogResponse(BaseModel):
    id: uuid.UUID
    logged_date: date
    amount_ml: int
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Daily summary ─────────────────────────────────────────────────────────────


class MacroTotals(BaseModel):
    """Aggregated macro totals for a meal slot or the whole day."""

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


class MealSection(BaseModel):
    meal_type: str
    entries: list[FoodLogResponse]
    totals: MacroTotals


class DailyNutritionResponse(BaseModel):
    """Full nutrition picture for a single date."""

    date: date
    meals: list[MealSection]  # one per meal_type that has at least one entry
    day_totals: MacroTotals
    water_logs: list[WaterLogResponse]
    water_total_ml: int
