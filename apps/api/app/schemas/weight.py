"""Schemas for the weight-tracking endpoints.

Unit strategy:
  - The API always accepts and returns kg.
  - display_unit is stored alongside the value so the frontend can show
    the original unit without visible rounding on round-trip.
  - BMI is computed server-side and included in responses when height is
    available in the user's profile.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ── Requests ──────────────────────────────────────────────────────────────────


class LogWeightRequest(BaseModel):
    """Log a weight measurement.

    Accepts either kg or lbs via display_unit; the service converts to kg
    for storage.  This keeps the conversion logic out of the frontend.
    """

    weight: float = Field(gt=0, le=700, description="Weight value in the chosen unit")
    display_unit: Literal["kg", "lbs"] = Field(default="kg")
    body_fat_pct: float | None = Field(
        default=None, ge=0, le=100, description="Body fat percentage (0-100)"
    )
    muscle_mass_kg: float | None = Field(
        default=None, ge=0, le=300, description="Muscle mass in kg"
    )
    measured_at: date = Field(
        default_factory=date.today,
        description="Measurement date (defaults to today)",
    )
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def muscle_mass_in_range(self) -> LogWeightRequest:
        """Muscle mass must be less than weight."""
        if self.muscle_mass_kg is not None:
            # Convert weight to kg for comparison
            weight_kg = self.weight * 0.453592 if self.display_unit == "lbs" else self.weight
            if self.muscle_mass_kg >= weight_kg:
                raise ValueError("muscle_mass_kg must be less than weight in kg")
        return self


class UpdateWeightEntryRequest(BaseModel):
    """Partial update — send only changed fields."""

    weight: float | None = Field(default=None, gt=0, le=700)
    display_unit: Literal["kg", "lbs"] | None = None
    body_fat_pct: float | None = Field(default=None, ge=0, le=100)
    muscle_mass_kg: float | None = Field(default=None, ge=0, le=300)
    measured_at: date | None = None
    notes: str | None = Field(default=None, max_length=500)


# ── Response ──────────────────────────────────────────────────────────────────


class WeightEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    weight_kg: float
    display_unit: str
    body_fat_pct: float | None
    muscle_mass_kg: float | None
    measured_at: date
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Computed — not stored
    weight_lbs: float | None = None
    bmi: float | None = None


class WeightListStats(BaseModel):
    """Summary statistics for a list of weight entries."""

    count: int
    latest_kg: float | None
    earliest_kg: float | None
    change_kg: float | None  # latest - earliest (negative = lost weight)
    min_kg: float | None
    max_kg: float | None
    # 7-day moving average of the most-recent 7 entries
    moving_avg_7d_kg: float | None


class WeightListResponse(BaseModel):
    entries: list[WeightEntryResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    stats: WeightListStats
