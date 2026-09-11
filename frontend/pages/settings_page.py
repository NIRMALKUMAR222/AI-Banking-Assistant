"""
frontend/pages/settings_page.py - Developer debug panel, backend health, and vector store management.
"""
from __future__ import annotations

import json

import streamlit as st

from frontend import api_client
from frontend.state import DEMO_USERS


def render_settings_page():
    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">⚙️ Settings & Developer Debug</h2>'
        '<p style="color:#64748b;margin-bottom:1.5rem">System status, vector store management, and debug tools.</p>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🩺 Backend Health", "📚 Vector Store", "👤 Demo Accounts", "🔧 Debug Console"])

    # ── Tab 1: Backend health ──────────────────────────────────────────────
    with tabs[0]:
        st.subheader("API Backend Status")
        if st.button("🔄 Refresh Status", key="health_refresh"):
            st.session_state.pop("health_cache", None)

        try:
            if "health_cache" not in st.session_state:
                h = api_client.health()
                st.session_state.health_cache = h
            else:
                h = st.session_state.health_cache

            status = h.get("status", "unknown")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Status", "✅ Online" if status == "ok" else "❌ Offline")
            c2.metric("Vector Store", h.get("vector_store", "—").upper())
            c3.metric("Embedding Model", h.get("embedding_model", "—"))
            c4.metric("LLM Model", h.get("llm", "—"))

            st.success("✅ FastAPI backend is reachable.")

            with st.expander("Raw response"):
                st.json(h)

        except Exception as exc:
            st.error(f"❌ Cannot reach backend: {exc}")
            st.warning(
                "Make sure the backend is running:\n\n"
                "```\nuvicorn app.main:app --reload --port 8000\n```"
            )

    # ── Tab 2: Vector store ────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Knowledge Base & Vector Store")

        try:
            vs_status = api_client.ingest_status()
            c1, c2 = st.columns(2)
            c1.metric("Backend", vs_status.get("backend", "—"))
            c2.metric("Total Documents", vs_status.get("total_documents", 0))
        except Exception as exc:
            st.warning(f"Could not fetch vector store status: {exc}")
            vs_status = {}

        total = vs_status.get("total_documents", 0)
        if total == 0:
            st.warning(
                "⚠️ Vector store is empty. Click **Ingest Documents** to load the knowledge base."
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Ingest Documents", type="primary", use_container_width=True):
                with st.spinner("Ingesting knowledge base documents..."):
                    try:
                        result = api_client.ingest_documents()
                        st.success(
                            f"✅ Ingested **{result.get('documents_ingested', 0)} chunks** into "
                            f"{result.get('backend', '')}. "
                            f"Total: {result.get('vector_store_total', 0)} documents."
                        )
                        st.session_state.pop("health_cache", None)
                    except Exception as exc:
                        st.error(f"Ingestion failed: {exc}")
        with col2:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.session_state.pop("health_cache", None)
                st.rerun()

        st.divider()
        st.markdown("""
        **Knowledge Base Documents** (`data/knowledge_base/`):
        | # | Document | Topic |
        |---|---|---|
        | 01 | `01_account_types.md` | Account types, fees, opening process |
        | 02 | `02_loan_products.md` | Home, personal, auto loan details |
        | 03 | `03_credit_cards.md` | Credit card rewards and terms |
        | 04 | `04_fraud_prevention.md` | Fraud types, prevention, reporting |
        | 05 | `05_international_transfers.md` | SWIFT, limits, fees |
        | 06 | `06_digital_banking.md` | App features, UPI, NEFT/RTGS |
        | 07 | `07_kyc_compliance.md` | KYC docs, AML, FATCA |
        | 08 | `08_interest_rates.md` | Savings, FD, loan rates |
        | 09 | `09_dispute_resolution.md` | Dispute process, ombudsman |
        | 10 | `10_terms_conditions.md` | Terms, dormancy, liability |
        """)

    # ── Tab 3: Demo accounts ───────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Demo Login Credentials")
        st.info("These are the pre-configured demo accounts for testing.")

        rows = []
        for uname, info in DEMO_USERS.items():
            rows.append({
                "Username":   uname,
                "Password":   info["password"],
                "Account ID": info["account_id"],
                "Name":       info["name"],
            })

        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("""
        **API Key** (for direct API calls):
        ```
        X-API-Key: securebank-dev-key-change-me
        ```
        
        **Backend URL:** `http://localhost:8000`
        
        **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
        """)

    # ── Tab 4: Debug console ───────────────────────────────────────────────
    with tabs[3]:
        st.subheader("🔧 Debug Console")

        debug_mode = st.toggle(
            "Enable Debug Mode (shows intent/source/latency in chat)",
            value=st.session_state.get("debug_mode", False),
            key="debug_toggle_settings",
        )
        if debug_mode != st.session_state.debug_mode:
            st.session_state.debug_mode = debug_mode
            st.rerun()

        st.divider()
        st.markdown("**Current Session State**")
        safe_state = {
            k: v for k, v in st.session_state.items()
            if k not in ("tx_cache", "account_cache", "balance_cache")
            and not callable(v)
        }
        st.code(json.dumps(safe_state, indent=2, default=str), language="json")

        st.divider()
        st.markdown("**Test API Directly**")
        test_query = st.text_input("Test query", value="What is my account balance?")
        test_acc   = st.text_input("Account ID", value=st.session_state.get("account_id", "ACC001"))

        if st.button("🚀 Send Test Request", type="primary"):
            with st.spinner("Sending..."):
                try:
                    result = api_client.chat(test_query, account_id=test_acc)
                    st.markdown("**Response:**")
                    st.code(json.dumps(result, indent=2), language="json")
                except Exception as exc:
                    st.error(f"Request failed: {exc}")