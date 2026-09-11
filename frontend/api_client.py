"""
frontend/api_client.py - HTTP client that talks to the SecureBank FastAPI backend.

Auth strategy:
  1. On login, call POST /auth/login -> store access_token + refresh_token in session.
  2. All subsequent API calls use Authorization: Bearer <access_token>.
  3. On 401, attempt a token refresh once; if that fails, signal the UI to re-login.
  4. Banking endpoints additionally send X-API-Key as fallback for service calls.

All functions are synchronous (Streamlit is sync). Uses httpx for convenience.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY  = os.getenv("API_KEY", "securebank-dev-key-change-me")
TIMEOUT  = 60.0   # seconds -- generous for LLM generation


# ---------------------------------------------------------------------------
# Header builders
# ---------------------------------------------------------------------------

def _bearer_headers() -> dict:
    """Use JWT Bearer token if we have one, fall back to API key."""
    token = st.session_state.get("access_token")
    if token:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }
    return {
        "X-API-Key":     API_KEY,
        "Content-Type":  "application/json",
    }


def _api_key_headers() -> dict:
    """Always use API key (for banking endpoints that support both)."""
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Low-level HTTP helpers (with one token-refresh retry on 401)
# ---------------------------------------------------------------------------

def _refresh_token() -> bool:
    """Try to refresh the access token. Return True on success."""
    refresh = st.session_state.get("refresh_token")
    if not refresh:
        return False
    try:
        resp = httpx.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh},
            timeout=10,
        )
        if resp.status_code == 200:
            st.session_state.access_token = resp.json()["access_token"]
            return True
    except Exception:
        pass
    return False


def _get(path: str, use_jwt: bool = False, **params) -> Any:
    url  = f"{BASE_URL}{path}"
    hdrs = _bearer_headers() if use_jwt else _api_key_headers()
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(url, headers=hdrs, params=params)
        if resp.status_code == 401 and use_jwt and _refresh_token():
            resp = client.get(url, headers=_bearer_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


def _post(path: str, body: dict, use_jwt: bool = False) -> Any:
    url  = f"{BASE_URL}{path}"
    hdrs = _bearer_headers() if use_jwt else _api_key_headers()
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(url, headers=hdrs, json=body)
        if resp.status_code == 401 and use_jwt and _refresh_token():
            resp = client.post(url, headers=_bearer_headers(), json=body)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login(username: str, password: str) -> dict:
    """Authenticate and return the full token response dict."""
    url = f"{BASE_URL}/auth/login"
    with httpx.Client(timeout=10) as client:
        resp = client.post(url, json={"username": username, "password": password})
        resp.raise_for_status()
        return resp.json()


def logout_backend() -> None:
    """Signal the backend that the user is logging out."""
    try:
        _post("/auth/logout", {}, use_jwt=True)
    except Exception:
        pass   # best-effort, client-side state is authoritative


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def health() -> dict:
    return _get("/health")


# ---------------------------------------------------------------------------
# Accounts (use API key -- banking endpoints support both)
# ---------------------------------------------------------------------------

def get_account(account_id: str) -> dict:
    return _get(f"/banking/accounts/{account_id}")


def get_balance(account_id: str) -> dict:
    return _get(f"/banking/accounts/{account_id}/balance")


def get_transactions(account_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    return _get(f"/banking/accounts/{account_id}/transactions", limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------

def transfer_funds(from_id: str, to_id: str, amount: float, description: str = "Fund transfer") -> dict:
    return _post("/banking/transfer", {
        "from_account_id": from_id,
        "to_account_id":   to_id,
        "amount":          amount,
        "description":     description,
    })


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

def get_card(account_id: str) -> dict:
    return _get(f"/banking/cards/{account_id}")


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

def list_loans() -> list[dict]:
    return _get("/banking/loans")


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def ingest_documents() -> dict:
    return _post("/ingest/", {})


def ingest_status() -> dict:
    return _get("/ingest/status")


# ---------------------------------------------------------------------------
# Chat (uses JWT for ownership enforcement)
# ---------------------------------------------------------------------------

def chat(
    query: str,
    account_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    return _post("/chat/", {
        "query":                query,
        "account_id":           account_id,
        "conversation_history": conversation_history or [],
    }, use_jwt=True)