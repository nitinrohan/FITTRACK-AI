"""Schemas for the recipes feature.

A recipe is a named, user-owned combination of foods + exact quantities
that can be re-logged later - optionally scaled - without re-describing it
or re-running AI estimation. Macro figures on items/totals are always
computed deterministically from the underlying Food's per-100g values,
never stored redundantly on the recipe itself (a Food's macros can be
edited later; the recipe should reflect current values, same as FoodLog).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.nutrition import FoodLogResponse, MacroTotals, MealType

# ── Recipe items ──────────────────────────────────────────────────────────────


class RecipeItemInput(BaseModel):
    food_id: uuid.UUID
    quantity_g: float = Field(gt=0)


class RecipeItemResponse(BaseModel):
    food_id: uuid.UUID
    food_name: str
    food_brand: str | None
    quantity_g: float

    # Computed macros for this item at its saved quantity.
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None


# ── Recipe CRUD ───────────────────────────────────────────────────────────────


class CreateRecipeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    items: list[RecipeItemInput] = Field(min_length=1, max_length=50)


class UpdateRecipeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    # When provided, replaces the entire item list.
    items: list[RecipeItemInput] | None = Field(default=None, min_length=1, max_length=50)


class RecipeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    items: list[RecipeItemResponse]
    totals: MacroTotals
    created_at: datetime
    updated_at: datetime


class RecipeListResponse(BaseModel):
    recipes: list[RecipeResponse]
    total: int
    page: int
    page_size: int


# ── Logging a recipe ──────────────────────────────────────────────────────────


class LogRecipeRequest(BaseModel):
    logged_date: date
    meal_type: MealType = "other"
    # 1.0 = log exactly as saved. E.g. 0.5 logs half the saved quantities.
    scale_factor: float = Field(default=1.0, gt=0, le=20)


class LogRecipeResponse(BaseModel):
    entries: list[FoodLogResponse]
    totals: MacroTotals
