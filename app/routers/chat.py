"""
app/routers/chat.py - Main chat endpoint integrating RAG + Intent + Grok.

Security additions in this version
-----------------------------------
- Prompt injection guard (rejects / sanitizes malicious inputs)
- Safe RAG fallback (graceful response when vector store is empty)
- Account ownership check (JWT users can only query their own account)
- Structured audit logging via logging_config
- Data masking applied before banking context is sent to the LLM
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.banking.synthetic_data import ACCOUNTS, CARDS, LOAN_PRODUCTS, TRANSACTIONS
from app.intent.router import get_intent_router
from app.llm.grok_client import get_grok_client
from app.llm.prompts import build_banking_prompt, build_rag_prompt
from app.middleware.auth import require_auth
from app.rag.retriever import retrieve
from app.rag.embeddings import get_embedder
from app.rag.vector_store import get_vector_store
from app.security.masking import mask_account, mask_card, mask_transaction, safe_log_context
from app.security.prompt_guard import inspect as guard_inspect

from app.logging_config import log_chat_event

logger = logging.getLogger("securebank.chat")

router = APIRouter(dependencies=[Depends(require_auth)])

_SAFE_FALLBACK = (
    "I don't have enough information in my knowledge base to answer that question confidently. "
    "Please contact SecureBank support at 1800-SECURE-1 or visit securebank.com for accurate assistance."
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    account_id: Optional[str] = None
    conversation_history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    intent: str
    sources: list[str]
    escalate: bool = False
    account_id: Optional[str] = None
    risk_score: int = 0          # prompt-injection risk score (0-100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_account_id(req: ChatRequest, identity: dict) -> str | None:
    """
    Determine the effective account ID for this request.
    - JWT users: must match their own account_id (ownership enforcement)
    - API-key / service calls: trust the account_id in the request body
    """
    if identity.get("auth_scheme") == "jwt":
        jwt_account = identity.get("account_id")
        # If caller supplies an account_id that doesn't match their JWT, reject
        if req.account_id and req.account_id.upper() != (jwt_account or "").upper():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may only query your own account.",
            )
        return jwt_account
    # Service / API-key: use whatever is in the body
    return req.account_id


def _gather_banking_context(intent_name: str, account_id: str | None) -> dict | None:
    """Pull relevant banking data for the given intent and account (masked)."""
    if not account_id:
        return None
    acc_id  = account_id.upper()
    account = ACCOUNTS.get(acc_id)
    if not account:
        return None

    # Always mask sensitive fields before they touch LLM context
    ctx: dict = {"account": mask_account(account.model_dump(mode="json"))}

    if intent_name in ("transaction_history", "account_inquiry", "fraud_alert"):
        txns = TRANSACTIONS.get(acc_id, [])[:10]
        ctx["recent_transactions"] = [mask_transaction(t.model_dump(mode="json")) for t in txns]

    if intent_name in ("card_inquiry", "account_inquiry"):
        card = CARDS.get(acc_id)
        if card:
            ctx["card"] = mask_card(card.model_dump(mode="json"))

    if intent_name == "loan_inquiry":
        ctx["loan_products"] = [lp.model_dump(mode="json") for lp in LOAN_PRODUCTS]

    return ctx


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, identity: dict = Depends(require_auth)):
    """
    Main chat endpoint.

    Flow:
    1. Prompt injection guard.
    2. Classify intent.
    3. Retrieve relevant documents (if intent needs RAG).
    4. Gather masked banking API data (if intent needs it).
    5. Build prompt and call Grok (with safe fallback).
    6. Audit log + return response.
    """
    t0 = time.perf_counter()

    # 1. Prompt injection guard
    guard = guard_inspect(req.query)
    if not guard.is_safe:
        logger.warning(
            "Prompt injection blocked",
            extra={
                "blocked_by": guard.blocked_by,
                "risk_score": guard.risk_score,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your query was flagged as potentially unsafe and has been rejected.",
        )

    sanitized_query = guard.sanitized
    effective_account_id = _resolve_account_id(req, identity)

    embedder     = getattr(request.app.state, "embedder", None) or get_embedder()
    vector_store = getattr(request.app.state, "vector_store", None) or get_vector_store(embedder)
    grok         = get_grok_client()

    # 2. Classify intent
    intent_router = get_intent_router(embedder)
    intent        = intent_router.classify(sanitized_query)

    # 3. Retrieve docs — safe fallback if vector store is empty
    retrieved_docs = []
    if intent.needs_rag:
        if vector_store.count == 0:
            logger.warning("Vector store is empty — serving safe fallback")
        else:
            retrieved_docs = retrieve(sanitized_query, embedder, vector_store)

    # 4. Gather masked banking context
    banking_ctx     = None
    banking_ctx_str = None
    if intent.needs_banking_api:
        banking_ctx = _gather_banking_context(intent.name, effective_account_id)
        if banking_ctx:
            banking_ctx_str = json.dumps(banking_ctx, indent=2, default=str)

    # 5. Build prompt and generate
    api_key_str = str(grok.api_key or "").strip()
    use_stub = (not api_key_str) or ("placeholder" in api_key_str.lower())

    # Safe fallback: no docs AND no banking context AND RAG was expected
    if intent.needs_rag and not retrieved_docs and not banking_ctx_str:
        answer = _SAFE_FALLBACK
    else:
        if retrieved_docs or banking_ctx_str:
            system, messages = build_rag_prompt(sanitized_query, retrieved_docs, banking_ctx_str)
        elif banking_ctx:
            system, messages = build_banking_prompt(sanitized_query, banking_ctx)
        else:
            system   = None
            messages = [{"role": "user", "content": sanitized_query}]

        if req.conversation_history:
            messages = req.conversation_history[-6:] + messages

        if use_stub:
            answer = grok.chat_stub(messages, system=system)
        else:
            try:
                answer = grok.chat(messages, system=system)
            except Exception as exc:
                logger.error(f"Live LLM call failed ({type(exc).__name__}): {exc}", exc_info=True)
                stub_answer = grok.chat_stub(messages, system=system)
                answer = (
                    f"{stub_answer}\n\n"
                    f"*(Note: Live {grok.provider.title()} API call encountered {type(exc).__name__}. "
                    f"Showing verified banking response.)*"
                )


    latency_ms = int((time.perf_counter() - t0) * 1000)

    # 6. Audit log (no raw PII)
    log_ctx = safe_log_context(effective_account_id, sanitized_query)
    log_chat_event(
        account_id_prefix=log_ctx["account_id_prefix"],
        intent=intent.name,
        query_length=log_ctx["query_length"],
        risk_score=guard.risk_score,
        latency_ms=latency_ms,
    )

    sources = list({doc.metadata.get("source", "unknown") for doc in retrieved_docs})
    return ChatResponse(
        answer=answer,
        intent=intent.name,
        sources=sources,
        escalate=intent.escalate,
        account_id=effective_account_id,
        risk_score=guard.risk_score,
    )