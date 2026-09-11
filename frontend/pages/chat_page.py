"""
frontend/pages/chat_page.py - Main AI chat interface with RAG answers,
quick-action chips, source citations, and developer debug panel.
"""
from __future__ import annotations

import json
import time

import streamlit as st

from frontend import api_client
from frontend.state import add_message, get_chat_history_for_api


# ── Intent badge colours ──────────────────────────────────────────────────────
INTENT_COLOURS: dict[str, str] = {
    "account_inquiry":    "#7c3aed",
    "balance_check":      "#2563eb",
    "transaction_history":"#0891b2",
    "product_info":       "#059669",
    "loan_inquiry":       "#d97706",
    "card_inquiry":       "#db2777",
    "fraud_alert":        "#dc2626",
    "general_banking":    "#475569",
    "unknown":            "#9ca3af",
}

INTENT_LABELS: dict[str, str] = {
    "account_inquiry":    "Account",
    "balance_check":      "Balance",
    "transaction_history":"Transactions",
    "product_info":       "Product Info",
    "loan_inquiry":       "Loan",
    "card_inquiry":       "Card",
    "fraud_alert":        "⚠️ Fraud Alert",
    "general_banking":    "General",
    "unknown":            "General",
}

# ── Quick action chips ────────────────────────────────────────────────────────
QUICK_ACTIONS = [
    ("💰", "What is my current balance?"),
    ("📋", "Show my recent transactions"),
    ("🏦", "Tell me about home loan rates"),
    ("💳", "What credit card rewards do I have?"),
    ("🌍", "How do I send an international transfer?"),
    ("🔒", "How do I freeze my card?"),
    ("📊", "What is the interest rate on my savings?"),
    ("🤔", "What are the KYC document requirements?"),
]


def _badge(text: str, colour: str, bg: str) -> str:
    return (
        f'<span style="background:{bg};color:{colour};border-radius:20px;'
        f'padding:0.15rem 0.7rem;font-size:0.72rem;font-weight:700;'
        f'display:inline-block;margin-right:0.3rem">{text}</span>'
    )


def _render_message(msg: dict, idx: int):
    role    = msg["role"]
    content = msg["content"]
    meta    = msg.get("meta", {})

    if role == "user":
        st.markdown(
            f'<div class="sb-user-bubble">{content}</div>',
            unsafe_allow_html=True,
        )
    elif role == "assistant":
        st.markdown(
            f'<div class="sb-bot-bubble">{content}</div>',
            unsafe_allow_html=True,
        )

        # Sources row
        sources = meta.get("sources", [])
        if sources:
            tags = "".join(
                f'<span class="sb-source-tag">📄 {s.replace(".md","").replace("_"," ").title()}</span>'
                for s in sources
            )
            st.markdown(
                f'<div class="sb-sources">{tags}</div>',
                unsafe_allow_html=True,
            )

        # Intent badge
        intent = meta.get("intent")
        if intent:
            col = INTENT_COLOURS.get(intent, "#475569")
            label = INTENT_LABELS.get(intent, intent)
            # darken for bg
            st.markdown(
                f'<div style="margin-top:0.3rem">'
                + _badge(label, col, col + "1a")
                + ("" if not meta.get("escalate") else
                   _badge("Escalated to Human", "#dc2626", "#fef2f2"))
                + "</div>",
                unsafe_allow_html=True,
            )

        # Escalation warning
        if meta.get("escalate"):
            st.markdown(
                '<div class="sb-escalate" style="margin-top:0.5rem">'
                "⚠️ <b>Security Alert:</b> This conversation has been flagged for human review. "
                "A specialist will contact you within 2 hours."
                "</div>",
                unsafe_allow_html=True,
            )

        # Developer debug panel
        if st.session_state.debug_mode and meta:
            with st.expander("🔧 Debug Info", expanded=False):
                st.markdown(
                    '<div class="sb-debug">'
                    + f"Intent: {meta.get('intent', 'N/A')}\n"
                    + f"Sources: {json.dumps(meta.get('sources', []))}\n"
                    + f"Escalate: {meta.get('escalate', False)}\n"
                    + f"Account ID: {meta.get('account_id', 'N/A')}\n"
                    + f"Latency: {meta.get('latency_ms', 'N/A')} ms"
                    + "</div>",
                    unsafe_allow_html=True,
                )

    elif role == "system":
        st.markdown(
            f'<div style="text-align:center;color:#94a3b8;font-size:0.8rem;'
            f'padding:0.3rem 0">{content}</div>',
            unsafe_allow_html=True,
        )


def _send_query(query: str):
    """Send query to backend, update session state."""
    if not query.strip():
        return

    add_message("user", query)

    account_id = st.session_state.get("account_id")
    history    = get_chat_history_for_api()[:-1]  # exclude the message we just added

    try:
        t0   = time.time()
        resp = api_client.chat(query, account_id=account_id, conversation_history=history)
        ms   = int((time.time() - t0) * 1000)

        answer  = resp.get("answer", "Sorry, I could not generate a response.")
        meta    = {
            "intent":     resp.get("intent"),
            "sources":    resp.get("sources", []),
            "escalate":   resp.get("escalate", False),
            "account_id": resp.get("account_id"),
            "latency_ms": ms,
        }
        add_message("assistant", answer, meta)

    except Exception as exc:
        add_message(
            "assistant",
            f"⚠️ **Backend error:** {exc}\n\nMake sure the FastAPI server is running on port 8000.",
        )


def render_chat_page():
    # ── Page header ────────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">💬 AI Banking Assistant</h2>'
        '<p style="color:#64748b;margin-bottom:1.2rem">Ask anything about your account, products, or banking services.</p>',
        unsafe_allow_html=True,
    )

    # ── Quick action chips ─────────────────────────────────────────────────
    with st.container():
        st.markdown("**Quick Actions**")
        cols = st.columns(4)
        for i, (icon, label) in enumerate(QUICK_ACTIONS):
            if cols[i % 4].button(f"{icon} {label}", key=f"qa_{i}", use_container_width=True):
                _send_query(label)
                st.rerun()

    st.divider()

    # ── Chat history ───────────────────────────────────────────────────────
    messages = st.session_state.messages
    if not messages:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#94a3b8">'
            '<div style="font-size:2.5rem">🏛️</div>'
            '<div style="font-size:1rem;margin-top:0.5rem">How can I help you today?</div>'
            '<div style="font-size:0.82rem;margin-top:0.3rem">Ask me about your balance, transactions, loans, or banking policies.</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        chat_container = st.container()
        with chat_container:
            for idx, msg in enumerate(messages):
                _render_message(msg, idx)

    # ── Input area ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([9, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="Ask about your balance, transactions, loan options...",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button("Send", use_container_width=True, type="primary")

    if submitted and user_input.strip():
        _send_query(user_input.strip())
        st.rerun()

    # ── Clear chat ─────────────────────────────────────────────────────────
    if messages:
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()