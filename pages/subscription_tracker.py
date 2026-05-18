# pages/subscription_tracker.py
"""
Subscription Tracker — Finance Hub add-on
Detects recurring charges from uploaded bank data and helps user manage them.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_all_user_data
from database import get_user_preferences, save_user_preferences
import json
import re
from collections import defaultdict

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    margin=dict(t=40, b=20, l=10, r=10),
)

# Known subscription keywords → friendly names
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
    """Find transactions that appear regularly (likely subscriptions)."""
    if data.empty or "Description" not in data.columns:
        return pd.DataFrame()

    debit = data[data.get("Category", pd.Series(["Debit"]*len(data))) == "Debit"].copy()
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


def subscription_tracker_page():
    _page_header()

    data = load_all_user_data(st.session_state.user["id"])

    # ── Manual subscriptions (persistent via user prefs JSON) ────────
    prefs = get_user_preferences(st.session_state.user["id"])
    raw_manual = {}
    if prefs and prefs.get("category_keywords"):
        try:
            ck = json.loads(prefs["category_keywords"])
            raw_manual = ck.get("__subscriptions__", {})
        except Exception:
            pass

    if "manual_subs" not in st.session_state:
        st.session_state.manual_subs = raw_manual if raw_manual else {}

    manual_subs = st.session_state.manual_subs  # {name: {amount, category, status}}

    # ── Auto-detected recurring charges ─────────────────────────────
    _section("🔍 Auto-Detected Recurring Charges",
             "These merchants appear more than once in your bank data — likely subscriptions.")

    if data.empty:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2.5rem;text-align:center;">
                <div style="font-size:2.5rem;margin-bottom:.6rem;">🔍</div>
                <div style="color:#7b7f94;font-size:.9rem;">
                    Upload bank statements in Spending Analysis to auto-detect subscriptions.</div>
            </div>""", unsafe_allow_html=True)
        recurring = pd.DataFrame()
    else:
        for col, fn in [("Date", lambda d: pd.to_datetime(d, errors="coerce")),
                        ("YearMonth", lambda d: d.dt.strftime("%Y-%m"))]:
            if col not in data.columns:
                data[col] = fn(data["Date"] if col != "Date" else data[col])
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        recurring = detect_recurring(data)

    if not recurring.empty:
        total_recurring_monthly = recurring["avg_amount"].sum()
        total_recurring_annual = total_recurring_monthly * 12

        c1, c2, c3 = st.columns(3)
        for col, lbl, val, clr in [
            (c1, "Detected Recurring Charges", len(recurring), "#f5a623"),
            (c2, "Est. Monthly Cost", f"J${total_recurring_monthly:,.0f}", "#f04e5e"),
            (c3, "Est. Annual Cost", f"J${total_recurring_annual:,.0f}", "#3d9df6"),
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

        for _, row in recurring.iterrows():
            status_key = f"status_{row['desc_clean'][:20]}"
            if status_key not in st.session_state:
                st.session_state[status_key] = "✅ Keep"

            c_icon, c_info, c_cost, c_action = st.columns([0.5, 3, 1.5, 1.5])
            with c_icon:
                st.markdown(f"<div style='font-size:1.8rem;padding-top:.4rem;'>"
                            f"{row['category'].split(' ')[0]}</div>", unsafe_allow_html=True)
            with c_info:
                st.markdown(f"""
                    <div style="padding:.4rem 0;">
                        <div style="font-weight:600;color:#e8eaf0;font-size:.92rem;">
                            {row['friendly_name']}</div>
                        <div style="font-size:.75rem;color:#7b7f94;margin-top:.15rem;">
                            {row['category'].split(' ',1)[-1]}  •  
                            {int(row['count'])} charges over {row['months_active']:.0f} months  •  
                            Last: {row['last_date'].strftime('%d %b %Y') if pd.notna(row['last_date']) else 'N/A'}
                        </div>
                    </div>""", unsafe_allow_html=True)
            with c_cost:
                st.markdown(f"""
                    <div style="text-align:right;padding:.4rem 0;">
                        <div style="font-weight:700;color:#f04e5e;font-size:1rem;">
                            J${row['avg_amount']:,.0f}<span style='font-size:.7rem;color:#7b7f94;'>/mo</span></div>
                        <div style="font-size:.72rem;color:#7b7f94;">
                            J${row['avg_amount']*12:,.0f}/yr</div>
                    </div>""", unsafe_allow_html=True)
            with c_action:
                choice = st.selectbox(
                    "Action", ["✅ Keep", "❌ Cancel", "🤔 Review"],
                    key=status_key, label_visibility="collapsed"
                )
                if choice == "❌ Cancel":
                    st.markdown(f"<div style='font-size:.72rem;color:#1fcf8a;'>Saves J${row['avg_amount']*12:,.0f}/yr!</div>",
                                unsafe_allow_html=True)

            st.markdown("<div style='height:.2rem;border-bottom:1px solid rgba(255,255,255,.05);margin-bottom:.2rem;'></div>",
                        unsafe_allow_html=True)

        # Savings summary
        to_cancel = [row for _, row in recurring.iterrows()
                     if st.session_state.get(f"status_{row['desc_clean'][:20]}", "✅ Keep") == "❌ Cancel"]
        if to_cancel:
            monthly_saving = sum(r["avg_amount"] for r in to_cancel)
            st.markdown(f"""
                <div style="background:rgba(31,207,138,.10);border:1px solid rgba(31,207,138,.25);
                            border-radius:12px;padding:1rem 1.5rem;margin-top:1rem;">
                    <div style="font-weight:700;color:#1fcf8a;margin-bottom:.3rem;">
                        💰 Cancel these {len(to_cancel)} subscriptions and save:</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#e8eaf0;">
                        J${monthly_saving:,.0f}/month  ·  J${monthly_saving*12:,.0f}/year</div>
                </div>""", unsafe_allow_html=True)

    # ── Manual subscription manager ───────────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("➕ Manual Subscription Manager",
             "Add subscriptions that may not show up in your bank data (e.g. annual plans, cash payments).")

    with st.expander("+ Add a subscription", expanded=len(manual_subs) == 0):
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            new_name = st.text_input("Subscription name", key="new_sub_name",
                                      placeholder="e.g. Gym membership")
        with nc2:
            new_amount = st.number_input("Monthly cost (J$)", min_value=0,
                                          step=100, key="new_sub_amount")
        with nc3:
            new_cat = st.selectbox("Category",
                                    ["🎬 Streaming","🎵 Music","💼 Productivity","💪 Fitness",
                                     "📱 Telecom","☁ Cloud","🔒 Security","🎨 Design",
                                     "📚 Education","🤖 AI","💑 Dating","📦 Other"],
                                    key="new_sub_cat")
        if st.button("✅ Add Subscription", type="primary"):
            if new_name:
                manual_subs[new_name] = {
                    "amount": new_amount,
                    "category": new_cat,
                    "status": "✅ Active",
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
                st.markdown(f"<div style='padding-top:.5rem;font-weight:700;color:#f04e5e;'>"
                            f"J${sub_data.get('amount',0):,.0f}/mo</div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div style='padding-top:.5rem;font-size:.8rem;color:#7b7f94;'>"
                            f"J${sub_data.get('amount',0)*12:,.0f}/yr</div>", unsafe_allow_html=True)
            with c4:
                if st.button("🗑", key=f"del_{sub_name}"):
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

        if st.button("💾 Save to Profile", type="primary"):
            # Persist into prefs category_keywords field under __subscriptions__ key
            if prefs and prefs.get("category_keywords"):
                ck = json.loads(prefs["category_keywords"])
            else:
                from config import DEFAULT_CATEGORY_MAPPING
                ck = DEFAULT_CATEGORY_MAPPING.copy()
            ck["__subscriptions__"] = manual_subs
            budgets = json.loads(prefs["monthly_budgets"]) if prefs and prefs.get("monthly_budgets") else {}
            goal = prefs.get("savings_goal", 5000) if prefs else 5000
            if save_user_preferences(st.session_state.user["id"], ck, budgets, goal):
                st.success("Saved!")

    # ── Visualisation ─────────────────────────────────────────────────
    all_subs = []
    if not recurring.empty:
        for _, r in recurring.iterrows():
            all_subs.append({
                "Name": r["friendly_name"],
                "Monthly": r["avg_amount"],
                "Category": r["category"].split(" ", 1)[-1],
                "Source": "Auto-detected",
            })
    for name, data_s in manual_subs.items():
        all_subs.append({
            "Name": name,
            "Monthly": data_s.get("amount", 0),
            "Category": data_s.get("category", "Other").split(" ", 1)[-1],
            "Source": "Manual",
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
                cat_group = df_subs.groupby("Category")["Monthly"].sum().reset_index()
                fig2 = px.bar(cat_group.sort_values("Monthly"),
                              x="Monthly", y="Category", orientation="h",
                              color="Monthly",
                              color_continuous_scale=["#1c6fd1","#f5a623","#f04e5e"],
                              title="Monthly spend by category")
                fig2.update_layout(height=340, showlegend=False,
                                    coloraxis_showscale=False, **_PLOTLY)
                st.plotly_chart(fig2, use_container_width=True)

            grand_total = df_subs["Monthly"].sum()
            st.markdown(f"""
                <div style="background:rgba(240,78,94,.08);border:1px solid rgba(240,78,94,.2);
                            border-radius:12px;padding:1.25rem 1.5rem;margin-top:.5rem;">
                    <div style="font-size:.8rem;color:#7b7f94;margin-bottom:.3rem;">
                        Total subscription spend across {len(df_subs)} services</div>
                    <div style="font-size:1.6rem;font-weight:700;color:#f04e5e;">
                        J${grand_total:,.0f} <span style="font-size:1rem;">/month</span>
                        &nbsp;&nbsp;·&nbsp;&nbsp;
                        J${grand_total*12:,.0f} <span style="font-size:1rem;">/year</span>
                    </div>
                </div>""", unsafe_allow_html=True)
