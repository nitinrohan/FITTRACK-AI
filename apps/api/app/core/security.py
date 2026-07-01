"""Password hashing and JWT token management.

Security decisions:
- bcrypt via passlib, cost factor 12 - strong enough for production while
  keeping login latency under 200ms on typical hardware.
- Two token types: short-lived access token (30 min) + long-lived refresh
  token (30 days). Both stored in HTTP-only, SameSite=Lax cookies.
- Tokens carry only the user ID in the 'sub' claim - no other PII.
- Token type ('access' | 'refresh') is embedded in the payload so access
  tokens cannot be used as refresh tokens and vice versa.
- Refresh tokens are rotated on every use (issued fresh on each /auth/refresh
  call) to limit the window of a stolen token.

Cookie names:
  fittrack_access   - short-lived JWT, authorises API requests
  fittrack_refresh  - long-lived JWT, used only on POST /api/v1/auth/refresh
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal, TypedDict

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger(__name__)

# Cookie names - referenced here and in the auth router so they stay in sync.
ACCESS_COOKIE_NAME = "fittrack_access"
REFRESH_COOKIE_NAME = "fittrack_refresh"

TokenType = Literal["access", "refresh"]

# passlib context - auto-rehashes if the algorithm or cost factor changes.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ── Password helpers ──────────────────────────────────────────────────────


def _prepare_password(plain_password: str) -> str:
    """SHA-256 pre-hash the password before bcrypt.

    bcrypt truncates input at 72 bytes; pre-hashing with SHA-256 converts any
    length password into a consistent 64-char hex digest, avoiding silent
    truncation and the ValueError raised by newer bcrypt versions (>=4.0).
    """
    return hashlib.sha256(plain_password.encode()).hexdigest()


def hash_password(plain_password: str) -> str:
    """Return the bcrypt hash of a plain-text password."""
    return _pwd_context.hash(_prepare_password(plain_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash.

    Uses a constant-time comparison internally - safe against timing attacks.
    """
    return _pwd_context.verify(_prepare_password(plain_password), hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────


def create_access_token(user_id: str) -> str:
    """Create a short-lived JWT access token for user_id."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    return _encode_token(user_id, "access", expire, settings.jwt_secret_key, settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token for user_id."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    return _encode_token(
        user_id, "refresh", expire, settings.jwt_secret_key, settings.jwt_algorithm
    )


def decode_token(token: str, expected_type: TokenType) -> str:
    """Decode and validate a JWT; return the user_id (sub claim).

    Raises JWTError if the token is invalid, expired, or the wrong type.
    The caller should convert JWTError to an appropriate HTTP exception.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise

    token_type: str | None = payload.get("type")
    if token_type != expected_type:
        raise JWTError(f"Expected token type '{expected_type}', got '{token_type}'")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise JWTError("Token missing 'sub' claim")

    return user_id


def _encode_token(
    user_id: str,
    token_type: TokenType,
    expire: datetime,
    secret: str,
    algorithm: str,
) -> str:
    payload = {
        "sub": user_id,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


# ── Cookie helpers ────────────────────────────────────────────────────────


class CookieKwargs(TypedDict):
    key: str
    value: str
    httponly: bool
    samesite: Literal["lax", "strict", "none"]
    secure: bool
    max_age: int
    path: str


def cookie_kwargs(name: str, value: str, max_age: int, is_production: bool) -> CookieKwargs:
    """Return kwargs for response.set_cookie() with consistent security settings."""
    return CookieKwargs(
        key=name,
        value=value,
        httponly=True,
        samesite="lax",
        secure=is_production,  # Require HTTPS in production only.
        max_age=max_age,
        path="/",
    )


def access_cookie_kwargs(token: str) -> CookieKwargs:
    settings = get_settings()
    max_age = settings.jwt_access_token_expire_minutes * 60
    return cookie_kwargs(ACCESS_COOKIE_NAME, token, max_age, settings.is_production)


def refresh_cookie_kwargs(token: str) -> CookieKwargs:
    settings = get_settings()
    max_age = settings.jwt_refresh_token_expire_days * 86400
    return cookie_kwargs(REFRESH_COOKIE_NAME, token, max_age, settings.is_production)
