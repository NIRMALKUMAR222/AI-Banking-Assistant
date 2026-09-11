"""
frontend/pages/login_page.py - Login screen with demo credentials panel.
"""
from __future__ import annotations

import streamlit as st
from frontend.state import login, DEMO_USERS


def render_login_page():
    # Center the login form
    col_left, col_mid, col_right = st.columns([1, 1.4, 1])

    with col_mid:
        # ── Logo ──────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="text-align:center;padding:1.5rem 0 0.5rem">
              <div style="font-size:3.5rem">🏛️</div>
              <div style="font-size:1.8rem;font-weight:800;color:#1e3a5f;letter-spacing:-0.02em">
                SecureBank
              </div>
              <div style="font-size:0.9rem;color:#64748b;margin-top:0.3rem;margin-bottom:2rem">
                AI-Powered Banking Assistant
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Login form ─────────────────────────────────────────────────────
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔐 Sign In", type="primary", use_container_width=True)

        if submitted:
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                success, err_msg = login(username, password)
                if success:
                    st.success(f"Welcome back, {st.session_state.display_name}!")
                    st.rerun()
                else:
                    st.error(err_msg or "Invalid username or password. Try one of the demo accounts below.")

        st.divider()

        # ── Demo credentials ───────────────────────────────────────────────
        with st.expander("🔑 View Demo Credentials", expanded=True):
            st.markdown("Use any of these accounts to explore the app:")
            for uname, info in DEMO_USERS.items():
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:space-between;
                                padding:0.3rem 0;border-bottom:1px solid #f1f5f9">
                      <span style="font-weight:600;color:#1e3a5f">
                        {info['name']}
                      </span>
                      <span style="color:#64748b;font-size:0.85rem">
                        {uname} / {info['password']} &nbsp;&bull;&nbsp; {info['account_id']}
                      </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        
        st.markdown(
            '<div style="text-align:center;color:#94a3b8;font-size:0.75rem;margin-top:1rem">'
            "This is a demonstration app. No real banking data is used."
            "</div>",
            unsafe_allow_html=True,
        )