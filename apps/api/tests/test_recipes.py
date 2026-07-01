"""Tests for the recipes feature (save a food combo, re-log it later).

Covers:
  - Macro math: item + recipe totals computed deterministically from the
    underlying Food's current per-100g values.
  - CRUD: create validates food ownership/visibility, get/update/delete
    enforce recipe ownership (404s rather than leaking existence).
  - log_recipe: creates one FoodLog per item, scale_factor multiplies every
    item's saved quantity, unknown meal_type falls back to "other".
  - Endpoint: auth guard, validation.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.exceptions import NotFoundError
from app.models.nutrition import Food, FoodLog
from app.models.recipe import Recipe, RecipeItem
from app.schemas.recipe import (
    CreateRecipeRequest,
    LogRecipeRequest,
    RecipeItemInput,
    UpdateRecipeRequest,
)

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


def _make_food(
    *,
    user_id: uuid.UUID | None = None,
    is_system: bool = False,
    is_active: bool = True,
    name: str = "Oats",
    cal: float = 389.0,
    pro: float = 13.0,
    carb: float = 66.0,
    fat: float = 7.0,
    fiber: float | None = 10.0,
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
    f.is_system = is_system
    f.is_active = is_active
    return f


def _make_recipe_item(*, food: MagicMock, quantity_g: float = 100.0, position: int = 0) -> MagicMock:
    item = MagicMock(spec=RecipeItem)
    item.food_id = food.id
    item.food = food
    item.quantity_g = quantity_g
    item.position = position
    return item


def _make_recipe(
    *, user_id: uuid.UUID, items: list[MagicMock], name: str = "Breakfast bowl"
) -> MagicMock:
    r = MagicMock(spec=Recipe)
    r.id = uuid.uuid4()
    r.user_id = user_id
    r.name = name
    r.description = None
    r.items = items
    r.created_at = _now()
    r.updated_at = _now()
    return r


def _make_food_log(*, user_id: uuid.UUID, food: MagicMock, quantity_g: float, meal_type: str = "other") -> MagicMock:
    fl = MagicMock(spec=FoodLog)
    fl.id = uuid.uuid4()
    fl.user_id = user_id
    fl.food_id = food.id
    fl.food = food
    fl.meal_type = meal_type
    fl.quantity_g = quantity_g
    fl.logged_date = TODAY
    fl.notes = None
    fl.created_at = _now()
    fl.updated_at = _now()
    return fl


# ── Macro math ────────────────────────────────────────────────────────────────


class TestRecipeMacroMath:
    def test_item_response_scales_from_food(self) -> None:
        from app.services.recipe_service import _build_item_response

        food = _make_food(cal=200.0, pro=20.0, carb=10.0, fat=5.0, fiber=2.0)
        item = _make_recipe_item(food=food, quantity_g=150.0)
        result = _build_item_response(item)
        assert result.calories == 300.0  # 200 * 1.5
        assert result.protein_g == 30.0
        assert result.fiber_g == 3.0

    def test_missing_fiber_stays_none(self) -> None:
        from app.services.recipe_service import _build_item_response

        food = _make_food(fiber=None)
        item = _make_recipe_item(food=food, quantity_g=100.0)
        result = _build_item_response(item)
        assert result.fiber_g is None

    def test_recipe_totals_sum_all_items(self) -> None:
        from app.services.recipe_service import _build_recipe_response

        food1 = _make_food(cal=100.0, pro=10.0, carb=10.0, fat=5.0, fiber=1.0)
        food2 = _make_food(cal=50.0, pro=5.0, carb=5.0, fat=2.0, fiber=0.5)
        items = [
            _make_recipe_item(food=food1, quantity_g=100.0, position=0),
            _make_recipe_item(food=food2, quantity_g=200.0, position=1),
        ]
        recipe = _make_recipe(user_id=uuid.uuid4(), items=items)
        result = _build_recipe_response(recipe)
        # food1@100g = 100 kcal, food2@200g = 100 kcal -> 200 total
        assert result.totals.calories == 200.0
        assert len(result.items) == 2


# ── CRUD ──────────────────────────────────────────────────────────────────────


class TestCreateRecipe:
    def test_rejects_food_owned_by_another_user(self) -> None:
        from app.services import recipe_service

        db = MagicMock()
        owner = uuid.uuid4()
        other_users_food = _make_food(user_id=uuid.uuid4(), is_system=False)
        payload = CreateRecipeRequest(
            name="Test", items=[RecipeItemInput(food_id=other_users_food.id, quantity_g=100)]
        )
        with (
            patch(
                "app.repositories.nutrition_repository.get_food_by_id",
                return_value=other_users_food,
            ),
            pytest.raises(NotFoundError),
        ):
            recipe_service.create_recipe(db, owner, payload)

    def test_allows_system_food(self) -> None:
        from app.services import recipe_service

        db = MagicMock()
        user_id = uuid.uuid4()
        system_food = _make_food(user_id=None, is_system=True)
        recipe = _make_recipe(user_id=user_id, items=[_make_recipe_item(food=system_food, quantity_g=50)])
        recipe.name = "Test"

        with (
            patch("app.repositories.nutrition_repository.get_food_by_id", return_value=system_food),
            patch("app.repositories.recipe_repository.create_recipe", return_value=recipe),
            patch("app.repositories.recipe_repository.add_item"),
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
        ):
            payload = CreateRecipeRequest(
                name="Test", items=[RecipeItemInput(food_id=system_food.id, quantity_g=50)]
            )
            result = recipe_service.create_recipe(db, user_id, payload)
        assert result.name == "Test"
        db.commit.assert_called_once()


class TestGetRecipe:
    def test_other_users_recipe_is_404(self) -> None:
        from app.services import recipe_service

        db = MagicMock()
        owner = uuid.uuid4()
        intruder = uuid.uuid4()
        food = _make_food()
        recipe = _make_recipe(user_id=owner, items=[_make_recipe_item(food=food)])

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            pytest.raises(NotFoundError),
        ):
            recipe_service.get_recipe(db, recipe.id, intruder)

    def test_missing_recipe_is_404(self) -> None:
        from app.services import recipe_service

        db = MagicMock()
        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=None),
            pytest.raises(NotFoundError),
        ):
            recipe_service.get_recipe(db, uuid.uuid4(), uuid.uuid4())


class TestUpdateRecipe:
    def test_replaces_items_when_provided(self) -> None:
        from app.services import recipe_service

        db = MagicMock()
        user_id = uuid.uuid4()
        food = _make_food()
        new_food = _make_food(name="Rice", user_id=user_id)
        recipe = _make_recipe(user_id=user_id, items=[_make_recipe_item(food=food)])

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            patch("app.repositories.nutrition_repository.get_food_by_id", return_value=new_food),
            patch("app.repositories.recipe_repository.replace_items") as replace_mock,
        ):
            payload = UpdateRecipeRequest(items=[RecipeItemInput(food_id=new_food.id, quantity_g=80)])
            recipe_service.update_recipe(db, recipe.id, user_id, payload)

        replace_mock.assert_called_once()
        db.commit.assert_called_once()


class TestDeleteRecipe:
    def test_deletes_owned_recipe(self) -> None:
        from app.services import recipe_service

        db = MagicMock()
        user_id = uuid.uuid4()
        recipe = _make_recipe(user_id=user_id, items=[_make_recipe_item(food=_make_food())])

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            patch("app.repositories.recipe_repository.delete_recipe") as delete_mock,
        ):
            recipe_service.delete_recipe(db, recipe.id, user_id)

        delete_mock.assert_called_once_with(db, recipe)
        db.commit.assert_called_once()


# ── Logging a recipe ─────────────────────────────────────────────────────────


class TestLogRecipe:
    def test_creates_one_log_per_item_at_saved_quantity(self) -> None:
        from app.services import recipe_service

        user_id = uuid.uuid4()
        db = MagicMock()
        food1 = _make_food(name="Oats", cal=389, pro=13, carb=66, fat=7, fiber=10)
        food2 = _make_food(name="Almond milk", cal=13, pro=0.4, carb=0.3, fat=1.1, fiber=0)
        items = [
            _make_recipe_item(food=food1, quantity_g=45.0, position=0),
            _make_recipe_item(food=food2, quantity_g=200.0, position=1),
        ]
        recipe = _make_recipe(user_id=user_id, items=items)

        log1 = _make_food_log(user_id=user_id, food=food1, quantity_g=45.0, meal_type="breakfast")
        log2 = _make_food_log(user_id=user_id, food=food2, quantity_g=200.0, meal_type="breakfast")

        payload = LogRecipeRequest(logged_date=TODAY, meal_type="breakfast", scale_factor=1.0)

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            patch(
                "app.repositories.nutrition_repository.create_food_log",
                side_effect=[log1, log2],
            ) as create_log_mock,
            patch(
                "app.repositories.nutrition_repository.get_food_log_by_id",
                side_effect=[log1, log2],
            ),
        ):
            entries, totals = recipe_service.log_recipe(db, recipe.id, user_id, payload)

        assert len(entries) == 2
        assert create_log_mock.call_args_list[0].kwargs["quantity_g"] == 45.0
        assert create_log_mock.call_args_list[1].kwargs["quantity_g"] == 200.0
        assert "From recipe" in create_log_mock.call_args_list[0].kwargs["notes"]
        assert totals.calories == round(entries[0].calories + entries[1].calories, 1)
        db.commit.assert_called_once()

    def test_scale_factor_multiplies_every_item(self) -> None:
        from app.services import recipe_service

        user_id = uuid.uuid4()
        db = MagicMock()
        food = _make_food(cal=400, pro=80, carb=10, fat=3)
        items = [_make_recipe_item(food=food, quantity_g=30.0, position=0)]
        recipe = _make_recipe(user_id=user_id, items=items)
        log = _make_food_log(user_id=user_id, food=food, quantity_g=15.0)

        payload = LogRecipeRequest(logged_date=TODAY, meal_type="snack", scale_factor=0.5)

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            patch(
                "app.repositories.nutrition_repository.create_food_log", return_value=log
            ) as create_log_mock,
            patch("app.repositories.nutrition_repository.get_food_log_by_id", return_value=log),
        ):
            recipe_service.log_recipe(db, recipe.id, user_id, payload)

        # 30g saved * 0.5 scale = 15g logged
        assert create_log_mock.call_args.kwargs["quantity_g"] == 15.0

    def test_unknown_meal_type_falls_back_to_other(self) -> None:
        from app.services import recipe_service

        user_id = uuid.uuid4()
        db = MagicMock()
        food = _make_food()
        items = [_make_recipe_item(food=food, quantity_g=100.0)]
        recipe = _make_recipe(user_id=user_id, items=items)
        log = _make_food_log(user_id=user_id, food=food, quantity_g=100.0, meal_type="other")

        payload = LogRecipeRequest.model_construct(
            logged_date=TODAY, meal_type="brunch", scale_factor=1.0
        )

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            patch(
                "app.repositories.nutrition_repository.create_food_log", return_value=log
            ) as create_log_mock,
            patch("app.repositories.nutrition_repository.get_food_log_by_id", return_value=log),
        ):
            recipe_service.log_recipe(db, recipe.id, user_id, payload)

        assert create_log_mock.call_args.kwargs["meal_type"] == "other"

    def test_other_users_recipe_cannot_be_logged(self) -> None:
        from app.services import recipe_service

        owner = uuid.uuid4()
        intruder = uuid.uuid4()
        db = MagicMock()
        recipe = _make_recipe(user_id=owner, items=[_make_recipe_item(food=_make_food())])
        payload = LogRecipeRequest(logged_date=TODAY)

        with (
            patch("app.repositories.recipe_repository.get_recipe_by_id", return_value=recipe),
            pytest.raises(NotFoundError),
        ):
            recipe_service.log_recipe(db, recipe.id, intruder, payload)


# ── Endpoint ─────────────────────────────────────────────────────────────────


class TestEndpoint:
    def test_create_requires_auth(self, client: TestClient) -> None:
        r = client.post("/api/v1/recipes", json={"name": "Test", "items": []})
        assert r.status_code == 401

    def test_create_empty_items_rejected(self, client: TestClient) -> None:
        user = _user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/recipes",
                json={"name": "Test", "items": []},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_log_requires_auth(self, client: TestClient) -> None:
        r = client.post(
            f"/api/v1/recipes/{uuid.uuid4()}/log",
            json={"logged_date": str(TODAY)},
        )
        assert r.status_code == 401

    def test_invalid_scale_factor_rejected(self, client: TestClient) -> None:
        user = _user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                f"/api/v1/recipes/{uuid.uuid4()}/log",
                json={"logged_date": str(TODAY), "scale_factor": 0},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_get_missing_recipe_is_404(self, client: TestClient) -> None:
        user = _user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.recipe_service.get_recipe",
                side_effect=NotFoundError("Recipe not found."),
            ),
        ):
            r = client.get(f"/api/v1/recipes/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404
