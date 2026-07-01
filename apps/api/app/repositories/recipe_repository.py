"""Repository functions for the recipes domain.

No business logic here - that belongs in recipe_service.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.recipe import Recipe, RecipeItem

# ── Recipe ────────────────────────────────────────────────────────────────────


def create_recipe(
    db: Session, *, user_id: uuid.UUID, name: str, description: str | None
) -> Recipe:
    recipe = Recipe(user_id=user_id, name=name, description=description)
    db.add(recipe)
    db.flush()
    return recipe


def add_item(
    db: Session, *, recipe_id: uuid.UUID, food_id: uuid.UUID, quantity_g: float, position: int
) -> RecipeItem:
    item = RecipeItem(recipe_id=recipe_id, food_id=food_id, quantity_g=quantity_g, position=position)
    db.add(item)
    db.flush()
    return item


def replace_items(
    db: Session, recipe: Recipe, items: list[tuple[uuid.UUID, float]]
) -> None:
    """Delete all existing items on a recipe and add a new ordered set."""
    for existing in list(recipe.items):
        db.delete(existing)
    db.flush()
    for position, (food_id, quantity_g) in enumerate(items):
        add_item(db, recipe_id=recipe.id, food_id=food_id, quantity_g=quantity_g, position=position)


def get_recipe_by_id(db: Session, recipe_id: uuid.UUID) -> Recipe | None:
    stmt = (
        select(Recipe)
        .options(joinedload(Recipe.items).joinedload(RecipeItem.food))
        .where(Recipe.id == recipe_id)
    )
    return db.scalars(stmt).unique().first()


def list_recipes(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Recipe], int]:
    stmt = select(Recipe).where(Recipe.user_id == user_id)
    if search:
        stmt = stmt.where(Recipe.name.ilike(f"%{search}%"))

    total = db.scalar(
        select(func.count()).select_from(stmt.with_only_columns(Recipe.id).order_by(None).subquery())
    ) or 0

    offset = (page - 1) * page_size
    stmt = (
        stmt.options(joinedload(Recipe.items).joinedload(RecipeItem.food))
        .order_by(Recipe.name)
        .offset(offset)
        .limit(page_size)
    )
    recipes = list(db.scalars(stmt).unique().all())
    return recipes, total


def update_recipe_fields(db: Session, recipe: Recipe, **fields: object) -> Recipe:
    for key, val in fields.items():
        setattr(recipe, key, val)
    db.flush()
    return recipe


def delete_recipe(db: Session, recipe: Recipe) -> None:
    db.delete(recipe)
    db.flush()
