"""Tests for the mindfulness domain (streak calc + endpoints)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.services import mindfulness_service as svc

TODAY = date(2026, 6, 26)


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


# ── compute_streak ──────────────────────────────────────────────────────────────


class TestComputeStreak:
    def test_empty(self) -> None:
        assert svc.compute_streak(set(), TODAY) == 0

    def test_today_and_back(self) -> None:
        days = {TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
        assert svc.compute_streak(days, TODAY) == 3

    def test_today_missing_counts_from_yesterday(self) -> None:
        days = {TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
        assert svc.compute_streak(days, TODAY) == 2

    def test_gap_breaks_streak(self) -> None:
        days = {TODAY, TODAY - timedelta(days=2)}
        assert svc.compute_streak(days, TODAY) == 1


# ── Endpoints ───────────────────────────────────────────────────────────────────


class TestEndpoints:
    def test_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/mindfulness/sessions").status_code == 401
        assert client.get("/api/v1/mindfulness/summary").status_code == 401

    def test_list_sessions(self, client: TestClient) -> None:
        user = _user()
        from app.schemas.mindfulness import (
            MindfulnessSessionListResponse,
            MindfulnessSessionResponse,
        )

        payload = MindfulnessSessionListResponse(
            items=[
                MindfulnessSessionResponse(
                    id=uuid.uuid4(),
                    user_id=None,
                    title="Box breathing",
                    category="breathing",
                    duration_minutes=5,
                    description="...",
                    external_url=None,
                    is_system=True,
                )
            ],
            total=1,
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.mindfulness_service.list_sessions", return_value=payload),
        ):
            r = client.get("/api/v1/mindfulness/sessions", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["items"][0]["title"] == "Box breathing"

    def test_log_minutes_validates(self, client: TestClient) -> None:
        user = _user()
        with patch(
            "app.dependencies.user_repository.get_user_by_id", return_value=user
        ):
            r = client.post(
                "/api/v1/mindfulness/logs", json={"duration_minutes": 0}, cookies=_auth(user)
            )
        assert r.status_code == 422

    def test_summary_shape(self, client: TestClient) -> None:
        user = _user()
        from app.schemas.mindfulness import MindfulnessDailySummary

        summary = MindfulnessDailySummary(
            date=TODAY, total_minutes=15, sessions_count=2, current_streak=4
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.mindfulness_service.daily_summary", return_value=summary),
        ):
            r = client.get(
                "/api/v1/mindfulness/summary?date=2026-06-26&tz=UTC", cookies=_auth(user)
            )
        assert r.status_code == 200
        body = r.json()
        assert body["total_minutes"] == 15 and body["current_streak"] == 4
