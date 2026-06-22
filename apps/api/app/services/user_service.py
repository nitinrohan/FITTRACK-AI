"""User profile and preferences service.

Business rules for reading and updating a user's profile, preferences,
and onboarding state. Keeps validation and orchestration out of route handlers.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.user import UserPreference, UserProfile
from app.repositories import user_repository
from app.schemas.users import (
    CompleteOnboardingStepRequest,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
)

logger = logging.getLogger(__name__)

# ── IANA timezone validation ──────────────────────────────────────────────────
# We do a lightweight check rather than bundling the full tz database.
# The API accepts any non-empty string that looks like a valid IANA zone.
# Definitive validation happens when the frontend and API actually use the
# timezone (e.g. when formatting dates).  A strict allow-list would require
# keeping it up to date as zones are added; this is a reasonable compromise.

_KNOWN_TZ_PREFIXES = {
    "Africa",
    "America",
    "Antarctica",
    "Arctic",
    "Asia",
    "Atlantic",
    "Australia",
    "Europe",
    "Indian",
    "Pacific",
    "UTC",
    "Etc",
}


def _validate_timezone(tz: str) -> None:
    if "/" in tz:
        prefix = tz.split("/")[0]
        if prefix not in _KNOWN_TZ_PREFIXES:
            raise ValidationError(f"Unknown timezone: {tz!r}")
    elif tz not in {"UTC", "GMT"}:
        raise ValidationError(
            f"Unknown timezone: {tz!r}. "
            "Use an IANA timezone string such as 'America/New_York' or 'UTC'."
        )


# ── Profile ───────────────────────────────────────────────────────────────────


def update_profile(db: Session, user_id: object, body: UpdateProfileRequest) -> UserProfile:
    """Update the user's profile fields.  Returns the updated UserProfile."""
    import uuid

    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    fields = body.model_dump(exclude_none=True)

    profile = user_repository.update_user_profile(db, user_id, **fields)
    if profile is None:
        raise NotFoundError("User profile not found")

    logger.info("Profile updated", extra={"user_id": str(user_id)})
    return profile


# ── Preferences ───────────────────────────────────────────────────────────────


def update_preferences(
    db: Session, user_id: object, body: UpdatePreferencesRequest
) -> UserPreference:
    """Update the user's preferences.  Returns the updated UserPreference."""
    import uuid

    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    fields = body.model_dump(exclude_none=True)

    if "timezone" in fields:
        _validate_timezone(fields["timezone"])

    prefs = user_repository.update_user_preferences(db, user_id, **fields)
    if prefs is None:
        raise NotFoundError("User preferences not found")

    logger.info("Preferences updated", extra={"user_id": str(user_id)})
    return prefs


# ── Onboarding ────────────────────────────────────────────────────────────────


def complete_onboarding_step(
    db: Session, user_id: object, body: CompleteOnboardingStepRequest
) -> UserProfile:
    """Advance the onboarding step and optionally persist profile/preference data.

    Saves profile and preference changes atomically in the same DB transaction
    so each wizard screen can POST once.
    """
    import uuid

    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    # Persist any profile fields sent along with this step.
    if body.profile:
        profile_fields = body.profile.model_dump(exclude_none=True)
        if profile_fields:
            user_repository.update_user_profile(db, user_id, **profile_fields)

    # Persist any preference fields sent along with this step.
    if body.preferences:
        pref_fields = body.preferences.model_dump(exclude_none=True)
        if "timezone" in pref_fields:
            _validate_timezone(pref_fields["timezone"])
        if pref_fields:
            user_repository.update_user_preferences(db, user_id, **pref_fields)

    # Advance the step counter; mark complete when requested.
    step_fields: dict[str, object] = {"onboarding_step": body.step}
    if body.completed:
        step_fields["onboarding_completed"] = True

    profile = user_repository.update_user_profile(db, user_id, **step_fields)
    if profile is None:
        raise NotFoundError("User profile not found")

    logger.info(
        "Onboarding step saved",
        extra={"user_id": str(user_id), "step": body.step, "completed": body.completed},
    )
    return profile
