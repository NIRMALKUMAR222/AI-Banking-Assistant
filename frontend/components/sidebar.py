"""
frontend/components/sidebar.py - Left navigation sidebar.
"""
from __future__ import annotations
import streamlit as st
from frontend.state import logout


NAV_ITEMS = [
    ("chat",         "💬", "AI Assistant"),
    ("balance",      "💰", "Balance & Account"),
    ("transactions", "📋", "Transactions"),
    ("cards",        "💳", "Cards"),
    ("loans",        "🏦", "Loan Products"),
    ("cheque",       "📝", "Cheque-Book Request"),
    ("settings",     "⚙️",  "Settings & Debug"),
]


def render_sidebar():
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style='padding:1rem 0 0.5rem'>
              <span style='font-size:1.5rem;font-weight:800;letter-spacing:-0.02em'>
                🏛️ SecureBank
              </span><br>
              <span style='font-size:0.75rem;opacity:0.6'>AI-Powered Banking</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Account pill ───────────────────────────────────────────────────
        name    = st.session_state.get("display_name", "Guest")
        acc_id  = st.session_state.get("account_id", "—")
        st.markdown(
            f"""
            <div style='background:rgba(255,255,255,0.08);border-radius:12px;
                        padding:0.75rem 1rem;margin-bottom:0.5rem'>
              <div style='font-size:0.75rem;opacity:0.6;text-transform:uppercase;
                          letter-spacing:0.06em'>Welcome back</div>
              <div style='font-weight:700;font-size:1rem'>{name}</div>
              <div style='font-size:0.78rem;opacity:0.65'>{acc_id}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Navigation**")

        # ── Nav buttons ────────────────────────────────────────────────────
        active = st.session_state.get("active_page", "chat")
        for page_key, icon, label in NAV_ITEMS:
            prefix = "→ " if page_key == active else ""
            if st.button(f"{icon}  {prefix}{label}", key=f"nav_{page_key}"):
                st.session_state.active_page = page_key
                st.rerun()

        st.divider()

        # ── Debug toggle ───────────────────────────────────────────────────
        debug = st.toggle("🔧 Developer Debug Mode", value=st.session_state.get("debug_mode", False))
        if debug != st.session_state.debug_mode:
            st.session_state.debug_mode = debug
            st.rerun()

        # ── Logout ─────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪  Log Out", key="logout_btn"):
            logout()
            st.rerun()