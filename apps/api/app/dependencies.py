"""FastAPI dependency injection for common request-scoped objects.

get_current_user is the central auth dependency - every protected endpoint
uses it via Depends(get_current_user).

Design:
- Reads the access token from the HTTP-only cookie (not Authorization header)
  so the token is never accessible to frontend JavaScript.
- Returns the full User ORM object so routes have access to profile/prefs
  when needed (loaded lazily by default).
- Raises UnauthorizedError (→ 401) for any token problem; this gives the
  frontend a clear signal to redirect to the login page.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Cookie, Depends
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.exceptions import UnauthorizedError
from app.models.user import User
from app.repositories import user_repository

logger = logging.getLogger(__name__)


def get_current_user(
    db: Session = Depends(get_db),
    fittrack_access: str | None = Cookie(default=None),
) -> User:
    """Resolve the authenticated user from the access-token cookie.

    Usage in a route:
        @router.get("/me")
        def me(current_user: User = Depends(get_current_user)):
            ...

    Raises UnauthorizedError (HTTP 401) if:
    - No access token cookie is present
    - The token is expired or has an invalid signature
    - The user_id in the token does not match any active user
    """
    if fittrack_access is None:
        raise UnauthorizedError()

    try:
        user_id_str = decode_token(fittrack_access, "access")
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired session. Please sign in again.") from exc

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise UnauthorizedError("Malformed token") from exc

    user = user_repository.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("Account not found or deactivated")

    return user


def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Like get_current_user but also requires email verification.

    Use this for sensitive operations once email verification is implemented.
    For the MVP, verification is not required; this dependency is a placeholder.
    """
    # TODO Phase 7: uncomment once email verification flow is built.
    # if not current_user.is_verified:
    #     raise ForbiddenError("Please verify your email address first.")
    return current_user
