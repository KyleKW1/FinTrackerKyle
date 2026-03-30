# pages/auth_pages.py
"""
Authentication pages - login and registration
Redesigned with a clean, professional dark-glass aesthetic
"""

import streamlit as st
from auth import register_user, authenticate_user, validate_email


# ── shared CSS injected once ──────────────────────────────────────────────
_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

/* ── page backdrop ── */
[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a4e 50%, #24243e 100%) !important;
    min-height: 100vh;
}
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a4e 50%, #24243e 100%) !important;
}

/* ── card ── */
.auth-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 24px;
    padding: 3rem 2.5rem 2.5rem;
    margin: 2rem auto 0;
    box-shadow: 0 32px 64px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.08);
    position: relative;
    overflow: hidden;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: -60px; left: -60px;
    width: 180px; height: 180px;
    background: radial-gradient(circle, rgba(102,126,234,0.35) 0%, transparent 70%);
    pointer-events: none;
}
.auth-card::after {
    content: '';
    position: absolute;
    bottom: -40px; right: -40px;
    width: 140px; height: 140px;
    background: radial-gradient(circle, rgba(118,75,162,0.30) 0%, transparent 70%);
    pointer-events: none;
}

/* ── heading ── */
.auth-logo {
    font-size: 3rem;
    text-align: center;
    margin-bottom: 0.25rem;
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0%,100% { transform: translateY(0); }
    50%      { transform: translateY(-6px); }
}
.auth-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.1rem;
    font-weight: 400;
    text-align: center;
    color: #ffffff;
    margin: 0 0 0.35rem;
    letter-spacing: -0.02em;
}
.auth-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.92rem;
    color: rgba(255,255,255,0.50);
    text-align: center;
    margin-bottom: 2rem;
    letter-spacing: 0.01em;
}

/* ── divider ── */
.auth-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
    margin: 1.5rem 0;
}

/* ── inputs ── */
.stTextInput label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: rgba(255,255,255,0.55) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1rem !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(102,126,234,0.70) !important;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.18) !important;
    background: rgba(255,255,255,0.09) !important;
}
.stTextInput > div > div > input::placeholder {
    color: rgba(255,255,255,0.22) !important;
}

/* ── primary button ── */
.stButton > button[kind="primary"],
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.5rem !important;
    transition: opacity 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(102,126,234,0.35) !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(102,126,234,0.50) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── secondary button ── */
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    box-shadow: none !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.10) !important;
    box-shadow: none !important;
}

/* ── alerts inside auth ── */
.stAlert {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
}

/* ── password-strength bar ── */
.strength-bar-wrap {
    background: rgba(255,255,255,0.08);
    border-radius: 99px;
    height: 4px;
    margin-top: 0.4rem;
    overflow: hidden;
}
.strength-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease, background 0.4s ease;
}

/* ── "or" separator ── */
.or-sep {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1rem 0;
    color: rgba(255,255,255,0.25);
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
}
.or-sep::before, .or-sep::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.10);
}

/* ── footnote link ── */
.auth-footnote {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.80rem;
    color: rgba(255,255,255,0.35);
    text-align: center;
    margin-top: 1.25rem;
}
.auth-footnote span {
    color: #a78bfa;
    cursor: pointer;
    font-weight: 600;
}

/* ── badge ── */
.demo-badge {
    display: inline-block;
    background: rgba(167,139,250,0.15);
    border: 1px solid rgba(167,139,250,0.30);
    color: #c4b5fd;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.3rem 0.8rem;
    border-radius: 99px;
    text-align: center;
    margin: 0 auto 1.5rem;
    display: block;
    width: fit-content;
}
</style>
"""


def _strength(pw: str):
    score = 0
    if len(pw) >= 8:  score += 1
    if any(c.isupper() for c in pw): score += 1
    if any(c.isdigit() for c in pw): score += 1
    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in pw): score += 1
    labels = ['', 'Weak', 'Fair', 'Good', 'Strong']
    colors = ['', '#ef4444', '#f59e0b', '#3b82f6', '#10b981']
    widths = ['0%', '25%', '50%', '75%', '100%']
    return score, labels[score], colors[max(score,0)], widths[score]


def login_page():
    """Render redesigned login page."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
            <div class="auth-card">
                <div class="auth-logo">💼</div>
                <h1 class="auth-title">Finance Hub</h1>
                <p class="auth-subtitle">Sign in to your account</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.1rem'></div>", unsafe_allow_html=True)

        username = st.text_input(
            "Username",
            placeholder="your_username",
            key="login_username"
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="••••••••",
            key="login_password"
        )

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            login_clicked = st.button("Sign in →", use_container_width=True, key="btn_login")
        with c2:
            register_clicked = st.button("Create account", use_container_width=True,
                                         type="secondary", key="btn_go_register")

        if login_clicked:
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                with st.spinner("Authenticating…"):
                    success, user = authenticate_user(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.success("Welcome back!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        if register_clicked:
            st.session_state.page = 'register'
            st.rerun()

        st.markdown('<div class="auth-divider"></div>', unsafe_allow_html=True)

        _, fc, _ = st.columns([1, 2, 1])
        with fc:
            if st.button("Forgot password / username?",
                         use_container_width=True, type="secondary", key="btn_forgot"):
                st.session_state.page = 'forgot'
                st.rerun()

        st.markdown("""
            <p class="auth-footnote">
                New here? <span onclick="">Create a free account</span> to get started.
            </p>
            <span class="demo-badge">✦ Demo — create any account to explore</span>
        """, unsafe_allow_html=True)


def register_page():
    """Render redesigned registration page."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
            <div class="auth-card">
                <div class="auth-logo">✨</div>
                <h1 class="auth-title">Create Account</h1>
                <p class="auth-subtitle">Join Finance Hub — it's free</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.1rem'></div>", unsafe_allow_html=True)

        username = st.text_input("Username",
                                  placeholder="choose_a_username",
                                  key="reg_username")
        email    = st.text_input("Email address",
                                  placeholder="you@example.com",
                                  key="reg_email")
        password = st.text_input("Password",
                                  type="password",
                                  placeholder="min 6 characters",
                                  key="reg_password")

        # live password strength indicator
        if password:
            score, label, bar_color, bar_width = _strength(password)
            st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                            margin-bottom:0.25rem;font-family:'DM Sans',sans-serif;
                            font-size:0.75rem;color:rgba(255,255,255,0.45);">
                    <span>Password strength</span>
                    <span style="color:{bar_color};font-weight:600">{label}</span>
                </div>
                <div class="strength-bar-wrap">
                    <div class="strength-bar-fill"
                         style="width:{bar_width};background:{bar_color};"></div>
                </div>
            """, unsafe_allow_html=True)

        confirm = st.text_input("Confirm password",
                                 type="password",
                                 placeholder="repeat password",
                                 key="reg_confirm")

        if confirm and password and confirm != password:
            st.markdown("""
                <p style="font-family:'DM Sans',sans-serif;font-size:0.78rem;
                           color:#f87171;margin-top:0.25rem;">
                    ✗ Passwords don't match
                </p>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            create_clicked = st.button("Create account →",
                                        use_container_width=True, key="btn_create")
        with c2:
            back_clicked = st.button("← Back to login",
                                      use_container_width=True,
                                      type="secondary", key="btn_back_login")

        if create_clicked:
            if not username or not email or not password or not confirm:
                st.error("All fields are required.")
            elif len(username) < 3:
                st.error("Username must be at least 3 characters.")
            elif not validate_email(email):
                st.error("Please enter a valid email address.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                with st.spinner("Creating your account…"):
                    success, message = register_user(username, email, password)
                if success:
                    st.success(f"Account created! Please sign in.")
                    st.balloons()
                    st.session_state.page = 'login'
                    st.rerun()
                else:
                    st.error(f"{message}")

        if back_clicked:
            st.session_state.page = 'login'
            st.rerun()

        st.markdown("""
            <p class="auth-footnote">
                By creating an account you agree to our Terms of Service.
            </p>
        """, unsafe_allow_html=True)
