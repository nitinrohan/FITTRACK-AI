"""Business logic for user-configurable daily nutrition targets.

These are plain user settings (no AI, no ownership edge cases beyond "the
current user"). They exist so AI features and dashboards can compare logged
intake against real numbers the user chose, instead of guessing a target.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.repositories import nutrition_target_repository
from app.schemas.nutrition_target import (
    NutritionTargetResponse,
    UpdateNutritionTargetRequest,
)


def _build_response(target: object | None) -> NutritionTargetResponse:
    if target is None:
        return NutritionTargetResponse(
            calorie_target_kcal=None,
            protein_target_g=None,
            carbs_target_g=None,
            fat_target_g=None,
            fiber_target_g=None,
            is_set=False,
            updated_at=None,
        )
    cal = target.calorie_target_kcal  # type: ignore[attr-defined]
    pro = target.protein_target_g  # type: ignore[attr-defined]
    carb = target.carbs_target_g  # type: ignore[attr-defined]
    fat = target.fat_target_g  # type: ignore[attr-defined]
    fiber = target.fiber_target_g  # type: ignore[attr-defined]
    return NutritionTargetResponse(
        calorie_target_kcal=cal,
        protein_target_g=pro,
        carbs_target_g=carb,
        fat_target_g=fat,
        fiber_target_g=fiber,
        is_set=any(v is not None for v in (cal, pro, carb, fat, fiber)),
        updated_at=target.updated_at,  # type: ignore[attr-defined]
    )


def get_targets(db: Session, user_id: uuid.UUID) -> NutritionTargetResponse:
    target = nutrition_target_repository.get_for_user(db, user_id)
    return _build_response(target)


def update_targets(
    db: Session, user_id: uuid.UUID, payload: UpdateNutritionTargetRequest
) -> NutritionTargetResponse:
    nutrition_target_repository.upsert(
        db,
        user_id,
        calorie_target_kcal=payload.calorie_target_kcal,
        protein_target_g=payload.protein_target_g,
        carbs_target_g=payload.carbs_target_g,
        fat_target_g=payload.fat_target_g,
        fiber_target_g=payload.fiber_target_g,
    )
    db.commit()
    refreshed = nutrition_target_repository.get_for_user(db, user_id)
    return _build_response(refreshed)
