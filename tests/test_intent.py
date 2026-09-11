"""
tests/test_intent.py - Tests for the intent classification router.
"""
import pytest
from app.rag.embeddings import Embedder
from app.intent.router import IntentRouter, INTENTS, _FALLBACK_INTENT


@pytest.fixture(scope="module")
def router():
    embedder = Embedder()
    return IntentRouter(embedder)


@pytest.mark.parametrize("query,expected_intent", [
    ("What is my account balance?", "balance_check"),
    ("Show me my recent transactions", "transaction_history"),
    ("I want to apply for a home loan", "loan_inquiry"),
    ("Tell me about your credit cards", "card_inquiry"),
    ("I think someone hacked my account", "fraud_alert"),
    ("How do I open a savings account?", "product_info"),
    ("What are the interest rates?", "loan_inquiry"),
    ("I need help with something", "general_banking"),
    ("Can I get a personal loan?", "loan_inquiry"),
    ("I see an unauthorized transaction", "fraud_alert"),
])
def test_intent_classification_keyword(router, query, expected_intent):
    intent = router.classify(query)
    assert intent.name == expected_intent, (
        f"Query: '{query}' -> got '{intent.name}', expected '{expected_intent}'"
    )


def test_intent_embedding_fallback(router):
    """A query with no keywords should still return a plausible intent."""
    # No keywords but semantically about balance
    intent = router.classify("How much do I currently possess in my financial holdings?")
    # Should be balance_check or account_inquiry (embedding similarity)
    assert intent.name in ("balance_check", "account_inquiry", "unknown")


def test_fraud_intent_has_escalate_flag(router):
    intent = router.classify("I think I was scammed")
    assert intent.name == "fraud_alert"
    assert intent.escalate is True


def test_loan_intent_needs_both(router):
    intent = router.classify("What loan products are available?")
    # loan_inquiry needs both banking API and RAG
    assert intent.needs_banking_api is True
    assert intent.needs_rag is True


def test_balance_check_no_rag(router):
    intent = router.classify("What is my current balance?")
    assert intent.name == "balance_check"
    assert intent.needs_rag is False


def test_product_info_no_banking_api(router):
    intent = router.classify("Tell me about your savings account features")
    assert intent.name == "product_info"
    assert intent.needs_banking_api is False


def test_all_intents_have_required_fields():
    for intent in INTENTS:
        assert intent.name
        assert intent.description
        assert isinstance(intent.keywords, list)
        assert isinstance(intent.needs_rag, bool)
        assert isinstance(intent.needs_banking_api, bool)
