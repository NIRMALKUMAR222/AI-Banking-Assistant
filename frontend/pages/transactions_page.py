"""
frontend/pages/transactions_page.py - Paginated transaction history with filters, 
fund transfer form, and a spend-by-category breakdown chart.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend import api_client


CAT_ICONS = {
    "purchase":   "🛍️",
    "withdrawal": "🏧",
    "payment":    "💸",
    "transfer":   "↔️",
    "fee":        "💼",
    "deposit":    "💵",
    "refund":     "↩️",
    "interest":   "📈",
}


def _txn_to_row(txn: dict) -> dict:
    ts = txn.get("timestamp", "")[:19].replace("T", " ")
    cat = txn.get("category", "")
    icon = CAT_ICONS.get(cat, "💱")
    txn_type = txn.get("transaction_type", "debit")
    amount = txn.get("amount", 0)
    sign = "+" if txn_type == "credit" else "-"
    return {
        "Date":        ts,
        "Description": f"{icon} {txn.get('description', '')}",
        "Type":        txn_type.title(),
        "Category":    cat.title(),
        "Amount":      f"{sign}${amount:,.2f}",
        "Balance":     f"${txn.get('balance_after', 0):,.2f}",
        "_credit":     txn_type == "credit",
        "_amount_raw": amount,
        "_cat_raw":    cat,
    }


def render_transactions_page():
    account_id = st.session_state.get("account_id")

    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">📋 Transactions</h2>'
        '<p style="color:#64748b;margin-bottom:1.5rem">Your transaction history and fund transfers.</p>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["📋 History", "↔️ Transfer Funds"])

    # ───────────────────── Tab 1: Transaction History ────────────────────
    with tabs[0]:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            limit = st.selectbox("Show", [10, 20, 30, 50], index=1, key="tx_limit")
        with col2:
            filter_type = st.selectbox("Filter", ["All", "Credit", "Debit"], key="tx_filter")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄", key="tx_refresh"):
                st.session_state.pop("tx_cache", None)

        try:
            cache_key = f"{account_id}_{limit}"
            if cache_key not in st.session_state.get("tx_cache", {}):
                txns = api_client.get_transactions(account_id, limit=limit)
                st.session_state.setdefault("tx_cache", {})[cache_key] = txns
            else:
                txns = st.session_state["tx_cache"][cache_key]
        except Exception as exc:
            st.error(f"Could not fetch transactions: {exc}")
            return

        if not txns:
            st.info("No transactions found.")
            return

        rows = [_txn_to_row(t) for t in txns]

        # Apply filter
        if filter_type == "Credit":
            rows = [r for r in rows if r["_credit"]]
        elif filter_type == "Debit":
            rows = [r for r in rows if not r["_credit"]]

        # ── Summary metrics ────────────────────────────────────────────
        total_credit = sum(r["_amount_raw"] for r in rows if r["_credit"])
        total_debit  = sum(r["_amount_raw"] for r in rows if not r["_credit"])
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Total Credits", f"${total_credit:,.2f}", delta_color="normal")
        mc2.metric("Total Debits",  f"${total_debit:,.2f}",  delta=f"-${total_debit:,.2f}", delta_color="inverse")
        mc3.metric("Net",           f"${total_credit - total_debit:,.2f}")

        st.divider()

        # ── Transaction rows ───────────────────────────────────────────
        for row in rows:
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.markdown(
                        f'<div style="font-size:0.9rem;font-weight:500;color:#0f172a">{row["Description"]}</div>'
                        f'<div style="font-size:0.75rem;color:#94a3b8">{row["Date"]} &bull; {row["Category"]}</div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    colour = "#16a34a" if row["_credit"] else "#dc2626"
                    st.markdown(
                        f'<div style="text-align:right;font-weight:700;color:{colour};'
                        f'font-size:0.95rem">{row["Amount"]}</div>',
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.markdown(
                        f'<div style="text-align:right;font-size:0.82rem;color:#64748b">'
                        f'{row["Balance"]}</div>',
                        unsafe_allow_html=True,
                    )
            st.markdown('<hr style="margin:0.35rem 0;border-color:#f1f5f9">', unsafe_allow_html=True)

        # ── Spend by category chart ────────────────────────────────────
        st.divider()
        st.subheader("Spend by Category")
        debit_rows = [r for r in rows if not r["_credit"]]
        if debit_rows:
            cat_totals: dict[str, float] = {}
            for r in debit_rows:
                cat_totals[r["_cat_raw"]] = cat_totals.get(r["_cat_raw"], 0) + r["_amount_raw"]
            df_cat = pd.DataFrame(
                [{"Category": k.title(), "Amount ($)": v} for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])]
            )
            st.bar_chart(df_cat.set_index("Category"))
        else:
            st.info("No debit transactions to chart.")

    # ───────────────────── Tab 2: Fund Transfer ─────────────────────────
    with tabs[1]:
        st.subheader("Transfer Funds")
        st.markdown(
            "Transfer money between SecureBank accounts. Use any account ID from **ACC001 to ACC010**.",
        )

        with st.form("transfer_form"):
            from_id = st.text_input("From Account", value=account_id, disabled=True)
            to_id   = st.text_input("To Account ID", placeholder="e.g. ACC002")
            amount  = st.number_input("Amount (USD)", min_value=0.01, value=100.0, step=0.01, format="%.2f")
            desc    = st.text_input("Description", value="Fund transfer", max_chars=80)
            submit  = st.form_submit_button("💸 Transfer Now", type="primary")

        if submit:
            if not to_id.strip():
                st.warning("Please enter a destination account ID.")
            elif to_id.strip().upper() == account_id.upper():
                st.warning("Cannot transfer to the same account.")
            else:
                try:
                    result = api_client.transfer_funds(account_id, to_id.strip().upper(), amount, desc)
                    if result.get("success"):
                        st.success(
                            f"✅ **Transfer successful!**\n\n"
                            f"Transaction ID: `{result.get('transaction_id')}`\n\n"
                            f"New balance: **${result.get('new_balance', 0):,.2f}**"
                        )
                        # Invalidate caches
                        st.session_state.pop("balance_cache", None)
                        st.session_state.pop("tx_cache", None)
                    else:
                        st.error("Transfer failed. Please check the details and try again.")
                except Exception as exc:
                    err = str(exc)
                    if "Insufficient" in err:
                        st.error("❌ Insufficient funds in your account.")
                    elif "404" in err:
                        st.error(f"❌ Destination account not found: `{to_id.strip().upper()}`")
                    else:
                        st.error(f"❌ Transfer failed: {exc}")