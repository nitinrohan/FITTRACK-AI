"""Schemas for user profile and preferences endpoints.

Separate from auth.py — auth schemas handle registration/login shapes;
these handle read and update shapes for the /api/v1/users/* endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Profile ───────────────────────────────────────────────────────────────────


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    date_of_birth: str | None = Field(
        default=None,
        description="ISO date string YYYY-MM-DD",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    height_cm: float | None = Field(default=None, gt=0, le=300)
    biological_sex: Literal["male", "female", "intersex", "prefer_not_to_say"] | None = None
    experience_level: Literal["beginner", "intermediate", "advanced"] | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class UserProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    date_of_birth: str | None
    height_cm: float | None
    biological_sex: str | None
    experience_level: str | None
    country_code: str | None
    onboarding_completed: bool
    onboarding_step: int
    updated_at: datetime


# ── Preferences ───────────────────────────────────────────────────────────────


class UpdatePreferencesRequest(BaseModel):
    unit_system: Literal["metric", "imperial"] | None = None
    timezone: str | None = Field(
        default=None,
        max_length=64,
        description="IANA timezone string, e.g. America/New_York",
    )
    language: str | None = Field(default=None, min_length=2, max_length=5)
    first_day_of_week: Literal[0, 1, 6] | None = Field(
        default=None,
        description="0=Sunday, 1=Monday, 6=Saturday",
    )
    email_notifications_enabled: bool | None = None
    ai_features_enabled: bool | None = None


class UserPreferencesResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    unit_system: str
    timezone: str
    language: str
    first_day_of_week: int
    email_notifications_enabled: bool
    ai_features_enabled: bool
    updated_at: datetime


# ── Onboarding ────────────────────────────────────────────────────────────────


class CompleteOnboardingStepRequest(BaseModel):
    """Advance the onboarding step counter.

    Send step=N after the user completes step N.
    When all steps are done, set completed=True.
    """

    step: int = Field(ge=0, le=10)
    completed: bool = False

    # Optional profile/preference data to save in the same request so
    # each onboarding screen can persist its fields without extra round-trips.
    profile: UpdateProfileRequest | None = None
    preferences: UpdatePreferencesRequest | None = None


class OnboardingStatusResponse(BaseModel):
    onboarding_completed: bool
    onboarding_step: int
