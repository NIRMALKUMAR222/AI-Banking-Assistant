"""
frontend/pages/cheque_page.py - Cheque-book request form with confirmation flow.
"""
from __future__ import annotations

import random
import string
from datetime import datetime

import streamlit as st


def _generate_ref() -> str:
    return "CHQ" + "".join(random.choices(string.digits, k=10))


def render_cheque_page():
    account_id   = st.session_state.get("account_id")
    display_name = st.session_state.get("display_name", "")

    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">📝 Cheque-Book Request</h2>'
        '<p style="color:#64748b;margin-bottom:1.5rem">Request a new cheque book for your account.</p>',
        unsafe_allow_html=True,
    )

    # ── Request state machine ──────────────────────────────────────────────
    req = st.session_state.get("cheque_request")

    if req is None:
        # ── Step 1: Form ───────────────────────────────────────────────────
        st.markdown("#### Step 1 of 2 — Choose Options")

        with st.form("cheque_form"):
            col1, col2 = st.columns(2)
            with col1:
                leaves = st.selectbox("Number of Leaves", [25, 50, 100])
                acct_num_display = st.text_input("Account ID", value=account_id, disabled=True)
            with col2:
                delivery = st.selectbox(
                    "Delivery Option",
                    ["Courier to registered address", "Collect from branch"],
                )
                priority = st.selectbox("Priority", ["Standard (5-7 days)", "Express (2-3 days)"])

            address = st.text_area(
                "Delivery Address (if courier)",
                placeholder="Enter your full delivery address...",
                height=90,
            )
            agree = st.checkbox("I confirm this request and agree to applicable charges.")
            submitted = st.form_submit_button("📬 Submit Request", type="primary")

        if submitted:
            if not agree:
                st.warning("Please confirm the request by checking the checkbox.")
            elif "Courier" in delivery and not address.strip():
                st.warning("Please enter a delivery address for courier delivery.")
            else:
                st.session_state.cheque_request = {
                    "account_id": account_id,
                    "leaves":     leaves,
                    "delivery":   delivery,
                    "priority":   priority,
                    "address":    address if "Courier" in delivery else "Branch collection",
                    "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ref":        _generate_ref(),
                    "status":     "pending_confirm",
                }
                st.rerun()

    elif req.get("status") == "pending_confirm":
        # ── Step 2: Confirmation ───────────────────────────────────────────
        st.markdown("#### Step 2 of 2 — Confirm Details")

        st.markdown(
            f"""
            <div style="background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem">
              <div style="font-size:0.78rem;color:#64748b;margin-bottom:0.8rem">PLEASE REVIEW YOUR REQUEST</div>
              <table style="width:100%;font-size:0.9rem">
                <tr><td style="color:#64748b;padding:0.25rem 0">Account ID</td><td style="font-weight:600">{req['account_id']}</td></tr>
                <tr><td style="color:#64748b;padding:0.25rem 0">Leaves</td><td style="font-weight:600">{req['leaves']}</td></tr>
                <tr><td style="color:#64748b;padding:0.25rem 0">Delivery</td><td style="font-weight:600">{req['delivery']}</td></tr>
                <tr><td style="color:#64748b;padding:0.25rem 0">Priority</td><td style="font-weight:600">{req['priority']}</td></tr>
                <tr><td style="color:#64748b;padding:0.25rem 0">Address</td><td style="font-weight:600">{req['address']}</td></tr>
              </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        charge = 0 if req["leaves"] <= 25 else (5 if req["leaves"] == 50 else 15)
        express_charge = 10 if "Express" in req["priority"] else 0
        total = charge + express_charge
        st.markdown(f"**Estimated charges:** ${total:.2f} (debited from your account)")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm & Submit", type="primary", use_container_width=True):
                st.session_state.cheque_request["status"] = "confirmed"
                st.rerun()
        with col2:
            if st.button("← Go Back", use_container_width=True):
                st.session_state.cheque_request = None
                st.rerun()

    elif req.get("status") == "confirmed":
        # ── Success ────────────────────────────────────────────────────────
        st.balloons()
        st.success("✅ **Cheque-book request submitted successfully!**")

        ref = req.get("ref", "CHQ0000000000")
        st.markdown(
            f"""
            <div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:14px;
                        padding:1.5rem;text-align:center;margin:1rem 0">
              <div style="font-size:0.8rem;color:#15803d;text-transform:uppercase;letter-spacing:0.06em">
                Reference Number
              </div>
              <div style="font-size:1.8rem;font-weight:800;color:#15803d;letter-spacing:0.05em">
                {ref}
              </div>
              <div style="font-size:0.85rem;color:#166534;margin-top:0.5rem">
                Keep this for your records. Delivery: {req.get('priority','Standard')}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            **Summary:**
            - Account: `{req['account_id']}`
            - Leaves: **{req['leaves']}**
            - Delivery: {req['delivery']}
            - Address: {req['address']}
            - Submitted: {req['submitted_at']}
            """
        )

        if st.button("📝 Submit Another Request"):
            st.session_state.cheque_request = None
            st.rerun()

    # ── Info panel ─────────────────────────────────────────────────────────
    st.divider()
    with st.expander("ℹ️ Cheque-Book Policy"):
        st.markdown("""
        - **Free allowance:** First 2 cheque books (25 leaves each) per year are free.
        - **Additional books:** \\$5 for 50 leaves, \\$15 for 100 leaves.
        - **Express delivery:** \\$10 additional charge.
        - **Standard delivery:** 5–7 working days.
        - **Express delivery:** 2–3 working days.
        - Lost cheque books must be reported immediately to 1800-SECURE-1.
        """)