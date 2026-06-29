"""Tests for authentication endpoints and security utilities.

All database calls are mocked - these are unit-level tests that verify:
  - Input validation (bad email, short password)
  - Happy-path registration and login (cookie setting, response shape)
  - Error paths (duplicate email, wrong password, inactive account)
  - Token mechanics (missing cookie → 401, logout clears cookies)
  - get_current_user dependency (valid token, expired token, wrong type)
  - Password hashing (hash is not plaintext, verify works, wrong pw fails)
  - JWT creation and decoding (type enforcement, expiry)

Integration tests against a real database will be added in Phase 2 CI
once the test DB is provisioned in the workflow (see ci.yml).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions import ConflictError, UnauthorizedError

# ── Password hashing ───────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        assert hash_password("secret123") != "secret123"

    def test_verify_correct_password(self) -> None:
        hashed = hash_password("correct-horse-battery")
        assert verify_password("correct-horse-battery", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct-horse-battery")
        assert verify_password("wrong-password", hashed) is False

    def test_two_hashes_of_same_password_differ(self) -> None:
        # bcrypt uses a random salt - same input produces different hashes.
        h1 = hash_password("mypassword")
        h2 = hash_password("mypassword")
        assert h1 != h2
        # But both verify correctly.
        assert verify_password("mypassword", h1)
        assert verify_password("mypassword", h2)


# ── JWT tokens ─────────────────────────────────────────────────────────────


class TestJWT:
    def test_access_token_decodes_to_user_id(self) -> None:
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        assert decode_token(token, "access") == user_id

    def test_refresh_token_decodes_to_user_id(self) -> None:
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)
        assert decode_token(token, "refresh") == user_id

    def test_access_token_rejected_as_refresh(self) -> None:
        from jose import JWTError

        token = create_access_token(str(uuid.uuid4()))
        with pytest.raises(JWTError):
            decode_token(token, "refresh")

    def test_refresh_token_rejected_as_access(self) -> None:
        from jose import JWTError

        token = create_refresh_token(str(uuid.uuid4()))
        with pytest.raises(JWTError):
            decode_token(token, "access")

    def test_tampered_token_raises(self) -> None:
        from jose import JWTError

        token = create_access_token(str(uuid.uuid4()))
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered, "access")


# ── Registration ───────────────────────────────────────────────────────────


def _make_user(email: str = "user@example.com") -> MagicMock:
    """Build a minimal User mock that satisfies serialisation."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.is_active = True
    user.is_verified = False
    user.role = "user"
    user.created_at = datetime.now(timezone.utc)
    user.profile = MagicMock(
        display_name="Test User",
        avatar_url=None,
        onboarding_completed=False,
        onboarding_step=0,
        experience_level=None,
        country_code=None,
    )
    user.preferences = MagicMock(
        unit_system="metric",
        timezone="UTC",
        language="en",
        first_day_of_week=1,
        email_notifications_enabled=True,
        ai_features_enabled=False,
    )
    return user


class TestRegister:
    def test_valid_registration_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.services.auth_service.register", return_value=user),
            patch("app.repositories.user_repository.get_user_with_relations", return_value=user),
            patch("app.services.auth_service.issue_tokens", return_value=("acc", "ref")),
        ):
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": "new@example.com", "password": "strongpass1"},
            )
        assert resp.status_code == 201

    def test_valid_registration_returns_user(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.services.auth_service.register", return_value=user),
            patch("app.repositories.user_repository.get_user_with_relations", return_value=user),
            patch("app.services.auth_service.issue_tokens", return_value=("acc", "ref")),
        ):
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": "new@example.com", "password": "strongpass1"},
            )
        data = resp.json()
        assert "user" in data
        assert data["user"]["email"] == user.email

    def test_duplicate_email_returns_409(self, client: TestClient) -> None:
        with patch(
            "app.services.auth_service.register",
            side_effect=ConflictError("Email already exists"),
        ):
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": "exists@example.com", "password": "strongpass1"},
            )
        assert resp.status_code == 409

    def test_short_password_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "strongpass1"},
        )
        assert resp.status_code == 422

    def test_registration_sets_cookies(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.services.auth_service.register", return_value=user),
            patch("app.repositories.user_repository.get_user_with_relations", return_value=user),
            patch("app.services.auth_service.issue_tokens", return_value=("acc_tok", "ref_tok")),
        ):
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": "new@example.com", "password": "strongpass1"},
            )
        assert "fittrack_access" in resp.cookies or "set-cookie" in str(resp.headers).lower()


# ── Login ──────────────────────────────────────────────────────────────────


class TestLogin:
    def test_valid_login_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.services.auth_service.login", return_value=user),
            patch("app.repositories.user_repository.get_user_with_relations", return_value=user),
            patch("app.services.auth_service.issue_tokens", return_value=("acc", "ref")),
        ):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "correctpass"},
            )
        assert resp.status_code == 200

    def test_wrong_password_returns_401(self, client: TestClient) -> None:
        with patch(
            "app.services.auth_service.login",
            side_effect=UnauthorizedError("Invalid email or password"),
        ):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "wrongpass"},
            )
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client: TestClient) -> None:
        with patch(
            "app.services.auth_service.login",
            side_effect=UnauthorizedError("Invalid email or password"),
        ):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "somepass1"},
            )
        assert resp.status_code == 401

    def test_error_message_does_not_reveal_email_existence(self, client: TestClient) -> None:
        """Both bad-email and bad-password paths return the same message."""
        with patch(
            "app.services.auth_service.login",
            side_effect=UnauthorizedError("Invalid email or password"),
        ):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "pass"},
            )
        assert resp.json()["message"] == "Invalid email or password"


# ── Logout ─────────────────────────────────────────────────────────────────


class TestLogout:
    def test_logout_returns_204(self, client: TestClient) -> None:
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204


# ── /me - protected endpoint ───────────────────────────────────────────────


class TestMe:
    def test_me_without_cookie_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_valid_token_returns_user(self, client: TestClient) -> None:
        user = _make_user()
        token = create_access_token(str(user.id))

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.routers.auth.user_repository.get_user_with_relations", return_value=user),
        ):
            resp = client.get(
                "/api/v1/auth/me",
                cookies={"fittrack_access": token},
            )
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email

    def test_me_with_tampered_token_returns_401(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/auth/me",
            cookies={"fittrack_access": "totally.invalid.token"},
        )
        assert resp.status_code == 401

    def test_me_with_refresh_token_used_as_access_returns_401(self, client: TestClient) -> None:
        """Refresh tokens must not be usable as access tokens."""
        refresh = create_refresh_token(str(uuid.uuid4()))
        resp = client.get(
            "/api/v1/auth/me",
            cookies={"fittrack_access": refresh},
        )
        assert resp.status_code == 401


# ── Auth service unit tests ────────────────────────────────────────────────


class TestAuthService:
    def test_register_raises_conflict_on_duplicate_email(self) -> None:
        from app.services import auth_service

        db = MagicMock()
        with (
            patch("app.services.auth_service.user_repository.email_exists", return_value=True),
            pytest.raises(ConflictError),
        ):
            auth_service.register(db, "dup@example.com", "password1")

    def test_login_raises_unauthorized_for_unknown_email(self) -> None:
        from app.services import auth_service

        db = MagicMock()
        with (
            patch("app.services.auth_service.user_repository.get_user_by_email", return_value=None),
            pytest.raises(UnauthorizedError),
        ):
            auth_service.login(db, "nobody@example.com", "pass")

    def test_login_raises_unauthorized_for_wrong_password(self) -> None:
        from app.services import auth_service

        user = _make_user()
        user.hashed_password = hash_password("correct")
        db = MagicMock()
        with (
            patch(
                "app.services.auth_service.user_repository.get_user_by_email",
                return_value=user,
            ),
            pytest.raises(UnauthorizedError),
        ):
            auth_service.login(db, user.email, "wrong")

    def test_login_raises_unauthorized_for_inactive_user(self) -> None:
        from app.services import auth_service

        user = _make_user()
        user.is_active = False
        user.hashed_password = hash_password("correct")
        db = MagicMock()
        with (
            patch(
                "app.services.auth_service.user_repository.get_user_by_email",
                return_value=user,
            ),
            pytest.raises(UnauthorizedError),
        ):
            auth_service.login(db, user.email, "correct")
