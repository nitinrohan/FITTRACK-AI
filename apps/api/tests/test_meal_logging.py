"""Tests for bulk multi-item meal logging (POST /api/v1/nutrition/log-meal).

Covers:
  - nutrition_service.log_meal: creates one Food + one FoodLog per item in a
    single atomic commit, returns correct per-entry macros and day totals.
  - Endpoint: auth required, validation (empty items list rejected).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.nutrition import Food, FoodLog
from app.schemas.ai import LogMealItemInput, LogMealRequest

TODAY = date.today()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _make_food_for_item(
    *, user_id: uuid.UUID, name: str, cal: float, pro: float, carb: float, fat: float, fiber: float | None
) -> MagicMock:
    f = MagicMock(spec=Food)
    f.id = uuid.uuid4()
    f.user_id = user_id
    f.name = name
    f.brand = None
    f.calories_per_100g = cal
    f.protein_per_100g = pro
    f.carbs_per_100g = carb
    f.fat_per_100g = fat
    f.fiber_per_100g = fiber
    f.is_system = False
    return f


def _make_log_for_food(*, user_id: uuid.UUID, food: MagicMock, quantity_g: float) -> MagicMock:
    fl = MagicMock(spec=FoodLog)
    fl.id = uuid.uuid4()
    fl.user_id = user_id
    fl.food_id = food.id
    fl.food = food
    fl.meal_type = "breakfast"
    fl.quantity_g = quantity_g
    fl.logged_date = TODAY
    fl.notes = None
    fl.created_at = _now()
    fl.updated_at = _now()
    return fl


class TestLogMealService:
    def test_creates_one_food_and_log_per_item(self) -> None:
        from app.services import nutrition_service

        user_id = uuid.uuid4()
        db = MagicMock()

        oats_food = _make_food_for_item(
            user_id=user_id, name="Oats", cal=389, pro=13, carb=66, fat=7, fiber=10
        )
        milk_food = _make_food_for_item(
            user_id=user_id, name="Almond milk", cal=13, pro=0.4, carb=0.3, fat=1.1, fiber=0
        )
        oats_log = _make_log_for_food(user_id=user_id, food=oats_food, quantity_g=45)
        milk_log = _make_log_for_food(user_id=user_id, food=milk_food, quantity_g=200)

        payload = LogMealRequest(
            logged_date=TODAY,
            meal_type="breakfast",
            items=[
                LogMealItemInput(
                    name="Oats",
                    quantity_g=45,
                    calories_per_100g=389,
                    protein_per_100g=13,
                    carbs_per_100g=66,
                    fat_per_100g=7,
                    fiber_per_100g=10,
                ),
                LogMealItemInput(
                    name="Almond milk",
                    quantity_g=200,
                    calories_per_100g=13,
                    protein_per_100g=0.4,
                    carbs_per_100g=0.3,
                    fat_per_100g=1.1,
                    fiber_per_100g=0,
                ),
            ],
        )

        with (
            patch(
                "app.repositories.nutrition_repository.create_food",
                side_effect=[oats_food, milk_food],
            ),
            patch(
                "app.repositories.nutrition_repository.create_food_log",
                side_effect=[oats_log, milk_log],
            ),
            patch(
                "app.repositories.nutrition_repository.get_food_log_by_id",
                side_effect=[oats_log, milk_log],
            ),
        ):
            entries, totals = nutrition_service.log_meal(db, user_id, payload)

        assert len(entries) == 2
        assert entries[0].food_name == "Oats"
        assert entries[0].quantity_g == 45
        # 45g @ 389kcal/100g = 175.05 -> 175.1
        assert entries[0].calories == round(389 * 0.45, 1)
        assert entries[1].food_name == "Almond milk"

        # Totals sum both entries.
        expected_cal = round(entries[0].calories + entries[1].calories, 1)
        assert totals.calories == expected_cal
        db.commit.assert_called_once()

    def test_unknown_meal_type_falls_back_to_other(self) -> None:
        from app.services import nutrition_service

        user_id = uuid.uuid4()
        db = MagicMock()
        food = _make_food_for_item(
            user_id=user_id, name="Snack bar", cal=450, pro=10, carb=50, fat=20, fiber=None
        )
        log = _make_log_for_food(user_id=user_id, food=food, quantity_g=100)
        log.meal_type = "other"

        payload = LogMealRequest(
            logged_date=TODAY,
            meal_type="brunch",  # not a real MealType value
            items=[
                LogMealItemInput(
                    name="Snack bar",
                    quantity_g=100,
                    calories_per_100g=450,
                    protein_per_100g=10,
                    carbs_per_100g=50,
                    fat_per_100g=20,
                )
            ],
        )

        with (
            patch("app.repositories.nutrition_repository.create_food", return_value=food),
            patch(
                "app.repositories.nutrition_repository.create_food_log",
                return_value=log,
            ) as create_log_mock,
            patch(
                "app.repositories.nutrition_repository.get_food_log_by_id",
                return_value=log,
            ),
        ):
            nutrition_service.log_meal(db, user_id, payload)

        assert create_log_mock.call_args.kwargs["meal_type"] == "other"


class TestEndpoint:
    def test_requires_auth(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/nutrition/log-meal",
            json={"logged_date": str(TODAY), "items": []},
        )
        assert r.status_code == 401

    def test_empty_items_list_rejected(self, client: TestClient) -> None:
        user = _user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/nutrition/log-meal",
                json={"logged_date": str(TODAY), "items": []},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_valid_payload_returns_created_entries(self, client: TestClient) -> None:
        from app.schemas.ai import LogMealResponse
        from app.schemas.nutrition import MacroTotals

        user = _user()
        fake_result = LogMealResponse(
            entries=[],
            totals=MacroTotals(calories=0, protein_g=0, carbs_g=0, fat_g=0, fiber_g=0),
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.log_meal",
                return_value=([], fake_result.totals),
            ),
        ):
            r = client.post(
                "/api/v1/nutrition/log-meal",
                json={
                    "logged_date": str(TODAY),
                    "meal_type": "breakfast",
                    "items": [
                        {
                            "name": "Oats",
                            "quantity_g": 45,
                            "calories_per_100g": 389,
                        }
                    ],
                },
                cookies=_auth(user),
            )
        assert r.status_code == 201
        assert r.json()["entries"] == []
