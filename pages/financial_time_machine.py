"""
pages/financial_time_machine.py - Revolutionary Future Scenario Simulator
Place this file in the pages/ directory

INTEGRATION STEPS:
1. Save this file as: pages/financial_time_machine.py
2. Update pages/dashboard.py to add the Time Machine button
3. Update pages/__init__.py to import this module
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_all_user_data
from utils import calculate_monthly_stats
from database import get_user_preferences
import calendar
from datetime import datetime, timedelta
import json


def calculate_retirement_age(monthly_savings, retirement_goal, current_age=30):
    """Calculate age at which retirement goal is reached"""
    if monthly_savings <= 0:
        return None
    
    months_needed = retirement_goal / monthly_savings
    years_needed = months_needed / 12
    retirement_age = current_age + years_needed
    
    return retirement_age


def financial_time_machine_page():
    """The Financial Time Machine - See your financial futures"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🔮 Financial Time Machine")
        st.caption("See how your daily decisions compound into your future")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    
    st.markdown("---")
    
    # Load user data
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No transaction data available")
        st.info("Upload your bank statements in Spending Analysis to unlock the Time Machine")
        if st.button("Go to Spending Analysis", use_container_width=False):
            st.session_state.selected_feature = 'analysis'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Ensure required columns
    if 'Year' not in data.columns:
        data['Year'] = pd.to_datetime(data['Date']).dt.year
    if 'Month' not in data.columns:
        data['Month'] = pd.to_datetime(data['Date']).dt.month
    if 'YearMonth' not in data.columns:
        data['YearMonth'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m')
    
    # ==========================================
    # ANALYZE RECENT BEHAVIOR
    # ==========================================
    st.markdown("#### 📊 Your Financial Baseline")
    st.caption("Based on your last 6 months of spending patterns")
    
    # Get last 6 months
    available_months = sorted(data['YearMonth'].unique(), reverse=True)
    analysis_months = available_months[:6] if len(available_months) >= 6 else available_months
    
    if len(analysis_months) < 3:
        st.warning("⚠️ Need at least 3 months of data for accurate predictions")
        st.info("Upload more bank statements to unlock full Time Machine features")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Calculate averages
    total_income = 0
    total_spending = 0
    spending_by_category = {}
    
    for ym in analysis_months:
        stats = calculate_monthly_stats(data, ym)
        total_income += stats['income']
        total_spending += stats['spending']
        
        # Get category breakdown
        month_data = data[data['YearMonth'] == ym]
        if 'Spending Category' in month_data.columns and 'Category' in month_data.columns:
            debits = month_data[month_data['Category'] == 'Debit']
            for cat in debits['Spending Category'].unique():
                cat_spending = debits[debits['Spending Category'] == cat]['Amount'].sum()
                if cat not in spending_by_category:
                    spending_by_category[cat] = []
                spending_by_category[cat].append(cat_spending)
    
    n_months = len(analysis_months)
    avg_monthly_income = total_income / n_months
    avg_monthly_spending = total_spending / n_months
    avg_monthly_savings = avg_monthly_income - avg_monthly_spending
    
    # Calculate category averages
    avg_category_spending = {
        cat: sum(amounts) / len(amounts) 
        for cat, amounts in spending_by_category.items()
    }
    
    # Display baseline
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                 padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>
                    💰 Avg Monthly Income
                </div>
                <div style='font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>
                    J${avg_monthly_income:,.0f}
                </div>
                <div style='font-size: 0.75rem; opacity: 0.8;'>
                    Based on {n_months} months
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                 padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>
                    💸 Avg Monthly Spending
                </div>
                <div style='font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>
                    J${avg_monthly_spending:,.0f}
                </div>
                <div style='font-size: 0.75rem; opacity: 0.8;'>
                    {(avg_monthly_spending/avg_monthly_income*100):.0f}% of income
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        savings_color = '#3b82f6' if avg_monthly_savings > 0 else '#f59e0b'
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, {savings_color} 0%, {savings_color}dd 100%); 
                 padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>
                    🎯 Avg Monthly Savings
                </div>
                <div style='font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>
                    J${avg_monthly_savings:,.0f}
                </div>
                <div style='font-size: 0.75rem; opacity: 0.8;'>
                    {(avg_monthly_savings/avg_monthly_income*100):.0f}% savings rate
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # ==========================================
    # CATEGORY BREAKDOWN
    # ==========================================
    st.markdown("---")
    st.markdown("##### 🏷️ Your Spending Breakdown")
    
    if avg_category_spending:
        category_df = pd.DataFrame([
            {'Category': cat, 'Monthly Average': amt}
            for cat, amt in sorted(avg_category_spending.items(), key=lambda x: x[1], reverse=True)
        ])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.bar(
                category_df,
                x='Category',
                y='Monthly Average',
                color='Monthly Average',
                color_continuous_scale='Reds',
                title='Average Monthly Spending by Category'
            )
            fig.update_layout(
                showlegend=False,
                xaxis_tickangle=-45,
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**Top Spending Categories:**")
            for idx, row in category_df.head(5).iterrows():
                pct = (row['Monthly Average'] / avg_monthly_spending) * 100
                st.markdown(f"""
                    <div style='background: #fee2e2; padding: 0.5rem; border-radius: 6px; margin-bottom: 0.5rem;'>
                        <div style='font-weight: 600; color: #991b1b;'>{row['Category']}</div>
                        <div style='color: #7f1d1d;'>J${row['Monthly Average']:,.0f} ({pct:.0f}%)</div>
                    </div>
                """, unsafe_allow_html=True)
    
    # ==========================================
    # USER CONFIGURATION
    # ==========================================
    st.markdown("---")
    st.markdown("#### ⚙️ Configure Your Time Machine")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        current_age = st.number_input(
            "Your Current Age",
            min_value=18,
            max_value=80,
            value=30,
            step=1,
            key="current_age",
            help="Your age today"
        )
    
    with col2:
        retirement_goal = st.number_input(
            "Retirement Goal (J$)",
            min_value=100000,
            max_value=50000000,
            value=5000000,
            step=100000,
            key="retirement_goal",
            help="How much you need to retire comfortably"
        )
    
    with col3:
        target_retirement_age = st.number_input(
            "Target Retirement Age",
            min_value=current_age + 5,
            max_value=80,
            value=65,
            step=1,
            key="target_retirement",
            help="When you want to retire"
        )
    
    # ==========================================
    # SCENARIO GENERATION
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🎯 Your Three Possible Futures")
    
    # Identify discretionary spending (Food, Entertainment, Miscellaneous)
    discretionary_cats = ['Food', 'Miscellaneous', 'Retail & Entertainment']
    discretionary_spending = sum([
        avg_category_spending.get(cat, 0) 
        for cat in discretionary_cats
    ])
    
    # SCENARIO 1: Current Path
    scenario_current = {
        'name': '😟 Current Path',
        'description': 'If you continue exactly as you are',
        'monthly_savings': avg_monthly_savings,
        'changes': [],
        'color': '#ef4444'
    }
    
    # SCENARIO 2: Optimized Path (20% cut in discretionary)
    discretionary_cut = discretionary_spending * 0.20
    scenario_optimized = {
        'name': '😊 Optimized Path',
        'description': 'Cut discretionary spending by 20%',
        'monthly_savings': avg_monthly_savings + discretionary_cut,
        'changes': [
            f"• Reduce dining out: -J${discretionary_cut * 0.5:,.0f}/month",
            f"• Smart shopping: -J${discretionary_cut * 0.3:,.0f}/month",
            f"• Cut subscriptions: -J${discretionary_cut * 0.2:,.0f}/month"
        ],
        'color': '#3b82f6'
    }
    
    # SCENARIO 3: Aggressive Path (50% lifestyle change)
    major_savings = avg_monthly_spending * 0.25  # Save 25% more of spending
    scenario_aggressive = {
        'name': '🚀 Aggressive Path',
        'description': 'Major lifestyle optimization',
        'monthly_savings': avg_monthly_savings + major_savings,
        'changes': [
            f"• Downsize housing: -J${major_savings * 0.4:,.0f}/month",
            f"• Meal prep (no dining out): -J${major_savings * 0.3:,.0f}/month",
            f"• Public transport: -J${major_savings * 0.2:,.0f}/month",
            f"• Cancel luxuries: -J${major_savings * 0.1:,.0f}/month"
        ],
        'color': '#10b981'
    }
    
    scenarios = [scenario_current, scenario_optimized, scenario_aggressive]
    
    # Calculate outcomes for each scenario
    for scenario in scenarios:
        savings = scenario['monthly_savings']
        
        scenario['1_year'] = savings * 12
        scenario['3_years'] = savings * 36
        scenario['5_years'] = savings * 60
        scenario['10_years'] = savings * 120
        
        # Calculate retirement age
        if savings > 0:
            months_to_goal = retirement_goal / savings
            years_to_goal = months_to_goal / 12
            scenario['retirement_age'] = current_age + years_to_goal
            scenario['years_to_retirement'] = years_to_goal
        else:
            scenario['retirement_age'] = None
            scenario['years_to_retirement'] = None
    
    # Display scenarios
    cols = st.columns(3)
    
    for idx, scenario in enumerate(scenarios):
        with cols[idx]:
            retirement_text = ""
            if scenario['retirement_age']:
                years_saved = target_retirement_age - scenario['retirement_age']
                if scenario['retirement_age'] <= target_retirement_age:
                    retirement_text = f"<div style='color: #10b981; font-weight: 600; margin-top: 0.5rem;'>✅ Retire at age {scenario['retirement_age']:.0f}<br/>🎉 {years_saved:.0f} years early!</div>"
                else:
                    retirement_text = f"<div style='color: #ef4444; font-weight: 600; margin-top: 0.5rem;'>⚠️ Retire at age {scenario['retirement_age']:.0f}<br/>⏰ {abs(years_saved):.0f} years late</div>"
            else:
                retirement_text = "<div style='color: #ef4444; font-weight: 600; margin-top: 0.5rem;'>❌ Never reach retirement goal</div>"
            
            changes_html = "<br/>".join(scenario['changes']) if scenario['changes'] else "No changes required"
            
            st.markdown(f"""
                <div style='background: white; border: 3px solid {scenario['color']}; 
                     border-radius: 12px; padding: 1.5rem; height: 100%;'>
                    <div style='font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;'>
                        {scenario['name']}
                    </div>
                    <div style='color: #6b7280; margin-bottom: 1rem; font-size: 0.9rem;'>
                        {scenario['description']}
                    </div>
                    <div style='background: {scenario['color']}22; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
                        <div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.25rem;'>Monthly Savings</div>
                        <div style='font-size: 1.5rem; font-weight: 700; color: {scenario['color']};'>
                            J${scenario['monthly_savings']:,.0f}
                        </div>
                    </div>
                    <div style='font-size: 0.85rem; color: #374151; margin-bottom: 0.5rem;'>
                        <strong>In 5 years:</strong> J${scenario['5_years']:,.0f}
                    </div>
                    <div style='font-size: 0.85rem; color: #374151; margin-bottom: 0.5rem;'>
                        <strong>In 10 years:</strong> J${scenario['10_years']:,.0f}
                    </div>
                    {retirement_text}
                    <hr style='margin: 1rem 0; opacity: 0.2;'>
                    <div style='font-size: 0.8rem; color: #6b7280;'>
                        <strong>Changes needed:</strong><br/>
                        {changes_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # ==========================================
    # VISUAL TIMELINE
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📅 Your Financial Timeline")
    st.caption("See when you'll reach major milestones in each scenario")
    
    # Define milestones
    milestones = [
        {'name': 'Emergency Fund', 'amount': 100000, 'icon': '🏥'},
        {'name': 'Vacation Fund', 'amount': 250000, 'icon': '✈️'},
        {'name': 'New Car', 'amount': 500000, 'icon': '🚗'},
        {'name': 'House Down Payment', 'amount': 2000000, 'icon': '🏠'},
        {'name': 'Retirement Goal', 'amount': retirement_goal, 'icon': '🎯'}
    ]
    
    # Calculate timeline for each scenario
    timeline_data = []
    
    for scenario in scenarios:
        if scenario['monthly_savings'] <= 0:
            continue
        
        for milestone in milestones:
            months_to_milestone = milestone['amount'] / scenario['monthly_savings']
            years_to_milestone = months_to_milestone / 12
            
            timeline_data.append({
                'Scenario': scenario['name'],
                'Milestone': f"{milestone['icon']} {milestone['name']}",
                'Years': years_to_milestone,
                'Amount': milestone['amount']
            })
    
    if timeline_data:
        timeline_df = pd.DataFrame(timeline_data)
        
        fig = go.Figure()
        
        colors = {'😟 Current Path': '#ef4444', '😊 Optimized Path': '#3b82f6', '🚀 Aggressive Path': '#10b981'}
        
        for scenario_name in timeline_df['Scenario'].unique():
            scenario_data = timeline_df[timeline_df['Scenario'] == scenario_name]
            
            fig.add_trace(go.Scatter(
                x=scenario_data['Years'],
                y=scenario_data['Milestone'],
                mode='markers+lines',
                name=scenario_name,
                marker=dict(size=15, color=colors.get(scenario_name, '#667eea')),
                line=dict(width=3, color=colors.get(scenario_name, '#667eea')),
                hovertemplate='<b>%{y}</b><br>Years: %{x:.1f}<br><extra></extra>'
            ))
        
        fig.update_layout(
            title='Timeline to Financial Milestones',
            xaxis_title='Years from Now',
            yaxis_title='Milestone',
            height=500,
            hovermode='closest',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # COMPOUND EFFECT VISUALIZATION
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📈 The Power of Compound Savings")
    st.caption("Watch your money grow over time with each scenario")
    
    # Generate 20-year projection
    years = list(range(0, 21))
    
    fig = go.Figure()
    
    for scenario in scenarios:
        cumulative = [scenario['monthly_savings'] * 12 * year for year in years]
        
        fig.add_trace(go.Scatter(
            x=years,
            y=cumulative,
            mode='lines',
            name=scenario['name'],
            line=dict(width=4, color=scenario['color']),
            fill='tonexty' if scenario != scenarios[0] else None,
            hovertemplate='<b>%{fullData.name}</b><br>Year %{x}<br>Total: J$%{y:,.0f}<extra></extra>'
        ))
    
    # Add retirement goal line
    fig.add_hline(
        y=retirement_goal,
        line_dash="dash",
        line_color="gold",
        annotation_text=f"Retirement Goal: J${retirement_goal:,.0f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title='20-Year Savings Projection',
        xaxis_title='Years from Now',
        yaxis_title='Total Savings (J$)',
        height=500,
        hovermode='x unified',
        yaxis=dict(
            tickformat=',.0f',
            tickprefix='J
    
    # ==========================================
    # ACTIONABLE INSIGHTS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 💡 Your Action Plan")
    
    # Find best scenario that meets retirement goal
    viable_scenarios = [s for s in scenarios if s['retirement_age'] and s['retirement_age'] <= target_retirement_age]
    
    if viable_scenarios:
        best_scenario = min(viable_scenarios, key=lambda x: len(x['changes']))
        
        st.success(f"✅ Good news! You CAN retire by age {target_retirement_age} with the **{best_scenario['name']}**")
        
        st.markdown("**Recommended Actions:**")
        for change in best_scenario['changes']:
            st.markdown(f"✓ {change}")
        
        st.info(f"💰 This will save you an extra **J${best_scenario['monthly_savings'] - avg_monthly_savings:,.0f}/month**")
    else:
        st.warning(f"⚠️ Your current path won't reach your retirement goal by age {target_retirement_age}")
        st.markdown("**Consider these options:**")
        st.markdown(f"• Increase your retirement age to {scenarios[-1]['retirement_age']:.0f}")
        st.markdown(f"• Reduce your retirement goal to J${scenarios[0]['monthly_savings'] * 12 * (target_retirement_age - current_age):,.0f}")
        st.markdown(f"• Adopt the 🚀 Aggressive Path to retire earlier")
    
    # ==========================================
    # SHARE YOUR TIMELINE
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📤 Share Your Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📸 Take Screenshot", use_container_width=True):
            st.info("💡 Use your browser's screenshot tool to capture your timeline!")
            st.caption("Tip: Share on social media to keep yourself accountable")
    
    with col2:
        if st.button("📧 Email My Timeline", use_container_width=True):
            from utils import send_email_alert
            
            email_body = f"""
Dear {st.session_state.user['username']},

Your Financial Time Machine Results:

CURRENT SITUATION:
• Monthly Income: J${avg_monthly_income:,.0f}
• Monthly Spending: J${avg_monthly_spending:,.0f}
• Monthly Savings: J${avg_monthly_savings:,.0f}

YOUR THREE FUTURES:

😟 CURRENT PATH:
   - Monthly Savings: J${scenarios[0]['monthly_savings']:,.0f}
   - 5-year savings: J${scenarios[0]['5_years']:,.0f}
   - Retirement age: {scenarios[0]['retirement_age']:.0f if scenarios[0]['retirement_age'] else 'Never'}

😊 OPTIMIZED PATH:
   - Monthly Savings: J${scenarios[1]['monthly_savings']:,.0f}
   - 5-year savings: J${scenarios[1]['5_years']:,.0f}
   - Retirement age: {scenarios[1]['retirement_age']:.0f if scenarios[1]['retirement_age'] else 'Never'}

🚀 AGGRESSIVE PATH:
   - Monthly Savings: J${scenarios[2]['monthly_savings']:,.0f}
   - 5-year savings: J${scenarios[2]['5_years']:,.0f}
   - Retirement age: {scenarios[2]['retirement_age']:.0f if scenarios[2]['retirement_age'] else 'Never'}

Keep building your future!

- Finance Hub
            """
            
            if send_email_alert(
                st.session_state.user['email'],
                "Your Financial Time Machine Results",
                email_body
            ):
                st.success("✅ Email sent!")
            else:
                st.error("❌ Failed to send email")
    
    st.markdown("</div>", unsafe_allow_html=True)

        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # ACTIONABLE INSIGHTS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 💡 Your Action Plan")
    
    # Find best scenario that meets retirement goal
    viable_scenarios = [s for s in scenarios if s['retirement_age'] and s['retirement_age'] <= target_retirement_age]
    
    if viable_scenarios:
        best_scenario = min(viable_scenarios, key=lambda x: len(x['changes']))
        
        st.success(f"✅ Good news! You CAN retire by age {target_retirement_age} with the **{best_scenario['name']}**")
        
        st.markdown("**Recommended Actions:**")
        for change in best_scenario['changes']:
            st.markdown(f"✓ {change}")
        
        st.info(f"💰 This will save you an extra **J${best_scenario['monthly_savings'] - avg_monthly_savings:,.0f}/month**")
    else:
        st.warning(f"⚠️ Your current path won't reach your retirement goal by age {target_retirement_age}")
        st.markdown("**Consider these options:**")
        st.markdown(f"• Increase your retirement age to {scenarios[-1]['retirement_age']:.0f}")
        st.markdown(f"• Reduce your retirement goal to J${scenarios[0]['monthly_savings'] * 12 * (target_retirement_age - current_age):,.0f}")
        st.markdown(f"• Adopt the 🚀 Aggressive Path to retire earlier")
    
    # ==========================================
    # SHARE YOUR TIMELINE
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📤 Share Your Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📸 Take Screenshot", use_container_width=True):
            st.info("💡 Use your browser's screenshot tool to capture your timeline!")
            st.caption("Tip: Share on social media to keep yourself accountable")
    
    with col2:
        if st.button("📧 Email My Timeline", use_container_width=True):
            from utils import send_email_alert
            
            email_body = f"""
Dear {st.session_state.user['username']},

Your Financial Time Machine Results:

CURRENT SITUATION:
• Monthly Income: J${avg_monthly_income:,.0f}
• Monthly Spending: J${avg_monthly_spending:,.0f}
• Monthly Savings: J${avg_monthly_savings:,.0f}

YOUR THREE FUTURES:

😟 CURRENT PATH:
   - Monthly Savings: J${scenarios[0]['monthly_savings']:,.0f}
   - 5-year savings: J${scenarios[0]['5_years']:,.0f}
   - Retirement age: {scenarios[0]['retirement_age']:.0f if scenarios[0]['retirement_age'] else 'Never'}

😊 OPTIMIZED PATH:
   - Monthly Savings: J${scenarios[1]['monthly_savings']:,.0f}
   - 5-year savings: J${scenarios[1]['5_years']:,.0f}
   - Retirement age: {scenarios[1]['retirement_age']:.0f if scenarios[1]['retirement_age'] else 'Never'}

🚀 AGGRESSIVE PATH:
   - Monthly Savings: J${scenarios[2]['monthly_savings']:,.0f}
   - 5-year savings: J${scenarios[2]['5_years']:,.0f}
   - Retirement age: {scenarios[2]['retirement_age']:.0f if scenarios[2]['retirement_age'] else 'Never'}

Keep building your future!

- Finance Hub
            """
            
            if send_email_alert(
                st.session_state.user['email'],
                "Your Financial Time Machine Results",
                email_body
            ):
                st.success("✅ Email sent!")
            else:
                st.error("❌ Failed to send email")
    
    st.markdown("</div>", unsafe_allow_html=True)
