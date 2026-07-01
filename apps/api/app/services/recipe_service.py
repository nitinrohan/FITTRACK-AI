"""Business logic for the recipes domain.

A recipe is a named, user-owned combination of foods + exact quantities.
Logging a recipe creates ordinary FoodLog rows (via nutrition_repository,
the same rows a manual or AI-estimated entry would create) - a Recipe
itself never appears directly in daily totals, progress, or the dashboard.

Macro figures are always computed fresh from the underlying Food's current
per-100g values (never cached on the recipe), matching how FoodLog display
values work - if a user edits a food's macros later, recipes reflect the
update automatically next time they're viewed or logged.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.nutrition import MEAL_TYPES
from app.models.recipe import Recipe, RecipeItem
from app.repositories import nutrition_repository, recipe_repository
from app.schemas.nutrition import FoodLogResponse, MacroTotals
from app.schemas.recipe import (
    CreateRecipeRequest,
    LogRecipeRequest,
    RecipeItemResponse,
    RecipeListResponse,
    RecipeResponse,
    UpdateRecipeRequest,
)
from app.services.nutrition_calculations import scale_macro, scale_optional_macro, sum_macro_totals

# ── Helpers ───────────────────────────────────────────────────────────────────


def _validate_food_accessible(db: Session, food_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Raise NotFoundError unless the food exists and is visible to this user
    (system food, or one the user owns) - mirrors nutrition_service.log_food."""
    food = nutrition_repository.get_food_by_id(db, food_id)
    if food is None or not food.is_active:
        raise NotFoundError("Food not found.")
    if not food.is_system and food.user_id != user_id:
        raise NotFoundError("Food not found.")


def _build_item_response(item: RecipeItem) -> RecipeItemResponse:
    food = item.food
    qty = item.quantity_g
    return RecipeItemResponse(
        food_id=item.food_id,
        food_name=food.name,
        food_brand=food.brand,
        quantity_g=qty,
        calories=scale_macro(food.calories_per_100g, qty),
        protein_g=scale_macro(food.protein_per_100g, qty),
        carbs_g=scale_macro(food.carbs_per_100g, qty),
        fat_g=scale_macro(food.fat_per_100g, qty),
        fiber_g=scale_optional_macro(food.fiber_per_100g, qty),
    )


def _build_recipe_response(recipe: Recipe) -> RecipeResponse:
    items = [_build_item_response(i) for i in recipe.items]
    calories, protein_g, carbs_g, fat_g, fiber_g = sum_macro_totals(items)
    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        items=items,
        totals=MacroTotals(
            calories=calories, protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g, fiber_g=fiber_g
        ),
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


def _get_owned_recipe(db: Session, recipe_id: uuid.UUID, user_id: uuid.UUID) -> Recipe:
    recipe = recipe_repository.get_recipe_by_id(db, recipe_id)
    if recipe is None or recipe.user_id != user_id:
        raise NotFoundError("Recipe not found.")
    return recipe


# ── CRUD ──────────────────────────────────────────────────────────────────────


def create_recipe(
    db: Session, user_id: uuid.UUID, payload: CreateRecipeRequest
) -> RecipeResponse:
    for item in payload.items:
        _validate_food_accessible(db, item.food_id, user_id)

    recipe = recipe_repository.create_recipe(
        db, user_id=user_id, name=payload.name.strip(), description=payload.description
    )
    for position, item in enumerate(payload.items):
        recipe_repository.add_item(
            db, recipe_id=recipe.id, food_id=item.food_id, quantity_g=item.quantity_g, position=position
        )
    db.commit()

    refreshed = recipe_repository.get_recipe_by_id(db, recipe.id)
    assert refreshed is not None
    return _build_recipe_response(refreshed)


def list_recipes(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> RecipeListResponse:
    recipes, total = recipe_repository.list_recipes(
        db, user_id, search=search, page=page, page_size=page_size
    )
    return RecipeListResponse(
        recipes=[_build_recipe_response(r) for r in recipes],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_recipe(db: Session, recipe_id: uuid.UUID, user_id: uuid.UUID) -> RecipeResponse:
    recipe = _get_owned_recipe(db, recipe_id, user_id)
    return _build_recipe_response(recipe)


def update_recipe(
    db: Session, recipe_id: uuid.UUID, user_id: uuid.UUID, payload: UpdateRecipeRequest
) -> RecipeResponse:
    recipe = _get_owned_recipe(db, recipe_id, user_id)

    if payload.name is not None:
        recipe_repository.update_recipe_fields(db, recipe, name=payload.name.strip())
    if payload.description is not None:
        recipe_repository.update_recipe_fields(db, recipe, description=payload.description)
    if payload.items is not None:
        for item in payload.items:
            _validate_food_accessible(db, item.food_id, user_id)
        recipe_repository.replace_items(
            db, recipe, [(item.food_id, item.quantity_g) for item in payload.items]
        )

    db.commit()
    refreshed = recipe_repository.get_recipe_by_id(db, recipe_id)
    assert refreshed is not None
    return _build_recipe_response(refreshed)


def delete_recipe(db: Session, recipe_id: uuid.UUID, user_id: uuid.UUID) -> None:
    recipe = _get_owned_recipe(db, recipe_id, user_id)
    recipe_repository.delete_recipe(db, recipe)
    db.commit()


# ── Logging a recipe ──────────────────────────────────────────────────────────


def log_recipe(
    db: Session, recipe_id: uuid.UUID, user_id: uuid.UUID, payload: LogRecipeRequest
) -> tuple[list[FoodLogResponse], MacroTotals]:
    """Re-log a saved recipe as real FoodLog rows, one per item.

    quantity_g for each item is the saved amount * scale_factor (1.0 = log
    exactly as saved). All items are created in a single atomic commit.
    """
    recipe = _get_owned_recipe(db, recipe_id, user_id)
    meal_type = payload.meal_type if payload.meal_type in MEAL_TYPES else "other"
    note = f"From recipe: {recipe.name}"[:500]

    created_ids: list[uuid.UUID] = []
    for item in recipe.items:
        log = nutrition_repository.create_food_log(
            db,
            user_id=user_id,
            food_id=item.food_id,
            logged_date=payload.logged_date,
            meal_type=meal_type,
            quantity_g=round(item.quantity_g * payload.scale_factor, 2),
            notes=note,
        )
        created_ids.append(log.id)

    db.commit()

    responses: list[FoodLogResponse] = []
    for log_id in created_ids:
        refreshed = nutrition_repository.get_food_log_by_id(db, log_id, user_id)
        assert refreshed is not None
        food = refreshed.food
        qty = refreshed.quantity_g
        responses.append(
            FoodLogResponse(
                id=refreshed.id,
                food_id=refreshed.food_id,
                logged_date=refreshed.logged_date,
                meal_type=refreshed.meal_type,
                quantity_g=qty,
                notes=refreshed.notes,
                calories=scale_macro(food.calories_per_100g, qty),
                protein_g=scale_macro(food.protein_per_100g, qty),
                carbs_g=scale_macro(food.carbs_per_100g, qty),
                fat_g=scale_macro(food.fat_per_100g, qty),
                fiber_g=scale_optional_macro(food.fiber_per_100g, qty),
                food_name=food.name,
                food_brand=food.brand,
                created_at=refreshed.created_at,
                updated_at=refreshed.updated_at,
            )
        )

    calories, protein_g, carbs_g, fat_g, fiber_g = sum_macro_totals(responses)
    totals = MacroTotals(
        calories=calories, protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g, fiber_g=fiber_g
    )
    return responses, totals
