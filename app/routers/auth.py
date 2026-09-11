"""
app/routers/auth.py - Authentication endpoints.

POST /auth/login    -> {access_token, refresh_token, token_type, ...}
POST /auth/refresh  -> {access_token, token_type}
GET  /auth/me       -> {username, account_id, role, display_name}
POST /auth/logout   -> {message}  (client-side invalidation only)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.security.users import authenticate_user, get_user
from app.security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    TokenError,
)
from app.middleware.auth import require_jwt
from app.logging_config import log_auth_event

logger = logging.getLogger("securebank.auth")
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int   # seconds
    username:      str
    account_id:    str
    display_name:  str
    role:          str


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int


class MeResponse(BaseModel):
    username:     str
    account_id:   str
    display_name: str
    role:         str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse, summary="Obtain JWT tokens")
def login(req: LoginRequest):
    """
    Authenticate with username + password.
    Returns a short-lived access token and a long-lived refresh token.
    """
    user = authenticate_user(req.username, req.password)
    if user is None:
        log_auth_event("login_failed", req.username, success=False)
        # Use 401 with a generic message to avoid username enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token  = create_access_token(user.username, user.account_id, user.role)
    refresh_token = create_refresh_token(user.username, user.account_id)

    from app.config import get_settings
    settings = get_settings()

    log_auth_event("login_success", user.username, success=True, extra={"role": user.role})
    logger.info("User logged in", extra={"username": user.username, "role": user.role})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        username=user.username,
        account_id=user.account_id,
        display_name=user.display_name,
        role=user.role,
    )


@router.post("/refresh", response_model=AccessTokenResponse, summary="Refresh access token")
def refresh(req: RefreshRequest):
    """
    Exchange a valid refresh token for a new access token.
    The refresh token itself is not rotated (stateless implementation).
    """
    try:
        payload = verify_refresh_token(req.refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {exc}",
        ) from exc

    username   = payload["sub"]
    account_id = payload["account_id"]

    user = get_user(username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

    from app.config import get_settings
    settings = get_settings()

    access_token = create_access_token(username, account_id, user.role)
    log_auth_event("token_refreshed", username, success=True)

    return AccessTokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=MeResponse, summary="Get current user info")
def me(payload: dict = Depends(require_jwt)):
    """Return the profile of the currently authenticated user."""
    username = payload.get("sub")
    user = get_user(username) if username else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return MeResponse(
        username=user.username,
        account_id=user.account_id,
        display_name=user.display_name,
        role=user.role,
    )


@router.post("/logout", summary="Invalidate session (client-side)")
def logout(payload: dict = Depends(require_jwt)):
    """
    Stateless logout — instructs the client to discard the tokens.
    In a stateful system, this would add the token JTI to a blocklist.
    """
    log_auth_event("logout", payload.get("sub"), success=True)
    return {"message": "Successfully logged out. Please discard your tokens."}