"""Authentication service — registration, login, and token lifecycle.

This layer contains all auth business rules. It calls the user repository
for database access and the security module for cryptography. Routes call
this service; they never call the repository or security module directly.

Error strategy:
- Raise domain exceptions (ConflictError, UnauthorizedError) that the
  exception handlers in main.py convert to consistent HTTP responses.
- Never reveal whether an email exists in a "wrong password" path —
  always use the generic "Invalid credentials" message to prevent
  email enumeration.
"""

from __future__ import annotations

import logging

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories import user_repository

logger = logging.getLogger(__name__)

_INVALID_CREDENTIALS = "Invalid email or password"


def register(db: Session, email: str, password: str, display_name: str | None = None) -> User:
    """Register a new user.

    Creates the User, UserProfile, and UserPreferences atomically.
    Raises ConflictError if the email is already registered.
    """
    if user_repository.email_exists(db, email):
        raise ConflictError("An account with this email already exists")

    hashed = hash_password(password)
    user = user_repository.create_user(db, email=email, hashed_password=hashed)

    if display_name:
        user_repository.update_user_profile(db, user.id, display_name=display_name)
        # Refresh so user.profile reflects the name.
        db.refresh(user)

    logger.info("User registered", extra={"user_id": str(user.id)})
    return user


def login(db: Session, email: str, password: str) -> User:
    """Verify credentials and return the authenticated User.

    Uses a constant-time comparison to resist timing attacks.
    Returns the same error message whether the email is unknown or the
    password is wrong — prevents email enumeration.
    """
    user = user_repository.get_user_by_email(db, email)

    # Always run verify_password even when the user is not found to
    # maintain consistent response time (prevents timing-based enumeration).
    if user is None:
        # Run a dummy verify so response time is indistinguishable from a real
        # wrong-password path. This hash is pre-computed and never valid.
        verify_password(password, "$2b$12$juIoP.G3HQL6UP1cRxvH6OpFdK1zfa2nDHobqxwzT4rF1zvJA9MOO")
        raise UnauthorizedError(_INVALID_CREDENTIALS)

    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError(_INVALID_CREDENTIALS)

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")

    logger.info("User logged in", extra={"user_id": str(user.id)})
    return user


def issue_tokens(user_id: str) -> tuple[str, str]:
    """Create a fresh access + refresh token pair for the given user_id.

    Returns (access_token, refresh_token).
    """
    return create_access_token(user_id), create_refresh_token(user_id)


def refresh_tokens(db: Session, refresh_token: str) -> tuple[User, str, str]:
    """Validate a refresh token and issue a new token pair.

    Raises UnauthorizedError if the token is invalid or the user no longer
    exists / is deactivated.

    Token rotation: a new refresh token is always issued, so the old one
    is implicitly invalidated (the new token replaces it in the cookie).
    Full server-side revocation (blocklist) can be added in Phase 7.
    """
    import uuid as _uuid

    try:
        user_id_str = decode_token(refresh_token, "refresh")
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired refresh token") from exc

    try:
        user_id = _uuid.UUID(user_id_str)
    except ValueError as exc:
        raise UnauthorizedError("Malformed token subject") from exc

    user = user_repository.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or account deactivated")

    access_token, new_refresh_token = issue_tokens(str(user.id))
    return user, access_token, new_refresh_token
