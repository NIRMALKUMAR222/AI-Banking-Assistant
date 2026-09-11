"""
app/intent/router.py - Intent classification and routing for the chat pipeline.

Intents
-------
account_inquiry      -> banking API + RAG
transaction_history  -> banking API only
balance_check        -> banking API only
product_info         -> RAG only
loan_inquiry         -> RAG + banking API
card_inquiry         -> RAG + banking API
fraud_alert          -> RAG + escalation flag
general_banking      -> RAG only
unknown              -> RAG only (fallback)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from app.rag.embeddings import Embedder


@dataclass
class Intent:
    name: str
    description: str
    keywords: List[str]
    needs_banking_api: bool = False
    needs_rag: bool = True
    escalate: bool = False


INTENTS: List[Intent] = [
    Intent(
        name="account_inquiry",
        description="Questions about account details, account number, account type, or account status.",
        keywords=["account details", "account number", "account status", "account info", "my account info"],
        needs_banking_api=True,
        needs_rag=True,
    ),
    Intent(
        name="balance_check",
        description="Check current account balance or available funds.",
        keywords=["balance", "how much", "available funds", "remaining balance", "current balance", "account balance"],
        needs_banking_api=True,
        needs_rag=False,
    ),
    Intent(
        name="transaction_history",
        description="View past transactions, payments, or transfers.",
        keywords=["transactions", "history", "statement", "payments", "transfers", "recent activity", "spending", "debits", "credits"],
        needs_banking_api=True,
        needs_rag=False,
    ),
    Intent(
        name="product_info",
        description="Information about banking products, interest rates, fees, or features.",
        keywords=["product", "fee", "features", "what is", "tell me about", "how does", "savings", "checking", "open a savings"],
        needs_banking_api=False,
        needs_rag=True,
    ),
    Intent(
        name="loan_inquiry",
        description="Questions about loan eligibility, loan rates, or existing loans.",
        keywords=["loan", "loan products", "borrow", "mortgage", "emi", "installment", "credit", "repayment", "interest"],
        needs_banking_api=True,
        needs_rag=True,
    ),
    Intent(
        name="card_inquiry",
        description="Questions about credit or debit cards, rewards, or card limits.",
        keywords=["card", "credit card", "debit card", "rewards", "cashback", "limit", "pin", "card number"],
        needs_banking_api=True,
        needs_rag=True,
    ),
    Intent(
        name="fraud_alert",
        description="Reports or concerns about fraud, unauthorized transactions, or suspicious activity.",
        keywords=["fraud", "unauthorized", "suspicious", "scam", "hacked", "stolen", "dispute", "chargeback"],
        needs_banking_api=True,
        needs_rag=True,
        escalate=True,
    ),
    Intent(
        name="general_banking",
        description="General banking questions, policies, procedures, KYC, or help.",
        keywords=["help", "support", "policy", "procedure", "how to", "what should", "can i", "branch", "atm", "kyc", "cheque", "chequebook", "international transfer", "swift"],
        needs_banking_api=False,
        needs_rag=True,
    ),
]

_FALLBACK_INTENT = Intent(
    name="unknown",
    description="Catch-all for unclassified queries.",
    keywords=[],
    needs_banking_api=False,
    needs_rag=True,
)


class IntentRouter:
    """
    Two-stage classifier:
    1. Keyword matching (fast, interpretable).
    2. Embedding cosine similarity as tiebreaker / fallback.
    """

    def __init__(self, embedder: Embedder):
        self._embedder = embedder
        self._intent_vecs: np.ndarray = embedder.embed_texts(
            [intent.description for intent in INTENTS]
        )

    def classify(self, query: str) -> Intent:
        query_lower = query.lower()

        # Stage 1: keyword matching
        keyword_scores = [
            sum(1 for kw in intent.keywords if kw in query_lower)
            for intent in INTENTS
        ]
        max_kw_score = max(keyword_scores)
        if max_kw_score > 0:
            best_idx = keyword_scores.index(max_kw_score)
            return INTENTS[best_idx]

        # Stage 2: embedding similarity fallback
        query_vec = self._embedder.embed_query(query)
        sims = self._intent_vecs @ query_vec
        best_idx = int(np.argmax(sims))
        if sims[best_idx] > 0.25:
            return INTENTS[best_idx]

        return _FALLBACK_INTENT


_router: IntentRouter | None = None


def get_intent_router(embedder: Embedder) -> IntentRouter:
    """Singleton IntentRouter (requires the shared embedder)."""
    global _router
    if _router is None:
        _router = IntentRouter(embedder)
    return _router
