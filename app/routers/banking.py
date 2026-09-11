"""
app/routers/banking.py - Synthetic banking REST endpoints.
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.banking.models import (
    Account, CardInfo, LoanProduct, Transaction,
    TransferRequest, TransferResponse,
)
from app.banking.synthetic_data import ACCOUNTS, CARDS, LOAN_PRODUCTS, TRANSACTIONS
from app.middleware.auth import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/accounts/{account_id}", response_model=Account)
def get_account(account_id: str):
    """Retrieve account details by account ID."""
    account = ACCOUNTS.get(account_id.upper())
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )
    return account


@router.get("/accounts/{account_id}/balance")
def get_balance(account_id: str):
    """Get current and available balance."""
    account = ACCOUNTS.get(account_id.upper())
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    return {
        "account_id": account.account_id,
        "balance": account.balance,
        "available_balance": account.available_balance,
        "currency": account.currency,
    }


@router.get("/accounts/{account_id}/transactions", response_model=List[Transaction])
def get_transactions(
    account_id: str,
    limit: int = 20,
    offset: int = 0,
):
    """Paginated transaction history for an account."""
    if account_id.upper() not in ACCOUNTS:
        raise HTTPException(status_code=404, detail="Account not found.")
    txns = TRANSACTIONS.get(account_id.upper(), [])
    return txns[offset: offset + limit]


@router.post("/transfer", response_model=TransferResponse)
def transfer_funds(req: TransferRequest):
    """Simulate a fund transfer between two accounts."""
    src = ACCOUNTS.get(req.from_account_id.upper())
    dst = ACCOUNTS.get(req.to_account_id.upper())

    if not src:
        raise HTTPException(status_code=404, detail="Source account not found.")
    if not dst:
        raise HTTPException(status_code=404, detail="Destination account not found.")
    if src.balance < req.amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient funds.",
        )

    src.balance = round(src.balance - req.amount, 2)
    src.available_balance = round(src.available_balance - req.amount, 2)
    dst.balance = round(dst.balance + req.amount, 2)
    dst.available_balance = round(dst.available_balance + req.amount, 2)

    txn_id = f"TXN{uuid.uuid4().hex[:10].upper()}"
    return TransferResponse(
        success=True,
        transaction_id=txn_id,
        message=f"Successfully transferred {req.amount} {src.currency} to {req.to_account_id}.",
        new_balance=src.balance,
    )


@router.get("/loans", response_model=List[LoanProduct])
def list_loans():
    """List all available loan products."""
    return LOAN_PRODUCTS


@router.get("/loans/{loan_id}", response_model=LoanProduct)
def get_loan(loan_id: str):
    """Get a specific loan product by ID."""
    for loan in LOAN_PRODUCTS:
        if loan.loan_id.upper() == loan_id.upper():
            return loan
    raise HTTPException(status_code=404, detail="Loan product not found.")


@router.get("/cards/{account_id}", response_model=CardInfo)
def get_card(account_id: str):
    """Get card details for an account."""
    card = CARDS.get(account_id.upper())
    if not card:
        raise HTTPException(status_code=404, detail="No card found for this account.")
    return card
