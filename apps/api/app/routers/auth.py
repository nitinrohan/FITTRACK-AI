"""Authentication router - /api/v1/auth/*

Endpoints:
  POST /register  - Create account, set auth cookies, return user.
  POST /login     - Verify credentials, set auth cookies, return user.
  POST /logout    - Clear auth cookies.
  POST /refresh   - Rotate tokens using the refresh cookie.
  GET  /me        - Return the currently authenticated user.

Cookie strategy:
  Tokens are set as HTTP-only cookies so they're never accessible to
  JavaScript, which prevents XSS token theft. The SameSite=Lax attribute
  provides CSRF protection for same-origin POST requests.

Rate limiting:
  Extension point - TODO Phase 7: add slowapi rate limiter to /login
  and /register to prevent brute-force and abuse.
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.security import (
    access_cookie_kwargs,
    refresh_cookie_kwargs,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    user = auth_service.register(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
    )
    # Reload with relations so the response includes profile + preferences.
    user = user_repository.get_user_with_relations(db, user.id) or user
    access_token, refresh_token = auth_service.issue_tokens(str(user.id))

    response.set_cookie(**access_cookie_kwargs(access_token))
    response.set_cookie(**refresh_cookie_kwargs(refresh_token))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Account created successfully",
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Sign in to an existing account",
)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    user = auth_service.login(db, email=body.email, password=body.password)
    user = user_repository.get_user_with_relations(db, user.id) or user
    access_token, refresh_token = auth_service.issue_tokens(str(user.id))

    response.set_cookie(**access_cookie_kwargs(access_token))
    response.set_cookie(**refresh_cookie_kwargs(refresh_token))

    return AuthResponse(user=UserResponse.model_validate(user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Sign out and clear session cookies",
)
def logout(response: Response) -> None:
    """Clear both auth cookies immediately."""
    response.delete_cookie(key="fittrack_access", path="/")
    response.delete_cookie(key="fittrack_refresh", path="/")


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Rotate access and refresh tokens",
)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    fittrack_refresh: str | None = Cookie(default=None),
) -> AuthResponse:
    """Issue new tokens using the refresh token cookie.

    Called automatically by the frontend when the access token expires.
    Both tokens are rotated - the old refresh token is implicitly invalidated.
    """
    from app.exceptions import UnauthorizedError

    if fittrack_refresh is None:
        raise UnauthorizedError("No refresh token present")

    user, access_token, new_refresh_token = auth_service.refresh_tokens(db, fittrack_refresh)
    user = user_repository.get_user_with_relations(db, user.id) or user

    response.set_cookie(**access_cookie_kwargs(access_token))
    response.set_cookie(**refresh_cookie_kwargs(new_refresh_token))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Tokens refreshed",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user",
)
def me(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserResponse:
    """Return the current user's full profile including preferences."""
    user = user_repository.get_user_with_relations(db, current_user.id) or current_user
    return UserResponse.model_validate(user)
