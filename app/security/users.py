"""
app/security/users.py - In-memory user store with bcrypt-hashed passwords.

In production this would be replaced by a database query.
Passwords are pre-hashed at module import so startup cost is paid once.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.security.password import hash_password, verify_password


@dataclass(frozen=True)
class User:
    username:   str
    hashed_password: str
    account_id: str
    display_name: str
    role: str = "customer"   # "customer" | "admin"
    is_active: bool = True


# ---------------------------------------------------------------------------
# User registry — passwords are hashed at import time
# ---------------------------------------------------------------------------

_PLAIN_USERS = [
    ("alice",   "alice123",   "ACC001", "Alice Johnson",  "customer"),
    ("bob",     "bob123",     "ACC002", "Bob Smith",      "customer"),
    ("charlie", "charlie123", "ACC003", "Charlie Brown",  "customer"),
    ("dave",    "dave123",    "ACC004", "Dave Wilson",    "customer"),
    ("eve",     "eve123",     "ACC005", "Eve Martinez",   "customer"),
    ("admin",   "Admin@1234", "ACC000", "SecureBank Admin", "admin"),
]

_USER_DB: dict[str, User] = {
    username: User(
        username=username,
        hashed_password=hash_password(plain_pw),
        account_id=account_id,
        display_name=display_name,
        role=role,
    )
    for username, plain_pw, account_id, display_name, role in _PLAIN_USERS
}


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_user(username: str) -> Optional[User]:
    """Return a User by username (case-insensitive), or None if not found."""
    return _USER_DB.get(username.lower().strip())


import bcrypt as _bcrypt
_DUMMY_HASH: str = _bcrypt.hashpw(b"dummy_timing_constant", _bcrypt.gensalt(12)).decode("utf-8")


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Validate credentials.  Returns the User on success, None on failure.
    Never leaks whether the username or password was wrong.
    """
    user = get_user(username)
    if user is None or not user.is_active:
        # Always run a bcrypt check to prevent timing-based username enumeration
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def list_usernames() -> list[str]:
    """Return all registered usernames (for admin/debug use only)."""
    return list(_USER_DB.keys())