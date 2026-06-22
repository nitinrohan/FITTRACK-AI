"""Tests for /api/v1/measurements/* endpoints.

Covers:
  Service-layer unit tests:
    - _count_recorded
    - _has_any_measurement
    - log_measurement raises ValidationError when no fields provided

  Endpoint tests:
    - POST   /api/v1/measurements     (201, 422, auth guard)
    - GET    /api/v1/measurements     (200, pagination, date range, auth guard)
    - GET    /api/v1/measurements/{id} (200, 404, auth guard)
    - PATCH  /api/v1/measurements/{id} (200, 404, auth guard)
    - DELETE /api/v1/measurements/{id} (204, 404, auth guard)

  Ownership isolation:
    - User A cannot read User B's measurements
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.measurement import BodyMeasurement
from app.schemas.measurement import (
    CreateMeasurementRequest,
    MeasurementResponse,
    UpdateMeasurementRequest,
)
from app.services.measurement_service import _count_recorded, _has_any_measurement

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


def _make_entry(
    *,
    user_id: uuid.UUID,
    waist_cm: float | None = 82.0,
    chest_cm: float | None = 98.0,
    hips_cm: float | None = None,
    measured_at: date = TODAY,
) -> MagicMock:
    e = MagicMock(spec=BodyMeasurement)
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.measured_at = measured_at
    e.waist_cm = waist_cm
    e.chest_cm = chest_cm
    e.hips_cm = hips_cm
    e.shoulders_cm = None
    e.abdomen_cm = None
    e.left_arm_cm = None
    e.right_arm_cm = None
    e.left_forearm_cm = None
    e.right_forearm_cm = None
    e.left_thigh_cm = None
    e.right_thigh_cm = None
    e.left_calf_cm = None
    e.right_calf_cm = None
    e.neck_cm = None
    e.notes = None
    e.created_at = _now()
    e.updated_at = _now()
    return e


def _make_response(entry: MagicMock) -> MeasurementResponse:
    return MeasurementResponse(
        id=entry.id,
        user_id=entry.user_id,
        measured_at=entry.measured_at,
        notes=entry.notes,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        recorded_count=2,
        waist_cm=entry.waist_cm,
        chest_cm=entry.chest_cm,
        hips_cm=entry.hips_cm,
        shoulders_cm=entry.shoulders_cm,
        abdomen_cm=entry.abdomen_cm,
        left_arm_cm=entry.left_arm_cm,
        right_arm_cm=entry.right_arm_cm,
        left_forearm_cm=entry.left_forearm_cm,
        right_forearm_cm=entry.right_forearm_cm,
        left_thigh_cm=entry.left_thigh_cm,
        right_thigh_cm=entry.right_thigh_cm,
        left_calf_cm=entry.left_calf_cm,
        right_calf_cm=entry.right_calf_cm,
        neck_cm=entry.neck_cm,
    )


# ── Service unit tests ────────────────────────────────────────────────────────


class TestCountRecorded:
    def test_counts_non_none_fields(self) -> None:
        user_id = uuid.uuid4()
        entry = _make_entry(user_id=user_id, waist_cm=82.0, chest_cm=98.0, hips_cm=None)
        assert _count_recorded(entry) == 2

    def test_zero_when_all_none(self) -> None:
        user_id = uuid.uuid4()
        entry = _make_entry(user_id=user_id, waist_cm=None, chest_cm=None)
        assert _count_recorded(entry) == 0

    def test_counts_all_fields(self) -> None:
        user_id = uuid.uuid4()
        entry = _make_entry(user_id=user_id)
        # set every field
        for field in [
            "waist_cm",
            "chest_cm",
            "hips_cm",
            "shoulders_cm",
            "abdomen_cm",
            "left_arm_cm",
            "right_arm_cm",
            "left_forearm_cm",
            "right_forearm_cm",
            "left_thigh_cm",
            "right_thigh_cm",
            "left_calf_cm",
            "right_calf_cm",
            "neck_cm",
        ]:
            setattr(entry, field, 50.0)
        assert _count_recorded(entry) == 14


class TestHasAnyMeasurement:
    def test_true_when_one_field_set(self) -> None:
        payload = CreateMeasurementRequest(waist_cm=82.0, measured_at=TODAY)
        assert _has_any_measurement(payload) is True

    def test_false_when_no_fields_set(self) -> None:
        payload = CreateMeasurementRequest(measured_at=TODAY)
        assert _has_any_measurement(payload) is False

    def test_true_for_update_with_field(self) -> None:
        payload = UpdateMeasurementRequest(chest_cm=96.0)
        assert _has_any_measurement(payload) is True


class TestLogMeasurementValidation:
    def test_raises_validation_error_when_no_fields(self) -> None:
        from app.exceptions import ValidationError
        from app.services import measurement_service

        payload = CreateMeasurementRequest(measured_at=TODAY)
        with pytest.raises(ValidationError, match="At least one measurement"):
            measurement_service.log_measurement(MagicMock(), uuid.uuid4(), payload)


# ── POST /api/v1/measurements ─────────────────────────────────────────────────


class TestLogMeasurementEndpoint:
    def test_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user_id=user.id)
        resp_data = _make_response(entry)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.log_measurement",
                return_value=resp_data,
            ),
        ):
            resp = client.post(
                "/api/v1/measurements",
                json={"waist_cm": 82.0, "measured_at": str(TODAY)},
                cookies=_auth(user),
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["waist_cm"] == 82.0

    def test_no_fields_returns_422_from_service(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import ValidationError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.log_measurement",
                side_effect=ValidationError("At least one measurement field must be provided."),
            ),
        ):
            resp = client.post(
                "/api/v1/measurements",
                json={"measured_at": str(TODAY)},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_negative_value_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/measurements",
                json={"waist_cm": -5.0, "measured_at": str(TODAY)},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_value_over_300_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/measurements",
                json={"waist_cm": 500.0, "measured_at": str(TODAY)},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/measurements",
            json={"waist_cm": 80.0, "measured_at": str(TODAY)},
        )
        assert resp.status_code == 401


# ── GET /api/v1/measurements ──────────────────────────────────────────────────


class TestListMeasurements:
    def test_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user_id=user.id)
        from app.schemas.measurement import MeasurementListResponse

        list_resp = MeasurementListResponse(
            entries=[_make_response(entry)],
            total=1,
            page=1,
            page_size=30,
            has_next=False,
            latest=_make_response(entry),
        )

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.list_measurements",
                return_value=list_resp,
            ),
        ):
            resp = client.get("/api/v1/measurements", cookies=_auth(user))

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["entries"]) == 1

    def test_date_range_params_forwarded(self, client: TestClient) -> None:
        user = _make_user()
        captured: dict[str, object] = {}

        def fake_list(db, uid, *, date_from=None, date_to=None, **kwargs):  # type: ignore
            captured["date_from"] = date_from
            captured["date_to"] = date_to
            from app.schemas.measurement import MeasurementListResponse

            return MeasurementListResponse(
                entries=[], total=0, page=1, page_size=30, has_next=False
            )

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.list_measurements",
                side_effect=fake_list,
            ),
        ):
            client.get(
                f"/api/v1/measurements?date_from=2026-01-01&date_to={TODAY}",
                cookies=_auth(user),
            )

        assert captured["date_from"] == date(2026, 1, 1)
        assert captured["date_to"] == TODAY

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/measurements")
        assert resp.status_code == 401

    def test_latest_snapshot_included(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user_id=user.id, waist_cm=80.0, chest_cm=95.0)
        from app.schemas.measurement import MeasurementListResponse

        list_resp = MeasurementListResponse(
            entries=[_make_response(entry)],
            total=1,
            page=1,
            page_size=30,
            has_next=False,
            latest=_make_response(entry),
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.list_measurements",
                return_value=list_resp,
            ),
        ):
            resp = client.get("/api/v1/measurements", cookies=_auth(user))

        assert resp.status_code == 200
        assert resp.json()["latest"] is not None
        assert resp.json()["latest"]["waist_cm"] == 80.0


# ── GET /api/v1/measurements/{id} ────────────────────────────────────────────


class TestGetMeasurement:
    def test_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user_id=user.id)
        resp_data = _make_response(entry)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.get_measurement",
                return_value=resp_data,
            ),
        ):
            resp = client.get(f"/api/v1/measurements/{entry.id}", cookies=_auth(user))

        assert resp.status_code == 200
        assert resp.json()["id"] == str(entry.id)

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import NotFoundError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.get_measurement",
                side_effect=NotFoundError("Measurement entry not found."),
            ),
        ):
            resp = client.get(f"/api/v1/measurements/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/measurements/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── PATCH /api/v1/measurements/{id} ──────────────────────────────────────────


class TestUpdateMeasurement:
    def test_updates_field(self, client: TestClient) -> None:
        user = _make_user()
        entry = _make_entry(user_id=user.id, waist_cm=79.0)
        resp_data = _make_response(entry)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.update_measurement",
                return_value=resp_data,
            ),
        ):
            resp = client.patch(
                f"/api/v1/measurements/{entry.id}",
                json={"waist_cm": 79.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import NotFoundError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.update_measurement",
                side_effect=NotFoundError("Measurement entry not found."),
            ),
        ):
            resp = client.patch(
                f"/api/v1/measurements/{uuid.uuid4()}",
                json={"waist_cm": 80.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.patch(f"/api/v1/measurements/{uuid.uuid4()}", json={"waist_cm": 80.0})
        assert resp.status_code == 401


# ── DELETE /api/v1/measurements/{id} ─────────────────────────────────────────


class TestDeleteMeasurement:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.delete_measurement",
                return_value=True,
            ),
        ):
            resp = client.delete(f"/api/v1/measurements/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.measurement_service.delete_measurement",
                return_value=False,
            ),
        ):
            resp = client.delete(f"/api/v1/measurements/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/measurements/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── Service ownership isolation ────────────────────────────────────────────────


class TestMeasurementOwnership:
    def test_get_not_found_for_other_user_entry(self) -> None:
        """Service returns 404 for entries not owned by the requesting user."""
        from app.exceptions import NotFoundError
        from app.services import measurement_service

        requester_id = uuid.uuid4()

        with (
            patch(
                "app.repositories.measurement_repository.get_measurement_by_id",
                return_value=None,  # repo enforces user_id in WHERE clause
            ),
            pytest.raises(NotFoundError),
        ):
            measurement_service.get_measurement(MagicMock(), uuid.uuid4(), requester_id)

    def test_update_not_found_for_other_user_entry(self) -> None:
        from app.exceptions import NotFoundError
        from app.services import measurement_service

        with (
            patch(
                "app.repositories.measurement_repository.get_measurement_by_id",
                return_value=None,
            ),
            pytest.raises(NotFoundError),
        ):
            measurement_service.update_measurement(
                MagicMock(),
                uuid.uuid4(),
                uuid.uuid4(),
                UpdateMeasurementRequest(waist_cm=82.0),
            )

    def test_delete_returns_false_for_other_user_entry(self) -> None:
        from app.services import measurement_service

        with patch(
            "app.repositories.measurement_repository.get_measurement_by_id",
            return_value=None,
        ):
            result = measurement_service.delete_measurement(MagicMock(), uuid.uuid4(), uuid.uuid4())
        assert result is False


# ── cm_to_inches conversion ───────────────────────────────────────────────────


class TestCmToInches:
    def test_known_conversion(self) -> None:
        from app.schemas.measurement import cm_to_inches

        # 25.4 cm = 10 inches (exactly)
        assert cm_to_inches(25.4) == 10.0

    def test_rounds_to_one_decimal(self) -> None:
        from app.schemas.measurement import cm_to_inches

        # 80 cm ÷ 2.54 = 31.496... → 31.5
        assert cm_to_inches(80.0) == 31.5

    def test_waist_typical_value(self) -> None:
        from app.schemas.measurement import cm_to_inches

        # 76 cm ÷ 2.54 = 29.921 → 29.9
        assert cm_to_inches(76.0) == 29.9
