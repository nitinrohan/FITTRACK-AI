"""Tests for the stress domain (service calculations + endpoints)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.schemas.stress import StressLogResponse
from app.services import stress_service as svc


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


# ── classify_band ───────────────────────────────────────────────────────────────


class TestClassifyBand:
    def test_boundaries(self) -> None:
        assert svc.classify_band(0) == "low"
        assert svc.classify_band(33) == "low"
        assert svc.classify_band(34) == "moderate"
        assert svc.classify_band(66) == "moderate"
        assert svc.classify_band(67) == "high"
        assert svc.classify_band(100) == "high"


# ── summarise ───────────────────────────────────────────────────────────────────


class TestSummarise:
    def test_empty_is_none_not_zero(self) -> None:
        s = svc.summarise([], on_date=date(2026, 6, 26))
        assert s.count == 0
        assert s.highest is None and s.lowest is None and s.average is None
        assert s.band is None

    def test_values(self) -> None:
        s = svc.summarise([10, 50, 90], on_date=date(2026, 6, 26))
        assert s.count == 3
        assert s.highest == 90
        assert s.lowest == 10
        assert s.average == 50
        assert s.band == "moderate"


# ── day bounds (timezone) ───────────────────────────────────────────────────────


class TestDayBounds:
    def test_utc_day(self) -> None:
        start, end = svc._day_bounds_utc(date(2026, 6, 26), "UTC")
        assert start == datetime(2026, 6, 26, 0, 0)
        assert end == datetime(2026, 6, 27, 0, 0)

    def test_offset_zone_shifts_window(self) -> None:
        # New York is UTC-4 in June; local midnight is 04:00 UTC.
        start, end = svc._day_bounds_utc(date(2026, 6, 26), "America/New_York")
        assert start == datetime(2026, 6, 26, 4, 0)
        assert end == datetime(2026, 6, 27, 4, 0)

    def test_bad_zone_falls_back_to_utc(self) -> None:
        start, _ = svc._day_bounds_utc(date(2026, 6, 26), "Not/AZone")
        assert start == datetime(2026, 6, 26, 0, 0)


# ── Endpoints ───────────────────────────────────────────────────────────────────


def _sample_response(user_id: uuid.UUID) -> StressLogResponse:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return StressLogResponse(
        id=uuid.uuid4(),
        user_id=user_id,
        level=42,
        band="moderate",
        recorded_at=now,
        source="manual",
        note=None,
        created_at=now,
        updated_at=now,
    )


class TestEndpoints:
    def test_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/stress").status_code == 401
        assert client.get("/api/v1/stress/summary").status_code == 401

    def test_log_returns_201_with_band(self, client: TestClient) -> None:
        user = _user()
        resp = _sample_response(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.stress_service.log_reading", return_value=resp),
        ):
            r = client.post("/api/v1/stress", json={"level": 42}, cookies=_auth(user))
        assert r.status_code == 201
        assert r.json()["band"] == "moderate"

    def test_log_validates_range(self, client: TestClient) -> None:
        user = _user()
        with patch(
            "app.dependencies.user_repository.get_user_by_id", return_value=user
        ):
            r = client.post("/api/v1/stress", json={"level": 101}, cookies=_auth(user))
        assert r.status_code == 422

    def test_summary_shape(self, client: TestClient) -> None:
        user = _user()
        from app.schemas.stress import StressDailySummary

        summary = StressDailySummary(
            date=date(2026, 6, 26), count=2, highest=70, lowest=10, average=40, band="moderate"
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.stress_service.daily_summary", return_value=summary),
        ):
            r = client.get(
                "/api/v1/stress/summary?date=2026-06-26&tz=UTC", cookies=_auth(user)
            )
        assert r.status_code == 200
        assert r.json()["highest"] == 70 and r.json()["band"] == "moderate"
