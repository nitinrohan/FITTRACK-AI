"""Stress router - /api/v1/stress.

  POST   /api/v1/stress               log a 0-100 stress reading
  GET    /api/v1/stress               list readings (paginated, newest first)
  GET    /api/v1/stress/summary       daily highest / lowest / average + band
  DELETE /api/v1/stress/{id}          delete a reading

All endpoints require authentication and operate only on the caller's data.
The summary takes the client's local `date` and IANA `tz` so day grouping is
correct regardless of server time zone.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.stress import (
    LogStressRequest,
    StressDailySummary,
    StressListResponse,
    StressLogResponse,
)
from app.services import stress_service

router = APIRouter(prefix="/api/v1/stress", tags=["stress"])


@router.post("", response_model=StressLogResponse, status_code=status.HTTP_201_CREATED)
def log_stress(
    payload: LogStressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StressLogResponse:
    return stress_service.log_reading(db, current_user.id, payload)


@router.get("", response_model=StressListResponse)
def list_stress(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StressListResponse:
    return stress_service.list_readings(
        db, current_user.id, page=page, page_size=page_size
    )


@router.get("/summary", response_model=StressDailySummary)
def stress_summary(
    on_date: date = Query(default_factory=date.today, alias="date"),
    tz: str = Query(default="UTC"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StressDailySummary:
    return stress_service.daily_summary(db, current_user.id, on_date=on_date, tz=tz)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_stress(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    stress_service.delete_reading(db, entry_id, current_user.id)
