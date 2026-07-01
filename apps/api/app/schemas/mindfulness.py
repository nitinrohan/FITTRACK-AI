"""Pydantic schemas for the mindfulness domain (sessions + minute logs)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

MindfulnessCategory = Literal["breathing", "meditation", "sleep", "focus"]


# ── Sessions (library content) ──────────────────────────────────────────────────


class MindfulnessSessionResponse(BaseModel):
    """A session in the library (system or user-created)."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    category: str
    duration_minutes: int
    description: str | None
    external_url: str | None
    is_system: bool

    model_config = {"from_attributes": True}


class MindfulnessSessionListResponse(BaseModel):
    items: list[MindfulnessSessionResponse]
    total: int


class CreateSessionRequest(BaseModel):
    """Create a custom (user-owned) session."""

    title: str = Field(min_length=1, max_length=200)
    category: MindfulnessCategory = "meditation"
    duration_minutes: int = Field(ge=1, le=600)
    description: str | None = Field(default=None, max_length=2000)
    external_url: str | None = Field(default=None, max_length=500)


# ── Logs (mindful minutes) ──────────────────────────────────────────────────────


class LogMindfulnessRequest(BaseModel):
    """Log a stretch of mindful minutes, optionally tied to a session."""

    duration_minutes: int = Field(ge=1, le=600)
    session_id: uuid.UUID | None = None
    recorded_at: datetime | None = Field(
        default=None, description="When practised (UTC). Defaults to now."
    )
    note: str | None = Field(default=None, max_length=2000)


class MindfulnessLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None
    session_title: str | None
    duration_minutes: int
    recorded_at: datetime
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MindfulnessLogListResponse(BaseModel):
    items: list[MindfulnessLogResponse]
    total: int
    page: int
    page_size: int


class MindfulnessDailySummary(BaseModel):
    """Mindful activity for one local calendar day, plus the running streak."""

    date: date
    total_minutes: int
    sessions_count: int
    current_streak: int
