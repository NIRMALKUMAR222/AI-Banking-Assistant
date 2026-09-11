"""
app/security/jwt_handler.py - JWT creation, validation, and refresh token support.

Access tokens:  short-lived (default 30 min), used for API calls.
Refresh tokens: long-lived (default 7 days), used to mint new access tokens.

All tokens are signed with HS256 using JWT_SECRET_KEY from settings.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()

_ALGORITHM = settings.jwt_algorithm
_SECRET    = settings.jwt_secret_key

# Sentinel that appears in the payload to distinguish token types
TokenKind = Literal["access", "refresh"]


class TokenError(Exception):
    """Raised when a JWT cannot be validated."""


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

def create_access_token(
    username: str,
    account_id: str,
    role: str = "customer",
) -> str:
    """Create a signed access token valid for JWT_ACCESS_TOKEN_EXPIRE_MINUTES."""
    expires = _utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub":        username,
        "account_id": account_id,
        "role":       role,
        "kind":       "access",
        "exp":        expires,
        "iat":        _utcnow(),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def create_refresh_token(username: str, account_id: str) -> str:
    """Create a signed refresh token valid for JWT_REFRESH_TOKEN_EXPIRE_DAYS."""
    expires = _utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub":        username,
        "account_id": account_id,
        "kind":       "refresh",
        "exp":        expires,
        "iat":        _utcnow(),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _decode(token: str, expected_kind: TokenKind) -> dict:
    """Decode and validate a JWT. Raises TokenError on any failure."""
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise TokenError(f"JWT decode failed: {exc}") from exc

    if payload.get("kind") != expected_kind:
        raise TokenError(
            f"Wrong token kind: expected '{expected_kind}', got '{payload.get('kind')}'"
        )
    return payload


def verify_access_token(token: str) -> dict:
    """
    Verify an access token and return its payload dict.
    Keys: sub, account_id, role, kind, exp, iat.
    Raises TokenError on failure.
    """
    return _decode(token, "access")


def verify_refresh_token(token: str) -> dict:
    """Verify a refresh token and return its payload dict."""
    return _decode(token, "refresh")


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------

def _bearer_to_token(authorization: str | None) -> str:
    """Extract the raw token from 'Bearer <token>' header value."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header (expected 'Bearer <token>').",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[len("Bearer "):].strip()


def get_current_user_payload(authorization: str | None) -> dict:
    """
    FastAPI-friendly helper: extract and validate the Bearer access token.
    Returns the decoded payload dict.
    Raises HTTP 401 on any failure.
    """
    token = _bearer_to_token(authorization)
    try:
        return verify_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc