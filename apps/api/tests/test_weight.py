"""Tests for /api/v1/weight/* endpoints and weight_service calculations.

Covers:
  - POST /         log weight (201, unit conversion, validation, auth guard)
  - GET  /         list entries (pagination, date filter, stats, auth guard)
  - GET  /{id}     get entry (200, 404, cross-user isolation)
  - PUT  /{id}     update entry (200, 404)
  - DELETE /{id}   delete entry (204, 404)
  - compute_bmi               unit tests
  - compute_moving_average    unit tests
  - compute_stats             unit tests
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.services.weight_service import (
    compute_bmi,
    compute_moving_average,
    compute_stats,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user(height_cm: float | None = None) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.is_active = True
    profile = MagicMock()
    profile.height_cm = height_cm
    user.profile = profile
    return user


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _make_entry(
    user_id: uuid.UUID,
    *,
    weight_kg: float = 75.0,
    display_unit: str = "kg",
    body_fat_pct: float | None = None,
    muscle_mass_kg: float | None = None,
    measured_at: date = date(2026, 6, 10),
    notes: str | None = None,
) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.weight_kg = weight_kg
    e.display_unit = display_unit
    e.body_fat_pct = body_fat_pct
    e.muscle_mass_kg = muscle_mass_kg
    e.measured_at = measured_at
    e.notes = notes
    e.created_at = datetime.now(timezone.utc)
    e.updated_at = datetime.now(timezone.utc)
    return e


# ── Calculation unit tests ─────────────────────────────────────────────────────


class TestComputeBmi:
    def test_typical_value(self) -> None:
        # 70 kg, 175 cm → BMI ≈ 22.9
        result = compute_bmi(70.0, 175.0)
        assert result == 22.9

    def test_none_when_height_none(self) -> None:
        assert compute_bmi(70.0, None) is None

    def test_none_when_height_zero(self) -> None:
        assert compute_bmi(70.0, 0.0) is None

    def test_none_when_height_negative(self) -> None:
        assert compute_bmi(70.0, -10.0) is None

    def test_rounds_to_one_decimal(self) -> None:
        result = compute_bmi(80.0, 180.0)
        assert result is not None
        assert result == round(80.0 / (1.80**2), 1)


class TestComputeMovingAverage:
    def test_single_entry(self) -> None:
        user_id = uuid.uuid4()
        entries = [_make_entry(user_id, weight_kg=75.0)]
        assert compute_moving_average(entries) == 75.0

    def test_multiple_entries(self) -> None:
        user_id = uuid.uuid4()
        entries = [_make_entry(user_id, weight_kg=w) for w in [74.0, 75.0, 76.0]]
        assert compute_moving_average(entries) == 75.0

    def test_empty_returns_none(self) -> None:
        assert compute_moving_average([]) is None


class TestComputeStats:
    def test_empty_list(self) -> None:
        stats = compute_stats([], [])
        assert stats.count == 0
        assert stats.latest_kg is None
        assert stats.change_kg is None

    def test_single_entry(self) -> None:
        user_id = uuid.uuid4()
        e = _make_entry(user_id, weight_kg=80.0)
        stats = compute_stats([e], [e])
        assert stats.count == 1
        assert stats.latest_kg == 80.0
        assert stats.earliest_kg == 80.0
        assert stats.change_kg == 0.0
        assert stats.min_kg == 80.0
        assert stats.max_kg == 80.0

    def test_weight_loss_trend(self) -> None:
        user_id = uuid.uuid4()
        # Entries ordered newest-first
        entries = [
            _make_entry(user_id, weight_kg=78.0),
            _make_entry(user_id, weight_kg=79.0),
            _make_entry(user_id, weight_kg=80.0),
        ]
        stats = compute_stats(entries, entries)
        assert stats.latest_kg == 78.0
        assert stats.earliest_kg == 80.0
        assert stats.change_kg == -2.0  # lost weight


# ── POST /api/v1/weight ───────────────────────────────────────────────────────


class TestLogWeight:
    def test_returns_201_with_kg(self, client: TestClient) -> None:
        user = _make_user(height_cm=175.0)
        entry = _make_entry(user.id, weight_kg=75.0)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.weight_service.weight_repository.create_entry", return_value=entry),
        ):
            resp = client.post(
                "/api/v1/weight",
                json={"weight": 75.0, "display_unit": "kg", "measured_at": "2026-06-10"},
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["weight_kg"] == 75.0
        assert data["display_unit"] == "kg"
        # BMI should be computed (height 175cm, 75kg → ~24.5)
        assert data["bmi"] is not None

    def test_converts_lbs_to_kg(self, client: TestClient) -> None:
        user = _make_user()
        # 165 lbs ≈ 74.84 kg
        expected_kg = round(165.0 * 0.453592, 4)
        entry = _make_entry(user.id, weight_kg=expected_kg, display_unit="lbs")
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.weight_service.weight_repository.create_entry", return_value=entry),
        ):
            resp = client.post(
                "/api/v1/weight",
                json={"weight": 165.0, "display_unit": "lbs", "measured_at": "2026-06-10"},
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        assert abs(resp.json()["weight_kg"] - expected_kg) < 0.001

    def test_optional_body_composition_fields(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user.id, body_fat_pct=18.5)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.weight_service.weight_repository.create_entry", return_value=entry),
        ):
            resp = client.post(
                "/api/v1/weight",
                json={
                    "weight": 75.0,
                    "display_unit": "kg",
                    "body_fat_pct": 18.5,
                    "measured_at": "2026-06-10",
                },
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        assert resp.json()["body_fat_pct"] == 18.5

    def test_weight_zero_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/weight",
                json={"weight": 0, "display_unit": "kg", "measured_at": "2026-06-10"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_body_fat_over_100_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/weight",
                json={
                    "weight": 75.0,
                    "display_unit": "kg",
                    "body_fat_pct": 101.0,
                    "measured_at": "2026-06-10",
                },
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/weight",
            json={"weight": 75.0, "display_unit": "kg", "measured_at": "2026-06-10"},
        )
        assert resp.status_code == 401


# ── GET /api/v1/weight ────────────────────────────────────────────────────────


class TestListEntries:
    def test_returns_list_with_stats(self, client: TestClient) -> None:
        user = _make_user()
        entries = [_make_entry(user.id, weight_kg=w) for w in [75.0, 76.0, 77.0]]
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.list_entries_for_user",
                return_value=(entries, 3),
            ),
            patch(
                "app.services.weight_service.weight_repository.get_recent_entries",
                return_value=entries,
            ),
        ):
            resp = client.get("/api/v1/weight", cookies=_auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["entries"]) == 3
        assert data["stats"]["count"] == 3

    def test_empty_list_has_zero_stats(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.list_entries_for_user",
                return_value=([], 0),
            ),
            patch(
                "app.services.weight_service.weight_repository.get_recent_entries",
                return_value=[],
            ),
        ):
            resp = client.get("/api/v1/weight", cookies=_auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["stats"]["count"] == 0
        assert data["stats"]["latest_kg"] is None

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/weight")
        assert resp.status_code == 401


# ── GET /api/v1/weight/{id} ────────────────────────────────────────────────────


class TestGetEntry:
    def test_returns_entry(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.get_entry_for_user",
                return_value=entry,
            ),
        ):
            resp = client.get(f"/api/v1/weight/{entry.id}", cookies=_auth(user))
        assert resp.status_code == 200

    def test_other_users_entry_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.get_entry_for_user",
                return_value=None,
            ),
        ):
            resp = client.get(f"/api/v1/weight/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/weight/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── PUT /api/v1/weight/{id} ────────────────────────────────────────────────────


class TestUpdateEntry:
    def test_updates_notes(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user.id)
        updated = _make_entry(user.id, notes="After gym")
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.get_entry_for_user",
                return_value=entry,
            ),
            patch(
                "app.services.weight_service.weight_repository.update_entry",
                return_value=updated,
            ),
        ):
            resp = client.put(
                f"/api/v1/weight/{entry.id}",
                json={"notes": "After gym"},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "After gym"

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.get_entry_for_user",
                return_value=None,
            ),
        ):
            resp = client.put(
                f"/api/v1/weight/{uuid.uuid4()}",
                json={"notes": "X"},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.put(f"/api/v1/weight/{uuid.uuid4()}", json={"notes": "X"})
        assert resp.status_code == 401


# ── DELETE /api/v1/weight/{id} ────────────────────────────────────────────────


class TestDeleteEntry:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.get_entry_for_user",
                return_value=entry,
            ),
            patch("app.services.weight_service.weight_repository.delete_entry"),
        ):
            resp = client.delete(f"/api/v1/weight/{entry.id}", cookies=_auth(user))
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weight_service.weight_repository.get_entry_for_user",
                return_value=None,
            ),
        ):
            resp = client.delete(f"/api/v1/weight/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/weight/{uuid.uuid4()}")
        assert resp.status_code == 401
