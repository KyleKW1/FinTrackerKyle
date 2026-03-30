# pages/financial_time_machine.py
"""Financial Time Machine — polished dark-luxury redesign"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_all_user_data
from utils import calculate_monthly_stats
import calendar, json

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.08)"),
    margin=dict(t=44, b=24, l=10, r=10),
)


def _page_header():
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown("""
            <div style="padding:.75rem 0 .25rem;">
                <span style="font-size:.7rem;font-weight:600;letter-spacing:.1em;
                             text-transform:uppercase;color:#f5a623;">SCENARIOS</span>
                <h2 style="font-family:'Playfair Display',serif;font-size:1.8rem;
                           font-weight:600;color:#e8eaf0;margin:.2rem 0 0;
                           letter-spacing:-.02em;">Financial Time Machine</h2>
                <p style="font-size:.82rem;color:#7b7f94;margin:.35rem 0 0;">
                    See how today's decisions compound into your financial future.</p>
            </div>""", unsafe_allow_html=True)
    with c2:
        if st.button("← Back", key="ftm_back", use_container_width=True):
            st.session_state.selected_feature = None; st.rerun()
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)


def _section(title, sub=""):
    st.markdown(f"""
        <p style="font-family:'Playfair Display',serif;font-size:1.15rem;
                  font-weight:600;color:#e8eaf0;margin:1.5rem 0 .6rem;
                  letter-spacing:-.01em;">{title}</p>
        {"<p style='font-size:.78rem;color:#7b7f94;margin:-.4rem 0 .6rem;'>" + sub + "</p>" if sub else ""}
    """, unsafe_allow_html=True)


def financial_time_machine_page():
    _page_header()

    data = load_all_user_data(st.session_state.user["id"])
    if data.empty:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.10);
                        border-radius:14px;padding:2.5rem;text-align:center;">
                <div style="font-size:2.5rem;margin-bottom:.6rem;">🔮</div>
                <div style="color:#7b7f94;font-size:.9rem;">
                    Upload bank statements in Spending Analysis to unlock the Time Machine.</div>
            </div>""", unsafe_allow_html=True)
        if st.button("Go to Spending Analysis", use_container_width=False):
            st.session_state.selected_feature = "analysis"; st.rerun()
        return

    for col, fn in [("Year", lambda d: d.dt.year), ("Month", lambda d: d.dt.month),
                    ("YearMonth", lambda d: d.dt.strftime("%Y-%m"))]:
        if col not in data.columns:
            data[col] = fn(pd.to_datetime(data["Date"]))

    avail = sorted(data["YearMonth"].unique(), reverse=True)
    months = avail[:6] if len(avail) >= 6 else avail
    if len(months) < 3:
        st.warning("Need at least 3 months of data for accurate predictions."); return

    # ── baseline ────────────────────────────────
    t_inc = t_spd = 0.0
    cat_data: dict = {}
    for ym in months:
        s = calculate_monthly_stats(data, ym)
        t_inc += s["income"]; t_spd += s["spending"]
        md = data[data["YearMonth"] == ym]
        if "Spending Category" in md.columns and "Category" in md.columns:
            for cat in md[md["Category"] == "Debit"]["Spending Category"].unique():
                v = md[(md["Category"]=="Debit") & (md["Spending Category"]==cat)]["Amount"].sum()
                cat_data.setdefault(cat, []).append(v)

    n = len(months)
    avg_inc = t_inc / n; avg_spd = t_spd / n; avg_sav = avg_inc - avg_spd
    avg_cats = {c: sum(v)/len(v) for c, v in cat_data.items()}

    _section("Your Financial Baseline", f"Averages from your last {n} months of data")
    c1, c2, c3 = st.columns(3)
    for col, lbl, val, grad, sub_txt in [
        (c1,"Avg Monthly Income",  avg_inc,"#1fcf8a",f"across {n} months"),
        (c2,"Avg Monthly Spending",avg_spd,"#f04e5e",f"{avg_spd/avg_inc*100:.0f}% of income"),
        (c3,"Avg Monthly Savings", avg_sav,"#f5a623",f"{avg_sav/avg_inc*100:.0f}% savings rate"),
    ]:
        with col:
            st.markdown(f"""
                <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                            border-left:3px solid {grad};border-radius:14px;
                            padding:1.25rem 1.4rem;">
                    <div style="font-size:.68rem;font-weight:600;letter-spacing:.07em;
                                text-transform:uppercase;color:#7b7f94;margin-bottom:.4rem;">
                        {lbl}</div>
                    <div style="font-size:1.7rem;font-weight:700;color:#e8eaf0;
                                margin-bottom:.2rem;">J${val:,.0f}</div>
                    <div style="font-size:.75rem;color:#7b7f94;">{sub_txt}</div>
                </div>""", unsafe_allow_html=True)

    # category chart
    if avg_cats:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        cat_df = pd.DataFrame([{"Category":k,"Avg":v}
                                for k,v in sorted(avg_cats.items(), key=lambda x:-x[1])])
        ca, cb = st.columns([2,1])
        with ca:
            fig = px.bar(cat_df, x="Category", y="Avg", color="Avg",
                         color_continuous_scale=["#3d9df6","#f5a623","#f04e5e"],
                         title="Monthly Spending by Category")
            fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-35,
                              height=320, **_PLOTLY)
            st.plotly_chart(fig, use_container_width=True)
        with cb:
            st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
            for _, r in cat_df.head(5).iterrows():
                pct = r["Avg"] / avg_spd * 100
                st.markdown(f"""
                    <div style="background:rgba(240,78,94,.07);border-left:3px solid #f04e5e;
                                border-radius:8px;padding:.55rem .8rem;margin-bottom:.4rem;">
                        <div style="font-weight:600;color:#e8eaf0;font-size:.85rem;">
                            {r['Category']}</div>
                        <div style="color:#7b7f94;font-size:.75rem;">
                            J${r['Avg']:,.0f} — {pct:.0f}%</div>
                    </div>""", unsafe_allow_html=True)

    # ── configure ───────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Configure Your Time Machine")
    c1, c2, c3 = st.columns(3)
    with c1: cur_age = st.number_input("Current Age",18,80,30,key="cur_age")
    with c2: ret_goal= st.number_input("Retirement Goal (J$)",100000,50000000,5000000,100000,key="ret_goal")
    with c3: tar_age = st.number_input("Target Retirement Age",cur_age+5,80,65,key="tar_age")

    # ── scenarios ───────────────────────────────
    disc  = sum(avg_cats.get(c,0) for c in ["Food","Miscellaneous","Retail & Entertainment"])
    major = avg_spd * 0.25

    scenarios = [
        dict(name="😟 Current Path",  desc="Continue exactly as today",
             sav=avg_sav, changes=[], color="#f04e5e"),
        dict(name="😊 Optimised Path", desc="Cut discretionary spending 20%",
             sav=avg_sav + disc*0.20,
             changes=[f"Dining out: −J${disc*.10:,.0f}/mo",
                      f"Smart shopping: −J${disc*.06:,.0f}/mo",
                      f"Subscriptions: −J${disc*.04:,.0f}/mo"],
             color="#3d9df6"),
        dict(name="🚀 Aggressive Path", desc="Major lifestyle optimisation",
             sav=avg_sav + major,
             changes=[f"Housing: −J${major*.4:,.0f}/mo",
                      f"Meal prep: −J${major*.3:,.0f}/mo",
                      f"Transport: −J${major*.2:,.0f}/mo",
                      f"Luxuries: −J${major*.1:,.0f}/mo"],
             color="#1fcf8a"),
    ]
    for s in scenarios:
        sv = s["sav"]
        s.update(y1=sv*12, y3=sv*36, y5=sv*60, y10=sv*120)
        if sv > 0:
            yrs = (ret_goal/sv)/12
            s.update(ret_age=cur_age+yrs, yrs_to=yrs)
        else:
            s.update(ret_age=None, yrs_to=None)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Your Three Possible Futures")
    cols = st.columns(3)
    for i, s in enumerate(scenarios):
        with cols[i]:
            if s["ret_age"]:
                diff = tar_age - s["ret_age"]
                if diff >= 0:
                    ret_html = f"<div style='color:#1fcf8a;font-weight:600;font-size:.82rem;margin-top:.6rem;'>✅ Retire at {s['ret_age']:.0f} — {diff:.0f} yrs early</div>"
                else:
                    ret_html = f"<div style='color:#f04e5e;font-weight:600;font-size:.82rem;margin-top:.6rem;'>⚠️ Retire at {s['ret_age']:.0f} — {abs(diff):.0f} yrs late</div>"
            else:
                ret_html = "<div style='color:#f04e5e;font-weight:600;font-size:.82rem;margin-top:.6rem;'>❌ Goal unreachable at this rate</div>"
            chg_html = "<br>".join(f"<span style='color:#7b7f94'>• {c}</span>" for c in s["changes"]) or "<span style='color:#7b7f94'>No changes needed</span>"
            st.markdown(f"""
                <div style="background:#13151f;border:1.5px solid {s['color']}33;
                            border-radius:16px;padding:1.5rem;height:100%;">
                    <div style="font-size:1.1rem;font-weight:700;color:#e8eaf0;
                                margin-bottom:.3rem;">{s['name']}</div>
                    <div style="font-size:.78rem;color:#7b7f94;margin-bottom:1rem;">
                        {s['desc']}</div>
                    <div style="background:{s['color']}18;border-radius:10px;
                                padding:.9rem;margin-bottom:1rem;">
                        <div style="font-size:.65rem;font-weight:600;letter-spacing:.07em;
                                    text-transform:uppercase;color:#7b7f94;margin-bottom:.3rem;">
                            Monthly Savings</div>
                        <div style="font-size:1.55rem;font-weight:700;color:{s['color']};">
                            J${s['sav']:,.0f}</div>
                    </div>
                    <div style="font-size:.8rem;color:#e8eaf0;margin-bottom:.25rem;">
                        <b>5 yr:</b> J${s['y5']:,.0f}</div>
                    <div style="font-size:.8rem;color:#e8eaf0;margin-bottom:.5rem;">
                        <b>10 yr:</b> J${s['y10']:,.0f}</div>
                    {ret_html}
                    <div style="border-top:1px solid rgba(255,255,255,.07);
                                margin:.9rem 0 .6rem;"></div>
                    <div style="font-size:.75rem;line-height:1.7;">{chg_html}</div>
                </div>""", unsafe_allow_html=True)

    # ── timeline chart ───────────────────────────
    milestones = [
        ("🏥 Emergency Fund", 100000), ("✈️ Vacation", 250000),
        ("🚗 New Car", 500000), ("🏠 Down Payment", 2000000),
        (f"🎯 Retirement (J${ret_goal:,.0f})", ret_goal),
    ]
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("Timeline to Financial Milestones")
    tl = []
    for s in scenarios:
        if s["sav"] <= 0: continue
        for lbl, amt in milestones:
            tl.append({"Scenario":s["name"], "Milestone":lbl,
                       "Years":amt/s["sav"]/12, "color":s["color"]})
    if tl:
        tl_df = pd.DataFrame(tl)
        fig = go.Figure()
        for sname in tl_df["Scenario"].unique():
            sub = tl_df[tl_df["Scenario"]==sname]
            clr = sub["color"].iloc[0]
            fig.add_trace(go.Scatter(
                x=sub["Years"], y=sub["Milestone"],
                mode="markers+lines", name=sname,
                marker=dict(size=14, color=clr, line=dict(width=2,color="#07080f")),
                line=dict(width=2.5, color=clr),
            ))
        fig.update_layout(height=400, xaxis_title="Years from Now",
                          legend=dict(orientation="h",y=1.06,x=1,xanchor="right"),
                          **_PLOTLY)
        st.plotly_chart(fig, use_container_width=True)

    # ── 20-yr projection ─────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _section("20-Year Savings Projection")
    years = list(range(0, 21))
    fig2 = go.Figure()
    for s in scenarios:
        cum = [s["sav"]*12*y for y in years]
        fig2.add_trace(go.Scatter(x=years, y=cum, mode="lines", name=s["name"],
                                  line=dict(width=3.5, color=s["color"])))
    fig2.add_hline(y=ret_goal, line_dash="dot", line_color="#f5a623",
                   annotation_text=f"Goal: J${ret_goal:,.0f}",
                   annotation_font_color="#f5a623")
    fig2.update_layout(height=420, xaxis_title="Years from Now",
                       yaxis=dict(tickprefix="J$", tickformat=",.0f",
                                  gridcolor="rgba(255,255,255,0.05)"),
                       legend=dict(orientation="h",y=1.06,x=1,xanchor="right"),
                       **_PLOTLY)
    st.plotly_chart(fig2, use_container_width=True)

    # ── action plan ──────────────────────────────
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    viable = [s for s in scenarios if s["ret_age"] and s["ret_age"] <= tar_age]
    if viable:
        best = min(viable, key=lambda x: len(x["changes"]))
        st.markdown(f"""
            <div style="background:rgba(31,207,138,.08);border:1px solid rgba(31,207,138,.25);
                        border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">
                <div style="font-weight:700;color:#1fcf8a;margin-bottom:.4rem;">
                    ✅ You CAN retire by age {tar_age} — {best['name']}</div>
                <div style="font-size:.85rem;color:#7b7f94;">
                    This adds <strong style="color:#e8eaf0;">
                    J${best['sav']-avg_sav:,.0f}/month</strong> in savings.</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="background:rgba(240,78,94,.08);border:1px solid rgba(240,78,94,.25);
                        border-radius:12px;padding:1.25rem 1.5rem;">
                <div style="font-weight:700;color:#f04e5e;margin-bottom:.4rem;">
                    ⚠️ Current path won't meet your goal by age {tar_age}</div>
                <div style="font-size:.85rem;color:#7b7f94;">
                    Consider the 🚀 Aggressive Path or adjusting your retirement age.</div>
            </div>""", unsafe_allow_html=True)

    # email
    _, ec = st.columns([3, 1])
    with ec:
        if st.button("📧 Email My Timeline", use_container_width=True):
            from utils import send_email_alert
            body = (f"Finance Hub — Time Machine Results\n\n"
                    f"Income: J${avg_inc:,.0f}/mo  Spending: J${avg_spd:,.0f}/mo\n\n"
                    + "".join(f"\n{s['name']}: J${s['sav']:,.0f}/mo  "
                              f"Retire @ {s['ret_age']:.0f if s['ret_age'] else 'N/A'}\n"
                              for s in scenarios))
            if send_email_alert(st.session_state.user["email"],
                                "Your Financial Time Machine Results", body):
                st.success("Sent!")
            else:
                st.error("Failed to send email.")
