"""Users router — /api/v1/users/*

Endpoints for reading and updating the current user's profile,
preferences, and onboarding state.

All endpoints require authentication via get_current_user.
Users can only access their own data — no cross-user reads here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import UserResponse
from app.schemas.users import (
    CompleteOnboardingStepRequest,
    OnboardingStatusResponse,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
    UserPreferencesResponse,
    UserProfileResponse,
)
from app.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ── Current user ──────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user (full)",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Alias for GET /api/v1/auth/me — available under /users for REST symmetry."""
    user = user_repository.get_user_with_relations(db, current_user.id) or current_user
    return UserResponse.model_validate(user)


# ── Profile ───────────────────────────────────────────────────────────────────

@router.put(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Update the current user's profile",
)
def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    profile = user_service.update_profile(db, current_user.id, body)
    return UserProfileResponse.model_validate(profile)


# ── Preferences ───────────────────────────────────────────────────────────────

@router.put(
    "/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Update the current user's preferences",
)
def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    prefs = user_service.update_preferences(db, current_user.id, body)
    return UserPreferencesResponse.model_validate(prefs)


# ── Onboarding ────────────────────────────────────────────────────────────────

@router.post(
    "/me/onboarding",
    response_model=OnboardingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Save an onboarding step and optionally mark onboarding complete",
)
def complete_onboarding_step(
    body: CompleteOnboardingStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingStatusResponse:
    """Persist one onboarding wizard step.

    The frontend POSTs after each screen with:
    - step: the step number just completed
    - completed: true on the final step
    - profile: any profile fields collected on this screen (optional)
    - preferences: any preference fields collected on this screen (optional)

    Returns the updated onboarding_completed and onboarding_step values so
    the frontend knows the current position.
    """
    profile = user_service.complete_onboarding_step(db, current_user.id, body)
    return OnboardingStatusResponse(
        onboarding_completed=profile.onboarding_completed,
        onboarding_step=profile.onboarding_step,
    )
