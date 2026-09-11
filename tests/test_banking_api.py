"""
tests/test_banking_api.py - Tests for the synthetic banking API endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings

settings = get_settings()
API_KEY = settings.api_key
HEADERS = {"X-API-Key": API_KEY}

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "vector_store" in data


def test_get_account_valid():
    resp = client.get("/banking/accounts/ACC001", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_id"] == "ACC001"
    assert "balance" in data
    assert "account_type" in data


def test_get_account_not_found():
    resp = client.get("/banking/accounts/ACC999", headers=HEADERS)
    assert resp.status_code == 404


def test_get_account_no_auth():
    resp = client.get("/banking/accounts/ACC001")
    assert resp.status_code == 422  # missing header


def test_get_account_bad_auth():
    resp = client.get("/banking/accounts/ACC001", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_get_balance():
    resp = client.get("/banking/accounts/ACC001/balance", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "balance" in data
    assert "available_balance" in data
    assert data["account_id"] == "ACC001"


def test_get_transactions():
    resp = client.get("/banking/accounts/ACC001/transactions", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 20  # default limit
    if data:
        txn = data[0]
        assert "transaction_id" in txn
        assert "amount" in txn
        assert "transaction_type" in txn


def test_get_transactions_pagination():
    resp = client.get(
        "/banking/accounts/ACC001/transactions?limit=5&offset=0",
        headers=HEADERS
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 5


def test_list_loans():
    resp = client.get("/banking/loans", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    loan_ids = {l["loan_id"] for l in data}
    assert "LOAN001" in loan_ids


def test_get_loan():
    resp = client.get("/banking/loans/LOAN002", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["loan_type"] == "personal"


def test_get_loan_not_found():
    resp = client.get("/banking/loans/LOAN999", headers=HEADERS)
    assert resp.status_code == 404


def test_get_card():
    resp = client.get("/banking/cards/ACC001", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "card_id" in data
    assert "last_four" in data


def test_transfer_funds():
    # Get initial balances
    src_resp = client.get("/banking/accounts/ACC001/balance", headers=HEADERS)
    src_balance = src_resp.json()["balance"]
    dst_resp = client.get("/banking/accounts/ACC002/balance", headers=HEADERS)
    dst_balance = dst_resp.json()["balance"]

    amount = 100.0
    resp = client.post(
        "/banking/transfer",
        json={
            "from_account_id": "ACC001",
            "to_account_id": "ACC002",
            "amount": amount,
            "description": "Test transfer",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "transaction_id" in data
    assert data["new_balance"] == pytest.approx(src_balance - amount, rel=1e-3)


def test_transfer_insufficient_funds():
    resp = client.post(
        "/banking/transfer",
        json={
            "from_account_id": "ACC001",
            "to_account_id": "ACC002",
            "amount": 999_999_999.0,
        },
        headers=HEADERS,
    )
    assert resp.status_code == 422


def test_ingest_status():
    resp = client.get("/ingest/status", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "backend" in data
    assert "total_documents" in data
