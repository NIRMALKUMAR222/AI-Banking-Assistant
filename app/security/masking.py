"""
app/security/masking.py - Data masking utilities for PII / sensitive fields.

Rules
-----
- Account numbers : keep last 4 digits  ->  ****-****-****-1234
- Card numbers    : keep last 4 digits  ->  **** **** **** 9876
- PAN (tax ID)    : keep last 4 chars   ->  ABCDE0000X  ->  ******000X
- IFSC codes      : keep first 4 + last 3  ->  SBNK***4567
- Email           : mask local part     ->  a***@example.com
- Phone           : keep last 4 digits  ->  ******1234
- Balance amounts : only masked in logs, not in API responses
"""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Individual field maskers
# ---------------------------------------------------------------------------

def mask_account_number(number: str) -> str:
    """****-****-****-XXXX"""
    clean = re.sub(r"[^0-9]", "", number)
    if len(clean) >= 4:
        return "****-****-****-" + clean[-4:]
    return "****"


def mask_card_number(number: str) -> str:
    """**** **** **** XXXX"""
    clean = re.sub(r"[^0-9]", "", number)
    if len(clean) >= 4:
        return "**** **** **** " + clean[-4:]
    return "****"


def mask_ifsc(ifsc: str) -> str:
    """SBNK***XXXX"""
    if len(ifsc) >= 7:
        return ifsc[:4] + "***" + ifsc[-3:]
    return "***"


def mask_email(email: str) -> str:
    """a***@domain.com"""
    if "@" not in email:
        return "***@***.***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return local + "***@" + domain
    return local[0] + "***@" + domain


def mask_phone(phone: str) -> str:
    """Keep last 4 digits."""
    digits = re.sub(r"[^0-9]", "", phone)
    if len(digits) >= 4:
        return "X" * (len(digits) - 4) + digits[-4:]
    return "****"


def mask_balance(amount: float) -> str:
    """Return a masked balance string for logging (not for API responses)."""
    return "****.**"


# ---------------------------------------------------------------------------
# Structured-data maskers (operate on dicts returned from the banking API)
# ---------------------------------------------------------------------------

_ACCOUNT_MASK_FIELDS = {
    "account_number": mask_account_number,
    "ifsc_code":      mask_ifsc,
}

_CARD_MASK_FIELDS = {
    "card_id":   lambda v: "CRD****" + v[-4:] if len(v) >= 4 else "****",
    "last_four": lambda v: v,   # already masked by design
}

_TXN_MASK_FIELDS = {
    "transaction_id": lambda v: v[:3] + "****" + v[-4:] if len(v) >= 7 else "****",
    "reference":      lambda v: "REF****" + v[-4:] if len(v) >= 4 else "****",
}


def mask_account(account: dict) -> dict:
    """Return a copy of account dict with sensitive fields masked."""
    masked = dict(account)
    for field, masker in _ACCOUNT_MASK_FIELDS.items():
        if field in masked:
            masked[field] = masker(str(masked[field]))
    return masked


def mask_card(card: dict) -> dict:
    """Return a copy of card dict with sensitive fields masked."""
    masked = dict(card)
    for field, masker in _CARD_MASK_FIELDS.items():
        if field in masked:
            masked[field] = masker(str(masked[field]))
    return masked


def mask_transaction(txn: dict) -> dict:
    """Return a copy of transaction dict with sensitive fields masked."""
    masked = dict(txn)
    for field, masker in _TXN_MASK_FIELDS.items():
        if field in masked:
            masked[field] = masker(str(masked[field]))
    return masked


# ---------------------------------------------------------------------------
# Log-safe context builder
# ---------------------------------------------------------------------------

def safe_log_context(account_id: str | None, query: str) -> dict:
    """Build a log-safe dict for audit logging — no raw PII."""
    return {
        "account_id_prefix": (account_id[:3] + "***") if account_id else None,
        "query_length":      len(query),
        "query_preview":     query[:30] + "..." if len(query) > 30 else query,
    }