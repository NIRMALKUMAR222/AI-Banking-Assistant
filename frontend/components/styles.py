"""
frontend/components/styles.py - Shared CSS injected into every Streamlit page.
"""
import streamlit as st

THEME_CSS = """
<style>
/* ── Global ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e3a5f 100%);
    color: white;
}
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    color: white !important;
    border-radius: 10px;
    width: 100%;
    text-align: left;
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
    transition: background 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.18);
    border-color: rgba(255,255,255,0.35);
}

/* ── Chat bubbles ────────────────────────────────────────────────────── */
.sb-user-bubble {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: white;
    border-radius: 18px 18px 4px 18px;
    padding: 0.75rem 1.1rem;
    margin: 0.4rem 0 0.4rem 20%;
    font-size: 0.95rem;
    line-height: 1.55;
    box-shadow: 0 2px 8px rgba(37,99,235,0.3);
}
.sb-bot-bubble {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 18px 18px 18px 4px;
    padding: 0.75rem 1.1rem;
    margin: 0.4rem 20% 0.4rem 0;
    font-size: 0.95rem;
    line-height: 1.6;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}

/* ── Source citations ────────────────────────────────────────────────── */
.sb-sources {
    margin-top: 0.5rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}
.sb-source-tag {
    background: #dbeafe;
    color: #1e40af;
    border-radius: 20px;
    padding: 0.15rem 0.7rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* ── Debug panel ─────────────────────────────────────────────────────── */
.sb-debug {
    background: #0f172a;
    color: #a3e635;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    margin-top: 0.5rem;
    border-left: 3px solid #a3e635;
}

/* ── Quick action buttons ────────────────────────────────────────────── */
.sb-quick-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: white;
    border: 1.5px solid #cbd5e1;
    border-radius: 20px;
    padding: 0.4rem 0.85rem;
    font-size: 0.82rem;
    cursor: pointer;
    transition: all 0.18s;
    color: #334155;
    font-weight: 500;
}
.sb-quick-btn:hover {
    border-color: #2563eb;
    color: #2563eb;
    background: #eff6ff;
}

/* ── Balance card ────────────────────────────────────────────────────── */
.sb-balance-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    color: white;
    border-radius: 20px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(37,99,235,0.25);
}
.sb-balance-label { font-size: 0.8rem; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.08em; }
.sb-balance-amount { font-size: 2.2rem; font-weight: 700; margin: 0.2rem 0; }
.sb-balance-avail  { font-size: 0.85rem; opacity: 0.8; }

/* ── Metric cards ────────────────────────────────────────────────────── */
.sb-metric {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.sb-metric-label { font-size: 0.78rem; color: #64748b; margin-bottom: 0.3rem; }
.sb-metric-value { font-size: 1.3rem; font-weight: 700; color: #0f172a; }

/* ── Transaction rows ────────────────────────────────────────────────── */
.sb-txn-credit { color: #16a34a; font-weight: 600; }
.sb-txn-debit  { color: #dc2626; font-weight: 600; }

/* ── Alert banners ───────────────────────────────────────────────────── */
.sb-alert-fraud {
    background: #fef2f2;
    border: 1.5px solid #fca5a5;
    border-left: 4px solid #dc2626;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #991b1b;
    font-weight: 500;
}
.sb-escalate {
    background: #fff7ed;
    border: 1.5px solid #fed7aa;
    border-left: 4px solid #ea580c;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #9a3412;
    font-weight: 500;
}

/* ── Card widget ─────────────────────────────────────────────────────── */
.sb-card-widget {
    background: linear-gradient(135deg, #1e1e2e 0%, #374151 100%);
    color: white;
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    min-height: 160px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
}
.sb-card-widget::after {
    content: '';
    position: absolute;
    right: -30px; top: -30px;
    width: 150px; height: 150px;
    background: rgba(255,255,255,0.04);
    border-radius: 50%;
}
.sb-card-number { font-size: 1.1rem; letter-spacing: 0.25em; margin: 0.7rem 0; }
.sb-card-expiry { font-size: 0.8rem; opacity: 0.7; }
.sb-card-name   { font-size: 0.85rem; opacity: 0.85; font-weight: 600; letter-spacing: 0.05em; }
.sb-card-network { font-size: 1.2rem; font-weight: 800; opacity: 0.9; float: right; }

/* ── Login page ──────────────────────────────────────────────────────── */
.sb-login-wrap {
    max-width: 420px;
    margin: 0 auto;
    padding: 2rem;
}
.sb-logo-text {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1e3a5f;
    letter-spacing: -0.02em;
}
.sb-logo-sub {
    font-size: 0.85rem;
    color: #64748b;
    margin-bottom: 2rem;
}

/* ── Scrollable chat ─────────────────────────────────────────────────── */
.sb-chat-scroll {
    max-height: 55vh;
    overflow-y: auto;
    padding-right: 0.5rem;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
}
</style>
"""


def inject_css():
    st.markdown(THEME_CSS, unsafe_allow_html=True)