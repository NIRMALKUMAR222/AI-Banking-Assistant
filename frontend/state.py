"""
frontend/state.py - Streamlit session state helpers and login logic.

Login now calls the backend /auth/login endpoint so passwords are
validated against bcrypt hashes. Tokens are stored in session state
and used by api_client.py for subsequent requests.
"""
from __future__ import annotations
import streamlit as st

# Demo credentials table — used only for the "View Demo Credentials" panel.
# Actual authentication is done server-side via the /auth/login endpoint.
DEMO_USERS: dict[str, dict] = {
    "alice":   {"password": "alice123",   "account_id": "ACC001", "name": "Alice Johnson"},
    "bob":     {"password": "bob123",     "account_id": "ACC002", "name": "Bob Smith"},
    "charlie": {"password": "charlie123", "account_id": "ACC003", "name": "Charlie Brown"},
    "dave":    {"password": "dave123",    "account_id": "ACC004", "name": "Dave Wilson"},
    "eve":     {"password": "eve123",     "account_id": "ACC005", "name": "Eve Martinez"},
    "admin":   {"password": "Admin@1234", "account_id": "ACC000", "name": "SecureBank Admin"},
}


def init_session():
    """Initialise all session-state keys with safe defaults."""
    defaults = {
        "logged_in":       False,
        "username":        None,
        "account_id":      None,
        "display_name":    None,
        "role":            None,
        "access_token":    None,        # JWT access token
        "refresh_token":   None,        # JWT refresh token
        "messages":        [],          # chat history [{role, content, meta}]
        "debug_mode":      False,
        "active_page":     "chat",
        "cheque_request":  None,
        "transfer_state":  None,
        "account_cache":   {},
        "balance_cache":   {},
        "tx_cache":        {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def login(username: str, password: str) -> tuple[bool, str]:
    """
    Authenticate against the backend /auth/login endpoint.
    Returns (success, error_message).
    On success, tokens and profile are stored in session state.
    """
    from frontend.api_client import login as api_login
    try:
        data = api_login(username.strip(), password.strip())
        st.session_state.logged_in    = True
        st.session_state.username     = data["username"]
        st.session_state.account_id   = data["account_id"]
        st.session_state.display_name = data["display_name"]
        st.session_state.role         = data["role"]
        st.session_state.access_token  = data["access_token"]
        st.session_state.refresh_token = data["refresh_token"]
        st.session_state.messages     = []
        return True, ""
    except Exception as exc:
        err = str(exc)
        if "401" in err:
            return False, "Invalid username or password."
        return False, f"Backend error: {err}"


def logout():
    """Clear all session state (also signals backend)."""
    from frontend.api_client import logout_backend
    logout_backend()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session()


def add_message(role: str, content: str, meta: dict | None = None):
    """Append a message to the chat history."""
    st.session_state.messages.append({
        "role":    role,
        "content": content,
        "meta":    meta or {},
    })


def get_chat_history_for_api() -> list[dict]:
    """Convert session messages to the format expected by the backend."""
    history = []
    for msg in st.session_state.messages[-12:]:
        if msg["role"] in ("user", "assistant"):
            history.append({"role": msg["role"], "content": msg["content"]})
    return history