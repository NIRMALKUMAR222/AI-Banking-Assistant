"""
app/banking/synthetic_data.py - In-memory synthetic banking data (Faker-generated).

Data is generated once at module import and cached in module-level dicts,
so all requests within a process share the same consistent state.
"""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List

from faker import Faker

from app.banking.models import (
    Account, AccountStatus, AccountType,
    CardInfo, LoanProduct,
    Transaction, TransactionCategory, TransactionType,
)

fake = Faker("en_IN")
random.seed(42)
Faker.seed(42)

ACCOUNT_IDS = [f"ACC{i:03d}" for i in range(1, 11)]

_ACCOUNT_TYPES = list(AccountType)
_BRANCHES = [
    "Mumbai Main", "Delhi Connaught", "Bangalore Koramangala",
    "Chennai Anna Nagar", "Hyderabad Banjara Hills",
]


def _make_account(account_id: str) -> Account:
    acct_type = random.choice(_ACCOUNT_TYPES)
    balance = round(random.uniform(500, 250_000), 2)
    return Account(
        account_id=account_id,
        account_number=fake.numerify("####-####-####-####"),
        account_type=acct_type,
        status=random.choices(
            list(AccountStatus),
            weights=[80, 5, 5, 10],
        )[0],
        owner_name=fake.name(),
        balance=balance,
        available_balance=round(balance * random.uniform(0.85, 1.0), 2),
        currency="USD",
        opened_date=fake.date_between(start_date="-8y", end_date="-30d"),
        branch=random.choice(_BRANCHES),
        ifsc_code="SBNK" + fake.numerify("0######"),
    )


ACCOUNTS: Dict[str, Account] = {
    acc_id: _make_account(acc_id) for acc_id in ACCOUNT_IDS
}

_MERCHANTS = [
    "Amazon", "Swiggy", "Zomato", "Uber", "Ola",
    "Netflix", "Spotify", "Flipkart", "BigBasket", "D-Mart",
    "BPCL Petrol", "IRCTC", "MakeMyTrip", "Reliance Retail",
]

_CATEGORIES_DEBIT = [
    (TransactionCategory.PURCHASE, "Purchase at"),
    (TransactionCategory.WITHDRAWAL, "ATM Withdrawal"),
    (TransactionCategory.PAYMENT, "Bill payment to"),
    (TransactionCategory.TRANSFER, "Transfer to"),
    (TransactionCategory.FEE, "Service fee"),
]

_CATEGORIES_CREDIT = [
    (TransactionCategory.DEPOSIT, "Salary credit"),
    (TransactionCategory.TRANSFER, "Transfer from"),
    (TransactionCategory.REFUND, "Refund from"),
    (TransactionCategory.INTEREST, "Interest credit"),
]


def _make_transactions(account_id: str, n: int = 60) -> List[Transaction]:
    account = ACCOUNTS[account_id]
    txns: List[Transaction] = []
    running_balance = account.balance
    now = datetime.utcnow()

    for i in range(n):
        is_credit = random.random() < 0.35
        amount = round(random.uniform(10, 5000), 2)
        ts = now - timedelta(days=random.randint(0, 365), hours=random.randint(0, 23))

        if is_credit:
            cat, desc_prefix = random.choice(_CATEGORIES_CREDIT)
            merchant = None
            description = f"{desc_prefix} {fake.name()}"
            running_balance += amount
            txn_type = TransactionType.CREDIT
        else:
            cat, desc_prefix = random.choice(_CATEGORIES_DEBIT)
            merchant = random.choice(_MERCHANTS)
            description = f"{desc_prefix} {merchant}"
            running_balance -= amount
            txn_type = TransactionType.DEBIT

        txns.append(Transaction(
            transaction_id=f"TXN{uuid.uuid4().hex[:10].upper()}",
            account_id=account_id,
            transaction_type=txn_type,
            category=cat,
            amount=amount,
            currency="USD",
            description=description,
            merchant=merchant,
            timestamp=ts,
            balance_after=round(running_balance, 2),
            reference=fake.numerify("REF###########"),
        ))

    return sorted(txns, key=lambda t: t.timestamp, reverse=True)


TRANSACTIONS: Dict[str, List[Transaction]] = {
    acc_id: _make_transactions(acc_id) for acc_id in ACCOUNT_IDS
}

LOAN_PRODUCTS: List[LoanProduct] = [
    LoanProduct(
        loan_id="LOAN001",
        name="SecureBank Home Loan",
        loan_type="home",
        min_amount=500_000,
        max_amount=50_000_000,
        interest_rate_pa=8.5,
        max_tenure_months=360,
        min_cibil_score=700,
        processing_fee_pct=0.5,
        features=[
            "Zero prepayment penalty",
            "Balance transfer facility",
            "Top-up loan available",
            "Digital documentation",
        ],
    ),
    LoanProduct(
        loan_id="LOAN002",
        name="SecureBank Personal Loan",
        loan_type="personal",
        min_amount=10_000,
        max_amount=2_000_000,
        interest_rate_pa=11.99,
        max_tenure_months=60,
        min_cibil_score=650,
        processing_fee_pct=2.0,
        features=[
            "Instant disbursal within 24 hours",
            "No collateral required",
            "Flexible repayment options",
        ],
    ),
    LoanProduct(
        loan_id="LOAN003",
        name="SecureBank Auto Loan",
        loan_type="auto",
        min_amount=100_000,
        max_amount=5_000_000,
        interest_rate_pa=9.25,
        max_tenure_months=84,
        min_cibil_score=680,
        processing_fee_pct=1.0,
        features=[
            "Up to 100% on-road funding",
            "Quick approval in 2 hours",
            "Competitive interest rates",
        ],
    ),
]

_NETWORKS = ["Visa", "Mastercard", "Rupay"]
_CARD_TYPES = ["credit", "debit"]


def _make_card(account_id: str) -> CardInfo:
    card_type = random.choice(_CARD_TYPES)
    return CardInfo(
        card_id=f"CRD{uuid.uuid4().hex[:8].upper()}",
        account_id=account_id,
        card_type=card_type,
        card_network=random.choice(_NETWORKS),
        last_four=fake.numerify("####"),
        expiry=f"{random.randint(1,12):02d}/{random.randint(27,32)}",
        credit_limit=round(random.uniform(50_000, 500_000), 2) if card_type == "credit" else None,
        outstanding_balance=round(random.uniform(0, 30_000), 2) if card_type == "credit" else None,
        rewards_points=random.randint(0, 15_000),
        is_active=random.random() > 0.1,
    )


CARDS: Dict[str, CardInfo] = {
    acc_id: _make_card(acc_id) for acc_id in ACCOUNT_IDS
}
