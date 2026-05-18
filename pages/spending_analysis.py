# PATCH for pages/spending_analysis.py
# Replace the render_cash_flow_charts function with this version.
# The bug: `legend=` was passed BOTH explicitly AND inside **_PLOTLY,
# which Python raises as TypeError: got multiple values for keyword argument.
# Fix: strip 'legend' out of _PLOTLY before spreading it.

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

    # ── FIX: build layout dict, never pass the same key twice ──────────
    _base = {k: v for k, v in _PLOTLY.items() if k != "legend"}   # strip legend from _PLOTLY
    fig.update_layout(
        barmode="group",
        height=420,
        title=dict(text=f"Cash Flow — {year}", font=dict(color="#e8eaf0", size=14)),
        legend=dict(orientation="h", y=1.06, x=1, xanchor="right"),  # our version wins
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
