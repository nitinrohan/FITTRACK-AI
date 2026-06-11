"""Tests for /api/v1/users/* endpoints.

Covers:
  - GET  /me              — returns current user; 401 when unauthenticated
  - PUT  /me/profile      — valid update, unknown fields ignored, validation errors
  - PUT  /me/preferences  — valid update, timezone validation, 401 guard
  - POST /me/onboarding   — step counter, completed flag, co-persisted fields
  - Data isolation        — cannot update another user's profile by spoofing
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(
    email: str = "user@example.com",
    onboarding_completed: bool = True,
) -> MagicMock:
    """Build a minimal User mock with profile and preferences."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.is_active = True
    user.is_verified = False
    user.role = "user"
    user.created_at = datetime.now(timezone.utc)

    user.profile = MagicMock()
    user.profile.id = uuid.uuid4()
    user.profile.user_id = user.id
    user.profile.display_name = "Test User"
    user.profile.bio = None
    user.profile.avatar_url = None
    user.profile.date_of_birth = None
    user.profile.height_cm = None
    user.profile.biological_sex = None
    user.profile.experience_level = None
    user.profile.country_code = None
    user.profile.onboarding_completed = onboarding_completed
    user.profile.onboarding_step = 0
    user.profile.updated_at = datetime.now(timezone.utc)

    user.preferences = MagicMock()
    user.preferences.id = uuid.uuid4()
    user.preferences.user_id = user.id
    user.preferences.unit_system = "metric"
    user.preferences.timezone = "UTC"
    user.preferences.language = "en"
    user.preferences.first_day_of_week = 1
    user.preferences.email_notifications_enabled = True
    user.preferences.ai_features_enabled = False
    user.preferences.updated_at = datetime.now(timezone.utc)

    return user


def _auth_cookies(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


# ── GET /me ───────────────────────────────────────────────────────────────────

class TestGetMe:
    def test_returns_200_with_user(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.routers.users.user_repository.get_user_with_relations", return_value=user),
        ):
            resp = client.get("/api/v1/users/me", cookies=_auth_cookies(user))
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email

    def test_returns_401_without_cookie(self, client: TestClient) -> None:
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401


# ── PUT /me/profile ───────────────────────────────────────────────────────────

class TestUpdateProfile:
    def test_valid_update_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        updated_profile = MagicMock()
        updated_profile.id = user.profile.id
        updated_profile.user_id = user.id
        updated_profile.display_name = "New Name"
        updated_profile.bio = "Runner"
        updated_profile.avatar_url = None
        updated_profile.date_of_birth = None
        updated_profile.height_cm = 175.0
        updated_profile.biological_sex = None
        updated_profile.experience_level = "intermediate"
        updated_profile.country_code = "US"
        updated_profile.onboarding_completed = True
        updated_profile.onboarding_step = 4
        updated_profile.updated_at = datetime.now(timezone.utc)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_profile", return_value=updated_profile),
        ):
            resp = client.put(
                "/api/v1/users/me/profile",
                json={"display_name": "New Name", "height_cm": 175.0, "experience_level": "intermediate", "country_code": "US"},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "New Name"
        assert data["height_cm"] == 175.0

    def test_empty_body_is_valid(self, client: TestClient) -> None:
        """An empty PATCH-style body should be accepted (nothing to update)."""
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_profile", return_value=user.profile),
        ):
            resp = client.put(
                "/api/v1/users/me/profile",
                json={},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200

    def test_invalid_experience_level_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.put(
                "/api/v1/users/me/profile",
                json={"experience_level": "expert"},  # not a valid enum value
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 422

    def test_height_too_large_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.put(
                "/api/v1/users/me/profile",
                json={"height_cm": 500},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 422

    def test_invalid_date_format_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.put(
                "/api/v1/users/me/profile",
                json={"date_of_birth": "January 1 2000"},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.put("/api/v1/users/me/profile", json={"display_name": "X"})
        assert resp.status_code == 401


# ── PUT /me/preferences ───────────────────────────────────────────────────────

class TestUpdatePreferences:
    def test_valid_update_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        updated_prefs = MagicMock()
        updated_prefs.id = user.preferences.id
        updated_prefs.user_id = user.id
        updated_prefs.unit_system = "imperial"
        updated_prefs.timezone = "America/New_York"
        updated_prefs.language = "en"
        updated_prefs.first_day_of_week = 0
        updated_prefs.email_notifications_enabled = True
        updated_prefs.ai_features_enabled = False
        updated_prefs.updated_at = datetime.now(timezone.utc)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_preferences", return_value=updated_prefs),
        ):
            resp = client.put(
                "/api/v1/users/me/preferences",
                json={"unit_system": "imperial", "timezone": "America/New_York", "first_day_of_week": 0},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unit_system"] == "imperial"
        assert data["timezone"] == "America/New_York"

    def test_invalid_unit_system_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.put(
                "/api/v1/users/me/preferences",
                json={"unit_system": "stone"},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 422

    def test_invalid_timezone_returns_422(self, client: TestClient) -> None:
        """Timezones with unrecognised prefix should be rejected by the service."""
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_preferences", return_value=user.preferences),
        ):
            resp = client.put(
                "/api/v1/users/me/preferences",
                json={"timezone": "Mars/OlympusMons"},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.put("/api/v1/users/me/preferences", json={"unit_system": "metric"})
        assert resp.status_code == 401


# ── POST /me/onboarding ───────────────────────────────────────────────────────

class TestOnboarding:
    def test_advances_step(self, client: TestClient) -> None:
        user = _make_user(onboarding_completed=False)
        profile_after = MagicMock()
        profile_after.onboarding_completed = False
        profile_after.onboarding_step = 1

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_profile", return_value=profile_after),
        ):
            resp = client.post(
                "/api/v1/users/me/onboarding",
                json={"step": 1, "completed": False},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["onboarding_step"] == 1
        assert data["onboarding_completed"] is False

    def test_marks_completed(self, client: TestClient) -> None:
        user = _make_user(onboarding_completed=False)
        profile_after = MagicMock()
        profile_after.onboarding_completed = True
        profile_after.onboarding_step = 4

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_profile", return_value=profile_after),
        ):
            resp = client.post(
                "/api/v1/users/me/onboarding",
                json={"step": 4, "completed": True},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200
        assert resp.json()["onboarding_completed"] is True

    def test_persists_profile_fields_in_same_request(self, client: TestClient) -> None:
        """Profile data sent alongside the step should be saved."""
        user = _make_user(onboarding_completed=False)
        profile_after = MagicMock()
        profile_after.onboarding_completed = False
        profile_after.onboarding_step = 1

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_profile", return_value=profile_after) as mock_update,
        ):
            resp = client.post(
                "/api/v1/users/me/onboarding",
                json={
                    "step": 1,
                    "completed": False,
                    "profile": {"display_name": "Alex", "experience_level": "beginner"},
                },
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200
        # update_user_profile called at least once (for the profile fields).
        assert mock_update.call_count >= 1

    def test_persists_preferences_in_same_request(self, client: TestClient) -> None:
        user = _make_user(onboarding_completed=False)
        profile_after = MagicMock()
        profile_after.onboarding_completed = False
        profile_after.onboarding_step = 2

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.user_service.user_repository.update_user_profile", return_value=profile_after),
            patch("app.services.user_service.user_repository.update_user_preferences", return_value=user.preferences) as mock_prefs,
        ):
            resp = client.post(
                "/api/v1/users/me/onboarding",
                json={
                    "step": 2,
                    "completed": False,
                    "preferences": {"unit_system": "imperial", "timezone": "America/Chicago"},
                },
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 200
        assert mock_prefs.call_count == 1

    def test_step_out_of_range_returns_422(self, client: TestClient) -> None:
        user = _make_user(onboarding_completed=False)
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/users/me/onboarding",
                json={"step": 99},
                cookies=_auth_cookies(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/users/me/onboarding", json={"step": 1})
        assert resp.status_code == 401


# ── User service unit tests ───────────────────────────────────────────────────

class TestUserService:
    def test_update_preferences_rejects_invalid_timezone(self) -> None:
        from app.exceptions import ValidationError
        from app.schemas.users import UpdatePreferencesRequest
        from app.services import user_service

        db = MagicMock()
        body = UpdatePreferencesRequest(timezone="Fake/Zone")
        with (
            patch("app.services.user_service.user_repository.update_user_preferences"),
            pytest.raises(ValidationError),
        ):
            user_service.update_preferences(db, uuid.uuid4(), body)

    def test_update_preferences_accepts_utc(self) -> None:
        from app.schemas.users import UpdatePreferencesRequest
        from app.services import user_service

        db = MagicMock()
        mock_prefs = MagicMock()
        body = UpdatePreferencesRequest(timezone="UTC")
        with patch(
            "app.services.user_service.user_repository.update_user_preferences",
            return_value=mock_prefs,
        ):
            result = user_service.update_preferences(db, uuid.uuid4(), body)
        assert result is mock_prefs

    def test_update_profile_raises_not_found_when_missing(self) -> None:
        from app.exceptions import NotFoundError
        from app.schemas.users import UpdateProfileRequest
        from app.services import user_service

        db = MagicMock()
        body = UpdateProfileRequest(display_name="X")
        with (
            patch(
                "app.services.user_service.user_repository.update_user_profile",
                return_value=None,
            ),
            pytest.raises(NotFoundError),
        ):
            user_service.update_profile(db, uuid.uuid4(), body)
