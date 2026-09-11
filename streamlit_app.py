"""
streamlit_app.py - SecureBank RAG Frontend entry point.

Run with:
    streamlit run streamlit_app.py
"""
import streamlit as st

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="SecureBank AI",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help":    "https://github.com/",
        "Report a bug": None,
        "About":       "SecureBank RAG Banking Assistant — demo app",
    },
)

# ── Imports after page config ──────────────────────────────────────────────
from frontend.state import init_session
from frontend.components.styles import inject_css
from frontend.components.sidebar import render_sidebar
from frontend.pages.login_page import render_login_page
from frontend.pages.chat_page import render_chat_page
from frontend.pages.balance_page import render_balance_page
from frontend.pages.transactions_page import render_transactions_page
from frontend.pages.cards_page import render_cards_page
from frontend.pages.loans_page import render_loans_page
from frontend.pages.cheque_page import render_cheque_page
from frontend.pages.settings_page import render_settings_page

# ── Initialise session & CSS ───────────────────────────────────────────────
init_session()
inject_css()

# ── Auth gate ──────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    render_login_page()
    st.stop()

# ── Render sidebar & active page ───────────────────────────────────────────
render_sidebar()

page = st.session_state.get("active_page", "chat")

PAGE_MAP = {
    "chat":         render_chat_page,
    "balance":      render_balance_page,
    "transactions": render_transactions_page,
    "cards":        render_cards_page,
    "loans":        render_loans_page,
    "cheque":       render_cheque_page,
    "settings":     render_settings_page,
}

renderer = PAGE_MAP.get(page, render_chat_page)
renderer()