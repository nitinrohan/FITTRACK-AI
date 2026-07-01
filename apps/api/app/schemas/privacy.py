"""Pydantic schemas for the privacy endpoints (export, summary, deletion)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PrivacySummary(BaseModel):
    """Per-category count of the records a user owns.

    Lets the privacy page show the user exactly what an export or an account
    deletion covers before they commit to either action.
    """

    model_config = ConfigDict(from_attributes=True)

    goals: int = 0
    weight_entries: int = 0
    body_measurements: int = 0
    custom_exercises: int = 0
    workout_templates: int = 0
    workouts: int = 0
    custom_foods: int = 0
    food_logs: int = 0
    water_logs: int = 0
    sleep_logs: int = 0
    daily_steps: int = 0
    wellness_logs: int = 0
    habits: int = 0
    stress_logs: int = 0
    mindfulness_logs: int = 0


class DataExport(BaseModel):
    """Wrapper for a full personal-data export.

    The export groups records by domain. Its shape is intentionally open
    (``dict[str, Any]`` payload) because it mirrors the database and grows with
    the schema; ``export_metadata.format_version`` signals the structure.
    """

    model_config = ConfigDict(extra="allow")

    export_metadata: dict[str, Any]


class AccountDeleteRequest(BaseModel):
    """Body for DELETE /api/v1/privacy/account.

    The password is re-verified server-side so a stolen session cookie alone
    cannot destroy an account.
    """

    password: str = Field(min_length=1, description="Current account password.")


class AccountDeletedResponse(BaseModel):
    """Confirmation returned after a successful account deletion."""

    status: str = "deleted"
    message: str = "Your account and all associated data have been permanently deleted."
