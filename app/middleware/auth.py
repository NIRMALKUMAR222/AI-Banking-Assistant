"""
app/middleware/auth.py - Authentication dependencies.

Supports two auth schemes:
  1. API Key  : X-API-Key header (service-to-service / legacy)
  2. JWT Bearer: Authorization: Bearer <token> (user-facing)

Routers choose which scheme to require via the appropriate dependency.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings
from app.security.jwt_handler import get_current_user_payload

settings = get_settings()


# ---------------------------------------------------------------------------
# Scheme 1: API Key
# ---------------------------------------------------------------------------

def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI dependency: validate the X-API-Key header."""
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return x_api_key


# ---------------------------------------------------------------------------
# Scheme 2: JWT Bearer
# ---------------------------------------------------------------------------

def require_jwt(authorization: str | None = Header(default=None)) -> dict:
    """
    FastAPI dependency: validate the Authorization: Bearer <token> header.
    Returns the decoded JWT payload dict.
    """
    return get_current_user_payload(authorization)


def require_admin(payload: dict = Depends(require_jwt)) -> dict:
    """Restrict to users with role='admin'."""
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return payload


# ---------------------------------------------------------------------------
# Scheme 3: Either API Key OR JWT (flexible — used by the chat endpoint)
# ---------------------------------------------------------------------------

def require_auth(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> dict:
    """
    Accept either API Key OR JWT Bearer.
    Returns a normalised identity dict: {sub, account_id, role, auth_scheme}.
    """
    # Try API key first
    if x_api_key:
        if x_api_key == settings.api_key:
            return {"sub": "service", "account_id": None, "role": "service", "auth_scheme": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    # Try JWT
    if authorization:
        payload = get_current_user_payload(authorization)
        payload["auth_scheme"] = "jwt"
        return payload

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-API-Key or Authorization: Bearer <token>.",
        headers={"WWW-Authenticate": "Bearer"},
    )