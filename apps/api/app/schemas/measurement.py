"""Schemas for the body measurements endpoints.

Unit strategy:
  - API stores and returns values in centimetres (cm).
  - display_unit hint lets the frontend show values in inches when preferred
    without a separate conversion call.
  - Conversion constant: 1 inch = 2.54 cm.

All measurement fields are optional — users can record only the
measurements they care about.  At least one measurement field must be
non-None on create (validated at the service layer, not here, to keep
the schema simple).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Measurement field set (shared between create / update / response) ─────────

_CM_FIELD = Field(default=None, gt=0, le=300, description="Measurement in centimetres")


class _MeasurementFields(BaseModel):
    """Shared field definitions for circumference measurements (all in cm)."""

    # Trunk
    waist_cm: float | None = _CM_FIELD
    chest_cm: float | None = _CM_FIELD
    hips_cm: float | None = _CM_FIELD
    shoulders_cm: float | None = _CM_FIELD
    abdomen_cm: float | None = _CM_FIELD

    # Upper body
    left_arm_cm: float | None = _CM_FIELD
    right_arm_cm: float | None = _CM_FIELD
    left_forearm_cm: float | None = _CM_FIELD
    right_forearm_cm: float | None = _CM_FIELD

    # Lower body
    left_thigh_cm: float | None = _CM_FIELD
    right_thigh_cm: float | None = _CM_FIELD
    left_calf_cm: float | None = _CM_FIELD
    right_calf_cm: float | None = _CM_FIELD

    # Neck
    neck_cm: float | None = _CM_FIELD


# ── Requests ──────────────────────────────────────────────────────────────────


class CreateMeasurementRequest(_MeasurementFields):
    """Log a new body measurement entry.

    At least one measurement field must be provided (validated in service).
    """

    measured_at: date = Field(
        default_factory=date.today,
        description="Measurement date (defaults to today)",
    )
    notes: str | None = Field(default=None, max_length=500)


class UpdateMeasurementRequest(_MeasurementFields):
    """Partial update — send only changed fields.

    Setting a field to null clears that measurement from the entry.
    """

    measured_at: date | None = None
    notes: str | None = Field(default=None, max_length=500)


# ── Response ──────────────────────────────────────────────────────────────────

# Ordered list of field names used in the "most recent" summary and charts.
MEASUREMENT_FIELDS: list[str] = [
    "waist_cm",
    "chest_cm",
    "hips_cm",
    "shoulders_cm",
    "abdomen_cm",
    "left_arm_cm",
    "right_arm_cm",
    "left_forearm_cm",
    "right_forearm_cm",
    "left_thigh_cm",
    "right_thigh_cm",
    "left_calf_cm",
    "right_calf_cm",
    "neck_cm",
]

# Human-readable labels for display
MEASUREMENT_LABELS: dict[str, str] = {
    "waist_cm": "Waist",
    "chest_cm": "Chest",
    "hips_cm": "Hips",
    "shoulders_cm": "Shoulders",
    "abdomen_cm": "Abdomen",
    "left_arm_cm": "Left arm",
    "right_arm_cm": "Right arm",
    "left_forearm_cm": "Left forearm",
    "right_forearm_cm": "Right forearm",
    "left_thigh_cm": "Left thigh",
    "right_thigh_cm": "Right thigh",
    "left_calf_cm": "Left calf",
    "right_calf_cm": "Right calf",
    "neck_cm": "Neck",
}


class MeasurementResponse(_MeasurementFields):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    measured_at: date
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # How many fields were recorded in this entry (convenience for UI)
    recorded_count: int = 0


class MeasurementListResponse(BaseModel):
    entries: list[MeasurementResponse]
    total: int
    page: int
    page_size: int
    has_next: bool

    # Most-recent values for each field (for the "current" snapshot card)
    latest: MeasurementResponse | None = None


# ── Unit display hint ─────────────────────────────────────────────────────────

DisplayUnit = Literal["cm", "in"]
_CM_TO_IN = 1 / 2.54


def cm_to_inches(value: float) -> float:
    """Convert centimetres to inches, rounded to 1 decimal place."""
    return round(value * _CM_TO_IN, 1)
