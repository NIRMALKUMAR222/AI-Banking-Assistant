"""
app/banking/models.py - Pydantic models for banking entities.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AccountType(str, Enum):
    SAVINGS = "savings"
    CHECKING = "checking"
    FIXED_DEPOSIT = "fixed_deposit"
    CURRENT = "current"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionCategory(str, Enum):
    TRANSFER = "transfer"
    PURCHASE = "purchase"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    PAYMENT = "payment"
    REFUND = "refund"
    FEE = "fee"
    INTEREST = "interest"


class Account(BaseModel):
    account_id: str
    account_number: str
    account_type: AccountType
    status: AccountStatus
    owner_name: str
    balance: float = Field(..., description="Current balance in USD")
    available_balance: float
    currency: str = "USD"
    opened_date: date
    branch: str
    ifsc_code: str


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    transaction_type: TransactionType
    category: TransactionCategory
    amount: float
    currency: str = "USD"
    description: str
    merchant: Optional[str] = None
    timestamp: datetime
    balance_after: float
    reference: str


class LoanProduct(BaseModel):
    loan_id: str
    name: str
    loan_type: str
    min_amount: float
    max_amount: float
    interest_rate_pa: float = Field(..., description="Annual interest rate percentage")
    max_tenure_months: int
    min_cibil_score: int
    processing_fee_pct: float
    features: List[str]


class CardInfo(BaseModel):
    card_id: str
    account_id: str
    card_type: str
    card_network: str
    last_four: str
    expiry: str
    credit_limit: Optional[float] = None
    outstanding_balance: Optional[float] = None
    rewards_points: int = 0
    is_active: bool = True


class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float = Field(..., gt=0, description="Amount to transfer (must be > 0)")
    description: str = "Fund transfer"


class TransferResponse(BaseModel):
    success: bool
    transaction_id: str
    message: str
    new_balance: Optional[float] = None
