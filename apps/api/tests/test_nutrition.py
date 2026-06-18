"""Tests for /api/v1/foods/* and /api/v1/nutrition/* endpoints.

Covers:
  Service-layer unit tests:
    - _scale (macro scaling)
    - _sum_macros
    - get_daily_nutrition aggregation
    - daily totals with mixed meal types

  Food API:
    - POST   /api/v1/foods         (201, validation, auth guard)
    - GET    /api/v1/foods         (200, search param, auth guard)
    - GET    /api/v1/foods/{id}    (200, 404 for missing, 404 for other user's food)
    - PATCH  /api/v1/foods/{id}    (200, 403 for system, 403 for other user's)
    - DELETE /api/v1/foods/{id}    (204, 403 for system, 403 for other user's)

  Nutrition log:
    - POST   /api/v1/nutrition/foods          (201, 404 for missing food)
    - GET    /api/v1/nutrition/daily          (200, empty day, with entries)
    - PATCH  /api/v1/nutrition/foods/{id}     (200, 404)
    - DELETE /api/v1/nutrition/foods/{id}     (204, 404)

  Water log:
    - POST   /api/v1/nutrition/water          (201, validation)
    - PATCH  /api/v1/nutrition/water/{id}     (200, 404)
    - DELETE /api/v1/nutrition/water/{id}     (204, 404)

  Ownership isolation:
    - Cannot access other user's private food
    - Cannot access other user's food log
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database import get_db
from app.main import app as fastapi_app
from app.models.nutrition import Food, FoodLog, WaterLog
from app.schemas.nutrition import (
    FoodLogResponse,
    FoodResponse,
    LogFoodRequest,
    MacroTotals,
    UpdateFoodRequest,
)
from app.services.nutrition_service import _scale, _sum_macros

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


TODAY = date.today()


def _make_food(
    *,
    user_id: uuid.UUID | None = None,
    is_system: bool = False,
    name: str = "Chicken Breast",
    calories_per_100g: float = 165.0,
    protein_per_100g: float = 31.0,
    carbs_per_100g: float = 0.0,
    fat_per_100g: float = 3.6,
    fiber_per_100g: float | None = None,
    serving_size_g: float | None = 100.0,
) -> MagicMock:
    f = MagicMock(spec=Food)
    f.id = uuid.uuid4()
    f.user_id = user_id
    f.name = name
    f.brand = None
    f.description = None
    f.calories_per_100g = calories_per_100g
    f.protein_per_100g = protein_per_100g
    f.carbs_per_100g = carbs_per_100g
    f.fat_per_100g = fat_per_100g
    f.fiber_per_100g = fiber_per_100g
    f.sugar_per_100g = None
    f.sodium_per_100g = None
    f.serving_size_g = serving_size_g
    f.serving_unit = None
    f.is_system = is_system
    f.is_active = True
    f.created_at = _now()
    f.updated_at = _now()
    return f


def _food_response(food: MagicMock) -> FoodResponse:
    return FoodResponse(
        id=food.id,
        user_id=food.user_id,
        name=food.name,
        brand=food.brand,
        description=food.description,
        calories_per_100g=food.calories_per_100g,
        protein_per_100g=food.protein_per_100g,
        carbs_per_100g=food.carbs_per_100g,
        fat_per_100g=food.fat_per_100g,
        fiber_per_100g=food.fiber_per_100g,
        sugar_per_100g=food.sugar_per_100g,
        sodium_per_100g=food.sodium_per_100g,
        serving_size_g=food.serving_size_g,
        serving_unit=food.serving_unit,
        is_system=food.is_system,
        created_at=food.created_at,
        updated_at=food.updated_at,
    )


def _make_food_log(
    *,
    user_id: uuid.UUID,
    food: MagicMock,
    meal_type: str = "lunch",
    quantity_g: float = 150.0,
    logged_date: date = TODAY,
) -> MagicMock:
    fl = MagicMock(spec=FoodLog)
    fl.id = uuid.uuid4()
    fl.user_id = user_id
    fl.food_id = food.id
    fl.food = food
    fl.meal_type = meal_type
    fl.quantity_g = quantity_g
    fl.logged_date = logged_date
    fl.notes = None
    fl.created_at = _now()
    fl.updated_at = _now()
    return fl


def _food_log_response(log: MagicMock) -> FoodLogResponse:
    food = log.food
    qty = log.quantity_g
    return FoodLogResponse(
        id=log.id,
        food_id=log.food_id,
        logged_date=log.logged_date,
        meal_type=log.meal_type,
        quantity_g=qty,
        notes=log.notes,
        calories=_scale(food.calories_per_100g, qty),
        protein_g=_scale(food.protein_per_100g, qty),
        carbs_g=_scale(food.carbs_per_100g, qty),
        fat_g=_scale(food.fat_per_100g, qty),
        fiber_g=None,
        food_name=food.name,
        food_brand=food.brand,
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


def _make_water_log(
    *,
    user_id: uuid.UUID,
    amount_ml: int = 250,
    logged_date: date = TODAY,
) -> MagicMock:
    wl = MagicMock(spec=WaterLog)
    wl.id = uuid.uuid4()
    wl.user_id = user_id
    wl.logged_date = logged_date
    wl.amount_ml = amount_ml
    wl.notes = None
    wl.created_at = _now()
    return wl


@contextmanager
def _override_db() -> Iterator[MagicMock]:
    mock_session = MagicMock()
    fastapi_app.dependency_overrides[get_db] = lambda: mock_session
    try:
        yield mock_session
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)


# ── Service unit tests ─────────────────────────────────────────────────────────


class TestScaleHelper:
    def test_scale_100g(self) -> None:
        assert _scale(165.0, 100.0) == 165.0

    def test_scale_half_portion(self) -> None:
        assert _scale(200.0, 50.0) == 100.0

    def test_scale_150g(self) -> None:
        # 165 * 1.5 = 247.5
        assert _scale(165.0, 150.0) == 247.5

    def test_scale_zero_macro(self) -> None:
        assert _scale(0.0, 250.0) == 0.0

    def test_scale_rounds_to_one_decimal(self) -> None:
        # 31 * 73 / 100 = 22.63
        result = _scale(31.0, 73.0)
        assert result == round(31.0 * 73.0 / 100, 1)


class TestSumMacros:
    def test_empty_list(self) -> None:
        result = _sum_macros([])
        assert result.calories == 0.0
        assert result.protein_g == 0.0

    def test_single_entry(self) -> None:
        user_id = uuid.uuid4()
        food = _make_food(user_id=user_id, calories_per_100g=200.0, protein_per_100g=20.0)
        log = _make_food_log(user_id=user_id, food=food, quantity_g=100.0)
        entries = [_food_log_response(log)]
        result = _sum_macros(entries)
        assert result.calories == 200.0
        assert result.protein_g == 20.0

    def test_two_entries_summed(self) -> None:
        user_id = uuid.uuid4()
        food = _make_food(user_id=user_id, calories_per_100g=100.0, protein_per_100g=10.0,
                          carbs_per_100g=20.0, fat_per_100g=5.0)
        log1 = _make_food_log(user_id=user_id, food=food, quantity_g=100.0)
        log2 = _make_food_log(user_id=user_id, food=food, quantity_g=200.0)
        entries = [_food_log_response(log1), _food_log_response(log2)]
        result = _sum_macros(entries)
        assert result.calories == 300.0
        assert result.protein_g == 30.0
        assert result.carbs_g == 60.0
        assert result.fat_g == 15.0


class TestDailyNutrition:
    def test_empty_day(self) -> None:
        from app.services.nutrition_service import get_daily_nutrition
        db = MagicMock()
        user_id = uuid.uuid4()
        with (
            patch(
                "app.repositories.nutrition_repository.list_food_logs_for_date",
                return_value=[],
            ),
            patch(
                "app.repositories.nutrition_repository.list_water_logs_for_date",
                return_value=[],
            ),
        ):
            result = get_daily_nutrition(db, user_id, TODAY)
        assert result.meals == []
        assert result.day_totals.calories == 0.0
        assert result.water_total_ml == 0

    def test_single_meal_section(self) -> None:
        from app.services.nutrition_service import get_daily_nutrition
        db = MagicMock()
        user_id = uuid.uuid4()
        food = _make_food(user_id=user_id)
        log = _make_food_log(user_id=user_id, food=food, meal_type="breakfast")
        with (
            patch(
                "app.repositories.nutrition_repository.list_food_logs_for_date",
                return_value=[log],
            ),
            patch(
                "app.repositories.nutrition_repository.list_water_logs_for_date",
                return_value=[],
            ),
        ):
            result = get_daily_nutrition(db, user_id, TODAY)
        assert len(result.meals) == 1
        assert result.meals[0].meal_type == "breakfast"
        assert len(result.meals[0].entries) == 1

    def test_meals_in_standard_order(self) -> None:
        from app.services.nutrition_service import get_daily_nutrition
        db = MagicMock()
        user_id = uuid.uuid4()
        food = _make_food(user_id=user_id)
        dinner_log = _make_food_log(user_id=user_id, food=food, meal_type="dinner")
        breakfast_log = _make_food_log(user_id=user_id, food=food, meal_type="breakfast")
        with (
            patch(
                "app.repositories.nutrition_repository.list_food_logs_for_date",
                return_value=[dinner_log, breakfast_log],
            ),
            patch(
                "app.repositories.nutrition_repository.list_water_logs_for_date",
                return_value=[],
            ),
        ):
            result = get_daily_nutrition(db, user_id, TODAY)
        # breakfast should come before dinner regardless of input order
        meal_types = [m.meal_type for m in result.meals]
        assert meal_types.index("breakfast") < meal_types.index("dinner")

    def test_water_total_aggregated(self) -> None:
        from app.services.nutrition_service import get_daily_nutrition
        db = MagicMock()
        user_id = uuid.uuid4()
        wl1 = _make_water_log(user_id=user_id, amount_ml=250)
        wl2 = _make_water_log(user_id=user_id, amount_ml=500)
        with (
            patch(
                "app.repositories.nutrition_repository.list_food_logs_for_date",
                return_value=[],
            ),
            patch(
                "app.repositories.nutrition_repository.list_water_logs_for_date",
                return_value=[wl1, wl2],
            ),
        ):
            result = get_daily_nutrition(db, user_id, TODAY)
        assert result.water_total_ml == 750
        assert len(result.water_logs) == 2

    def test_day_totals_sum_all_meals(self) -> None:
        from app.services.nutrition_service import get_daily_nutrition
        db = MagicMock()
        user_id = uuid.uuid4()
        food = _make_food(
            user_id=user_id, calories_per_100g=100.0, protein_per_100g=10.0,
            carbs_per_100g=10.0, fat_per_100g=5.0
        )
        breakfast_log = _make_food_log(
            user_id=user_id, food=food, meal_type="breakfast", quantity_g=100.0
        )
        lunch_log = _make_food_log(
            user_id=user_id, food=food, meal_type="lunch", quantity_g=200.0
        )
        with (
            patch(
                "app.repositories.nutrition_repository.list_food_logs_for_date",
                return_value=[breakfast_log, lunch_log],
            ),
            patch(
                "app.repositories.nutrition_repository.list_water_logs_for_date",
                return_value=[],
            ),
        ):
            result = get_daily_nutrition(db, user_id, TODAY)
        # 100 + 200 = 300 kcal total
        assert result.day_totals.calories == 300.0
        assert result.day_totals.protein_g == 30.0


# ── POST /api/v1/foods ────────────────────────────────────────────────────────


class TestCreateFood:
    def test_returns_201_with_valid_data(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(user_id=user.id)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.create_food",
                return_value=_food_response(food),
            ),
        ):
            resp = client.post(
                "/api/v1/foods",
                json={
                    "name": "Chicken Breast",
                    "calories_per_100g": 165.0,
                    "protein_per_100g": 31.0,
                    "carbs_per_100g": 0.0,
                    "fat_per_100g": 3.6,
                },
                cookies=_auth(user),
            )

        assert resp.status_code == 201
        assert resp.json()["name"] == food.name

    def test_missing_calories_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/foods",
                json={"name": "Mystery Food"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_empty_name_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/foods",
                json={"name": "", "calories_per_100g": 100.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_negative_calories_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/foods",
                json={"name": "Bad Food", "calories_per_100g": -10.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/foods", json={"name": "x", "calories_per_100g": 1})
        assert resp.status_code == 401


# ── GET /api/v1/foods ─────────────────────────────────────────────────────────


class TestListFoods:
    def test_returns_list(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(is_system=True)
        from app.schemas.nutrition import FoodListResponse
        resp_data = FoodListResponse(
            foods=[_food_response(food)], total=1, page=1, page_size=50
        )

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.list_foods",
                return_value=resp_data,
            ),
        ):
            resp = client.get("/api/v1/foods", cookies=_auth(user))

        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert len(resp.json()["foods"]) == 1

    def test_search_param_forwarded(self, client: TestClient) -> None:
        user = _make_user()
        captured: dict[str, Any] = {}

        def fake_list(db, uid, *, search=None, **kwargs):  # type: ignore
            captured["search"] = search
            from app.schemas.nutrition import FoodListResponse
            return FoodListResponse(foods=[], total=0, page=1, page_size=50)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.nutrition_service.list_foods", side_effect=fake_list),
        ):
            client.get("/api/v1/foods?search=chicken", cookies=_auth(user))

        assert captured["search"] == "chicken"

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/foods")
        assert resp.status_code == 401


# ── GET /api/v1/foods/{id} ────────────────────────────────────────────────────


class TestGetFood:
    def test_returns_food(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(user_id=user.id)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.get_food",
                return_value=_food_response(food),
            ),
        ):
            resp = client.get(f"/api/v1/foods/{food.id}", cookies=_auth(user))

        assert resp.status_code == 200
        assert resp.json()["id"] == str(food.id)

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import NotFoundError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.get_food",
                side_effect=NotFoundError("Food not found."),
            ),
        ):
            resp = client.get(f"/api/v1/foods/{uuid.uuid4()}", cookies=_auth(user))

        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/foods/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── PATCH /api/v1/foods/{id} ──────────────────────────────────────────────────


class TestUpdateFood:
    def test_updates_name(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(user_id=user.id, name="Updated Name")

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.update_food",
                return_value=_food_response(food),
            ),
        ):
            resp = client.patch(
                f"/api/v1/foods/{food.id}",
                json={"name": "Updated Name"},
                cookies=_auth(user),
            )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_system_food_returns_403(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import ForbiddenError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.update_food",
                side_effect=ForbiddenError("System foods cannot be modified."),
            ),
        ):
            resp = client.patch(
                f"/api/v1/foods/{uuid.uuid4()}",
                json={"name": "Hack"},
                cookies=_auth(user),
            )

        assert resp.status_code == 403

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.patch(f"/api/v1/foods/{uuid.uuid4()}", json={"name": "x"})
        assert resp.status_code == 401


# ── DELETE /api/v1/foods/{id} ─────────────────────────────────────────────────


class TestDeleteFood:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.nutrition_service.delete_food", return_value=True),
        ):
            resp = client.delete(f"/api/v1/foods/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 204

    def test_system_food_returns_403(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import ForbiddenError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.delete_food",
                side_effect=ForbiddenError("System foods cannot be deleted."),
            ),
        ):
            resp = client.delete(f"/api/v1/foods/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 403

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/foods/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── POST /api/v1/nutrition/foods ──────────────────────────────────────────────


class TestLogFood:
    def test_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(user_id=user.id)
        log = _make_food_log(user_id=user.id, food=food)
        log_resp = _food_log_response(log)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.log_food",
                return_value=log_resp,
            ),
        ):
            resp = client.post(
                "/api/v1/nutrition/foods",
                json={
                    "food_id": str(food.id),
                    "logged_date": str(TODAY),
                    "meal_type": "lunch",
                    "quantity_g": 150.0,
                },
                cookies=_auth(user),
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["meal_type"] == "lunch"
        assert data["quantity_g"] == 150.0

    def test_zero_quantity_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/nutrition/foods",
                json={
                    "food_id": str(uuid.uuid4()),
                    "logged_date": str(TODAY),
                    "quantity_g": 0,
                },
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_missing_food_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import NotFoundError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.log_food",
                side_effect=NotFoundError("Food not found."),
            ),
        ):
            resp = client.post(
                "/api/v1/nutrition/foods",
                json={
                    "food_id": str(uuid.uuid4()),
                    "logged_date": str(TODAY),
                    "quantity_g": 100,
                },
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/nutrition/foods",
            json={"food_id": str(uuid.uuid4()), "logged_date": str(TODAY), "quantity_g": 100},
        )
        assert resp.status_code == 401


# ── GET /api/v1/nutrition/daily ───────────────────────────────────────────────


class TestGetDailyNutrition:
    def _empty_day(self) -> object:
        from app.schemas.nutrition import DailyNutritionResponse
        return DailyNutritionResponse(
            date=TODAY,
            meals=[],
            day_totals=MacroTotals(
                calories=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, fiber_g=0.0
            ),
            water_logs=[],
            water_total_ml=0,
        )

    def test_returns_200_with_date(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.get_daily_nutrition",
                return_value=self._empty_day(),
            ),
        ):
            resp = client.get(
                f"/api/v1/nutrition/daily?date={TODAY}",
                cookies=_auth(user),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == str(TODAY)
        assert data["water_total_ml"] == 0

    def test_missing_date_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.get("/api/v1/nutrition/daily", cookies=_auth(user))
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/nutrition/daily?date={TODAY}")
        assert resp.status_code == 401

    def test_with_food_and_water_entries(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(user_id=user.id, calories_per_100g=200.0, protein_per_100g=20.0)
        log = _make_food_log(user_id=user.id, food=food, meal_type="breakfast", quantity_g=100.0)
        log_resp = _food_log_response(log)

        from app.schemas.nutrition import DailyNutritionResponse, MealSection, WaterLogResponse
        water_id = uuid.uuid4()
        day = DailyNutritionResponse(
            date=TODAY,
            meals=[
                MealSection(
                    meal_type="breakfast",
                    entries=[log_resp],
                    totals=MacroTotals(
                        calories=200.0, protein_g=20.0, carbs_g=0.0, fat_g=3.6, fiber_g=0.0
                    ),
                )
            ],
            day_totals=MacroTotals(
                calories=200.0, protein_g=20.0, carbs_g=0.0, fat_g=3.6, fiber_g=0.0
            ),
            water_logs=[
                WaterLogResponse(
                    id=water_id,
                    logged_date=TODAY,
                    amount_ml=500,
                    notes=None,
                    created_at=_now(),
                )
            ],
            water_total_ml=500,
        )

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.get_daily_nutrition",
                return_value=day,
            ),
        ):
            resp = client.get(
                f"/api/v1/nutrition/daily?date={TODAY}",
                cookies=_auth(user),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["meals"]) == 1
        assert data["meals"][0]["meal_type"] == "breakfast"
        assert data["day_totals"]["calories"] == 200.0
        assert data["water_total_ml"] == 500


# ── PATCH /api/v1/nutrition/foods/{id} ────────────────────────────────────────


class TestUpdateFoodLog:
    def test_updates_quantity(self, client: TestClient) -> None:
        user = _make_user()
        food = _make_food(user_id=user.id)
        log = _make_food_log(user_id=user.id, food=food, quantity_g=200.0)
        log_resp = _food_log_response(log)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.update_food_log",
                return_value=log_resp,
            ),
        ):
            resp = client.patch(
                f"/api/v1/nutrition/foods/{log.id}",
                json={"quantity_g": 200.0},
                cookies=_auth(user),
            )

        assert resp.status_code == 200

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.update_food_log",
                return_value=None,
            ),
        ):
            resp = client.patch(
                f"/api/v1/nutrition/foods/{uuid.uuid4()}",
                json={"quantity_g": 100.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.patch(
            f"/api/v1/nutrition/foods/{uuid.uuid4()}",
            json={"quantity_g": 100.0},
        )
        assert resp.status_code == 401


# ── DELETE /api/v1/nutrition/foods/{id} ───────────────────────────────────────


class TestDeleteFoodLog:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.nutrition_service.delete_food_log", return_value=True),
        ):
            resp = client.delete(
                f"/api/v1/nutrition/foods/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.nutrition_service.delete_food_log", return_value=False),
        ):
            resp = client.delete(
                f"/api/v1/nutrition/foods/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/nutrition/foods/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── POST /api/v1/nutrition/water ──────────────────────────────────────────────


class TestLogWater:
    def _make_water_resp(self, user_id: uuid.UUID, amount_ml: int = 250) -> object:
        from app.schemas.nutrition import WaterLogResponse
        return WaterLogResponse(
            id=uuid.uuid4(),
            logged_date=TODAY,
            amount_ml=amount_ml,
            notes=None,
            created_at=_now(),
        )

    def test_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.log_water",
                return_value=self._make_water_resp(user.id),
            ),
        ):
            resp = client.post(
                "/api/v1/nutrition/water",
                json={"logged_date": str(TODAY), "amount_ml": 250},
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        assert resp.json()["amount_ml"] == 250

    def test_zero_amount_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/nutrition/water",
                json={"logged_date": str(TODAY), "amount_ml": 0},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_excessive_amount_returns_422(self, client: TestClient) -> None:
        """More than 10 000 ml in a single entry is rejected."""
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/nutrition/water",
                json={"logged_date": str(TODAY), "amount_ml": 99999},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/nutrition/water",
            json={"logged_date": str(TODAY), "amount_ml": 250},
        )
        assert resp.status_code == 401


# ── PATCH /api/v1/nutrition/water/{id} ────────────────────────────────────────


class TestUpdateWaterLog:
    def test_updates_amount(self, client: TestClient) -> None:
        user = _make_user()
        from app.schemas.nutrition import WaterLogResponse
        resp_data = WaterLogResponse(
            id=uuid.uuid4(), logged_date=TODAY, amount_ml=500,
            notes=None, created_at=_now()
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.update_water_log",
                return_value=resp_data,
            ),
        ):
            resp = client.patch(
                f"/api/v1/nutrition/water/{uuid.uuid4()}",
                json={"amount_ml": 500},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        assert resp.json()["amount_ml"] == 500

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.nutrition_service.update_water_log",
                return_value=None,
            ),
        ):
            resp = client.patch(
                f"/api/v1/nutrition/water/{uuid.uuid4()}",
                json={"amount_ml": 250},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.patch(
            f"/api/v1/nutrition/water/{uuid.uuid4()}",
            json={"amount_ml": 250},
        )
        assert resp.status_code == 401


# ── DELETE /api/v1/nutrition/water/{id} ───────────────────────────────────────


class TestDeleteWaterLog:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.nutrition_service.delete_water_log", return_value=True),
        ):
            resp = client.delete(
                f"/api/v1/nutrition/water/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.nutrition_service.delete_water_log", return_value=False),
        ):
            resp = client.delete(
                f"/api/v1/nutrition/water/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/nutrition/water/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── Service ownership isolation ────────────────────────────────────────────────


class TestNutritionServiceOwnership:
    def test_get_food_raises_not_found_for_other_users_food(self) -> None:
        from app.exceptions import NotFoundError
        from app.services import nutrition_service

        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        food = _make_food(user_id=owner_id, is_system=False)

        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=food,
            ),
            pytest.raises(NotFoundError),
        ):
            nutrition_service.get_food(MagicMock(), food.id, requester_id)

    def test_update_food_raises_forbidden_for_system(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import nutrition_service

        food = _make_food(is_system=True)
        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=food,
            ),
            pytest.raises(ForbiddenError),
        ):
            nutrition_service.update_food(
                MagicMock(), food.id, uuid.uuid4(), UpdateFoodRequest(name="Hack")
            )

    def test_update_food_raises_forbidden_for_other_users_food(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import nutrition_service

        owner_id = uuid.uuid4()
        food = _make_food(user_id=owner_id, is_system=False)
        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=food,
            ),
            pytest.raises(ForbiddenError),
        ):
            nutrition_service.update_food(
                MagicMock(), food.id, uuid.uuid4(), UpdateFoodRequest(name="Hack")
            )

    def test_delete_food_raises_forbidden_for_system(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import nutrition_service

        food = _make_food(is_system=True)
        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=food,
            ),
            pytest.raises(ForbiddenError),
        ):
            nutrition_service.delete_food(MagicMock(), food.id, uuid.uuid4())

    def test_delete_food_raises_forbidden_for_other_users_food(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import nutrition_service

        owner_id = uuid.uuid4()
        food = _make_food(user_id=owner_id, is_system=False)
        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=food,
            ),
            pytest.raises(ForbiddenError),
        ):
            nutrition_service.delete_food(MagicMock(), food.id, uuid.uuid4())

    def test_log_food_raises_not_found_for_other_users_private_food(self) -> None:
        from app.exceptions import NotFoundError
        from app.services import nutrition_service

        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        food = _make_food(user_id=owner_id, is_system=False)

        payload = LogFoodRequest(
            food_id=food.id,
            logged_date=TODAY,
            meal_type="lunch",
            quantity_g=100.0,
        )

        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=food,
            ),
            pytest.raises(NotFoundError),
        ):
            nutrition_service.log_food(MagicMock(), requester_id, payload)
