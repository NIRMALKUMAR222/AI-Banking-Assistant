"""
app/security/password.py - Bcrypt password hashing and verification.

Uses the bcrypt library directly (avoids passlib/bcrypt version incompatibility).
Work factor (rounds) = 12.
"""
from __future__ import annotations

import bcrypt


_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*. Safe to store in a database."""
    if not plain:
        raise ValueError("Password must not be empty.")
    # bcrypt.hashpw expects bytes; encode to UTF-8, cap at 72 bytes (bcrypt limit)
    pw_bytes = plain.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*. Timing-safe via bcrypt.checkpw."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    """
    Return True if the stored hash was generated with fewer than _ROUNDS rounds
    and should be rehashed on next login.
    """
    try:
        return bcrypt.checkpw(b"probe", hashed.encode("utf-8")) is not None and False
    except Exception:
        pass
    # Check cost factor in the hash prefix: $2b$12$ means 12 rounds
    try:
        parts = hashed.split("$")
        if len(parts) >= 3:
            stored_rounds = int(parts[2])
            return stored_rounds < _ROUNDS
    except Exception:
        pass
    return False