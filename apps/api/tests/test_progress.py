"""Tests for the progress series service and endpoint.

Covers:
  - _stats summary maths (empty, values, change sign)
  - per-metric builders (weight / workouts / calories) with mocked data
  - day clamping in get_progress
  - endpoint auth + shape
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.schemas.progress import ProgressResponse
from app.services import progress_service as svc

TODAY = date.today()


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


# ── _stats ──────────────────────────────────────────────────────────────────────


class TestStats:
    def test_empty(self) -> None:
        s = svc._stats([])
        assert s["average"] is None and s["total"] == 0.0 and s["change"] is None

    def test_values(self) -> None:
        s = svc._stats([80.0, 79.5, 79.0])
        assert s["minimum"] == 79.0
        assert s["maximum"] == 80.0
        assert s["average"] == 79.5
        assert s["first"] == 80.0
        assert s["latest"] == 79.0
        assert s["change"] == -1.0  # lost weight

    def test_single_point_change_zero(self) -> None:
        s = svc._stats([70.0])
        assert s["change"] == 0.0


# ── Builders ─────────────────────────────────────────────────────────────────────


class TestWeightSeries:
    def test_reverses_to_chronological(self) -> None:
        # repository returns newest-first
        e1 = MagicMock(measured_at=TODAY, weight_kg=79.0)
        e0 = MagicMock(measured_at=TODAY - timedelta(days=2), weight_kg=80.0)
        db = MagicMock()
        with patch.object(
            svc.weight_repository,
            "list_entries_for_user",
            return_value=([e1, e0], 2),
        ):
            series = svc._weight_series(db, uuid.uuid4(), TODAY - timedelta(days=29), TODAY)
        assert series is not None
        assert [p.value for p in series.points] == [80.0, 79.0]  # oldest -> newest
        assert series.change == -1.0
        assert series.unit == "kg"

    def test_no_entries_returns_none(self) -> None:
        db = MagicMock()
        with patch.object(
            svc.weight_repository, "list_entries_for_user", return_value=([], 0)
        ):
            assert svc._weight_series(db, uuid.uuid4(), TODAY, TODAY) is None


class TestWorkoutSeries:
    def test_zero_filled_counts(self) -> None:
        start = TODAY - timedelta(days=2)
        w_today = MagicMock(started_at=TODAY, completed_at=TODAY)
        w_today2 = MagicMock(started_at=TODAY, completed_at=TODAY)
        db = MagicMock()
        db.execute.return_value.scalars.return_value = [w_today, w_today2]
        series = svc._workout_series(db, uuid.uuid4(), start, TODAY)
        assert series is not None
        assert series.count == 3  # 3 days zero-filled
        assert series.total == 2.0  # two workouts, both today
        assert series.points[-1].value == 2.0
        assert series.points[0].value == 0.0

    def test_no_workouts_returns_none(self) -> None:
        db = MagicMock()
        db.execute.return_value.scalars.return_value = []
        assert svc._workout_series(db, uuid.uuid4(), TODAY - timedelta(days=6), TODAY) is None


class TestCalorieSeries:
    def test_aggregates_per_day(self) -> None:
        # rows: (logged_date, calories_per_100g, quantity_g)
        rows = [
            (TODAY, 150.0, 200.0),  # 300 kcal
            (TODAY, 400.0, 50.0),   # 200 kcal -> day total 500
            (TODAY - timedelta(days=1), 100.0, 100.0),  # 100 kcal
        ]
        db = MagicMock()
        db.execute.return_value.all.return_value = rows
        series = svc._calorie_series(db, uuid.uuid4(), TODAY - timedelta(days=3), TODAY)
        assert series is not None
        assert series.count == 2  # two distinct logged days
        by_date = {p.date: p.value for p in series.points}
        assert by_date[TODAY.isoformat()] == 500.0
        assert by_date[(TODAY - timedelta(days=1)).isoformat()] == 100.0

    def test_no_logs_returns_none(self) -> None:
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        assert svc._calorie_series(db, uuid.uuid4(), TODAY - timedelta(days=6), TODAY) is None


# ── get_progress ─────────────────────────────────────────────────────────────────


class TestGetProgress:
    def test_clamps_days(self) -> None:
        db = MagicMock()
        with (
            patch.object(svc, "_weight_series", return_value=None),
            patch.object(svc, "_workout_series", return_value=None),
            patch.object(svc, "_calorie_series", return_value=None),
        ):
            too_big = svc.get_progress(db, user_id=uuid.uuid4(), days=10_000)
            too_small = svc.get_progress(db, user_id=uuid.uuid4(), days=1)
        assert too_big.range_days == svc.MAX_DAYS
        assert too_small.range_days == svc.MIN_DAYS


# ── Endpoint ─────────────────────────────────────────────────────────────────────


class TestEndpoint:
    def test_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/progress").status_code == 401

    def test_returns_series(self, client: TestClient) -> None:
        user = _user()
        resp = ProgressResponse(
            range_days=30, start_date="2026-05-26", end_date="2026-06-24"
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.progress_service.get_progress", return_value=resp),
        ):
            r = client.get("/api/v1/progress?days=30", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["range_days"] == 30

    def test_invalid_days_422(self, client: TestClient) -> None:
        user = _user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.get("/api/v1/progress?days=0", cookies=_auth(user))
        assert r.status_code == 422
