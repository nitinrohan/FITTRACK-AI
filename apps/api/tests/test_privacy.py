"""Tests for the privacy service and endpoints (export, summary, deletion).

Covers:
  - _serialize: UUID/date conversion and hashed_password redaction
  - build_export: every domain key present; metadata correct
  - build_summary: counts shape
  - delete_account: password verification (correct vs wrong) and purge order
  - endpoints: auth required, shapes, deletion clears cookies
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.exceptions import UnauthorizedError
from app.models.user import User
from app.models.weight_entry import WeightEntry
from app.services import privacy_service as svc


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _empty_db() -> MagicMock:
    """A db mock whose every ``query(...).filter(...).all()/.count()`` is empty."""
    db = MagicMock()
    chain = db.query.return_value.filter.return_value
    chain.all.return_value = []
    chain.count.return_value = 0
    db.query.return_value.filter.return_value.delete.return_value = 0
    return db


# ── _serialize ────────────────────────────────────────────────────────────────


class TestSerialize:
    def test_redacts_password_hash(self) -> None:
        u = User(email="a@b.com", hashed_password="super-secret", role="user")
        data = svc._serialize(u)
        assert "hashed_password" not in data
        assert data["email"] == "a@b.com"

    def test_converts_uuid_and_date_to_strings(self) -> None:
        entry = WeightEntry(
            user_id=uuid.uuid4(), weight_kg=80.0, measured_at=date(2026, 6, 1)
        )
        data = svc._serialize(entry)
        assert data["measured_at"] == "2026-06-01"
        assert isinstance(data["user_id"], str)
        assert data["weight_kg"] == 80.0


# ── build_export ──────────────────────────────────────────────────────────────


class TestBuildExport:
    def test_includes_all_domains_and_metadata(self) -> None:
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "person@example.com"
        user.role = "user"
        user.is_active = True
        user.is_verified = False
        user.created_at = None
        user.updated_at = None
        user.profile = None
        user.preferences = None

        export = svc.build_export(_empty_db(), user=user)

        assert export["export_metadata"]["user_id"] == str(user.id)
        assert export["export_metadata"]["format_version"] == svc.EXPORT_FORMAT_VERSION
        assert export["account"]["email"] == "person@example.com"
        # Every domain group must be present even when empty.
        for key in (
            "goals",
            "weight_entries",
            "body_measurements",
            "custom_exercises",
            "workout_templates",
            "workouts",
            "custom_foods",
            "food_logs",
            "water_logs",
            "sleep_logs",
            "daily_steps",
            "wellness_logs",
            "habits",
            "ai_usage_logs",
        ):
            assert export[key] == []

    def test_export_excludes_password_hash(self) -> None:
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "p@e.com"
        user.role = "user"
        user.is_active = True
        user.is_verified = True
        user.created_at = None
        user.updated_at = None
        user.profile = None
        user.preferences = None
        export = svc.build_export(_empty_db(), user=user)
        assert "hashed_password" not in export["account"]


# ── build_summary ─────────────────────────────────────────────────────────────


class TestBuildSummary:
    def test_returns_zero_counts(self) -> None:
        user = _user()
        summary = svc.build_summary(_empty_db(), user=user)
        assert summary["goals"] == 0
        assert summary["workouts"] == 0
        assert set(summary).issuperset({"habits", "food_logs", "custom_foods"})


# ── delete_account ────────────────────────────────────────────────────────────


class TestDeleteAccount:
    def test_wrong_password_raises_and_does_not_delete(self) -> None:
        db = _empty_db()
        user = MagicMock()
        user.id = uuid.uuid4()
        user.hashed_password = hash_password("correct-horse")

        try:
            svc.delete_account(db, user=user, password="wrong-password")
            raised = False
        except UnauthorizedError:
            raised = True

        assert raised is True
        db.delete.assert_not_called()
        db.commit.assert_not_called()

    def test_correct_password_purges_and_deletes(self) -> None:
        db = _empty_db()
        user = MagicMock()
        user.id = uuid.uuid4()
        user.hashed_password = hash_password("correct-horse")

        svc.delete_account(db, user=user, password="correct-horse")

        # ai_usage_logs purged explicitly, then the user row deleted, then commit.
        db.query.return_value.filter.return_value.delete.assert_called_once()
        db.delete.assert_called_once_with(user)
        db.commit.assert_called_once()


# ── Endpoints ─────────────────────────────────────────────────────────────────


class TestEndpoints:
    def test_summary_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/privacy/summary").status_code == 401

    def test_export_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/privacy/export").status_code == 401

    def test_delete_requires_auth(self, client: TestClient) -> None:
        r = client.request(
            "DELETE", "/api/v1/privacy/account", json={"password": "x"}
        )
        assert r.status_code == 401

    def test_summary_shape(self, client: TestClient) -> None:
        user = _user()
        counts = {"goals": 2, "workouts": 5}
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.privacy_service.build_summary", return_value=counts
            ),
        ):
            r = client.get("/api/v1/privacy/summary", cookies=_auth(user))
        assert r.status_code == 200
        body = r.json()
        assert body["goals"] == 2 and body["workouts"] == 5

    def test_export_returns_payload(self, client: TestClient) -> None:
        user = _user()
        payload = {"export_metadata": {"format_version": "1.0"}, "goals": []}
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.privacy_service.build_export", return_value=payload),
        ):
            r = client.get("/api/v1/privacy/export", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["export_metadata"]["format_version"] == "1.0"

    def test_delete_validates_empty_password(self, client: TestClient) -> None:
        user = _user()
        with patch(
            "app.dependencies.user_repository.get_user_by_id", return_value=user
        ):
            r = client.request(
                "DELETE", "/api/v1/privacy/account", json={"password": ""}, cookies=_auth(user)
            )
        assert r.status_code == 422

    def test_delete_success_clears_cookies(self, client: TestClient) -> None:
        user = _user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.privacy_service.delete_account", return_value=None),
        ):
            r = client.request(
                "DELETE",
                "/api/v1/privacy/account",
                json={"password": "correct-horse"},
                cookies=_auth(user),
            )
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"
        # Both auth cookies should be cleared in the response.
        set_cookie = r.headers.get("set-cookie", "")
        assert "fittrack_access=" in set_cookie
        assert "fittrack_refresh=" in set_cookie

    def test_delete_wrong_password_401(self, client: TestClient) -> None:
        user = _user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.privacy_service.delete_account",
                side_effect=UnauthorizedError("Password is incorrect."),
            ),
        ):
            r = client.request(
                "DELETE",
                "/api/v1/privacy/account",
                json={"password": "nope"},
                cookies=_auth(user),
            )
        assert r.status_code == 401
