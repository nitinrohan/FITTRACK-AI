"""Business logic for the nutrition domain.

Key responsibilities:
- Food CRUD with ownership rules (system foods cannot be modified/deleted by users).
- FoodLog CRUD - only the owner can read/write.
- WaterLog CRUD - only the owner can read/write.
- Daily nutrition summary: aggregates FoodLog entries for a date into
  per-meal sections and day-level totals.

Macro calculation:
  displayed_value = (per_100g_value * quantity_g) / 100
  Rounded to 1 decimal place for display.

All functions that modify data follow the commit-then-re-fetch pattern used
elsewhere in this codebase (instead of db.refresh) to keep the service layer
testable with MagicMock sessions.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError, NotFoundError
from app.models.nutrition import MEAL_TYPES, Food, FoodLog, WaterLog
from app.repositories import nutrition_repository
from app.schemas.ai import LogMealRequest
from app.schemas.nutrition import (
    CreateFoodRequest,
    DailyNutritionResponse,
    FoodListResponse,
    FoodLogResponse,
    FoodResponse,
    LogFoodRequest,
    LogWaterRequest,
    MacroTotals,
    MealSection,
    UpdateFoodLogRequest,
    UpdateFoodRequest,
    UpdateWaterLogRequest,
    WaterLogResponse,
)
from app.services.nutrition_calculations import scale_macro, sum_macro_totals

# ── Helpers ───────────────────────────────────────────────────────────────────


def _scale(per_100g: float, quantity_g: float) -> float:
    """Scale a per-100g value to the actual quantity eaten.

    Thin wrapper kept for backward compatibility (existing tests import this
    name directly) - the real implementation lives in nutrition_calculations
    so recipe_service can share it without reaching into this module.
    """
    return scale_macro(per_100g, quantity_g)


def _build_food_response(food: Food) -> FoodResponse:
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


def _build_food_log_response(log: FoodLog) -> FoodLogResponse:
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
        fiber_g=_scale(food.fiber_per_100g, qty) if food.fiber_per_100g is not None else None,
        food_name=food.name,
        food_brand=food.brand,
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


def _build_water_log_response(log: WaterLog) -> WaterLogResponse:
    return WaterLogResponse(
        id=log.id,
        logged_date=log.logged_date,
        amount_ml=log.amount_ml,
        notes=log.notes,
        created_at=log.created_at,
    )


def _sum_macros(entries: list[FoodLogResponse]) -> MacroTotals:
    calories, protein_g, carbs_g, fat_g, fiber_g = sum_macro_totals(entries)
    return MacroTotals(
        calories=calories, protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g, fiber_g=fiber_g
    )


# ── Food CRUD ─────────────────────────────────────────────────────────────────


def create_food(db: Session, user_id: uuid.UUID, payload: CreateFoodRequest) -> FoodResponse:
    food = nutrition_repository.create_food(
        db,
        user_id=user_id,
        name=payload.name.strip(),
        brand=payload.brand,
        description=payload.description,
        calories_per_100g=payload.calories_per_100g,
        protein_per_100g=payload.protein_per_100g,
        carbs_per_100g=payload.carbs_per_100g,
        fat_per_100g=payload.fat_per_100g,
        fiber_per_100g=payload.fiber_per_100g,
        sugar_per_100g=payload.sugar_per_100g,
        sodium_per_100g=payload.sodium_per_100g,
        serving_size_g=payload.serving_size_g,
        serving_unit=payload.serving_unit,
        is_system=False,
    )
    db.commit()
    refreshed = nutrition_repository.get_food_by_id(db, food.id)
    assert refreshed is not None
    return _build_food_response(refreshed)


def list_foods(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> FoodListResponse:
    foods, total = nutrition_repository.list_foods(
        db, user_id, search=search, page=page, page_size=page_size
    )
    return FoodListResponse(
        foods=[_build_food_response(f) for f in foods],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_food(db: Session, food_id: uuid.UUID, user_id: uuid.UUID) -> FoodResponse:
    food = nutrition_repository.get_food_by_id(db, food_id)
    if food is None or not food.is_active:
        raise NotFoundError("Food not found.")
    # Private food belonging to another user
    if not food.is_system and food.user_id != user_id:
        raise NotFoundError("Food not found.")
    return _build_food_response(food)


def update_food(
    db: Session,
    food_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateFoodRequest,
) -> FoodResponse:
    food = nutrition_repository.get_food_by_id(db, food_id)
    if food is None or not food.is_active:
        raise NotFoundError("Food not found.")
    if food.is_system:
        raise ForbiddenError("System foods cannot be modified.")
    if food.user_id != user_id:
        raise ForbiddenError("You do not own this food.")

    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if fields:
        nutrition_repository.update_food_fields(db, food, **fields)
    db.commit()
    refreshed = nutrition_repository.get_food_by_id(db, food_id)
    assert refreshed is not None
    return _build_food_response(refreshed)


def delete_food(db: Session, food_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    food = nutrition_repository.get_food_by_id(db, food_id)
    if food is None or not food.is_active:
        return False
    if food.is_system:
        raise ForbiddenError("System foods cannot be deleted.")
    if food.user_id != user_id:
        raise ForbiddenError("You do not own this food.")
    nutrition_repository.delete_food(db, food)
    db.commit()
    return True


# ── FoodLog CRUD ──────────────────────────────────────────────────────────────


def log_food(db: Session, user_id: uuid.UUID, payload: LogFoodRequest) -> FoodLogResponse:
    # Verify food exists and is accessible
    food = nutrition_repository.get_food_by_id(db, payload.food_id)
    if food is None or not food.is_active:
        raise NotFoundError("Food not found.")
    if not food.is_system and food.user_id != user_id:
        raise NotFoundError("Food not found.")

    log = nutrition_repository.create_food_log(
        db,
        user_id=user_id,
        food_id=payload.food_id,
        logged_date=payload.logged_date,
        meal_type=payload.meal_type,
        quantity_g=payload.quantity_g,
        notes=payload.notes,
    )
    db.commit()
    refreshed = nutrition_repository.get_food_log_by_id(db, log.id, user_id)
    assert refreshed is not None
    return _build_food_log_response(refreshed)


def log_meal(
    db: Session, user_id: uuid.UUID, payload: LogMealRequest
) -> tuple[list[FoodLogResponse], MacroTotals]:
    """Bulk-save a user-approved multi-item meal as real Food + FoodLog rows.

    Each item becomes its own private Food (so it can be edited/reused later,
    same as the single-item AI estimate flow) plus one FoodLog entry. All
    inserts happen in a single commit so the batch is atomic - either every
    item is logged or none are.
    """
    meal_type = payload.meal_type if payload.meal_type in MEAL_TYPES else "other"
    created_logs: list[FoodLog] = []

    for item in payload.items:
        food = nutrition_repository.create_food(
            db,
            user_id=user_id,
            name=item.name.strip(),
            brand=None,
            description=None,
            calories_per_100g=item.calories_per_100g,
            protein_per_100g=item.protein_per_100g,
            carbs_per_100g=item.carbs_per_100g,
            fat_per_100g=item.fat_per_100g,
            fiber_per_100g=item.fiber_per_100g,
            sugar_per_100g=None,
            sodium_per_100g=None,
            serving_size_g=item.quantity_g,
            serving_unit=item.serving_unit,
            is_system=False,
        )
        log = nutrition_repository.create_food_log(
            db,
            user_id=user_id,
            food_id=food.id,
            logged_date=payload.logged_date,
            meal_type=meal_type,
            quantity_g=item.quantity_g,
            notes=None,
        )
        created_logs.append(log)

    db.commit()

    responses: list[FoodLogResponse] = []
    for log in created_logs:
        refreshed = nutrition_repository.get_food_log_by_id(db, log.id, user_id)
        assert refreshed is not None
        responses.append(_build_food_log_response(refreshed))

    return responses, _sum_macros(responses)


def update_food_log(
    db: Session,
    log_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateFoodLogRequest,
) -> FoodLogResponse | None:
    log = nutrition_repository.get_food_log_by_id(db, log_id, user_id)
    if log is None:
        return None
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if fields:
        nutrition_repository.update_food_log_fields(db, log, **fields)
    db.commit()
    refreshed = nutrition_repository.get_food_log_by_id(db, log_id, user_id)
    assert refreshed is not None
    return _build_food_log_response(refreshed)


def delete_food_log(db: Session, log_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    log = nutrition_repository.get_food_log_by_id(db, log_id, user_id)
    if log is None:
        return False
    nutrition_repository.delete_food_log(db, log)
    db.commit()
    return True


# ── WaterLog CRUD ─────────────────────────────────────────────────────────────


def log_water(db: Session, user_id: uuid.UUID, payload: LogWaterRequest) -> WaterLogResponse:
    log = nutrition_repository.create_water_log(
        db,
        user_id=user_id,
        logged_date=payload.logged_date,
        amount_ml=payload.amount_ml,
        notes=payload.notes,
    )
    db.commit()
    refreshed = nutrition_repository.get_water_log_by_id(db, log.id, user_id)
    assert refreshed is not None
    return _build_water_log_response(refreshed)


def update_water_log(
    db: Session,
    log_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateWaterLogRequest,
) -> WaterLogResponse | None:
    log = nutrition_repository.get_water_log_by_id(db, log_id, user_id)
    if log is None:
        return None
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if fields:
        nutrition_repository.update_water_log_fields(db, log, **fields)
    db.commit()
    refreshed = nutrition_repository.get_water_log_by_id(db, log_id, user_id)
    assert refreshed is not None
    return _build_water_log_response(refreshed)


def delete_water_log(db: Session, log_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    log = nutrition_repository.get_water_log_by_id(db, log_id, user_id)
    if log is None:
        return False
    nutrition_repository.delete_water_log(db, log)
    db.commit()
    return True


# ── Daily summary ─────────────────────────────────────────────────────────────


def get_daily_nutrition(
    db: Session, user_id: uuid.UUID, target_date: date
) -> DailyNutritionResponse:
    """Aggregate all food and water logs for a user on a given date."""
    food_logs = nutrition_repository.list_food_logs_for_date(db, user_id, target_date)
    water_logs = nutrition_repository.list_water_logs_for_date(db, user_id, target_date)

    log_responses = [_build_food_log_response(fl) for fl in food_logs]
    water_responses = [_build_water_log_response(wl) for wl in water_logs]

    # Group by meal_type, preserving standard display order
    meal_map: dict[str, list[FoodLogResponse]] = {}
    for entry in log_responses:
        meal_map.setdefault(entry.meal_type, []).append(entry)

    meals: list[MealSection] = []
    for mt in MEAL_TYPES:
        entries = meal_map.get(mt, [])
        if entries:
            meals.append(
                MealSection(
                    meal_type=mt,
                    entries=entries,
                    totals=_sum_macros(entries),
                )
            )
    # Include any unexpected meal types at the end
    for mt, entries in meal_map.items():
        if mt not in MEAL_TYPES:
            meals.append(
                MealSection(
                    meal_type=mt,
                    entries=entries,
                    totals=_sum_macros(entries),
                )
            )

    day_totals = _sum_macros(log_responses)
    water_total_ml = sum(wl.amount_ml for wl in water_responses)

    return DailyNutritionResponse(
        date=target_date,
        meals=meals,
        day_totals=day_totals,
        water_logs=water_responses,
        water_total_ml=water_total_ml,
    )
