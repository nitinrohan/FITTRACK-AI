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
