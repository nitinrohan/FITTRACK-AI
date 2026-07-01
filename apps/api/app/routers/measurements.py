"""Body measurements router - /api/v1/measurements/*

Endpoints:
  POST   /              log a new measurement entry
  GET    /              list entries (paginated, optional date range)
  GET    /{entry_id}    get a single entry
  PATCH  /{entry_id}    partial update
  DELETE /{entry_id}    delete

All endpoints require authentication.  Users can only access their own data.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.schemas.measurement import (
    CreateMeasurementRequest,
    MeasurementListResponse,
    MeasurementResponse,
    UpdateMeasurementRequest,
)
from app.services import measurement_service

router = APIRouter(prefix="/api/v1/measurements", tags=["measurements"])


@router.post(
    "",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_measurement(
    payload: CreateMeasurementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementResponse:
    try:
        return measurement_service.log_measurement(db, current_user.id, payload)
    except ValidationError as exc:
        raise exc


@router.get("", response_model=MeasurementListResponse)
def list_measurements(
    date_from: date | None = Query(default=None, alias="date_from"),
    date_to: date | None = Query(default=None, alias="date_to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementListResponse:
    return measurement_service.list_measurements(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/{entry_id}", response_model=MeasurementResponse)
def get_measurement(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementResponse:
    try:
        return measurement_service.get_measurement(db, entry_id, current_user.id)
    except NotFoundError as exc:
        raise exc


@router.patch("/{entry_id}", response_model=MeasurementResponse)
def update_measurement(
    entry_id: uuid.UUID,
    payload: UpdateMeasurementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementResponse:
    try:
        return measurement_service.update_measurement(db, entry_id, current_user.id, payload)
    except NotFoundError as exc:
        raise exc


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_measurement(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    found = measurement_service.delete_measurement(db, entry_id, current_user.id)
    if not found:
        raise NotFoundError("Measurement entry not found.")
