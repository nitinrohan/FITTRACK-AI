"""Pydantic schemas for the stress domain (0-100 readings)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

StressBand = Literal["low", "moderate", "high"]


class LogStressRequest(BaseModel):
    """Request body for POST /api/v1/stress."""

    level: int = Field(ge=0, le=100, description="Stress level, 0 (calm) to 100 (high).")
    recorded_at: datetime | None = Field(
        default=None, description="When the reading was taken (UTC). Defaults to now."
    )
    note: str | None = Field(default=None, max_length=2000)


class StressLogResponse(BaseModel):
    """A single stress reading."""

    id: uuid.UUID
    user_id: uuid.UUID
    level: int
    band: StressBand
    recorded_at: datetime
    source: str
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StressListResponse(BaseModel):
    """Paginated list of stress readings (newest first)."""

    items: list[StressLogResponse]
    total: int
    page: int
    page_size: int


class StressDailySummary(BaseModel):
    """Aggregated stress for one local calendar day.

    All aggregate fields are null when there are no readings for the day, so
    "no data" is never shown as a misleading 0.
    """

    date: date
    count: int
    highest: int | None
    lowest: int | None
    average: int | None
    band: StressBand | None
