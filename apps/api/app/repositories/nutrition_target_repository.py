"""Repository functions for user nutrition targets.

No business logic here - that belongs in nutrition_target_service.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nutrition_target import NutritionTarget


def get_for_user(db: Session, user_id: uuid.UUID) -> NutritionTarget | None:
    stmt = select(NutritionTarget).where(NutritionTarget.user_id == user_id)
    return db.scalars(stmt).first()


def upsert(
    db: Session,
    user_id: uuid.UUID,
    *,
    calorie_target_kcal: float | None,
    protein_target_g: float | None,
    carbs_target_g: float | None,
    fat_target_g: float | None,
    fiber_target_g: float | None,
) -> NutritionTarget:
    target = get_for_user(db, user_id)
    if target is None:
        target = NutritionTarget(user_id=user_id)
        db.add(target)

    target.calorie_target_kcal = calorie_target_kcal
    target.protein_target_g = protein_target_g
    target.carbs_target_g = carbs_target_g
    target.fat_target_g = fat_target_g
    target.fiber_target_g = fiber_target_g

    db.flush()
    return target
