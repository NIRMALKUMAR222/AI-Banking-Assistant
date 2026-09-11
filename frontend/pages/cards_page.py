"""
frontend/pages/cards_page.py - Card details widget and card management actions.
"""
from __future__ import annotations

import streamlit as st

from frontend import api_client


NETWORK_ICONS = {
    "Visa":       "💳 VISA",
    "Mastercard": "💳 MC",
    "Rupay":      "💳 RuPay",
}


def render_cards_page():
    account_id = st.session_state.get("account_id")

    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">💳 Cards</h2>'
        '<p style="color:#64748b;margin-bottom:1.5rem">Your linked cards and management options.</p>',
        unsafe_allow_html=True,
    )

    try:
        card = api_client.get_card(account_id)
    except Exception as exc:
        st.error(f"Could not fetch card details: {exc}")
        return

    card_type    = card.get("card_type", "debit")
    network      = card.get("card_network", "Visa")
    last_four    = card.get("last_four", "****")
    expiry       = card.get("expiry", "MM/YY")
    is_active    = card.get("is_active", True)
    rewards      = card.get("rewards_points", 0)
    credit_limit = card.get("credit_limit")
    outstanding  = card.get("outstanding_balance")
    owner        = st.session_state.get("display_name", "")

    status_text   = "ACTIVE" if is_active else "INACTIVE"
    status_colour = "#22c55e" if is_active else "#ef4444"
    card_bg       = ("linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%)"
                     if card_type == "credit"
                     else "linear-gradient(135deg,#1e1e2e 0%,#374151 100%)")

    # ── Card visual ────────────────────────────────────────────────────────
    col_card, col_info = st.columns([1, 1])

    with col_card:
        st.markdown(
            f"""
            <div class="sb-card-widget" style="background:{card_bg}">
              <div style="font-size:0.75rem;opacity:0.6;text-transform:uppercase;letter-spacing:0.1em">
                SecureBank {card_type.title()} Card
              </div>
              <div class="sb-card-number">**** **** **** {last_four}</div>
              <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-top:0.8rem">
                <div>
                  <div class="sb-card-expiry">VALID THRU</div>
                  <div style="font-size:0.95rem;font-weight:600">{expiry}</div>
                </div>
                <div class="sb-card-network">{NETWORK_ICONS.get(network, network)}</div>
              </div>
              <div class="sb-card-name" style="margin-top:0.6rem">{owner.upper()}</div>
              <div style="margin-top:0.5rem">
                <span style="background:{'rgba(34,197,94,0.2)' if is_active else 'rgba(239,68,68,0.2)'};
                             color:{status_colour};border-radius:20px;padding:0.1rem 0.6rem;
                             font-size:0.72rem;font-weight:700">
                  ● {status_text}
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_info:
        st.markdown(f"**Card Type:** {card_type.title()}")
        st.markdown(f"**Network:** {network}")
        st.markdown(f"**Last 4 Digits:** •••• {last_four}")
        st.markdown(f"**Expires:** {expiry}")
        st.markdown(f"**Status:** :{('green' if is_active else 'red')}[{status_text}]")
        st.markdown(f"**Rewards Points:** 🌟 {rewards:,}")

        if card_type == "credit" and credit_limit is not None:
            st.markdown(f"**Credit Limit:** ${credit_limit:,.2f}")
        if outstanding is not None:
            used_pct = (outstanding / credit_limit * 100) if credit_limit else 0
            st.markdown(f"**Outstanding:** ${outstanding:,.2f} ({used_pct:.1f}% used)")
            st.progress(min(used_pct / 100, 1.0))

    st.divider()

    # ── Quick actions ──────────────────────────────────────────────────────
    st.subheader("Quick Card Actions")
    ac1, ac2, ac3, ac4 = st.columns(4)

    with ac1:
        if st.button("🔒 Block Card", use_container_width=True):
            st.warning("⚠️ Card blocking is a sensitive action. Please call 1800-SECURE-1 to proceed.")

    with ac2:
        if st.button("🔄 Reset PIN", use_container_width=True):
            st.info("PIN reset link will be sent to your registered mobile number.")

    with ac3:
        if st.button("🌍 Travel Mode", use_container_width=True):
            st.success("✅ International usage enabled for 30 days.")

    with ac4:
        if st.button("📱 Virtual Card", use_container_width=True):
            import random
            vn = "".join([str(random.randint(0,9)) for _ in range(16)])
            formatted = f"{vn[:4]}-{vn[4:8]}-{vn[8:12]}-{vn[12:]}"
            st.success(f"Virtual card: `{formatted}` · CVV: {random.randint(100,999)} · Valid for 10 mins")

    st.divider()

    # ── Rewards panel ──────────────────────────────────────────────────────
    st.subheader("🌟 Reward Points")
    redemption_value = rewards * 0.25
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Points Balance", f"{rewards:,}")
    rc2.metric("Redemption Value", f"${redemption_value:,.2f}")
    rc3.metric("Points Expiry", "36 months")

    if rewards > 0:
        st.markdown("**Redeem your points for:**")
        opt_cols = st.columns(3)
        with opt_cols[0]:
            if st.button("✈️ Flight Miles"):
                st.success(f"Converted {rewards:,} pts → {rewards * 0.8:.0f} air miles!")
        with opt_cols[1]:
            if st.button("🛍️ Shopping Voucher"):
                st.success(f"${redemption_value:.2f} voucher sent to your registered email.")
        with opt_cols[2]:
            if st.button("💰 Cashback"):
                st.success(f"${redemption_value:.2f} cashback credited to your account.")