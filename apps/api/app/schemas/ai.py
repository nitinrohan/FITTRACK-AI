"""AI feature schemas.

WeeklySummaryRequest  — parameters the client can send (currently empty;
                         reserved for future options like preferred language).
WeeklySummaryResponse — structured response returned to the frontend.

The frontend must show the summary to the user before any data changes.
AI never mutates application data directly.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class WeeklySummaryRequest(BaseModel):
    """Optional parameters for the weekly summary.

    Reserved for future use (e.g. preferred_language, focus_area).
    """

    pass


class WeeklyDataSnapshot(BaseModel):
    """Read-only snapshot of the data used to generate the summary.

    Returned alongside the AI text so the frontend can display it as
    context and the user can verify what the AI actually saw.
    """

    week_start: date
    week_end: date
    weight_entries: int
    workouts_completed: int
    food_log_days: int  # distinct days with at least one food log entry
    water_log_days: int
    active_goals: int


class WeeklySummaryResponse(BaseModel):
    """Structured weekly summary from the AI."""

    model_config = ConfigDict(protected_namespaces=())

    # ── Content ───────────────────────────────────────────────────────────
    highlights: list[str] = Field(
        default_factory=list,
        description="2-4 specific observations about the user's week.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="1-3 concrete, manageable suggestions for next week.",
    )
    encouragement: str = Field(
        default="",
        description="One warm, motivating sentence.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    data_snapshot: WeeklyDataSnapshot
    ai_available: bool
    provider: str | None = None  # "anthropic" | "openai" | None
    model_id: str | None = None
    prompt_version: str | None = None
    log_id: str | None = None  # AIUsageLog.id for future accept/dismiss


class AcceptSummaryRequest(BaseModel):
    """Record the user's decision about a generated summary."""

    log_id: str
    accepted: bool


# ── Macro estimation (nutrition AI) ───────────────────────────────────────────


class MacroEstimateRequest(BaseModel):
    """A free-text description of food/drink to estimate macros for."""

    description: str = Field(min_length=1, max_length=280)


class MacroPortion(BaseModel):
    """Macros for the described portion (computed deterministically from the
    per-100g figures and the estimated serving size — not by the model)."""

    grams: float
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MacroEstimateResponse(BaseModel):
    """An AI macro estimate for a food description.

    These are ESTIMATES, never exact values. The frontend must show this as a
    preview the user can edit, and only the user's confirmed values are saved.
    Per-100g figures map directly onto CreateFoodRequest for saving.
    """

    model_config = ConfigDict(protected_namespaces=())

    ai_available: bool
    # Estimate (present only when ai_available is True)
    name: str | None = None
    serving_size_g: float | None = None
    serving_unit: str | None = None
    calories_per_100g: float | None = None
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    portion: MacroPortion | None = None
    confidence: str | None = None  # "low" | "medium" | "high"

    # Always present
    is_estimate: bool = True
    disclaimer: str = "AI estimate — review and edit before saving."
    message: str | None = None  # set when ai_available is False

    # Metadata
    provider: str | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    log_id: str | None = None
