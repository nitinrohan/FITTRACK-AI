"""Weight router - /api/v1/weight/*

Endpoints:
  POST   /              - Log a new weight entry.
  GET    /              - List entries (paginated, optional date range).
  GET    /{entry_id}    - Get a single entry.
  PUT    /{entry_id}    - Update an entry.
  DELETE /{entry_id}    - Delete an entry.

All endpoints require authentication.
Height from the user's profile is passed to the service when available
so BMI can be computed without a separate profile fetch per entry.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.weight import (
    LogWeightRequest,
    UpdateWeightEntryRequest,
    WeightEntryResponse,
    WeightListResponse,
)
from app.services import weight_service

router = APIRouter(prefix="/api/v1/weight", tags=["weight"])


def _height_cm(user: User) -> float | None:
    """Extract height from the user's profile, or None if unavailable."""
    if user.profile and user.profile.height_cm:
        return float(user.profile.height_cm)
    return None


@router.post(
    "",
    response_model=WeightEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a weight measurement",
)
def log_weight(
    body: LogWeightRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeightEntryResponse:
    return weight_service.log_weight(db, current_user.id, body, height_cm=_height_cm(current_user))


@router.get(
    "",
    response_model=WeightListResponse,
    summary="List weight entries for the current user",
)
def list_entries(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeightListResponse:
    return weight_service.list_entries(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        height_cm=_height_cm(current_user),
    )


@router.get(
    "/{entry_id}",
    response_model=WeightEntryResponse,
    summary="Get a single weight entry",
)
def get_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeightEntryResponse:
    return weight_service.get_entry(
        db, entry_id, current_user.id, height_cm=_height_cm(current_user)
    )


@router.put(
    "/{entry_id}",
    response_model=WeightEntryResponse,
    summary="Update a weight entry",
)
def update_entry(
    entry_id: uuid.UUID,
    body: UpdateWeightEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeightEntryResponse:
    return weight_service.update_entry(
        db, entry_id, current_user.id, body, height_cm=_height_cm(current_user)
    )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a weight entry",
)
def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    weight_service.delete_entry(db, entry_id, current_user.id)
