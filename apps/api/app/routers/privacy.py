"""Privacy router - /api/v1/privacy.

  GET    /api/v1/privacy/summary   per-category counts of the caller's records
  GET    /api/v1/privacy/export    full machine-readable export of the caller's data
  DELETE /api/v1/privacy/account   permanently delete the caller's account (password required)

Every endpoint operates only on the authenticated caller's own data.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.privacy import (
    AccountDeletedResponse,
    AccountDeleteRequest,
    DataExport,
    PrivacySummary,
)
from app.services import privacy_service

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


@router.get("/summary", response_model=PrivacySummary)
def get_privacy_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrivacySummary:
    """Return how many records the caller owns in each category."""
    counts = privacy_service.build_summary(db, user=current_user)
    return PrivacySummary(**counts)


@router.get("/export", response_model=DataExport)
def export_my_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return a complete snapshot of every record the caller owns."""
    return privacy_service.build_export(db, user=current_user)


@router.delete("/account", response_model=AccountDeletedResponse)
def delete_my_account(
    payload: AccountDeleteRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountDeletedResponse:
    """Permanently delete the caller's account and all associated data.

    Requires the current password. On success the auth cookies are cleared so
    the now-invalid session does not linger in the browser. Irreversible.
    """
    privacy_service.delete_account(db, user=current_user, password=payload.password)
    response.delete_cookie(key="fittrack_access", path="/")
    response.delete_cookie(key="fittrack_refresh", path="/")
    return AccountDeletedResponse()
