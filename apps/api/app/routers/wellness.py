"""Wellness router - sleep, steps, and wellness check-in endpoints.

Sub-routers (combined at the bottom of this file):
  /api/v1/sleep
    POST   /              log a sleep entry
    GET    /              list entries (paginated, optional date range)
    GET    /{id}          get a single entry
    PATCH  /{id}          partial update
    DELETE /{id}          delete

  /api/v1/steps
    POST   /              log a steps entry
    GET    /              list entries (paginated, optional date range)
    GET    /{id}          get a single entry
    PATCH  /{id}          partial update
    DELETE /{id}          delete

  /api/v1/wellness
    POST   /              log a wellness check-in
    GET    /              list entries (paginated, optional date range)
    GET    /daily         daily snapshot (sleep + steps + wellness + water)
    GET    /{id}          get a single entry
    PATCH  /{id}          partial update
    DELETE /{id}          delete

All endpoints require authentication.  Users can only access their own data.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError
from app.models.user import User
from app.schemas.wellness import (
    DailyWellnessSnapshot,
    LogSleepRequest,
    LogStepsRequest,
    LogWellnessRequest,
    SleepListResponse,
    SleepLogResponse,
    StepsListResponse,
    StepsLogResponse,
    UpdateSleepRequest,
    UpdateStepsRequest,
    UpdateWellnessRequest,
    WellnessListResponse,
    WellnessLogResponse,
)
from app.services import wellness_service

# ── Sleep sub-router ──────────────────────────────────────────────────────────

sleep_router = APIRouter(prefix="/api/v1/sleep", tags=["sleep"])


@sleep_router.post(
    "",
    response_model=SleepLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_sleep(
    payload: LogSleepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SleepLogResponse:
    return wellness_service.log_sleep(db, current_user.id, payload)


@sleep_router.get("", response_model=SleepListResponse)
def list_sleep_logs(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SleepListResponse:
    return wellness_service.list_sleep_logs(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@sleep_router.get("/{entry_id}", response_model=SleepLogResponse)
def get_sleep_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SleepLogResponse:
    try:
        return wellness_service.get_sleep_log(db, entry_id, current_user.id)
    except NotFoundError as exc:
        raise exc


@sleep_router.patch("/{entry_id}", response_model=SleepLogResponse)
def update_sleep_log(
    entry_id: uuid.UUID,
    payload: UpdateSleepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SleepLogResponse:
    try:
        return wellness_service.update_sleep_log(db, entry_id, current_user.id, payload)
    except NotFoundError as exc:
        raise exc


@sleep_router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_sleep_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    found = wellness_service.delete_sleep_log(db, entry_id, current_user.id)
    if not found:
        raise NotFoundError("Sleep log entry not found.")


# ── Steps sub-router ──────────────────────────────────────────────────────────

steps_router = APIRouter(prefix="/api/v1/steps", tags=["steps"])


@steps_router.post(
    "",
    response_model=StepsLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_steps(
    payload: LogStepsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StepsLogResponse:
    return wellness_service.log_steps(db, current_user.id, payload)


@steps_router.get("", response_model=StepsListResponse)
def list_steps_logs(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StepsListResponse:
    return wellness_service.list_steps_logs(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@steps_router.get("/{entry_id}", response_model=StepsLogResponse)
def get_steps_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StepsLogResponse:
    try:
        return wellness_service.get_steps_log(db, entry_id, current_user.id)
    except NotFoundError as exc:
        raise exc


@steps_router.patch("/{entry_id}", response_model=StepsLogResponse)
def update_steps_log(
    entry_id: uuid.UUID,
    payload: UpdateStepsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StepsLogResponse:
    try:
        return wellness_service.update_steps_log(db, entry_id, current_user.id, payload)
    except NotFoundError as exc:
        raise exc


@steps_router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_steps_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    found = wellness_service.delete_steps_log(db, entry_id, current_user.id)
    if not found:
        raise NotFoundError("Steps log entry not found.")


# ── Wellness sub-router ───────────────────────────────────────────────────────

wellness_router = APIRouter(prefix="/api/v1/wellness", tags=["wellness"])


@wellness_router.post(
    "",
    response_model=WellnessLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_wellness(
    payload: LogWellnessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WellnessLogResponse:
    return wellness_service.log_wellness(db, current_user.id, payload)


@wellness_router.get("", response_model=WellnessListResponse)
def list_wellness_logs(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WellnessListResponse:
    return wellness_service.list_wellness_logs(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@wellness_router.get("/daily", response_model=DailyWellnessSnapshot)
def get_daily_snapshot(
    snapshot_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyWellnessSnapshot:
    """Return a combined daily snapshot.  Defaults to today when no date given."""
    from datetime import date as date_type

    target = snapshot_date or date_type.today()
    return wellness_service.get_daily_snapshot(db, current_user.id, target)


@wellness_router.get("/{entry_id}", response_model=WellnessLogResponse)
def get_wellness_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WellnessLogResponse:
    try:
        return wellness_service.get_wellness_log(db, entry_id, current_user.id)
    except NotFoundError as exc:
        raise exc


@wellness_router.patch("/{entry_id}", response_model=WellnessLogResponse)
def update_wellness_log(
    entry_id: uuid.UUID,
    payload: UpdateWellnessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WellnessLogResponse:
    try:
        return wellness_service.update_wellness_log(db, entry_id, current_user.id, payload)
    except NotFoundError as exc:
        raise exc


@wellness_router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_wellness_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    found = wellness_service.delete_wellness_log(db, entry_id, current_user.id)
    if not found:
        raise NotFoundError("Wellness log entry not found.")


# ── Combined router (imported by main.py) ────────────────────────────────────

router = APIRouter()
router.include_router(sleep_router)
router.include_router(steps_router)
router.include_router(wellness_router)
