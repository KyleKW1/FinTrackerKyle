# pages/network_analysis.py
"""Network Analysis — polished dark-luxury redesign"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_all_user_data
from utils import calculate_monthly_stats, get_spending_by_category
import calendar

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=44, b=24, l=10, r=10),
)
_ACCENT = ["#f5a623","#f04e5e","#3d9df6","#1fcf8a","#7c6bf6","#f093fb","#30cfd0","#fee140"]


def _page_header():
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown("""
            <div style="padding:.75rem 0 .25rem;">
                <span style="font-size:.7rem;font-weight:600;letter-spacing:.1em;
                             text-transform:uppercase;color:#f5a623;">PATTERNS</span>
                <h2 style="font-family:'Playfair Display',serif;font-size:1.8rem;
                           font-weight:600;color:#e8eaf0;margin:.2rem 0 0;
                           letter-spacing:-.02em;">Network Analysis</h2>
                <p style="font-size:.82rem;color:#7b7f94;margin:.35rem 0 0;">
                    Merchant relationships, category flows, and spending heatmaps.</p>
            </div>""", unsafe_allow_html=True)
    with c2:
        if st.button("← Back", key="na_back", use_container_width=True):
            st.session_state.selected_feature = None; st.rerun()
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)


def _section(title, sub=""):
    st.markdown(f"""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:1.5rem 0 .5rem;">{title}</p>
        {"<p style='font-size:.78rem;color:#7b7f94;margin:-.3rem 0 .6rem;'>" + sub + "</p>" if sub else ""}
    """, unsafe_allow_html=True)


def _merchant_row(name, left_val, left_lbl, right_val, right_lbl, accent):
    st.markdown(f"""
        <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                    border-left:3px solid {accent};border-radius:10px;
                    padding:.7rem 1rem;margin-bottom:.4rem;
                    display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-weight:600;color:#e8eaf0;font-size:.85rem;">{name[:44]}</div>
                <div style="font-size:.72rem;color:#7b7f94;margin-top:.15rem;">{left_lbl}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:700;color:{accent};font-size:.95rem;">{left_val}</div>
                <div style="font-size:.72rem;color:#7b7f94;">{right_lbl}: {right_val}</div>
            </div>
        </div>""", unsafe_allow_html=True)


def network_analysis_page():
    _page_header()

    data = load_all_user_data(st.session_state.user["id"])
    if data.empty:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2.5rem;text-align:center;">
                <div style="font-size:2.5rem;margin-bottom:.6rem;">🌐</div>
                <div style="color:#7b7f94;font-size:.9rem;">
                    Upload transaction data in Spending Analysis first.</div>
            </div>""", unsafe_allow_html=True)
        if st.button("Go to Spending Analysis"):
            st.session_state.selected_feature = "analysis"; st.rerun()
        return

    for col, fn in [("Year", lambda d: d.dt.year), ("Month", lambda d: d.dt.month)]:
        if col not in data.columns:
            data[col] = fn(pd.to_datetime(data["Date"]))

    # ── period selector ──────────────────────────
    _section("Select Period")
    c1, c2 = st.columns(2)
    avail_years = sorted(data["Year"].unique())
    with c1:
        sel_year = st.selectbox("Year", avail_years,
                                index=len(avail_years)-1, key="na_year")
    with c2:
        period = st.selectbox("Range", ["Last Month","Last 3 Months",
                                         "Last 6 Months","All Year"], key="na_period")

    yr_data = data[data["Year"] == sel_year]
    avail_mn = sorted(yr_data["Month"].unique())
    sel_months = {"Last Month": avail_mn[-1:],
                  "Last 3 Months": avail_mn[-3:] if len(avail_mn)>=3 else avail_mn,
                  "Last 6 Months": avail_mn[-6:] if len(avail_mn)>=6 else avail_mn,
                  "All Year": avail_mn}.get(period, avail_mn)

    pd_filt = yr_data[yr_data["Month"].isin(sel_months)]
    if pd_filt.empty:
        st.warning("No data for selected period."); return

    st.markdown(f"""
        <div style="background:rgba(245,166,35,.07);border:1px solid rgba(245,166,35,.2);
                    border-radius:10px;padding:.65rem 1rem;margin:.75rem 0;
                    font-size:.82rem;color:#f5a623;">
            Analysing <strong>{len(pd_filt):,}</strong> transactions
            across <strong>{len(sel_months)}</strong> month(s)
        </div>""", unsafe_allow_html=True)

    # ── top merchants ────────────────────────────
    _section("Top Merchants", "Most frequented merchants by spend and frequency")
    ms = pd_filt.groupby("Description")["Amount"].agg(["sum","count","mean"]).reset_index()
    ms.columns = ["Merchant","Total","Txns","Avg"]
    ms = ms.sort_values("Total", ascending=False).head(15)

    fig = px.scatter(ms, x="Txns", y="Total", size="Avg",
                     color="Total", color_continuous_scale=["#3d9df6","#f5a623","#f04e5e"],
                     size_max=55, custom_data=["Merchant","Total","Txns","Avg"],
                     title="Merchant Spending Bubble Chart")
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Total: J$%{customdata[1]:,.0f}<br>"
                      "Visits: %{customdata[2]}<br>Avg: J$%{customdata[3]:,.0f}<extra></extra>")
    fig.update_layout(height=440, coloraxis_showscale=False,
                      xaxis_title="Number of Transactions",
                      yaxis_title="Total Spent (J$)", **_PLOTLY)
    st.plotly_chart(fig, use_container_width=True)

    ca, cb = st.columns(2)
    with ca:
        st.markdown("<p style='font-size:.82rem;font-weight:600;color:#7b7f94;margin-bottom:.6rem;'>💰 Highest Spending</p>", unsafe_allow_html=True)
        for _, r in ms.head(8).iterrows():
            _merchant_row(r["Merchant"], f"J${r['Total']:,.0f}", "total",
                          f"{int(r['Txns'])} txns", "visits", "#f5a623")
    with cb:
        st.markdown("<p style='font-size:.82rem;font-weight:600;color:#7b7f94;margin-bottom:.6rem;'>🔁 Most Frequent</p>", unsafe_allow_html=True)
        for _, r in ms.sort_values("Txns", ascending=False).head(8).iterrows():
            _merchant_row(r["Merchant"], f"{int(r['Txns'])} visits", "frequency",
                          f"J${r['Total']:,.0f}", "total", "#3d9df6")

    # ── category flow ────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Spending Flow by Category")
    if "Spending Category" in pd_filt.columns:
        cat_tot = pd_filt.groupby("Spending Category")["Amount"].sum().reset_index()
        cat_tot = cat_tot.sort_values("Amount", ascending=False)
        n = len(cat_tot)
        colors = _ACCENT[:n] + ["#aab0c2"] * max(0, n-len(_ACCENT))
        fig2 = go.Figure(data=[go.Sankey(
            node=dict(pad=18, thickness=18,
                      line=dict(color="rgba(0,0,0,0)", width=0),
                      label=cat_tot["Spending Category"].tolist() + ["Total"],
                      color=colors + ["#f5a623"]),
            link=dict(source=list(range(n)), target=[n]*n,
                      value=cat_tot["Amount"].tolist(),
                      color=[c.replace("#","rgba(").replace(c,"") + "0.25)"
                             for c in colors]),
        )])
        # simplify sankey link colors
        fig2 = go.Figure(data=[go.Sankey(
            node=dict(pad=18, thickness=18,
                      line=dict(color="rgba(0,0,0,0)", width=0),
                      label=cat_tot["Spending Category"].tolist() + ["Total"],
                      color=colors + ["#f5a623"]),
            link=dict(source=list(range(n)), target=[n]*n,
                      value=cat_tot["Amount"].tolist(),
                      color=["rgba(245,166,35,0.20)"]*n),
        )])
        fig2.update_layout(height=380, **{k:v for k,v in _PLOTLY.items()
                                          if k not in ("xaxis","yaxis")})
        st.plotly_chart(fig2, use_container_width=True)

    # ── heatmap ──────────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Spending Heatmap", "Intensity by category × month")
    hm_rows = []
    for m in sel_months:
        md = pd_filt[pd_filt["Month"] == m]
        if "Spending Category" in md.columns:
            for _, r in md.groupby("Spending Category")["Amount"].sum().reset_index().iterrows():
                hm_rows.append({"Month": calendar.month_abbr[m],
                                 "Category": r["Spending Category"], "Amount": r["Amount"]})
    if hm_rows:
        hm_df   = pd.DataFrame(hm_rows)
        pivot   = hm_df.pivot(index="Category", columns="Month", values="Amount").fillna(0)
        fig_hm  = go.Figure(go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
            colorscale=[[0,"#0e1018"],[0.5,"#1c4480"],[1,"#f5a623"]],
            text=[[f"J${v:,.0f}" for v in row] for row in pivot.values],
            texttemplate="%{text}", textfont=dict(size=10, color="#e8eaf0"),
            colorbar=dict(title="J$", tickfont=dict(color="#7b7f94")),
        ))
        fig_hm.update_layout(height=400, xaxis_title="Month",
                              yaxis_title="Category", **_PLOTLY)
        st.plotly_chart(fig_hm, use_container_width=True)

    # ── daily timeline ───────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Daily Spending Timeline")
    daily = pd_filt.groupby(pd_filt["Date"].dt.date)["Amount"].sum().reset_index()
    daily.columns = ["Date","Amount"]
    avg_d = daily["Amount"].mean()
    fig_d = go.Figure()
    fig_d.add_trace(go.Scatter(
        x=daily["Date"], y=daily["Amount"], mode="lines+markers",
        line=dict(color="#f5a623", width=2),
        marker=dict(size=5, color="#f5a623", line=dict(width=1.5,color="#07080f")),
        fill="tozeroy", fillcolor="rgba(245,166,35,0.08)",
    ))
    fig_d.add_hline(y=avg_d, line_dash="dot", line_color="#7c6bf6",
                    annotation_text=f"Avg: J${avg_d:,.0f}",
                    annotation_font_color="#7c6bf6")
    fig_d.update_layout(height=380, xaxis_title="Date",
                        yaxis_title="Daily Spend (J$)", **_PLOTLY)
    st.plotly_chart(fig_d, use_container_width=True)

    # ── key insights ─────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Key Insights")
    biggest = pd_filt.nlargest(1, "Amount").iloc[0]
    uniq    = pd_filt["Description"].nunique()
    avg_tx  = pd_filt["Amount"].mean()
    c1, c2, c3 = st.columns(3)
    for col, title, val, sub, grad in [
        (c1, "Largest Transaction",
         f"J${biggest['Amount']:,.0f}", biggest["Description"][:32],
         "linear-gradient(135deg,#7c6bf6,#764ba2)"),
        (c2, "Unique Merchants",
         str(uniq), "distinct places visited",
         "linear-gradient(135deg,#1fcf8a,#0fa86e)"),
        (c3, "Avg Transaction",
         f"J${avg_tx:,.0f}", "per transaction",
         "linear-gradient(135deg,#f5a623,#f07a23)"),
    ]:
        with col:
            st.markdown(f"""
                <div style="background:{grad};border-radius:14px;
                            padding:1.35rem 1.4rem;color:white;">
                    <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                text-transform:uppercase;opacity:.85;margin-bottom:.45rem;">
                        {title}</div>
                    <div style="font-size:1.6rem;font-weight:700;margin-bottom:.2rem;">
                        {val}</div>
                    <div style="font-size:.75rem;opacity:.75;">{sub}</div>
                </div>""", unsafe_allow_html=True)
