# pages/dashboard.py
import streamlit as st
from data_loader import load_all_user_data
from utils import calculate_monthly_stats, calculate_percentage_change


# ── helpers ───────────────────────────────────────────────────────────────
def _delta_html(pct: float, invert: bool = False) -> str:
    """Return coloured delta string."""
    positive = (pct >= 0) if not invert else (pct <= 0)
    arrow = "↑" if pct >= 0 else "↓"
    cls = "up" if positive else "down"
    return f'<span class="sc-delta {cls}">{arrow} {abs(pct):.1f}% vs last month</span>'


def _stat_card(label: str, icon: str, value: str, delta_html: str,
               accent_grad: str) -> str:
    return f"""
    <div class="stat-card" style="--accent-grad:{accent_grad};">
        <div class="sc-label">{icon} {label}</div>
        <div class="sc-value">{value}</div>
        {delta_html}
    </div>"""


def _nav_button(label: str, key: str, feature: str):
    if st.button(label, key=key, use_container_width=True):
        st.session_state.selected_feature = feature
        st.rerun()


# ── main page ─────────────────────────────────────────────────────────────
def dashboard_page():
    """Render the main Finance Hub dashboard."""

    # ── load data ──────────────────────────────
    data = None
    try:
        with st.spinner(""):
            data = load_all_user_data(st.session_state.user["id"])
    except Exception as e:
        st.error(f"Error loading data: {e}")

    # ── compute stats ───────────────────────────
    cur_inc = cur_spd = cur_sav = 0.0
    inc_chg = spd_chg = sav_chg = 0.0

    if data is not None and not data.empty and "YearMonth" in data.columns:
        try:
            months = sorted(data["YearMonth"].unique())
            if months:
                cs = calculate_monthly_stats(data, months[-1])
                cur_inc, cur_spd, cur_sav = cs["income"], cs["spending"], cs["savings"]
                if len(months) >= 2:
                    ps = calculate_monthly_stats(data, months[-2])
                    inc_chg = calculate_percentage_change(cur_inc, ps["income"])
                    spd_chg = calculate_percentage_change(cur_spd, ps["spending"])
                    sav_chg = calculate_percentage_change(cur_sav, ps["savings"])
        except Exception:
            pass

    # ── page header ─────────────────────────────
    username = st.session_state.user.get("username", "")
    st.markdown(f"""
        <div style="padding:2rem 0 1.5rem;">
            <div style="font-size:0.72rem;font-weight:600;letter-spacing:.12em;
                        text-transform:uppercase;color:#f5a623;margin-bottom:.5rem;">
                FINANCE HUB
            </div>
            <h1 style="font-family:'Playfair Display',serif;font-size:2.6rem;
                       font-weight:600;color:#e8eaf0;margin:0 0 .4rem;
                       letter-spacing:-.025em;">
                Good day, {username}.
            </h1>
            <p style="font-size:.95rem;color:#7b7f94;margin:0;">
                Here's a snapshot of your financial health.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── stat cards ───────────────────────────────
    c1, c2, c3 = st.columns(3)
    cards = [
        (c1, "Total Income",   "💰", f"J${cur_inc:,.0f}", _delta_html(inc_chg),
         "linear-gradient(135deg,#1fcf8a 0%,#0fa86e 100%)"),
        (c2, "Total Spending", "💸", f"J${cur_spd:,.0f}", _delta_html(spd_chg, invert=True),
         "linear-gradient(135deg,#f04e5e 0%,#c2273b 100%)"),
        (c3, "Net Savings",    "🎯", f"J${cur_sav:,.0f}", _delta_html(sav_chg),
         "linear-gradient(135deg,#3d9df6 0%,#1c6fd1 100%)"),
    ]
    for col, lbl, ico, val, dlt, grad in cards:
        with col:
            st.markdown(_stat_card(lbl, ico, val, dlt, grad), unsafe_allow_html=True)

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    # ── feature selection or sub-page ───────────
    sel = st.session_state.get("selected_feature")
    if sel is None:
        _feature_grid(data)
    elif sel == "analysis":
        from .spending_analysis import spending_analysis_page
        spending_analysis_page()
    elif sel == "planner":
        sub = st.session_state.get("selected_sub_feature")
        if sub == "possible_savings":
            from .possible_savings import possible_savings_page
            possible_savings_page()
        else:
            from .budget_planner import budget_planner_page
            budget_planner_page()
    elif sel == "network":
        from .network_analysis import network_analysis_page
        network_analysis_page()
    elif sel == "timemachine":
        from .financial_time_machine import financial_time_machine_page
        financial_time_machine_page()


# ── feature grid ──────────────────────────────────────────────────────────
def _feature_grid(data):
    st.markdown("""
        <div style="margin:2rem 0 1.25rem;">
            <h2 style="font-family:'Playfair Display',serif;font-size:1.5rem;
                       font-weight:600;color:#e8eaf0;margin:0 0 .35rem;
                       letter-spacing:-.02em;">What would you like to explore?</h2>
            <p style="font-size:.875rem;color:#7b7f94;margin:0;">
                Choose a tool to dive deeper into your finances.
            </p>
        </div>
    """, unsafe_allow_html=True)

    features = [
        dict(key="btn_analysis",    feature="analysis",    icon="📊",
             title="Spending Analysis",
             desc="Upload bank statements and visualise spending patterns with detailed charts and category breakdowns.",
             featured=False),
        dict(key="btn_planner",     feature="planner",     icon="📅",
             title="Budget Planner",
             desc="Set monthly budgets, track progress against actuals, and get alerts when limits are approached.",
             featured=False),
        dict(key="btn_network",     feature="network",     icon="🌐",
             title="Network Analysis",
             desc="Discover merchant relationships, heatmaps and daily spending timelines in one interactive view.",
             featured=False),
        dict(key="btn_timemachine", feature="timemachine", icon="🔮",
             title="Time Machine",
             desc="See your financial future across three scenarios. Compare paths and find out when you can retire.",
             featured=True),
    ]

    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2]

    for i, f in enumerate(features):
        feat_cls = "feat-card featured" if f["featured"] else "feat-card"
        with cols[i]:
            st.markdown(f"""
                <div class="{feat_cls}">
                    <div class="fc-icon">{f['icon']}</div>
                    <div class="fc-title">{f['title']}</div>
                    <p class="fc-desc">{f['desc']}</p>
                </div>
            """, unsafe_allow_html=True)
            btn_lbl = ("✦ Open " if f["featured"] else "Open ") + f["title"]
            _nav_button(btn_lbl, f["key"], f["feature"])
            st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)

    # ── quick insights ───────────────────────────
    if data is not None and not data.empty:
        st.markdown("""<div class="section-divider"></div>
            <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                      font-weight:600;color:#e8eaf0;margin-bottom:1rem;">
                Quick Insights
            </p>""", unsafe_allow_html=True)

        try:
            total_tx   = len(data)
            merchants  = data["Description"].nunique() if "Description" in data.columns else 0
            months_trk = data["YearMonth"].nunique()   if "YearMonth"    in data.columns else 0
            avg_tx     = data["Amount"].mean()          if "Amount"       in data.columns else 0

            pills = [
                ("Total Transactions", f"{total_tx:,}"),
                ("Unique Merchants",   str(merchants)),
                ("Months Tracked",     str(months_trk)),
                ("Avg Transaction",    f"J${avg_tx:,.0f}"),
            ]
            cs = st.columns(4)
            for col, (lbl, val) in zip(cs, pills):
                with col:
                    st.markdown(f"""
                        <div class="insight-pill">
                            <div class="ip-label">{lbl}</div>
                            <div class="ip-value">{val}</div>
                        </div>
                    """, unsafe_allow_html=True)
        except Exception:
            pass

    # ── logout footer ────────────────────────────
    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)
    _, _, logout_col = st.columns([3, 1, 1])
    with logout_col:
        from auth import logout
        if st.button("Sign out", key="dashboard_logout", use_container_width=True):
            logout()
