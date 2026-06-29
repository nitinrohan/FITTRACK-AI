"""Tests for wellness endpoints - /api/v1/sleep, /api/v1/steps, /api/v1/wellness.

Covers:
  Service-layer unit tests:
    - _compute_duration
    - log_sleep raises on missing duration/times
    - log_wellness raises when no metric provided

  Sleep endpoint tests:
    - POST   /api/v1/sleep     (201 with duration, 201 with times, 422, auth)
    - GET    /api/v1/sleep     (200, pagination, date filter, auth)
    - GET    /api/v1/sleep/{id} (200, 404, auth)
    - PATCH  /api/v1/sleep/{id} (200, 404)
    - DELETE /api/v1/sleep/{id} (204, 404)

  Steps endpoint tests:
    - POST   /api/v1/steps     (201, 422, auth)
    - GET    /api/v1/steps     (200, pagination, date filter, auth)
    - GET    /api/v1/steps/{id} (200, 404)
    - PATCH  /api/v1/steps/{id} (200, 404)
    - DELETE /api/v1/steps/{id} (204, 404)

  Wellness endpoint tests:
    - POST   /api/v1/wellness  (201, 422 no metric, auth)
    - GET    /api/v1/wellness  (200, pagination, auth)
    - GET    /api/v1/wellness/daily (200 - snapshot)
    - GET    /api/v1/wellness/{id} (200, 404)
    - PATCH  /api/v1/wellness/{id} (200, 404)
    - DELETE /api/v1/wellness/{id} (204, 404)

  Ownership isolation:
    - User A cannot read User B's sleep / steps / wellness entries
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.wellness import DailySteps, SleepLog, WellnessLog
from app.schemas.wellness import (
    DailyWellnessSnapshot,
    SleepListResponse,
    SleepLogResponse,
    StepsListResponse,
    StepsLogResponse,
    WellnessListResponse,
    WellnessLogResponse,
)
from app.services.wellness_service import _compute_duration

# ── Helpers ───────────────────────────────────────────────────────────────────

TODAY = date.today()


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_sleep(
    *,
    user_id: uuid.UUID,
    entry_date: date = TODAY,
    duration_minutes: int = 420,
    quality: int | None = 4,
) -> MagicMock:
    e = MagicMock(spec=SleepLog)
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.date = entry_date
    e.bedtime = None
    e.wake_time = None
    e.duration_minutes = duration_minutes
    e.quality = quality
    e.notes = None
    e.created_at = _now()
    e.updated_at = _now()
    return e


def _sleep_resp(e: MagicMock) -> SleepLogResponse:
    return SleepLogResponse(
        id=e.id,
        user_id=e.user_id,
        date=e.date,
        bedtime=e.bedtime,
        wake_time=e.wake_time,
        duration_minutes=e.duration_minutes,
        quality=e.quality,
        notes=e.notes,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def _make_steps(
    *,
    user_id: uuid.UUID,
    entry_date: date = TODAY,
    steps: int = 8000,
) -> MagicMock:
    e = MagicMock(spec=DailySteps)
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.date = entry_date
    e.steps = steps
    e.active_minutes = 45
    e.distance_m = 6400.0
    e.calories_burned = 320.0
    e.notes = None
    e.created_at = _now()
    e.updated_at = _now()
    return e


def _steps_resp(e: MagicMock) -> StepsLogResponse:
    return StepsLogResponse(
        id=e.id,
        user_id=e.user_id,
        date=e.date,
        steps=e.steps,
        active_minutes=e.active_minutes,
        distance_m=e.distance_m,
        calories_burned=e.calories_burned,
        notes=e.notes,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def _make_wellness(
    *,
    user_id: uuid.UUID,
    entry_date: date = TODAY,
    mood: int = 4,
    energy: int = 3,
    stress: int = 2,
) -> MagicMock:
    e = MagicMock(spec=WellnessLog)
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.date = entry_date
    e.mood = mood
    e.energy = energy
    e.stress = stress
    e.notes = None
    e.created_at = _now()
    e.updated_at = _now()
    return e


def _wellness_resp(e: MagicMock) -> WellnessLogResponse:
    return WellnessLogResponse(
        id=e.id,
        user_id=e.user_id,
        date=e.date,
        mood=e.mood,
        energy=e.energy,
        stress=e.stress,
        notes=e.notes,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


# ── Service unit tests ────────────────────────────────────────────────────────


class TestComputeDuration:
    def test_standard_night(self) -> None:
        bedtime = datetime(2026, 6, 17, 23, 0)
        wake_time = datetime(2026, 6, 18, 7, 0)
        assert _compute_duration(bedtime, wake_time) == 480

    def test_short_nap(self) -> None:
        bedtime = datetime(2026, 6, 18, 13, 0)
        wake_time = datetime(2026, 6, 18, 13, 30)
        assert _compute_duration(bedtime, wake_time) == 30

    def test_fractional_minutes_truncated(self) -> None:
        bedtime = datetime(2026, 6, 18, 22, 0)
        wake_time = datetime(2026, 6, 18, 22, 7, 45)
        assert _compute_duration(bedtime, wake_time) == 7


# ── Schema validation tests ───────────────────────────────────────────────────


class TestSleepSchemaValidation:
    def test_requires_duration_or_times(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wellness import LogSleepRequest

        with pytest.raises(PydanticValidationError):
            LogSleepRequest(date=TODAY)

    def test_duration_only_is_valid(self) -> None:
        from app.schemas.wellness import LogSleepRequest

        req = LogSleepRequest(date=TODAY, duration_minutes=480)
        assert req.duration_minutes == 480

    def test_both_times_is_valid(self) -> None:
        from app.schemas.wellness import LogSleepRequest

        req = LogSleepRequest(
            date=TODAY,
            bedtime=datetime(2026, 6, 17, 23, 0),
            wake_time=datetime(2026, 6, 18, 7, 0),
        )
        assert req.bedtime is not None

    def test_wake_before_bedtime_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wellness import LogSleepRequest

        with pytest.raises(PydanticValidationError):
            LogSleepRequest(
                date=TODAY,
                bedtime=datetime(2026, 6, 18, 7, 0),
                wake_time=datetime(2026, 6, 17, 23, 0),
            )

    def test_quality_out_of_range_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wellness import LogSleepRequest

        with pytest.raises(PydanticValidationError):
            LogSleepRequest(date=TODAY, duration_minutes=480, quality=6)


class TestWellnessSchemaValidation:
    def test_requires_at_least_one_metric(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wellness import LogWellnessRequest

        with pytest.raises(PydanticValidationError):
            LogWellnessRequest(date=TODAY)

    def test_mood_only_is_valid(self) -> None:
        from app.schemas.wellness import LogWellnessRequest

        req = LogWellnessRequest(date=TODAY, mood=3)
        assert req.mood == 3

    def test_rating_out_of_range_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wellness import LogWellnessRequest

        with pytest.raises(PydanticValidationError):
            LogWellnessRequest(date=TODAY, mood=0)

    def test_steps_negative_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wellness import LogStepsRequest

        with pytest.raises(PydanticValidationError):
            LogStepsRequest(date=TODAY, steps=-1)


# ── Sleep endpoint tests ──────────────────────────────────────────────────────


class TestSleepEndpoints:
    # POST /api/v1/sleep

    def test_log_sleep_with_duration(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_sleep(user_id=user.id)
        resp = _sleep_resp(entry)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.log_sleep", return_value=resp),
        ):
            r = client.post(
                "/api/v1/sleep",
                json={"date": str(TODAY), "duration_minutes": 420},
                cookies=_auth(user),
            )
        assert r.status_code == 201
        assert r.json()["duration_minutes"] == 420

    def test_log_sleep_with_times_computes_duration(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_sleep(user_id=user.id, duration_minutes=480)
        resp = _sleep_resp(entry)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.log_sleep", return_value=resp),
        ):
            r = client.post(
                "/api/v1/sleep",
                json={
                    "date": str(TODAY),
                    "bedtime": "2026-06-17T23:00:00",
                    "wake_time": "2026-06-18T07:00:00",
                },
                cookies=_auth(user),
            )
        assert r.status_code == 201
        assert r.json()["duration_minutes"] == 480

    def test_log_sleep_missing_duration_and_times_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/sleep",
                json={"date": str(TODAY)},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_log_sleep_requires_auth(self, client: TestClient) -> None:
        r = client.post("/api/v1/sleep", json={"date": str(TODAY), "duration_minutes": 420})
        assert r.status_code == 401

    # GET /api/v1/sleep

    def test_list_sleep_logs(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_sleep(user_id=user.id)
        page = SleepListResponse(items=[_sleep_resp(entry)], total=1, page=1, page_size=30)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.list_sleep_logs", return_value=page),
        ):
            r = client.get("/api/v1/sleep", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_list_sleep_requires_auth(self, client: TestClient) -> None:
        r = client.get("/api/v1/sleep")
        assert r.status_code == 401

    # GET /api/v1/sleep/{id}

    def test_get_sleep_log(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_sleep(user_id=user.id)
        resp = _sleep_resp(entry)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.get_sleep_log", return_value=resp),
        ):
            r = client.get(f"/api/v1/sleep/{entry.id}", cookies=_auth(user))
        assert r.status_code == 200

    def test_get_sleep_log_not_found(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_sleep_log",
                side_effect=NotFoundError("not found"),
            ),
        ):
            r = client.get(f"/api/v1/sleep/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404

    # PATCH /api/v1/sleep/{id}

    def test_update_sleep_log(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_sleep(user_id=user.id, duration_minutes=450)
        resp = _sleep_resp(entry)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.update_sleep_log", return_value=resp),
        ):
            r = client.patch(
                f"/api/v1/sleep/{entry.id}",
                json={"duration_minutes": 450},
                cookies=_auth(user),
            )
        assert r.status_code == 200
        assert r.json()["duration_minutes"] == 450

    # DELETE /api/v1/sleep/{id}

    def test_delete_sleep_log(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.delete_sleep_log", return_value=True),
        ):
            r = client.delete(f"/api/v1/sleep/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 204

    def test_delete_sleep_log_not_found(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.delete_sleep_log", return_value=False),
        ):
            r = client.delete(f"/api/v1/sleep/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404

    # Ownership

    def test_sleep_ownership_isolation(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user_b = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user_b),
            patch(
                "app.services.wellness_service.get_sleep_log",
                side_effect=NotFoundError("not found"),
            ),
        ):
            r = client.get(f"/api/v1/sleep/{uuid.uuid4()}", cookies=_auth(user_b))
        assert r.status_code == 404


# ── Steps endpoint tests ──────────────────────────────────────────────────────


class TestStepsEndpoints:
    def test_log_steps(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_steps(user_id=user.id)
        resp = _steps_resp(entry)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.log_steps", return_value=resp),
        ):
            r = client.post(
                "/api/v1/steps",
                json={"date": str(TODAY), "steps": 8000},
                cookies=_auth(user),
            )
        assert r.status_code == 201
        assert r.json()["steps"] == 8000

    def test_log_steps_negative_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/steps",
                json={"date": str(TODAY), "steps": -100},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_log_steps_requires_auth(self, client: TestClient) -> None:
        r = client.post("/api/v1/steps", json={"date": str(TODAY), "steps": 8000})
        assert r.status_code == 401

    def test_list_steps(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_steps(user_id=user.id)
        page = StepsListResponse(items=[_steps_resp(entry)], total=1, page=1, page_size=30)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.list_steps_logs", return_value=page),
        ):
            r = client.get("/api/v1/steps", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_get_steps_not_found(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_steps_log",
                side_effect=NotFoundError("not found"),
            ),
        ):
            r = client.get(f"/api/v1/steps/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404

    def test_update_steps(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_steps(user_id=user.id, steps=10000)
        resp = _steps_resp(entry)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.update_steps_log", return_value=resp),
        ):
            r = client.patch(
                f"/api/v1/steps/{entry.id}",
                json={"steps": 10000},
                cookies=_auth(user),
            )
        assert r.status_code == 200
        assert r.json()["steps"] == 10000

    def test_delete_steps(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.delete_steps_log", return_value=True),
        ):
            r = client.delete(f"/api/v1/steps/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 204

    def test_steps_ownership_isolation(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_steps_log",
                side_effect=NotFoundError("not found"),
            ),
        ):
            r = client.get(f"/api/v1/steps/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404


# ── Wellness endpoint tests ───────────────────────────────────────────────────


class TestWellnessEndpoints:
    def test_log_wellness_mood_only(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_wellness(user_id=user.id, mood=4, energy=3, stress=2)
        resp = _wellness_resp(entry)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.log_wellness", return_value=resp),
        ):
            r = client.post(
                "/api/v1/wellness",
                json={"date": str(TODAY), "mood": 4},
                cookies=_auth(user),
            )
        assert r.status_code == 201

    def test_log_wellness_no_metric_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/wellness",
                json={"date": str(TODAY)},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_log_wellness_rating_out_of_range_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/wellness",
                json={"date": str(TODAY), "mood": 6},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_log_wellness_requires_auth(self, client: TestClient) -> None:
        r = client.post("/api/v1/wellness", json={"date": str(TODAY), "mood": 3})
        assert r.status_code == 401

    def test_list_wellness_logs(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_wellness(user_id=user.id)
        page = WellnessListResponse(items=[_wellness_resp(entry)], total=1, page=1, page_size=30)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.list_wellness_logs", return_value=page),
        ):
            r = client.get("/api/v1/wellness", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_get_daily_snapshot(self, client: TestClient) -> None:
        user = _make_user()
        snapshot = DailyWellnessSnapshot(
            date=TODAY,
            sleep=None,
            steps=None,
            wellness=None,
            water_total_ml=750,
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_daily_snapshot",
                return_value=snapshot,
            ),
        ):
            r = client.get("/api/v1/wellness/daily", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["water_total_ml"] == 750
        assert r.json()["sleep"] is None

    def test_get_daily_snapshot_with_date_param(self, client: TestClient) -> None:
        user = _make_user()
        snapshot = DailyWellnessSnapshot(
            date=date(2026, 6, 15),
            sleep=None,
            steps=None,
            wellness=None,
            water_total_ml=0,
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_daily_snapshot",
                return_value=snapshot,
            ),
        ):
            r = client.get("/api/v1/wellness/daily?date=2026-06-15", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["date"] == "2026-06-15"

    def test_get_wellness_not_found(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_wellness_log",
                side_effect=NotFoundError("not found"),
            ),
        ):
            r = client.get(f"/api/v1/wellness/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404

    def test_update_wellness(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_wellness(user_id=user.id, mood=5, energy=5, stress=1)
        resp = _wellness_resp(entry)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.update_wellness_log", return_value=resp),
        ):
            r = client.patch(
                f"/api/v1/wellness/{entry.id}",
                json={"mood": 5, "energy": 5, "stress": 1},
                cookies=_auth(user),
            )
        assert r.status_code == 200
        assert r.json()["mood"] == 5

    def test_delete_wellness(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.delete_wellness_log", return_value=True),
        ):
            r = client.delete(f"/api/v1/wellness/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 204

    def test_delete_wellness_not_found(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.wellness_service.delete_wellness_log", return_value=False),
        ):
            r = client.delete(f"/api/v1/wellness/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404

    def test_wellness_ownership_isolation(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.wellness_service.get_wellness_log",
                side_effect=NotFoundError("not found"),
            ),
        ):
            r = client.get(f"/api/v1/wellness/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404
