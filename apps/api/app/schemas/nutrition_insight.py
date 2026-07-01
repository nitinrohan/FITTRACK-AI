"""Schemas for the daily nutrition insight feature.

Read-only: this never changes any data. It compares a day's logged totals
against the user's own configured targets (never invented ones) and asks the
AI to explain the picture in plain language plus suggest manageable next
steps for the remaining meals. All numeric comparisons are computed by
deterministic app code - the model only writes the narrative around numbers
it is given.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.nutrition import MacroTotals
from app.schemas.nutrition_target import NutritionTargetResponse


class MacroComparison(BaseModel):
    """Deterministic comparison of one metric against the user's own target."""

    metric: str  # "calories" | "protein" | "carbs" | "fat" | "fiber"
    label: str
    unit: str
    current: float
    target: float | None
    percent_of_target: float | None  # null when no target is set for this metric
    remaining: float | None  # target - current; can be negative if over target


class DailyInsightResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    date: date
    day_totals: MacroTotals
    targets: NutritionTargetResponse
    comparisons: list[MacroComparison]
    meals_logged: list[str]
    meals_remaining: list[str]

    ai_available: bool
    highlights: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    encouragement: str = ""

    disclaimer: str = (
        "AI-generated observations based on your own logged data - "
        "an estimate, not medical or dietetic advice."
    )
    message: str | None = None  # set when ai_available is False

    provider: str | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    log_id: str | None = None
    generated_at: datetime | None = None
