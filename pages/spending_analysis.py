# pages/spending_analysis.py
"""Spending Analysis — polished dark-luxury redesign"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_all_user_data, clear_data_cache
from database import (
    save_user_file, delete_user_file,
    get_user_files_paginated, get_user_preferences,
    save_user_preferences, create_connection,
)
from utils import (
    calculate_monthly_stats, get_spending_by_category,
    export_to_excel, compare_budget_vs_actual,
)
from config import FILES_PER_PAGE, DEFAULT_CATEGORY_MAPPING, DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
import json, calendar
from io import BytesIO

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.08)"),
    margin=dict(t=40, b=20, l=10, r=10),
)
_ACCENT   = ["#f5a623","#f04e5e","#3d9df6","#1fcf8a","#7c6bf6","#f093fb","#30cfd0","#fee140"]
_PIE_HOLE = 0.52


def _section(title: str, subtitle: str = ""):
    st.markdown(f"""
        <div style="margin:1.75rem 0 1rem;">
            <h3 style="font-family:'Playfair Display',serif;font-size:1.2rem;
                       font-weight:600;color:#e8eaf0;margin:0 0 .2rem;
                       letter-spacing:-.02em;">{title}</h3>
            {"<p style='font-size:.82rem;color:#7b7f94;margin:0;'>" + subtitle + "</p>" if subtitle else ""}
        </div>""", unsafe_allow_html=True)


def _page_header(title: str, icon: str, back_key: str, back_feature=None):
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"""
            <div style="padding:.75rem 0 .25rem;">
                <span style="font-size:0.7rem;font-weight:600;letter-spacing:.1em;
                             text-transform:uppercase;color:#f5a623;">{icon}</span>
                <h2 style="font-family:'Playfair Display',serif;font-size:1.8rem;
                           font-weight:600;color:#e8eaf0;margin:.2rem 0 0;
                           letter-spacing:-.02em;">{title}</h2>
            </div>""", unsafe_allow_html=True)
    with col2:
        if st.button("← Back", key=back_key, use_container_width=True):
            st.session_state.selected_feature = back_feature
            st.rerun()
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)


def render_category_editor():
    with st.expander("🏷️ Customise Spending Categories", expanded=False):
        st.caption("Add comma-separated keywords. Matching transactions are auto-categorised.")
        prefs = get_user_preferences(st.session_state.user["id"])
        cur = json.loads(prefs["category_keywords"]) if prefs and prefs.get("category_keywords") else DEFAULT_CATEGORY_MAPPING.copy()
        updated = {}
        cats = [c for c in DEFAULT_CATEGORY_MAPPING if c != "Other"]
        mid = len(cats) // 2
        c1, c2 = st.columns(2)
        for i, cat in enumerate(cats):
            with (c1 if i < mid else c2):
                kw = st.text_area(f"**{cat}**", value=", ".join(cur.get(cat, [])),
                                  height=72, key=f"cat_{cat}")
                updated[cat] = [k.strip() for k in kw.split(",") if k.strip()]
        updated["Other"] = []
        b1, b2, _ = st.columns([1, 1, 2])
        budgets = json.loads(prefs["monthly_budgets"]) if prefs and prefs.get("monthly_budgets") else DEFAULT_BUDGETS
        goal    = prefs.get("savings_goal", DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
        with b1:
            if st.button("💾 Save", use_container_width=True, key="cat_save"):
                if save_user_preferences(st.session_state.user["id"], updated, budgets, goal):
                    st.success("Saved!"); clear_data_cache(); st.rerun()
        with b2:
            if st.button("↺ Defaults", use_container_width=True, key="cat_reset"):
                if save_user_preferences(st.session_state.user["id"], DEFAULT_CATEGORY_MAPPING, budgets, goal):
                    st.success("Reset!"); clear_data_cache(); st.rerun()


def render_cash_flow_charts(data, year, months):
    rows = []
    for m in sorted(months):
        ym = f"{year}-{m:02d}"
        s  = calculate_monthly_stats(data, ym)
        rows.append({"Month": calendar.month_abbr[m], "Income": s["income"],
                     "Spending": s["spending"], "Savings": s["savings"]})
    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Income",   x=df["Month"], y=df["Income"],
                         marker_color="#1fcf8a",
                         text=df["Income"].map(lambda v: f"J${v:,.0f}"),
                         textposition="outside"))
    fig.add_trace(go.Bar(name="Spending", x=df["Month"], y=df["Spending"],
                         marker_color="#f04e5e",
                         text=df["Spending"].map(lambda v: f"J${v:,.0f}"),
                         textposition="outside"))
    fig.add_trace(go.Scatter(name="Net Savings", x=df["Month"], y=df["Savings"],
                             mode="lines+markers",
                             line=dict(color="#f5a623", width=3),
                             marker=dict(size=9, color="#f5a623",
                                         line=dict(width=2, color="#07080f"))))

    # ── FIX: strip 'legend' from _PLOTLY before spreading to avoid duplicate key TypeError
    _base = {k: v for k, v in _PLOTLY.items() if k != "legend"}
    fig.update_layout(
        barmode="group",
        height=420,
        title=dict(text=f"Cash Flow — {year}", font=dict(color="#e8eaf0", size=14)),
        legend=dict(orientation="h", y=1.06, x=1, xanchor="right"),
        **_base,
    )
    st.plotly_chart(fig, use_container_width=True)

    t_inc = df["Income"].sum(); t_spd = df["Spending"].sum()
    t_sav = df["Savings"].sum(); avg_sav = df["Savings"].mean()
    cs = st.columns(4)
    for col, lbl, val in zip(cs,
        ["Total Income","Total Spending","Net Savings","Avg Monthly Saved"],
        [t_inc, t_spd, t_sav, avg_sav]):
        with col:
            st.markdown(f"""
                <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                            border-radius:12px;padding:1rem 1.25rem;text-align:center;">
                    <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                text-transform:uppercase;color:#7b7f94;margin-bottom:.4rem;">
                        {lbl}</div>
                    <div style="font-size:1.3rem;font-weight:700;color:#e8eaf0;">
                        J${val:,.0f}</div>
                </div>""", unsafe_allow_html=True)


def render_monthly_analysis(data, year_month, month_name):
    md = data[data["YearMonth"] == year_month]
    if md.empty:
        st.warning("No data for this month."); return
    s  = calculate_monthly_stats(data, year_month)
    sm = get_spending_by_category(data, year_month)

    cs = st.columns(3)
    for col, lbl, val, grad in zip(cs,
        ["Income","Spending","Net Savings"],
        [s["income"], s["spending"], s["savings"]],
        ["#1fcf8a","#f04e5e","#f5a623"]):
        with col:
            st.markdown(f"""
                <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                            border-left:3px solid {grad};border-radius:12px;
                            padding:1rem 1.25rem;">
                    <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                text-transform:uppercase;color:#7b7f94;margin-bottom:.35rem;">
                        {lbl}</div>
                    <div style="font-size:1.55rem;font-weight:700;color:#e8eaf0;">
                        J${val:,.0f}</div>
                </div>""", unsafe_allow_html=True)

    if sm.empty: return
    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca:
        fig = px.pie(sm, values="Amount", names="Spending Category", hole=_PIE_HOLE,
                     color_discrete_sequence=_ACCENT, title="Distribution")
        fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
        fig.update_layout(height=340, showlegend=False, **_PLOTLY)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        fig = px.bar(sm.sort_values("Amount"), x="Amount", y="Spending Category",
                     orientation="h", color="Amount",
                     color_continuous_scale=["#1c6fd1","#f5a623","#f04e5e"],
                     title="Category Amounts")
        fig.update_layout(height=340, showlegend=False, coloraxis_showscale=False, **_PLOTLY)
        st.plotly_chart(fig, use_container_width=True)

    prefs = get_user_preferences(st.session_state.user["id"])
    if prefs and prefs.get("monthly_budgets"):
        budgets = json.loads(prefs["monthly_budgets"])
        cmp = compare_budget_vs_actual(budgets, sm)
        if not cmp.empty:
            st.markdown(f"""<p style="font-family:'Playfair Display',serif;font-size:1rem;
                            font-weight:600;color:#e8eaf0;margin:1rem 0 .75rem;">
                            Budget vs Actual — {month_name}</p>""",
                        unsafe_allow_html=True)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name="Budget", x=cmp["Spending Category"],
                                  y=cmp["Budget"], marker_color="#3d9df6"))
            fig2.add_trace(go.Bar(name="Actual", x=cmp["Spending Category"],
                                  y=cmp["Amount"], marker_color="#f04e5e"))
            fig2.update_layout(barmode="group", height=340, xaxis_tickangle=-35, **_PLOTLY)
            st.plotly_chart(fig2, use_container_width=True)
            ob = cmp[cmp["Amount"] > cmp["Budget"]]
            if not ob.empty:
                st.warning(f"⚠️ Over budget in {len(ob)} categories")
                for _, r in ob.iterrows():
                    st.caption(f"**{r['Spending Category']}**: J${r['Amount']:,.0f} / J${r['Budget']:,.0f} (+J${r['Amount']-r['Budget']:,.0f})")

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    disp = sm.copy()
    disp["Amount"]     = disp["Amount"].map(lambda v: f"J${v:,.2f}")
    disp["Percentage"] = disp["Percentage"].map(lambda v: f"{v:.1f}%")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    oth = sm[sm["Spending Category"] == "Other"]
    if not oth.empty:
        amt = oth["Amount"].iloc[0]; pct = oth["Percentage"].iloc[0]
        with st.expander(f"🔍 Uncategorised transactions — J${amt:,.0f} ({pct:.1f}%)"):
            st.caption("These weren't matched to any keyword. Add keywords above to auto-categorise them.")
            sub = md[md["Spending Category"] == "Other"]
            ms  = sub.groupby("Description")["Amount"].agg(["sum","count"]).reset_index()
            ms.columns = ["Merchant","Total","Count"]
            ms  = ms.sort_values("Total", ascending=False).head(12)
            for _, r in ms.iterrows():
                st.markdown(f"""
                    <div style="background:rgba(240,78,94,.08);border-left:3px solid #f04e5e;
                                border-radius:8px;padding:.6rem .9rem;margin-bottom:.4rem;">
                        <span style="font-weight:600;color:#e8eaf0;">{r['Merchant'][:55]}</span>
                        <span style="float:right;color:#f5a623;font-weight:600;">J${r['Total']:,.0f}</span>
                        <div style="font-size:.75rem;color:#7b7f94;">{int(r['Count'])} transaction(s)</div>
                    </div>""", unsafe_allow_html=True)


def render_aggregate_analysis(data, year, months):
    _section("Aggregate Analysis", "Combined view across all selected months")
    pd_filt = data[(data["Year"] == year) & (data["Month"].isin(months))]
    if pd_filt.empty: return
    yms = [f"{year}-{m:02d}" for m in months]
    t_inc = sum(calculate_monthly_stats(data, ym)["income"]   for ym in yms)
    t_spd = sum(calculate_monthly_stats(data, ym)["spending"] for ym in yms)
    t_sav = t_inc - t_spd

    cs = st.columns(3)
    for col, lbl, val, clr in zip(cs,
        ["Total Income","Total Spending","Net Savings"],
        [t_inc, t_spd, t_sav],["#1fcf8a","#f04e5e","#f5a623"]):
        with col:
            st.markdown(f"""
                <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                            border-left:3px solid {clr};border-radius:12px;
                            padding:1rem 1.25rem;text-align:center;">
                    <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                text-transform:uppercase;color:#7b7f94;margin-bottom:.4rem;">
                        {lbl}</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#e8eaf0;">
                        J${val:,.0f}</div>
                </div>""", unsafe_allow_html=True)

    chunks = [get_spending_by_category(data, ym) for ym in yms]
    chunks = [c for c in chunks if not c.empty]
    if not chunks: return
    agg = pd.concat(chunks).groupby("Spending Category")["Amount"].sum().reset_index()
    agg["Percentage"] = 100 * agg["Amount"] / agg["Amount"].sum()
    agg = agg.sort_values("Amount", ascending=False)

    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca:
        fig = px.pie(agg, values="Amount", names="Spending Category", hole=_PIE_HOLE,
                     color_discrete_sequence=_ACCENT, title="Spending Distribution")
        fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
        fig.update_layout(height=340, showlegend=False, **_PLOTLY)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        fig = px.bar(agg.sort_values("Amount"), x="Amount", y="Spending Category",
                     orientation="h", color="Amount",
                     color_continuous_scale=["#1c6fd1","#f5a623","#f04e5e"],
                     title="Category Totals")
        fig.update_layout(height=340, showlegend=False, coloraxis_showscale=False, **_PLOTLY)
        st.plotly_chart(fig, use_container_width=True)

    disp = agg.copy()
    disp["Amount"]     = disp["Amount"].map(lambda v: f"J${v:,.2f}")
    disp["Percentage"] = disp["Percentage"].map(lambda v: f"{v:.1f}%")
    st.dataframe(disp, use_container_width=True, hide_index=True)


def render_analysis_section(data):
    if data.empty: st.error("No data to analyse."); return
    if "Date" in data.columns:
        data["Date"]  = pd.to_datetime(data["Date"], errors="coerce")
        data          = data.dropna(subset=["Date"])
        data["Year"]  = data["Date"].dt.year.astype(int)
        data["Month"] = data["Date"].dt.month.astype(int)

    avail_years = sorted(data["Year"].dropna().unique().astype(int))
    if not avail_years: st.error("No valid years in data."); return

    mn, mx = data["Date"].min(), data["Date"].max()
    st.markdown(f"""
        <div style="background:rgba(245,166,35,.07);border:1px solid rgba(245,166,35,.20);
                    border-radius:10px;padding:.7rem 1rem;margin-bottom:1rem;
                    font-size:.82rem;color:#f5a623;">
            📊 Data range: <strong>{mn.strftime('%B %Y')}</strong>
            to <strong>{mx.strftime('%B %Y')}</strong>
        </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        atype = st.selectbox("Period", ["Specific Months","Last 3 Months",
                                         "Last 6 Months","All Time"], key="analysis_type")
    with c2:
        sel_year = st.selectbox("Year", avail_years, index=len(avail_years)-1, key="selected_year")

    yr_data  = data[data["Year"] == sel_year]
    avail_mn = sorted(yr_data["Month"].dropna().unique().astype(int))
    if not avail_mn: st.error(f"No data for {sel_year}."); return
    mn_names = [calendar.month_name[m] for m in avail_mn]

    if atype == "Specific Months":
        with c3:
            sel_names = st.multiselect("Months", mn_names, default=mn_names, key="sel_months")
        if not sel_names: st.warning("Select at least one month."); return
        all_names  = [calendar.month_name[i] for i in range(1, 13)]
        sel_months = [all_names.index(n)+1 for n in sel_names]
    elif atype == "Last 3 Months":
        sel_months = avail_mn[-3:] if len(avail_mn) >= 3 else avail_mn
        with c3: st.info(f"{len(sel_months)} months")
    elif atype == "Last 6 Months":
        sel_months = avail_mn[-6:] if len(avail_mn) >= 6 else avail_mn
        with c3: st.info(f"{len(sel_months)} months")
    else:
        sel_months = avail_mn
        with c3: st.info(f"{len(sel_months)} months")

    pd_filt = data[(data["Year"] == sel_year) & (data["Month"].isin(sel_months))]
    if pd_filt.empty: st.error("No transactions found."); return

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    render_cash_flow_charts(data, sel_year, sel_months)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    _section("Monthly Breakdown")
    tabs = st.tabs([f"📊 {calendar.month_name[m]}" for m in sorted(sel_months)])
    for i, m in enumerate(sorted(sel_months)):
        with tabs[i]:
            render_monthly_analysis(data, f"{sel_year}-{m:02d}", calendar.month_name[m])

    if len(sel_months) > 1:
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        render_aggregate_analysis(data, sel_year, sel_months)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Export Data")
    ec1, ec2 = st.columns([2, 1])
    with ec1:
        fmt = st.radio("Format", ["Excel","PDF Report"], horizontal=True,
                       label_visibility="collapsed")
    with ec2:
        if fmt == "Excel":
            st.download_button("📥 Download Excel",
                               data=export_to_excel(pd_filt),
                               file_name=f"transactions_{sel_year}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True, type="primary")
        else:
            try:
                from pdf_generator import create_comprehensive_pdf
                pdf = create_comprehensive_pdf(data=data, selected_year=int(sel_year),
                                               selected_months=[int(m) for m in sel_months],
                                               analysis_type=atype,
                                               user_id=st.session_state.user["id"])
                st.download_button("📥 Download PDF", data=pdf,
                                   file_name=f"Finance_Report_{sel_year}.pdf",
                                   mime="application/pdf",
                                   use_container_width=True, type="primary")
            except Exception as e:
                st.error(f"PDF error: {e}")


def display_file_card(file):
    icon = "📄" if file["file_type"] == "pdf" else "📊"
    st.markdown(f"""
        <div class="file-card">
            <div style="font-size:2rem;margin-bottom:.5rem;">{icon}</div>
            <div style="font-weight:600;font-size:.85rem;color:#e8eaf0;
                        margin-bottom:.25rem;word-break:break-all;">{file['filename']}</div>
            <div style="font-size:.72rem;color:#7b7f94;">
                {file['upload_date'].strftime('%d %b %Y')}</div>
        </div>""", unsafe_allow_html=True)
    if st.button("🗑️ Delete", key=f"del_{file['id']}", use_container_width=True):
        if delete_user_file(file["id"], st.session_state.user["id"]):
            st.success("Deleted"); clear_data_cache(); st.rerun()


def display_pagination_controls(total, page_size):
    total_pages = (total + page_size - 1) // page_size
    cur = st.session_state.file_page
    c1, c2, c3, c4, c5 = st.columns([1,1,2,1,1])
    with c1:
        if st.button("⏮", disabled=cur==0, key="page_first"): st.session_state.file_page=0; st.rerun()
    with c2:
        if st.button("◀", disabled=cur==0, key="page_prev"): st.session_state.file_page=cur-1; st.rerun()
    with c3:
        st.markdown(f"<div style='text-align:center;padding:.4rem;color:#7b7f94;font-size:.85rem;'>"
                    f"Page {cur+1} / {total_pages}</div>", unsafe_allow_html=True)
    with c4:
        if st.button("▶", disabled=cur>=total_pages-1, key="page_next"): st.session_state.file_page=cur+1; st.rerun()
    with c5:
        if st.button("⏭", disabled=cur>=total_pages-1, key="page_last"): st.session_state.file_page=total_pages-1; st.rerun()


def spending_analysis_page():
    _page_header("Spending Analysis", "ANALYTICS", "sa_back", back_feature=None)

    _section("Upload Bank Statements",
             "JMMB CSV or NCB PDF bank statements are supported.")

    if "files_uploaded" not in st.session_state:
        st.session_state.files_uploaded = False
    uploader_key = f"file_uploader_{st.session_state.get('upload_counter', 0)}"
    uploaded = st.file_uploader("Choose files", type=["csv","pdf"],
                                 accept_multiple_files=True, key=uploader_key,
                                 help="One or more CSV / PDF files from your bank")
    if uploaded:
        st.write(f"**{len(uploaded)} file(s) selected**")
        for f in uploaded:
            st.caption(f"{'📄' if f.name.endswith('.pdf') else '📊'} {f.name}")
        b1, b2, _ = st.columns([1,1,2])
        with b1:
            if st.button("📤 Upload All", type="primary", use_container_width=True):
                ok = err = 0
                bar = st.progress(0); txt = st.empty()
                for i, f in enumerate(uploaded):
                    txt.text(f"Uploading {f.name}…")
                    try:
                        if save_user_file(st.session_state.user["id"], f.name,
                                          f.read(), f.name.split(".")[-1].lower()):
                            ok += 1
                        else: err += 1
                    except Exception as e:
                        st.error(str(e)); err += 1
                    bar.progress((i+1)/len(uploaded))
                bar.empty(); txt.empty()
                if ok:
                    st.success(f"✅ {ok} file(s) uploaded")
                    clear_data_cache()
                    st.session_state.upload_counter = st.session_state.get("upload_counter",0)+1
                    st.session_state.files_uploaded = True
                    st.rerun()
                if err: st.error(f"{err} file(s) failed")
        with b2:
            if st.button("✕ Clear selection", use_container_width=True):
                st.session_state.upload_counter = st.session_state.get("upload_counter",0)+1
                st.rerun()

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Uploaded Files")
    if "file_page" not in st.session_state: st.session_state.file_page = 0
    files, total = get_user_files_paginated(st.session_state.user["id"],
                                             st.session_state.file_page, FILES_PER_PAGE)
    if total == 0:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2rem;text-align:center;">
                <div style="font-size:2rem;margin-bottom:.5rem;">📂</div>
                <div style="color:#7b7f94;font-size:.9rem;">No files uploaded yet.</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption(f"{total} file(s) stored")
        cols = st.columns(3)
        for i, f in enumerate(files):
            with cols[i % 3]: display_file_card(f)
        if total > FILES_PER_PAGE: display_pagination_controls(total, FILES_PER_PAGE)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    render_category_editor()

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Spending Visualisations")
    with st.spinner("Loading data…"):
        data = load_all_user_data(st.session_state.user["id"])
    if data.empty:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2.5rem;text-align:center;">
                <div style="font-size:2rem;margin-bottom:.5rem;">📊</div>
                <div style="color:#7b7f94;font-size:.9rem;">
                    Upload files above to see your spending analysis.</div>
            </div>""", unsafe_allow_html=True)
        return
    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data = data.dropna(subset=["Date"])
        for col_name, fn in [("Year", lambda d: d.dt.year),
                              ("Month", lambda d: d.dt.month),
                              ("YearMonth", lambda d: d.dt.strftime("%Y-%m"))]:
            if col_name not in data.columns:
                data[col_name] = fn(data["Date"])
        if "Spending Category" not in data.columns:
            from data_processing import categorize_transactions
            data = categorize_transactions(data)
        render_analysis_section(data)
    else:
        st.error("No Date column found in data.")
