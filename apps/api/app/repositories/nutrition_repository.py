"""Repository functions for the nutrition domain.

All functions accept a SQLAlchemy Session and return ORM objects (or None).
No business logic lives here — that belongs in nutrition_service.py.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.nutrition import Food, FoodLog, WaterLog

# ── Food ──────────────────────────────────────────────────────────────────────


def create_food(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    name: str,
    brand: str | None,
    description: str | None,
    calories_per_100g: float,
    protein_per_100g: float,
    carbs_per_100g: float,
    fat_per_100g: float,
    fiber_per_100g: float | None,
    sugar_per_100g: float | None,
    sodium_per_100g: float | None,
    serving_size_g: float | None,
    serving_unit: str | None,
    is_system: bool = False,
) -> Food:
    food = Food(
        user_id=user_id,
        name=name,
        brand=brand,
        description=description,
        calories_per_100g=calories_per_100g,
        protein_per_100g=protein_per_100g,
        carbs_per_100g=carbs_per_100g,
        fat_per_100g=fat_per_100g,
        fiber_per_100g=fiber_per_100g,
        sugar_per_100g=sugar_per_100g,
        sodium_per_100g=sodium_per_100g,
        serving_size_g=serving_size_g,
        serving_unit=serving_unit,
        is_system=is_system,
    )
    db.add(food)
    db.flush()
    return food


def get_food_by_id(db: Session, food_id: uuid.UUID) -> Food | None:
    return db.get(Food, food_id)


def list_foods(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Food], int]:
    """Return foods visible to the user: system foods + their own custom ones."""
    stmt = select(Food).where(
        Food.is_active == True,  # noqa: E712
        or_(Food.is_system == True, Food.user_id == user_id),  # noqa: E712
    )
    if search:
        stmt = stmt.where(Food.name.ilike(f"%{search}%"))

    total_stmt = stmt.with_only_columns(Food.id).order_by(None)
    total = len(db.execute(total_stmt).all())

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Food.name).offset(offset).limit(page_size)
    foods = list(db.scalars(stmt).all())
    return foods, total


def update_food_fields(db: Session, food: Food, **fields: object) -> Food:
    for key, val in fields.items():
        setattr(food, key, val)
    db.flush()
    return food


def delete_food(db: Session, food: Food) -> None:
    """Soft-delete by marking inactive so FoodLog references remain valid."""
    food.is_active = False
    db.flush()


# ── FoodLog ───────────────────────────────────────────────────────────────────


def create_food_log(
    db: Session,
    *,
    user_id: uuid.UUID,
    food_id: uuid.UUID,
    logged_date: date,
    meal_type: str,
    quantity_g: float,
    notes: str | None,
) -> FoodLog:
    log = FoodLog(
        user_id=user_id,
        food_id=food_id,
        logged_date=logged_date,
        meal_type=meal_type,
        quantity_g=quantity_g,
        notes=notes,
    )
    db.add(log)
    db.flush()
    return log


def get_food_log_by_id(db: Session, log_id: uuid.UUID, user_id: uuid.UUID) -> FoodLog | None:
    stmt = (
        select(FoodLog)
        .options(joinedload(FoodLog.food))
        .where(FoodLog.id == log_id, FoodLog.user_id == user_id)
    )
    return db.scalars(stmt).first()


def list_food_logs_for_date(db: Session, user_id: uuid.UUID, logged_date: date) -> list[FoodLog]:
    stmt = (
        select(FoodLog)
        .options(joinedload(FoodLog.food))
        .where(FoodLog.user_id == user_id, FoodLog.logged_date == logged_date)
        .order_by(FoodLog.created_at)
    )
    return list(db.scalars(stmt).all())


def update_food_log_fields(db: Session, log: FoodLog, **fields: object) -> FoodLog:
    for key, val in fields.items():
        setattr(log, key, val)
    db.flush()
    return log


def delete_food_log(db: Session, log: FoodLog) -> None:
    db.delete(log)
    db.flush()


# ── WaterLog ──────────────────────────────────────────────────────────────────


def create_water_log(
    db: Session,
    *,
    user_id: uuid.UUID,
    logged_date: date,
    amount_ml: int,
    notes: str | None,
) -> WaterLog:
    log = WaterLog(
        user_id=user_id,
        logged_date=logged_date,
        amount_ml=amount_ml,
        notes=notes,
    )
    db.add(log)
    db.flush()
    return log


def get_water_log_by_id(db: Session, log_id: uuid.UUID, user_id: uuid.UUID) -> WaterLog | None:
    stmt = select(WaterLog).where(WaterLog.id == log_id, WaterLog.user_id == user_id)
    return db.scalars(stmt).first()


def list_water_logs_for_date(db: Session, user_id: uuid.UUID, logged_date: date) -> list[WaterLog]:
    stmt = (
        select(WaterLog)
        .where(WaterLog.user_id == user_id, WaterLog.logged_date == logged_date)
        .order_by(WaterLog.created_at)
    )
    return list(db.scalars(stmt).all())


def update_water_log_fields(db: Session, log: WaterLog, **fields: object) -> WaterLog:
    for key, val in fields.items():
        setattr(log, key, val)
    db.flush()
    return log


def delete_water_log(db: Session, log: WaterLog) -> None:
    db.delete(log)
    db.flush()
