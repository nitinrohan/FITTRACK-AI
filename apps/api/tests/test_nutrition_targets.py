"""Tests for user-configurable daily nutrition targets.

Covers:
  - nutrition_target_service: get returns is_set=False / all-null when no
    row exists; update upserts and reflects is_set correctly.
  - Endpoint auth guard + validation.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.schemas.nutrition_target import UpdateNutritionTargetRequest


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


class TestGetTargets:
    def test_no_row_returns_all_null_and_unset(self) -> None:
        from app.services import nutrition_target_service as svc

        db = MagicMock()
        with patch(
            "app.repositories.nutrition_target_repository.get_for_user",
            return_value=None,
        ):
            result = svc.get_targets(db, uuid.uuid4())
        assert result.is_set is False
        assert result.protein_target_g is None
        assert result.calorie_target_kcal is None

    def test_row_with_one_field_is_set_true(self) -> None:
        from app.services import nutrition_target_service as svc

        db = MagicMock()
        row = MagicMock()
        row.calorie_target_kcal = None
        row.protein_target_g = 150.0
        row.carbs_target_g = None
        row.fat_target_g = None
        row.fiber_target_g = None
        row.updated_at = None
        with patch(
            "app.repositories.nutrition_target_repository.get_for_user",
            return_value=row,
        ):
            result = svc.get_targets(db, uuid.uuid4())
        assert result.is_set is True
        assert result.protein_target_g == 150.0


class TestUpdateTargets:
    def test_upsert_persists_and_commits(self) -> None:
        from app.services import nutrition_target_service as svc

        db = MagicMock()
        user_id = uuid.uuid4()
        row = MagicMock()
        row.calorie_target_kcal = 2000
        row.protein_target_g = 150
        row.carbs_target_g = 200
        row.fat_target_g = 70
        row.fiber_target_g = 30
        row.updated_at = None

        payload = UpdateNutritionTargetRequest(
            calorie_target_kcal=2000,
            protein_target_g=150,
            carbs_target_g=200,
            fat_target_g=70,
            fiber_target_g=30,
        )
        with (
            patch(
                "app.repositories.nutrition_target_repository.upsert",
                return_value=row,
            ) as upsert_mock,
            patch(
                "app.repositories.nutrition_target_repository.get_for_user",
                return_value=row,
            ),
        ):
            result = svc.update_targets(db, user_id, payload)

        upsert_mock.assert_called_once()
        assert upsert_mock.call_args.kwargs["protein_target_g"] == 150
        assert result.protein_target_g == 150
        assert result.is_set is True
        db.commit.assert_called_once()


class TestEndpoint:
    def test_get_requires_auth(self, client: TestClient) -> None:
        r = client.get("/api/v1/nutrition/targets")
        assert r.status_code == 401

    def test_put_requires_auth(self, client: TestClient) -> None:
        r = client.put("/api/v1/nutrition/targets", json={"protein_target_g": 150})
        assert r.status_code == 401

    def test_negative_target_rejected(self, client: TestClient) -> None:
        user = _user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.put(
                "/api/v1/nutrition/targets",
                json={"protein_target_g": -10},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_get_returns_preview(self, client: TestClient) -> None:
        from app.schemas.nutrition_target import NutritionTargetResponse

        user = _user()
        preview = NutritionTargetResponse(
            calorie_target_kcal=None,
            protein_target_g=None,
            carbs_target_g=None,
            fat_target_g=None,
            fiber_target_g=None,
            is_set=False,
            updated_at=None,
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_target_service.get_targets",
                return_value=preview,
            ),
        ):
            r = client.get("/api/v1/nutrition/targets", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["is_set"] is False
