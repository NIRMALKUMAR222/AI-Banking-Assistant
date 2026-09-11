"""
frontend/pages/loans_page.py - Loan products catalog with eligibility checker.
"""
from __future__ import annotations

import streamlit as st
from frontend import api_client


LOAN_ICONS = {"home": "🏠", "personal": "👤", "auto": "🚗"}

LOAN_COLOURS = {
    "home":     ("#1e3a5f", "#dbeafe"),
    "personal": ("#7c3aed", "#ede9fe"),
    "auto":     ("#059669", "#d1fae5"),
}


def render_loans_page():
    st.markdown(
        '<h2 style="font-weight:800;color:#0f172a;margin-bottom:0">🏦 Loan Products</h2>'
        '<p style="color:#64748b;margin-bottom:1.5rem">Explore SecureBank loan offerings and check your eligibility.</p>',
        unsafe_allow_html=True,
    )

    try:
        loans = api_client.list_loans()
    except Exception as exc:
        st.error(f"Could not fetch loan products: {exc}")
        return

    # ── Product cards ──────────────────────────────────────────────────────
    for loan in loans:
        loan_type   = loan.get("loan_type", "personal")
        icon        = LOAN_ICONS.get(loan_type, "🏦")
        fg, bg      = LOAN_COLOURS.get(loan_type, ("#0f172a", "#f8fafc"))
        rate        = loan.get("interest_rate_pa", 0)
        min_amt     = loan.get("min_amount", 0)
        max_amt     = loan.get("max_amount", 0)
        tenure      = loan.get("max_tenure_months", 0)
        cibil       = loan.get("min_cibil_score", 0)
        proc_fee    = loan.get("processing_fee_pct", 0)
        features    = loan.get("features", [])

        with st.container():
            st.markdown(
                f"""
                <div style="background:{bg};border:1.5px solid {fg}22;border-radius:16px;
                            padding:1.2rem 1.5rem;margin-bottom:1rem">
                  <div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:0.7rem">
                    <span style="font-size:1.5rem">{icon}</span>
                    <div>
                      <div style="font-size:1.05rem;font-weight:800;color:{fg}">{loan.get('name')}</div>
                      <div style="font-size:0.78rem;color:#64748b">{loan_type.title()} Loan &bull; ID: {loan.get('loan_id')}</div>
                    </div>
                    <div style="margin-left:auto;text-align:right">
                      <div style="font-size:1.6rem;font-weight:800;color:{fg}">{rate}%</div>
                      <div style="font-size:0.72rem;color:#64748b">p.a.</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Min Amount", f"${min_amt:,.0f}")
            col2.metric("Max Amount", f"${max_amt:,.0f}")
            col3.metric("Max Tenure", f"{tenure} months")
            col4.metric("Min CIBIL", str(cibil))

            with st.expander(f"View {loan.get('name')} Details"):
                st.markdown(f"**Processing Fee:** {proc_fee}% of loan amount")
                st.markdown("**Key Features:**")
                for feat in features:
                    st.markdown(f"  - ✅ {feat}")

        st.markdown("<br>", unsafe_allow_html=True)

    st.divider()

    # ── Eligibility calculator ─────────────────────────────────────────────
    st.subheader("🧮 Quick Eligibility Check")
    with st.form("eligibility_form"):
        col1, col2 = st.columns(2)
        with col1:
            loan_sel   = st.selectbox("Loan Type", ["Home Loan", "Personal Loan", "Auto Loan"])
            income     = st.number_input("Monthly Income ($)", min_value=0, value=50000, step=1000)
        with col2:
            cibil_input = st.number_input("Your CIBIL Score", min_value=300, max_value=900, value=720, step=1)
            desired_amt = st.number_input("Desired Loan Amount ($)", min_value=0, value=500000, step=10000)
        check = st.form_submit_button("Check Eligibility", type="primary")

    if check:
        loan_map = {
            "Home Loan":     (loans[0] if len(loans) > 0 else None),
            "Personal Loan": (loans[1] if len(loans) > 1 else None),
            "Auto Loan":     (loans[2] if len(loans) > 2 else None),
        }
        selected = loan_map.get(loan_sel)
        if selected:
            eligible = True
            issues   = []

            if cibil_input < selected["min_cibil_score"]:
                eligible = False
                issues.append(f"CIBIL score {cibil_input} is below minimum {selected['min_cibil_score']}")
            if desired_amt > selected["max_amount"]:
                eligible = False
                issues.append(f"Desired amount exceeds maximum ${selected['max_amount']:,.0f}")
            if desired_amt < selected["min_amount"]:
                eligible = False
                issues.append(f"Desired amount is below minimum ${selected['min_amount']:,.0f}")

            # Income check: EMI should be <= 50% of monthly income
            rate_monthly = selected["interest_rate_pa"] / 100 / 12
            n = selected["max_tenure_months"]
            if rate_monthly > 0:
                emi = desired_amt * rate_monthly * (1 + rate_monthly)**n / ((1 + rate_monthly)**n - 1)
            else:
                emi = desired_amt / n
            if emi > income * 0.5:
                eligible = False
                issues.append(f"Estimated EMI ${emi:,.0f}/month exceeds 50% of income")

            if eligible:
                st.success(
                    f"✅ **You are likely eligible!**\n\n"
                    f"Estimated EMI: **${emi:,.2f}/month** over {n} months at {selected['interest_rate_pa']}% p.a.\n\n"
                    f"Processing fee: ${desired_amt * selected['processing_fee_pct'] / 100:,.0f}"
                )
            else:
                st.error("❌ **Not eligible based on the inputs provided.**")
                for issue in issues:
                    st.markdown(f"  - {issue}")