"""Recipes router - saved food combinations you can re-log later.

Endpoints:
  /api/v1/recipes
    POST   /              create a recipe from a list of foods + quantities
    GET    /              list/search the current user's recipes
    GET    /{id}          get one recipe (with computed macros)
    PATCH  /{id}          update name/description/items (owner only)
    DELETE /{id}          delete a recipe (owner only)
    POST   /{id}/log      re-log a recipe as real food-log entries, optionally scaled
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.schemas.recipe import (
    CreateRecipeRequest,
    LogRecipeRequest,
    LogRecipeResponse,
    RecipeListResponse,
    RecipeResponse,
    UpdateRecipeRequest,
)
from app.services import recipe_service

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: CreateRecipeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecipeResponse:
    return recipe_service.create_recipe(db, current_user.id, payload)


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecipeListResponse:
    return recipe_service.list_recipes(
        db, current_user.id, search=search, page=page, page_size=page_size
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecipeResponse:
    return recipe_service.get_recipe(db, recipe_id, current_user.id)


@router.patch("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: uuid.UUID,
    payload: UpdateRecipeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecipeResponse:
    try:
        return recipe_service.update_recipe(db, recipe_id, current_user.id, payload)
    except (NotFoundError, ForbiddenError) as exc:
        raise exc


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    recipe_service.delete_recipe(db, recipe_id, current_user.id)


@router.post("/{recipe_id}/log", response_model=LogRecipeResponse, status_code=status.HTTP_201_CREATED)
def log_recipe(
    recipe_id: uuid.UUID,
    payload: LogRecipeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LogRecipeResponse:
    """Re-log a saved recipe as real food-log entries.

    ``scale_factor`` (default 1.0) multiplies every item's saved quantity -
    e.g. 0.5 logs half the saved recipe.
    """
    entries, totals = recipe_service.log_recipe(db, recipe_id, current_user.id, payload)
    return LogRecipeResponse(entries=entries, totals=totals)
