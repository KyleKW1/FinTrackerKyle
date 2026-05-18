# pages/subscription_tracker.py
"""
Subscription Tracker — Finance Hub
- Auto-detects recurring charges from uploaded bank data OR Gmail-synced emails
- Gmail sync built directly into this page (no need to go to Spending Analysis)
- Duplicate selectbox keys fixed with enumerate index
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_all_user_data, clear_data_cache
from database import get_user_preferences, save_user_preferences
import json

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    margin=dict(t=40, b=20, l=10, r=10),
)

KNOWN_SUBS = {
    "netflix": ("Netflix", "🎬 Streaming"),
    "spotify": ("Spotify", "🎵 Music"),
    "disney": ("Disney+", "🎬 Streaming"),
    "hulu": ("Hulu", "🎬 Streaming"),
    "apple": ("Apple Services", "📱 Tech"),
    "google": ("Google Services", "📱 Tech"),
    "amazon": ("Amazon", "🛍 Shopping"),
    "youtube": ("YouTube Premium", "🎬 Streaming"),
    "microsoft": ("Microsoft 365", "💼 Productivity"),
    "adobe": ("Adobe", "🎨 Design"),
    "dropbox": ("Dropbox", "☁ Cloud"),
    "icloud": ("iCloud", "☁ Cloud"),
    "linkedin": ("LinkedIn", "💼 Productivity"),
    "zoom": ("Zoom", "💼 Productivity"),
    "slack": ("Slack", "💼 Productivity"),
    "github": ("GitHub", "💻 Dev Tools"),
    "gym": ("Gym Membership", "💪 Fitness"),
    "digicel": ("Digicel", "📱 Telecom"),
    "flow": ("Flow", "📡 Internet"),
    "bumble": ("Bumble", "💑 Dating"),
    "tinder": ("Tinder", "💑 Dating"),
    "canva": ("Canva", "🎨 Design"),
    "notion": ("Notion", "💼 Productivity"),
    "chatgpt": ("ChatGPT Plus", "🤖 AI"),
    "openai": ("OpenAI", "🤖 AI"),
    "vpn": ("VPN Service", "🔒 Security"),
    "norton": ("Norton Security", "🔒 Security"),
    "duolingo": ("Duolingo", "📚 Education"),
}


def detect_recurring(data: pd.DataFrame, min_occurrences: int = 2) -> pd.DataFrame:
    if data.empty or "Description" not in data.columns:
        return pd.DataFrame()

    if "Category" in data.columns:
        debit = data[data["Category"] == "Debit"].copy()
    else:
        debit = data.copy()

    if debit.empty:
        return pd.DataFrame()

    debit["desc_clean"] = debit["Description"].str.lower().str.strip()
    groups = debit.groupby("desc_clean").agg(
        count=("Amount", "count"),
        avg_amount=("Amount", "mean"),
        total=("Amount", "sum"),
        last_date=("Date", "max"),
        first_date=("Date", "min"),
    ).reset_index()

    recurring = groups[groups["count"] >= min_occurrences].copy()
    recurring = recurring.sort_values("total", ascending=False)

    def match_known(desc):
        for kw, (name, cat) in KNOWN_SUBS.items():
            if kw in desc:
                return name, cat
        return desc[:40].title(), "📦 Other"

    recurring[["friendly_name", "category"]] = recurring["desc_clean"].apply(
        lambda d: pd.Series(match_known(d))
    )
    recurring["months_active"] = (
        (recurring["last_date"] - recurring["first_date"]).dt.days / 30
    ).clip(lower=1).round(1)

    return recurring.reset_index(drop=True)


def _page_header():
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown("""
            <div style="padding:.75rem 0 .25rem;">
                <span style="font-size:.7rem;font-weight:600;letter-spacing:.1em;
                             text-transform:uppercase;color:#f5a623;">RECURRING</span>
                <h2 style="font-family:'Playfair Display',serif;font-size:1.8rem;
                           font-weight:600;color:#e8eaf0;margin:.2rem 0 0;
                           letter-spacing:-.02em;">Subscription Tracker</h2>
                <p style="font-size:.82rem;color:#7b7f94;margin:.35rem 0 0;">
                    Stop paying for things you forgot about.</p>
            </div>""", unsafe_allow_html=True)
    with c2:
        if st.button("← Back", key="st_back", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)


def _section(title, sub=""):
    st.markdown(f"""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:1.5rem 0 .5rem;">{title}</p>
        {"<p style='font-size:.78rem;color:#7b7f94;margin:-.3rem 0 .6rem;'>" + sub + "</p>" if sub else ""}
    """, unsafe_allow_html=True)


# ── Gmail sync section (self-contained here) ─────────────────────────────

def _render_gmail_sync():
    """Gmail sync panel built into the subscription tracker."""
    user_id = st.session_state.user["id"]

    # Try importing — graceful fallback if email_scanner not deployed yet
    try:
        from database import (save_email_sync_settings, get_email_sync_settings,
                              delete_all_email_transactions)
        from email_scanner import sync_gmail_transactions
        email_module_available = True
    except ImportError:
        email_module_available = False

    _section("📧 Gmail Banking Sync",
             "Connect your Gmail once — every bank alert email is scanned automatically.")

    if not email_module_available:
        st.warning("email_scanner.py not found. Add it to your project root to enable Gmail sync.")
        return

    cfg = get_email_sync_settings(user_id)

    # Status banner
    if cfg:
        last_sync = cfg.get("last_sync")
        last_str = last_sync.strftime("%d %b %Y %I:%M %p") if last_sync else "Never"
        st.markdown(f"""
            <div style="background:rgba(31,207,138,.07);border:1px solid rgba(31,207,138,.2);
                        border-radius:10px;padding:.65rem 1.1rem;margin-bottom:.75rem;
                        display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:.85rem;color:#1fcf8a;font-weight:600;">
                    ✓ Connected: {cfg['gmail_address']}
                </span>
                <span style="font-size:.78rem;color:#7b7f94;">Last sync: {last_str}</span>
            </div>""", unsafe_allow_html=True)

    with st.expander("⚙️ Gmail settings" if cfg else "🔗 Connect Gmail",
                     expanded=not bool(cfg)):
        st.markdown("""
            <div style="background:rgba(61,157,246,.08);border:1px solid rgba(61,157,246,.2);
                        border-radius:8px;padding:.7rem 1rem;margin-bottom:.75rem;
                        font-size:.82rem;color:#3d9df6;">
                <strong>Need a Gmail App Password?</strong><br>
                Google Account → Security → 2-Step Verification (enable) →
                App passwords → Generate for "Mail" → paste the 16-char code below.
            </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            gmail_addr = st.text_input("Gmail address",
                value=cfg["gmail_address"] if cfg else "",
                placeholder="yourname@gmail.com", key="gmail_addr_sub")
        with c2:
            app_pwd = st.text_input("App Password", type="password",
                value=cfg["app_password"] if cfg else "",
                placeholder="xxxx xxxx xxxx xxxx", key="gmail_pwd_sub")

        sync_days = st.slider("Scan last N days", 7, 365,
                              value=cfg["sync_days"] if cfg else 90,
                              step=7, key="gmail_days_sub")

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("💾 Save", use_container_width=True, key="gmail_save_sub"):
                if not gmail_addr or "@" not in gmail_addr:
                    st.error("Enter a valid Gmail address.")
                elif len(app_pwd.replace(" ", "")) < 16:
                    st.error("App password should be 16 characters.")
                else:
                    if save_email_sync_settings(user_id, gmail_addr.strip(),
                                                app_pwd.strip(), sync_days):
                        st.success("Saved!")
                        st.rerun()

        with b2:
            if st.button("🔄 Sync now", use_container_width=True,
                         type="primary", key="gmail_sync_sub",
                         disabled=not bool(cfg)):
                addr = gmail_addr or (cfg["gmail_address"] if cfg else "")
                pwd  = app_pwd   or (cfg["app_password"]  if cfg else "")
                if addr and pwd:
                    with st.spinner("Scanning Gmail for bank alerts…"):
                        n, err = sync_gmail_transactions(user_id, addr, pwd, sync_days)
                    if err:
                        st.error(f"❌ {err}")
                    else:
                        clear_data_cache()
                        st.success(f"✅ {n} new transaction(s) imported!" if n
                                   else "Scan complete — no new transactions found.")
                        st.rerun()

        with b3:
            if st.button("🗑 Clear email data", use_container_width=True,
                         key="gmail_clear_sub", disabled=not bool(cfg)):
                delete_all_email_transactions(user_id)
                clear_data_cache()
                st.success("Cleared.")
                st.rerun()

    # Source breakdown
    try:
        data = load_all_user_data(user_id)
        if not data.empty and "source" in data.columns:
            n_email = int((data["source"] == "email").sum())
            n_file  = int((data["source"] == "file").sum())
            if n_email > 0 or n_file > 0:
                st.markdown(f"""
                    <div style="font-size:.78rem;color:#7b7f94;margin-top:.5rem;">
                        Current data:
                        <span style="color:#1fcf8a;font-weight:600;">{n_email} from Gmail</span>
                        &nbsp;+&nbsp;
                        <span style="color:#f5a623;font-weight:600;">{n_file} from files</span>
                        &nbsp;=&nbsp;
                        <span style="color:#e8eaf0;font-weight:600;">{n_email + n_file} total</span>
                    </div>""", unsafe_allow_html=True)
    except Exception:
        pass


# ── Main page ─────────────────────────────────────────────────────────────

def subscription_tracker_page():
    _page_header()

    user_id = st.session_state.user["id"]

    # ── Gmail sync always visible at the top ──────────────────────────
    _render_gmail_sync()

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ── Load data (files + email combined) ───────────────────────────
    data = load_all_user_data(user_id)

    # ── Manual subscriptions ─────────────────────────────────────────
    prefs = get_user_preferences(user_id)
    raw_manual = {}
    if prefs and prefs.get("category_keywords"):
        try:
            ck = json.loads(prefs["category_keywords"])
            raw_manual = ck.get("__subscriptions__", {})
        except Exception:
            pass

    if "manual_subs" not in st.session_state:
        st.session_state.manual_subs = raw_manual if raw_manual else {}
    manual_subs = st.session_state.manual_subs

    # ── Auto-detected recurring charges ──────────────────────────────
    _section("🔍 Auto-Detected Recurring Charges",
             "Merchants that appear more than once across your bank data and Gmail alerts.")

    if data.empty:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2rem;text-align:center;">
                <div style="font-size:2rem;margin-bottom:.5rem;">🔍</div>
                <div style="color:#7b7f94;font-size:.9rem;">
                    Connect Gmail above or upload bank statements in Spending Analysis
                    to auto-detect subscriptions.</div>
            </div>""", unsafe_allow_html=True)
        recurring = pd.DataFrame()
    else:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        recurring = detect_recurring(data)

    if not recurring.empty:
        total_monthly = recurring["avg_amount"].sum()
        total_annual  = total_monthly * 12

        c1, c2, c3 = st.columns(3)
        for col, lbl, val, clr in [
            (c1, "Recurring charges detected", len(recurring), "#f5a623"),
            (c2, "Est. monthly cost",  f"J${total_monthly:,.0f}", "#f04e5e"),
            (c3, "Est. annual cost",   f"J${total_annual:,.0f}",  "#3d9df6"),
        ]:
            with col:
                st.markdown(f"""
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                                border-left:3px solid {clr};border-radius:12px;
                                padding:1rem 1.25rem;text-align:center;">
                        <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                    text-transform:uppercase;color:#7b7f94;margin-bottom:.4rem;">
                            {lbl}</div>
                        <div style="font-size:1.55rem;font-weight:700;color:{clr};">
                            {val}</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)

        # ── Use enumerate index for unique keys ───────────────────────
        for idx, (_, row) in enumerate(recurring.iterrows()):
            status_key = f"sub_action_{idx}"          # unique — no more duplicate key error

            c_icon, c_info, c_cost, c_action = st.columns([0.5, 3, 1.5, 1.5])
            with c_icon:
                st.markdown(
                    f"<div style='font-size:1.8rem;padding-top:.4rem;'>"
                    f"{row['category'].split(' ')[0]}</div>",
                    unsafe_allow_html=True)
            with c_info:
                source_tag = ""
                if "source" in row and row.get("source"):
                    pass  # source not on recurring rows
                st.markdown(f"""
                    <div style="padding:.4rem 0;">
                        <div style="font-weight:600;color:#e8eaf0;font-size:.92rem;">
                            {row['friendly_name']}</div>
                        <div style="font-size:.75rem;color:#7b7f94;margin-top:.15rem;">
                            {row['category'].split(' ', 1)[-1]}  •
                            {int(row['count'])} charges over {row['months_active']:.0f} months  •
                            Last: {row['last_date'].strftime('%d %b %Y') if pd.notna(row['last_date']) else 'N/A'}
                        </div>
                    </div>""", unsafe_allow_html=True)
            with c_cost:
                st.markdown(f"""
                    <div style="text-align:right;padding:.4rem 0;">
                        <div style="font-weight:700;color:#f04e5e;font-size:1rem;">
                            J${row['avg_amount']:,.0f}
                            <span style='font-size:.7rem;color:#7b7f94;'>/mo</span></div>
                        <div style="font-size:.72rem;color:#7b7f94;">
                            J${row['avg_amount']*12:,.0f}/yr</div>
                    </div>""", unsafe_allow_html=True)
            with c_action:
                choice = st.selectbox(
                    "Action",
                    ["✅ Keep", "❌ Cancel", "🤔 Review"],
                    key=status_key,
                    label_visibility="collapsed",
                )
                if choice == "❌ Cancel":
                    st.markdown(
                        f"<div style='font-size:.72rem;color:#1fcf8a;'>"
                        f"Saves J${row['avg_amount']*12:,.0f}/yr!</div>",
                        unsafe_allow_html=True)

            st.markdown(
                "<div style='height:.2rem;border-bottom:1px solid rgba(255,255,255,.05);"
                "margin-bottom:.2rem;'></div>",
                unsafe_allow_html=True)

        # Savings summary for items marked Cancel
        to_cancel = [
            row for idx2, (_, row) in enumerate(recurring.iterrows())
            if st.session_state.get(f"sub_action_{idx2}", "✅ Keep") == "❌ Cancel"
        ]
        if to_cancel:
            monthly_saving = sum(r["avg_amount"] for r in to_cancel)
            st.markdown(f"""
                <div style="background:rgba(31,207,138,.10);border:1px solid rgba(31,207,138,.25);
                            border-radius:12px;padding:1rem 1.5rem;margin-top:1rem;">
                    <div style="font-weight:700;color:#1fcf8a;margin-bottom:.3rem;">
                        💰 Cancel {len(to_cancel)} subscription(s) and save:</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#e8eaf0;">
                        J${monthly_saving:,.0f}/month  ·  J${monthly_saving*12:,.0f}/year</div>
                </div>""", unsafe_allow_html=True)

    # ── Manual subscription manager ───────────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("➕ Manual Subscription Manager",
             "Add subscriptions not in your bank data — annual plans, cash payments, etc.")

    with st.expander("+ Add a subscription", expanded=len(manual_subs) == 0):
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            new_name = st.text_input("Name", key="new_sub_name",
                                     placeholder="e.g. Gym membership")
        with nc2:
            new_amount = st.number_input("Monthly cost (J$)", min_value=0,
                                         step=100, key="new_sub_amount")
        with nc3:
            new_cat = st.selectbox("Category", [
                "🎬 Streaming", "🎵 Music", "💼 Productivity", "💪 Fitness",
                "📱 Telecom", "☁ Cloud", "🔒 Security", "🎨 Design",
                "📚 Education", "🤖 AI", "💑 Dating", "📦 Other",
            ], key="new_sub_cat")

        if st.button("✅ Add", type="primary", key="add_sub_btn"):
            if new_name:
                manual_subs[new_name] = {
                    "amount": new_amount, "category": new_cat, "status": "✅ Active"
                }
                st.session_state.manual_subs = manual_subs
                st.success(f"Added {new_name}!")
                st.rerun()

    if manual_subs:
        for sub_name, sub_data in list(manual_subs.items()):
            c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
            with c1:
                st.markdown(f"""
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                                border-left:3px solid #7c6bf6;border-radius:10px;
                                padding:.7rem 1rem;margin-bottom:.4rem;">
                        <div style="font-weight:600;color:#e8eaf0;">{sub_name}</div>
                        <div style="font-size:.72rem;color:#7b7f94;">{sub_data.get('category','')}</div>
                    </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(
                    f"<div style='padding-top:.5rem;font-weight:700;color:#f04e5e;'>"
                    f"J${sub_data.get('amount',0):,.0f}/mo</div>",
                    unsafe_allow_html=True)
            with c3:
                st.markdown(
                    f"<div style='padding-top:.5rem;font-size:.8rem;color:#7b7f94;'>"
                    f"J${sub_data.get('amount',0)*12:,.0f}/yr</div>",
                    unsafe_allow_html=True)
            with c4:
                if st.button("🗑", key=f"del_manual_{sub_name}"):
                    del manual_subs[sub_name]
                    st.session_state.manual_subs = manual_subs
                    st.rerun()

        manual_total = sum(v.get("amount", 0) for v in manual_subs.values())
        st.markdown(f"""
            <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                        border-radius:10px;padding:.85rem 1rem;margin-top:.5rem;
                        display:flex;justify-content:space-between;">
                <span style="color:#7b7f94;font-size:.85rem;">
                    {len(manual_subs)} manual subscriptions</span>
                <span style="font-weight:700;color:#f04e5e;">
                    J${manual_total:,.0f}/month  ·  J${manual_total*12:,.0f}/year</span>
            </div>""", unsafe_allow_html=True)

        if st.button("💾 Save to profile", type="primary", key="save_manual_subs"):
            if prefs and prefs.get("category_keywords"):
                ck = json.loads(prefs["category_keywords"])
            else:
                from config import DEFAULT_CATEGORY_MAPPING
                ck = DEFAULT_CATEGORY_MAPPING.copy()
            ck["__subscriptions__"] = manual_subs
            budgets = json.loads(prefs["monthly_budgets"]) if prefs and prefs.get("monthly_budgets") else {}
            goal = prefs.get("savings_goal", 5000) if prefs else 5000
            if save_user_preferences(user_id, ck, budgets, goal):
                st.success("Saved!")

    # ── Visualisation ─────────────────────────────────────────────────
    all_subs = []
    if not recurring.empty:
        for _, r in recurring.iterrows():
            all_subs.append({
                "Name": r["friendly_name"],
                "Monthly": r["avg_amount"],
                "Category": r["category"].split(" ", 1)[-1],
            })
    for name, d in manual_subs.items():
        all_subs.append({
            "Name": name,
            "Monthly": d.get("amount", 0),
            "Category": d.get("category", "Other").split(" ", 1)[-1],
        })

    if all_subs:
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        _section("📊 Subscription Spend Breakdown")
        df_subs = pd.DataFrame(all_subs)
        df_subs = df_subs[df_subs["Monthly"] > 0]

        if not df_subs.empty:
            ca, cb = st.columns(2)
            with ca:
                fig = px.pie(df_subs, values="Monthly", names="Name",
                             hole=0.5, title="Monthly cost by subscription",
                             color_discrete_sequence=[
                                 "#f5a623","#f04e5e","#3d9df6","#1fcf8a",
                                 "#7c6bf6","#f093fb","#30cfd0","#fee140"])
                fig.update_traces(textposition="inside", textinfo="percent+label",
                                  textfont_size=10)
                fig.update_layout(height=340, showlegend=False, **_PLOTLY)
                st.plotly_chart(fig, use_container_width=True)
            with cb:
                cat_grp = df_subs.groupby("Category")["Monthly"].sum().reset_index()
                fig2 = px.bar(cat_grp.sort_values("Monthly"),
                              x="Monthly", y="Category", orientation="h",
                              color="Monthly",
                              color_continuous_scale=["#1c6fd1","#f5a623","#f04e5e"],
                              title="Spend by category")
                fig2.update_layout(height=340, showlegend=False,
                                   coloraxis_showscale=False, **_PLOTLY)
                st.plotly_chart(fig2, use_container_width=True)

            grand_total = df_subs["Monthly"].sum()
            st.markdown(f"""
                <div style="background:rgba(240,78,94,.08);border:1px solid rgba(240,78,94,.2);
                            border-radius:12px;padding:1.25rem 1.5rem;margin-top:.5rem;">
                    <div style="font-size:.8rem;color:#7b7f94;margin-bottom:.3rem;">
                        Total across {len(df_subs)} subscriptions</div>
                    <div style="font-size:1.6rem;font-weight:700;color:#f04e5e;">
                        J${grand_total:,.0f} <span style="font-size:1rem;">/month</span>
                        &nbsp;·&nbsp;
                        J${grand_total*12:,.0f} <span style="font-size:1rem;">/year</span>
                    </div>
                </div>""", unsafe_allow_html=True)
