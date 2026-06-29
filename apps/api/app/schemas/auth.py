"""Pydantic schemas for authentication and user endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ── Requests ─────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Body for POST /api/v1/auth/register."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_not_email(cls, v: str, info: object) -> str:
        # Prevent trivially weak passwords - full policy enforced server-side.
        if len(v.strip()) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    """Body for POST /api/v1/auth/login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Optional body for POST /api/v1/auth/refresh.

    The refresh token is read from the cookie by default; this body is
    provided only for non-browser clients that cannot use cookies.
    """

    refresh_token: str | None = None


# ── Responses ─────────────────────────────────────────────────────────────


class UserPreferenceResponse(BaseModel):
    """Serialised UserPreference."""

    model_config = ConfigDict(from_attributes=True)

    unit_system: str
    timezone: str
    language: str
    first_day_of_week: int
    email_notifications_enabled: bool
    ai_features_enabled: bool


class UserProfileResponse(BaseModel):
    """Serialised UserProfile (safe fields only)."""

    model_config = ConfigDict(from_attributes=True)

    display_name: str | None
    avatar_url: str | None
    onboarding_completed: bool
    onboarding_step: int
    experience_level: str | None
    country_code: str | None


class UserResponse(BaseModel):
    """Public user representation returned from auth endpoints.

    Never includes hashed_password or other sensitive internal fields.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_verified: bool
    role: str
    created_at: datetime
    profile: UserProfileResponse | None = None
    preferences: UserPreferenceResponse | None = None


class AuthResponse(BaseModel):
    """Response from /register and /login.

    Tokens are set as HTTP-only cookies; this body contains only the
    user information needed to bootstrap the frontend session.
    """

    user: UserResponse
    message: str = "Authentication successful"
