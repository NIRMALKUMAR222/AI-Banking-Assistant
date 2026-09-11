"""
frontend/pages/balance_page.py - Account overview with balance card and account details.
"""
from __future__ import annotations

import streamlit as st
from frontend import api_client


def render_balance_page():
    account_id = st.session_state.get("account_id")

    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">💰 Balance & Account</h2>'
        '<p style="color:#64748b;margin-bottom:1.5rem">Your account overview at a glance.</p>',
        unsafe_allow_html=True,
    )

    # ── Fetch balance & account ────────────────────────────────────────────
    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", key="refresh_balance"):
            st.session_state.pop("balance_cache", None)
            st.session_state.pop("account_cache", None)

    try:
        # Balance
        if account_id not in st.session_state.get("balance_cache", {}):
            bal = api_client.get_balance(account_id)
            st.session_state.setdefault("balance_cache", {})[account_id] = bal
        else:
            bal = st.session_state["balance_cache"][account_id]

        # Account
        if account_id not in st.session_state.get("account_cache", {}):
            acct = api_client.get_account(account_id)
            st.session_state.setdefault("account_cache", {})[account_id] = acct
        else:
            acct = st.session_state["account_cache"][account_id]

    except Exception as exc:
        st.error(f"Could not fetch account data: {exc}")
        return

    # ── Balance card ───────────────────────────────────────────────────────
    currency = bal.get("currency", "USD")
    balance  = bal.get("balance", 0)
    avail    = bal.get("available_balance", 0)
    owner    = acct.get("owner_name", st.session_state.get("display_name", ""))
    acct_type = acct.get("account_type", "").replace("_", " ").title()
    status_val = acct.get("status", "active")

    status_colour = {
        "active":  "#22c55e",
        "dormant": "#f59e0b",
        "frozen":  "#ef4444",
        "closed":  "#6b7280",
    }.get(status_val, "#22c55e")

    st.markdown(
        f"""
        <div class="sb-balance-card">
          <div class="sb-balance-label">Current Balance</div>
          <div class="sb-balance-amount">{currency} {balance:,.2f}</div>
          <div class="sb-balance-avail">Available: {currency} {avail:,.2f}</div>
          <div style="margin-top:0.8rem;font-size:0.8rem;opacity:0.7">{owner} &bull; {acct_type}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Metric row ─────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Account ID", acct.get("account_id", account_id))
    with m2:
        st.metric("Account Type", acct_type)
    with m3:
        st.metric("Branch", acct.get("branch", "N/A"))
    with m4:
        st.metric("Status", status_val.title())

    st.divider()

    # ── Account details table ──────────────────────────────────────────────
    st.subheader("Account Details")
    cols = st.columns(2)
    fields_left = [
        ("Account Number", acct.get("account_number", "—")),
        ("IFSC Code",      acct.get("ifsc_code", "—")),
        ("Currency",       acct.get("currency", "USD")),
        ("Opened Date",    acct.get("opened_date", "—")),
    ]
    fields_right = [
        ("Account Type",   acct_type),
        ("Status",         f'<span style="color:{status_colour};font-weight:700">{status_val.upper()}</span>'),
        ("Branch",         acct.get("branch", "—")),
        ("Account ID",     acct.get("account_id", account_id)),
    ]

    with cols[0]:
        for label, val in fields_left:
            st.markdown(
                f'<div style="margin-bottom:0.8rem">'
                f'<div style="font-size:0.76rem;color:#64748b;text-transform:uppercase;'
                f'letter-spacing:0.06em">{label}</div>'
                f'<div style="font-size:0.97rem;font-weight:600;color:#0f172a">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    with cols[1]:
        for label, val in fields_right:
            st.markdown(
                f'<div style="margin-bottom:0.8rem">'
                f'<div style="font-size:0.76rem;color:#64748b;text-transform:uppercase;'
                f'letter-spacing:0.06em">{label}</div>'
                f'<div style="font-size:0.97rem;font-weight:600;color:#0f172a">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Frozen account warning ─────────────────────────────────────────────
    if status_val == "frozen":
        st.markdown(
            '<div class="sb-alert-fraud">'
            "🔒 Your account is currently <b>frozen</b>. "
            "Please contact SecureBank at 1800-SECURE-1 to resolve this."
            "</div>",
            unsafe_allow_html=True,
        )