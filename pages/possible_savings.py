# pages/possible_savings.py
"""Possible Savings Calculator — polished dark-luxury redesign"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_all_user_data
import calendar, math

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    margin=dict(t=44, b=24, l=10, r=10),
)


def _roundup(amount, rnd):
    if rnd == 0: return 0
    return math.ceil(amount / rnd) * rnd - amount


def _page_header():
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown("""
            <div style="padding:.75rem 0 .25rem;">
                <span style="font-size:.7rem;font-weight:600;letter-spacing:.1em;
                             text-transform:uppercase;color:#f5a623;">SAVINGS</span>
                <h2 style="font-family:'Playfair Display',serif;font-size:1.8rem;
                           font-weight:600;color:#e8eaf0;margin:.2rem 0 0;
                           letter-spacing:-.02em;">Possible Savings Calculator</h2>
                <p style="font-size:.82rem;color:#7b7f94;margin:.35rem 0 0;">
                    See how automatic round-ups on every transaction add up over time.</p>
            </div>""", unsafe_allow_html=True)
    with c2:
        if st.button("← Back", key="ps_back", use_container_width=True):
            st.session_state.selected_sub_feature = None; st.rerun()
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)


def _section(title, sub=""):
    st.markdown(f"""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:1.5rem 0 .5rem;">{title}</p>
        {"<p style='font-size:.78rem;color:#7b7f94;margin:-.3rem 0 .6rem;'>" + sub + "</p>" if sub else ""}
    """, unsafe_allow_html=True)


def possible_savings_page():
    _page_header()

    data = load_all_user_data(st.session_state.user["id"])
    if data.empty:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2.5rem;text-align:center;">
                <div style="font-size:2.5rem;margin-bottom:.6rem;">💰</div>
                <div style="color:#7b7f94;font-size:.9rem;">
                    Upload bank statements first to calculate savings potential.</div>
            </div>""", unsafe_allow_html=True)
        if st.button("Go to Spending Analysis"):
            st.session_state.selected_feature = "analysis"
            st.session_state.selected_sub_feature = None; st.rerun()
        return

    for col, fn in [("Year", lambda d: d.dt.year), ("Month", lambda d: d.dt.month)]:
        if col not in data.columns:
            data[col] = fn(pd.to_datetime(data["Date"]))

    # ── period ───────────────────────────────────
    _section("Select Period")
    c1, c2 = st.columns(2)
    avail_years = sorted(data["Year"].unique(), reverse=True)
    with c1: sel_year = st.selectbox("Year", avail_years, key="ps_year")
    with c2: period   = st.selectbox("Range",
                                      ["Last Month","Last 3 Months","Last 6 Months","All Year"],
                                      key="ps_period")
    yr_data  = data[data["Year"] == sel_year]
    avail_mn = sorted(yr_data["Month"].unique())
    sel_months = {"Last Month": avail_mn[-1:],
                  "Last 3 Months": avail_mn[-3:] if len(avail_mn)>=3 else avail_mn,
                  "Last 6 Months": avail_mn[-6:] if len(avail_mn)>=6 else avail_mn,
                  "All Year": avail_mn}.get(period, avail_mn)

    pd_filt = yr_data[yr_data["Month"].isin(sel_months)]
    spd     = pd_filt[pd_filt["Category"] == "Debit"].copy() if "Category" in pd_filt.columns else pd_filt.copy()
    if spd.empty:
        st.warning("No spending transactions found."); return

    # ── round-up overview ────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Round-Up Options",
             "Pick how you'd like each transaction rounded up — the difference goes to savings.")

    options = {"J$1": 1, "J$10": 10, "J$100": 100, "J$1,000": 1000}
    results = {}
    for lbl, rnd in options.items():
        col = f"ru_{rnd}"
        spd[col] = spd["Amount"].apply(lambda v: _roundup(v, rnd))
        results[lbl] = dict(
            total=spd[col].sum(),
            per_tx=spd[col].mean(),
            monthly=spd[col].sum() / len(sel_months) if sel_months else 0,
            rnd=rnd, col=col,
        )

    card_colors = ["#1fcf8a","#f5a623","#7c6bf6","#f04e5e"]
    cs = st.columns(4)
    for i, (lbl, r) in enumerate(results.items()):
        with cs[i]:
            clr = card_colors[i]
            st.markdown(f"""
                <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                            border-top:3px solid {clr};border-radius:14px;
                            padding:1.25rem;text-align:center;">
                    <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                text-transform:uppercase;color:#7b7f94;margin-bottom:.5rem;">
                        Round to {lbl}</div>
                    <div style="font-size:1.7rem;font-weight:700;color:{clr};
                                margin-bottom:.35rem;">J${r['total']:,.0f}</div>
                    <div style="font-size:.72rem;color:#7b7f94;margin-bottom:.15rem;">
                        Avg J${r['per_tx']:,.2f} / txn</div>
                    <div style="font-size:.72rem;color:#7b7f94;">
                        J${r['monthly']:,.0f} / month</div>
                </div>""", unsafe_allow_html=True)

    # ── comparison chart ─────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    ca, cb = st.columns([2,1])
    with ca:
        fig = go.Figure(go.Bar(
            x=list(results.keys()),
            y=[r["total"] for r in results.values()],
            marker_color=card_colors,
            text=[f"J${r['total']:,.0f}" for r in results.values()],
            textposition="outside",
        ))
        fig.update_layout(title=f"Total Savings by Round-Up — {period}",
                          xaxis_title="Round-Up", yaxis_title="Total (J$)",
                          height=360, showlegend=False, **_PLOTLY)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        best = max(results.items(), key=lambda x: x[1]["total"])
        annual = best[1]["total"] * 12 / len(sel_months)
        st.markdown(f"""
            <div style="background:rgba(31,207,138,.08);border:1px solid rgba(31,207,138,.22);
                        border-radius:12px;padding:1rem 1.1rem;margin-bottom:1rem;">
                <div style="font-weight:700;color:#1fcf8a;font-size:.85rem;
                            margin-bottom:.35rem;">🎯 Best Option</div>
                <div style="font-size:.82rem;color:#7b7f94;">
                    Rounding to <strong style="color:#e8eaf0;">{best[0]}</strong>
                    saves the most:<br>
                    <strong style="color:#1fcf8a;font-size:1rem;">J${best[1]['total']:,.0f}</strong>
                </div>
            </div>
            <p style="font-size:.75rem;font-weight:600;color:#7b7f94;text-transform:uppercase;
                      letter-spacing:.06em;margin-bottom:.5rem;">Monthly averages</p>
            {"".join(f"<div style='font-size:.8rem;color:#7b7f94;margin-bottom:.25rem;'>"
                     f"• {lbl}: <span style='color:#e8eaf0;'>J${r['monthly']:,.0f}</span></div>"
                     for lbl, r in results.items())}
            <div style="border-top:1px solid rgba(255,255,255,.07);margin:1rem 0 .75rem;"></div>
            <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;
                        color:#7b7f94;margin-bottom:.3rem;">Annual projection</div>
            <div style="font-size:1.35rem;font-weight:700;color:#f5a623;">J${annual:,.0f}</div>
        """, unsafe_allow_html=True)

    # ── goals ────────────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    gc1, gc2 = st.columns([4,1])
    with gc1: _section("What Could You Achieve?")
    with gc2: cust = st.checkbox("✏️ Edit", key="cust_goals")

    best_sav = best[1]["total"]
    def_goals = [
        {"name":"Emergency Fund","amount":50000,"icon":"🏥"},
        {"name":"Vacation",      "amount":100000,"icon":"✈️"},
        {"name":"New Phone",     "amount":150000,"icon":"📱"},
        {"name":"Down Payment",  "amount":500000,"icon":"🏠"},
    ]
    if "custom_goals" not in st.session_state:
        st.session_state.custom_goals = def_goals[:]
    goals = st.session_state.custom_goals

    if cust:
        cols = st.columns(4)
        updated = []
        for i, g in enumerate(goals):
            with cols[i]:
                new_amt = st.number_input(f"{g['icon']} {g['name']}", 1000, 10_000_000,
                                          int(g["amount"]), 10000, key=f"ga_{i}",
                                          label_visibility="visible")
                updated.append({**g, "amount": new_amt})
        b1, b2, _ = st.columns([1,1,2])
        with b1:
            if st.button("💾 Save", use_container_width=True):
                st.session_state.custom_goals = updated; st.success("Saved!"); st.rerun()
        with b2:
            if st.button("↺ Reset", use_container_width=True):
                st.session_state.custom_goals = def_goals[:]; st.rerun()
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    cols = st.columns(4)
    for i, g in enumerate(goals):
        pct  = min(best_sav / g["amount"] * 100, 100)
        mos  = max(1, math.ceil((g["amount"]-best_sav) / (best_sav/len(sel_months)))) if best_sav > 0 else 0
        clr  = "#1fcf8a" if pct >= 100 else "#3d9df6"
        with cols[i]:
            st.markdown(f"""
                <div style="background:#13151f;border:1.5px solid {clr}44;
                            border-radius:14px;padding:1.25rem;text-align:center;">
                    <div style="font-size:2rem;margin-bottom:.5rem;">{g['icon']}</div>
                    <div style="font-weight:600;color:#e8eaf0;font-size:.9rem;
                                margin-bottom:.35rem;">{g['name']}</div>
                    <div style="font-size:.75rem;color:#7b7f94;margin-bottom:.6rem;">
                        Goal: J${g['amount']:,}</div>
                    <div style="background:rgba(255,255,255,.06);height:6px;border-radius:99px;
                                overflow:hidden;margin-bottom:.5rem;">
                        <div style="background:{clr};height:100%;width:{pct:.0f}%;
                                    border-radius:99px;"></div>
                    </div>
                    <div style="font-size:.8rem;font-weight:700;color:{clr};">{pct:.0f}%</div>
                    <div style="font-size:.72rem;color:#7b7f94;margin-top:.2rem;">
                        {"✓ Reached!" if pct >= 100 else f"{mos} months to go"}</div>
                </div>""", unsafe_allow_html=True)

    # ── detailed analysis ────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Detailed Analysis", "Select a method to see month-by-month breakdown")
    sel_rnd = st.selectbox("Round-up method", list(options.keys()), key="ps_detail")
    rnd_to  = options[sel_rnd]
    spd["RU"] = spd["Amount"].apply(lambda v: _roundup(v, rnd_to))
    t_sav = spd["RU"].sum()

    monthly_rows = []
    for m in sel_months:
        md = spd[spd["Month"] == m]
        monthly_rows.append({"Month": calendar.month_name[m],
                              "Savings": md["RU"].sum(), "Txns": len(md)})
    mo_df  = pd.DataFrame(monthly_rows)
    mo_avg = t_sav / len(sel_months) if sel_months else 0

    fig_mo = go.Figure()
    fig_mo.add_trace(go.Scatter(
        x=mo_df["Month"], y=mo_df["Savings"], mode="lines+markers",
        line=dict(color="#f5a623", width=3),
        marker=dict(size=9, color="#f5a623", line=dict(width=2,color="#07080f")),
        fill="tozeroy", fillcolor="rgba(245,166,35,0.08)",
    ))
    fig_mo.add_hline(y=mo_avg, line_dash="dot", line_color="#7c6bf6",
                     annotation_text=f"Avg J${mo_avg:,.0f}",
                     annotation_font_color="#7c6bf6")
    fig_mo.update_layout(title=f"Monthly Savings — {sel_rnd} Round-Up",
                          xaxis_title="Month", yaxis_title="Savings (J$)",
                          height=360, **_PLOTLY)
    st.plotly_chart(fig_mo, use_container_width=True)

    # category pie + bin bar
    da, db = st.columns(2)
    with da:
        if "Spending Category" in spd.columns:
            cat_sav = spd.groupby("Spending Category")["RU"].sum().reset_index()
            fig_p = px.pie(cat_sav, values="RU", names="Spending Category",
                           hole=0.5, color_discrete_sequence=
                           ["#f5a623","#f04e5e","#3d9df6","#1fcf8a","#7c6bf6","#f093fb","#30cfd0"],
                           title="Savings by Category")
            fig_p.update_traces(textposition="inside", textinfo="percent+label",
                                 textfont_size=10)
            fig_p.update_layout(height=320, showlegend=False, **_PLOTLY)
            st.plotly_chart(fig_p, use_container_width=True)
    with db:
        spd["Bin"] = pd.cut(spd["RU"], bins=[0,1,10,50,100,float("inf")],
                            labels=["J$0-1","J$1-10","J$10-50","J$50-100","J$100+"])
        bins = spd["Bin"].value_counts().reset_index()
        bins.columns = ["Range","Count"]
        fig_b = px.bar(bins, x="Range", y="Count",
                       color="Count", color_continuous_scale=["#0e1018","#1fcf8a"],
                       text="Count", title="Savings per Transaction")
        fig_b.update_traces(textposition="outside")
        fig_b.update_layout(height=320, showlegend=False,
                             coloraxis_showscale=False, **_PLOTLY)
        st.plotly_chart(fig_b, use_container_width=True)

    # top opportunities
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Top Savings Opportunities",
             "Transactions with the highest round-up potential")
    cols_needed = ["Date","Description","Amount","RU"] + (
        ["Spending Category"] if "Spending Category" in spd.columns else [])
    top = spd.nlargest(10, "RU")[cols_needed]
    for _, r in top.iterrows():
        rounded = r["Amount"] + r["RU"]
        cat = f" · {r['Spending Category']}" if "Spending Category" in r else ""
        st.markdown(f"""
            <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                        border-left:3px solid #1fcf8a;border-radius:10px;
                        padding:.8rem 1rem;margin-bottom:.4rem;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:600;color:#e8eaf0;font-size:.85rem;">
                        {r['Description'][:52]}</div>
                    <div style="font-size:.72rem;color:#7b7f94;margin-top:.1rem;">
                        {r['Date'].strftime('%d %b %Y')}{cat}</div>
                </div>
                <div style="text-align:right;min-width:120px;">
                    <div style="font-size:.75rem;color:#7b7f94;margin-bottom:.1rem;">
                        J${r['Amount']:,.2f} → J${rounded:,.2f}</div>
                    <div style="font-weight:700;color:#1fcf8a;font-size:.95rem;">
                        +J${r['RU']:,.2f}</div>
                </div>
            </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
