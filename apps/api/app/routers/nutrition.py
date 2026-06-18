"""Nutrition router — food library, food logging, and water logging.

Endpoints:
  /api/v1/foods
    POST   /              create custom food
    GET    /              list/search foods (system + own)
    GET    /{id}          get food
    PATCH  /{id}          update food (owner only)
    DELETE /{id}          soft-delete food (owner only)

  /api/v1/nutrition
    POST   /foods         log a food entry
    GET    /daily         daily nutrition summary (?date=YYYY-MM-DD)
    PATCH  /foods/{id}    update a food log entry
    DELETE /foods/{id}    delete a food log entry
    POST   /water         log water intake
    PATCH  /water/{id}    update a water log entry
    DELETE /water/{id}    delete a water log entry
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.schemas.nutrition import (
    CreateFoodRequest,
    DailyNutritionResponse,
    FoodListResponse,
    FoodLogResponse,
    FoodResponse,
    LogFoodRequest,
    LogWaterRequest,
    UpdateFoodLogRequest,
    UpdateFoodRequest,
    UpdateWaterLogRequest,
    WaterLogResponse,
)
from app.services import nutrition_service

# ── Sub-routers ───────────────────────────────────────────────────────────────

food_router = APIRouter(prefix="/api/v1/foods", tags=["foods"])
nutrition_router = APIRouter(prefix="/api/v1/nutrition", tags=["nutrition"])


# ── Food library ──────────────────────────────────────────────────────────────


@food_router.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
def create_food(
    payload: CreateFoodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodResponse:
    return nutrition_service.create_food(db, current_user.id, payload)


@food_router.get("", response_model=FoodListResponse)
def list_foods(
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodListResponse:
    return nutrition_service.list_foods(
        db, current_user.id, search=search, page=page, page_size=page_size
    )


@food_router.get("/{food_id}", response_model=FoodResponse)
def get_food(
    food_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodResponse:
    try:
        return nutrition_service.get_food(db, food_id, current_user.id)
    except NotFoundError as exc:
        raise exc


@food_router.patch("/{food_id}", response_model=FoodResponse)
def update_food(
    food_id: uuid.UUID,
    payload: UpdateFoodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodResponse:
    try:
        return nutrition_service.update_food(db, food_id, current_user.id, payload)
    except (NotFoundError, ForbiddenError) as exc:
        raise exc


@food_router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_food(
    food_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        nutrition_service.delete_food(db, food_id, current_user.id)
    except (NotFoundError, ForbiddenError) as exc:
        raise exc


# ── Nutrition log (food entries) ──────────────────────────────────────────────


@nutrition_router.post(
    "/foods", response_model=FoodLogResponse, status_code=status.HTTP_201_CREATED
)
def log_food(
    payload: LogFoodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodLogResponse:
    try:
        return nutrition_service.log_food(db, current_user.id, payload)
    except NotFoundError as exc:
        raise exc


@nutrition_router.get("/daily", response_model=DailyNutritionResponse)
def get_daily_nutrition(
    log_date: date = Query(
        default=...,
        alias="date",
        description="Date in YYYY-MM-DD format",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyNutritionResponse:
    return nutrition_service.get_daily_nutrition(db, current_user.id, log_date)


@nutrition_router.patch("/foods/{log_id}", response_model=FoodLogResponse)
def update_food_log(
    log_id: uuid.UUID,
    payload: UpdateFoodLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodLogResponse:
    result = nutrition_service.update_food_log(db, log_id, current_user.id, payload)
    if result is None:
        raise NotFoundError("Food log entry not found.")
    return result


@nutrition_router.delete(
    "/foods/{log_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_food_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    found = nutrition_service.delete_food_log(db, log_id, current_user.id)
    if not found:
        raise NotFoundError("Food log entry not found.")


# ── Water log ─────────────────────────────────────────────────────────────────


@nutrition_router.post(
    "/water", response_model=WaterLogResponse, status_code=status.HTTP_201_CREATED
)
def log_water(
    payload: LogWaterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WaterLogResponse:
    return nutrition_service.log_water(db, current_user.id, payload)


@nutrition_router.patch("/water/{log_id}", response_model=WaterLogResponse)
def update_water_log(
    log_id: uuid.UUID,
    payload: UpdateWaterLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WaterLogResponse:
    result = nutrition_service.update_water_log(db, log_id, current_user.id, payload)
    if result is None:
        raise NotFoundError("Water log entry not found.")
    return result


@nutrition_router.delete(
    "/water/{log_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_water_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    found = nutrition_service.delete_water_log(db, log_id, current_user.id)
    if not found:
        raise NotFoundError("Water log entry not found.")


# ── Combined router ───────────────────────────────────────────────────────────
# IMPORTANT: include_router() calls must come AFTER all decorator definitions.

router = APIRouter()
router.include_router(food_router)
router.include_router(nutrition_router)
