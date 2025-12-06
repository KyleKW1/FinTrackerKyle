"""
Add this to pages/budget_planner.py (create new file)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import get_user_preferences, save_user_preferences
from data_loader import load_all_user_data
from utils import get_spending_by_category, calculate_monthly_stats
from config import DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
import json
import calendar


def budget_planner_page():
    """Budget Planner - Set and track monthly budgets"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 💰 Budget Planner")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    
    st.markdown("---")
    
    # Load user preferences
    prefs = get_user_preferences(st.session_state.user['id'])
    if prefs and prefs.get('monthly_budgets'):
        current_budgets = json.loads(prefs['monthly_budgets'])
    else:
        current_budgets = DEFAULT_BUDGETS.copy()
    
    current_savings_goal = prefs.get('savings_goal', DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
    
    # Load user data
    data = load_all_user_data(st.session_state.user['id'])
    
    # ==========================================
    # BUDGET SETTINGS
    # ==========================================
    st.markdown("#### 🎯 Set Your Monthly Budgets")
    st.info("💡 Set realistic spending limits for each category. We'll track your progress and alert you when you're close to limits.")
    
    # Create two columns for budget inputs
    col1, col2 = st.columns(2)
    
    categories = [cat for cat in current_budgets.keys() if cat not in ['Income', 'Other']]
    mid = len(categories) // 2
    
    new_budgets = current_budgets.copy()
    
    with col1:
        st.markdown("##### 🏷️ Category Budgets")
        for category in categories[:mid]:
            new_budgets[category] = st.number_input(
                f"{category}",
                min_value=0,
                value=int(current_budgets[category]),
                step=500,
                key=f"budget_{category}",
                help=f"Monthly budget for {category}"
            )
    
    with col2:
        st.markdown("##### 🏷️ Category Budgets")
        for category in categories[mid:]:
            new_budgets[category] = st.number_input(
                f"{category}",
                min_value=0,
                value=int(current_budgets[category]),
                step=500,
                key=f"budget_{category}",
                help=f"Monthly budget for {category}"
            )
    
    # Savings goal
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("##### 💎 Monthly Savings Goal")
        new_savings_goal = st.number_input(
            "Target amount to save each month",
            min_value=0,
            value=int(current_savings_goal),
            step=500,
            key="savings_goal_input"
        )
    
    with col2:
        st.markdown("##### 📊 Total Budget")
        total_budget = sum(new_budgets.values())
        st.metric("Monthly Limit", f"J${total_budget:,.0f}")
    
    with col3:
        st.markdown("##### 💰 Target Income")
        target_income = total_budget + new_savings_goal
        st.metric("Needed", f"J${target_income:,.0f}")
    
    # Save button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Budgets", use_container_width=True, type="primary"):
            # Get current category keywords
            if prefs and prefs.get('category_keywords'):
                keywords = json.loads(prefs['category_keywords'])
            else:
                from config import DEFAULT_CATEGORY_MAPPING
                keywords = DEFAULT_CATEGORY_MAPPING.copy()
            
            if save_user_preferences(
                st.session_state.user['id'],
                keywords,
                new_budgets,
                new_savings_goal
            ):
                st.success("✅ Budgets saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save budgets")
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            if prefs and prefs.get('category_keywords'):
                keywords = json.loads(prefs['category_keywords'])
            else:
                from config import DEFAULT_CATEGORY_MAPPING
                keywords = DEFAULT_CATEGORY_MAPPING.copy()
            
            if save_user_preferences(
                st.session_state.user['id'],
                keywords,
                DEFAULT_BUDGETS,
                DEFAULT_SAVINGS_GOAL
            ):
                st.success("✅ Reset to defaults!")
                st.rerun()
    
    # ==========================================
    # BUDGET PERFORMANCE
    # ==========================================
    if not data.empty and 'YearMonth' in data.columns:
        st.markdown("---")
        st.markdown("#### 📈 Budget Performance")
        
        # Get available months
        available_months = sorted(data['YearMonth'].unique(), reverse=True)
        
        if available_months:
            # Month selector
            col1, col2 = st.columns([1, 3])
            
            with col1:
                selected_month = st.selectbox(
                    "Select Month",
                    available_months,
                    key="performance_month"
                )
            
            # Calculate performance
            month_stats = calculate_monthly_stats(data, selected_month)
            month_summary = get_spending_by_category(data, selected_month)
            
            if not month_summary.empty:
                # Create comparison
                comparison_data = []
                for category in new_budgets.keys():
                    if category in ['Income', 'Other']:
                        continue
                    
                    budget = new_budgets[category]
                    actual = month_summary[month_summary['Spending Category'] == category]['Amount'].sum()
                    
                    comparison_data.append({
                        'Category': category,
                        'Budget': budget,
                        'Actual': actual,
                        'Remaining': budget - actual,
                        'Percentage': (actual / budget * 100) if budget > 0 else 0
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                # Overall metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Budget",
                        f"J${total_budget:,.0f}",
                        help="Total monthly budget limit"
                    )
                
                with col2:
                    st.metric(
                        "Total Spent",
                        f"J${month_stats['spending']:,.0f}",
                        delta=f"{month_stats['spending'] - total_budget:,.0f}" if month_stats['spending'] > total_budget else None,
                        delta_color="inverse"
                    )
                
                with col3:
                    remaining = total_budget - month_stats['spending']
                    st.metric(
                        "Remaining",
                        f"J${remaining:,.0f}",
                        delta=f"{(remaining / total_budget * 100):.0f}%" if total_budget > 0 else None
                    )
                
                with col4:
                    st.metric(
                        "Savings",
                        f"J${month_stats['savings']:,.0f}",
                        delta=f"{month_stats['savings'] - new_savings_goal:,.0f}",
                        delta_color="normal"
                    )
                
                st.markdown("---")
                
                # Budget vs Actual Chart
                st.markdown("##### 📊 Budget vs Actual Spending")
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    name='Budget',
                    x=comparison_df['Category'],
                    y=comparison_df['Budget'],
                    marker_color='#3b82f6',
                    text=comparison_df['Budget'].apply(lambda x: f'J${x:,.0f}'),
                    textposition='outside'
                ))
                
                fig.add_trace(go.Bar(
                    name='Actual',
                    x=comparison_df['Category'],
                    y=comparison_df['Actual'],
                    marker_color=comparison_df['Percentage'].apply(
                        lambda x: '#ef4444' if x > 100 else '#10b981'
                    ),
                    text=comparison_df['Actual'].apply(lambda x: f'J${x:,.0f}'),
                    textposition='outside'
                ))
                
                fig.update_layout(
                    barmode='group',
                    height=400,
                    xaxis_tickangle=-45,
                    yaxis_title='Amount (J$)',
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
                
                # Detailed breakdown
                st.markdown("##### 📋 Category Details")
                
                # Create a better visual table
                for _, row in comparison_df.iterrows():
                    pct = row['Percentage']
                    
                    # Determine status and color
                    if pct > 100:
                        status = "🔴 OVER BUDGET"
                        color = "#ef4444"
                        bg_color = "#fee2e2"
                    elif pct > 80:
                        status = "🟡 WARNING"
                        color = "#f59e0b"
                        bg_color = "#fef3c7"
                    else:
                        status = "🟢 ON TRACK"
                        color = "#10b981"
                        bg_color = "#d1fae5"
                    
                    # Create card for each category
                    st.markdown(f"""
                        <div style='background: {bg_color}; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {color};'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <div style='flex: 1;'>
                                    <div style='font-size: 1.1rem; font-weight: 600; color: #111827; margin-bottom: 0.25rem;'>
                                        {row['Category']}
                                    </div>
                                    <div style='font-size: 0.85rem; color: #6b7280;'>
                                        Budget: J${row['Budget']:,.0f} | Spent: J${row['Actual']:,.0f} | Left: J${row['Remaining']:,.0f}
                                    </div>
                                </div>
                                <div style='text-align: right;'>
                                    <div style='font-size: 0.9rem; font-weight: 600; color: {color}; margin-bottom: 0.25rem;'>
                                        {status}
                                    </div>
                                    <div style='font-size: 1.25rem; font-weight: 700; color: {color};'>
                                        {pct:.0f}%
                                    </div>
                                </div>
                            </div>
                            <div style='margin-top: 0.5rem;'>
                                <div style='background: white; height: 8px; border-radius: 4px; overflow: hidden;'>
                                    <div style='background: {color}; height: 100%; width: {min(pct, 100):.0f}%; transition: width 0.3s ease;'></div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Alerts and Email
                st.markdown("---")
                
                over_budget = comparison_df[comparison_df['Percentage'] > 100]
                warning_budget = comparison_df[(comparison_df['Percentage'] > 80) & (comparison_df['Percentage'] <= 100)]
                
                if not over_budget.empty:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.error(f"⚠️ **{len(over_budget)} categories over budget!**")
                        for _, row in over_budget.iterrows():
                            st.caption(f"• **{row['Category']}**: {row['Percentage']:.0f}% used (J${row['Actual']:,.0f} / J${row['Budget']:,.0f})")
                    
                    with col2:
                        st.markdown("##### 📧 Email Alert")
                        recipient_email = st.text_input(
                            "Email Address",
                            value=st.session_state.user['email'],
                            key="budget_alert_email",
                            placeholder="your@email.com"
                        )
                        
                        if st.button("📧 Send Alert", use_container_width=True, type="primary", key="send_budget_alert"):
                            if recipient_email:
                                from utils import send_email_alert
                                
                                # Generate email body
                                body_lines = [
                                    f"Dear {st.session_state.user['username']},\n",
                                    f"Budget Alert for {selected_month}:\n\n",
                                    "Categories Over Budget:\n"
                                ]
                                
                                for _, row in over_budget.iterrows():
                                    body_lines.append(
                                        f"- {row['Category']}: J${row['Actual']:,.0f} / J${row['Budget']:,.0f} ({row['Percentage']:.0f}%)"
                                    )
                                
                                if not warning_budget.empty:
                                    body_lines.append("\n\nCategories Approaching Limit:\n")
                                    for _, row in warning_budget.iterrows():
                                        body_lines.append(
                                            f"- {row['Category']}: J${row['Actual']:,.0f} / J${row['Budget']:,.0f} ({row['Percentage']:.0f}%)"
                                        )
                                
                                body_lines.append("\n\nPlease review your spending.\n\nBest regards,\nFinance Hub Team")
                                
                                email_body = "\n".join(body_lines)
                                
                                with st.spinner("Sending email..."):
                                    if send_email_alert(recipient_email, f"Budget Alert - {selected_month}", email_body):
                                        st.success("✅ Email sent successfully!")
                                    else:
                                        st.error("❌ Failed to send email")
                            else:
                                st.error("Please enter an email address")
                
                elif not warning_budget.empty:
                    st.warning(f"⚡ **{len(warning_budget)} categories approaching limit**")
                    for _, row in warning_budget.iterrows():
                        st.caption(f"• **{row['Category']}**: {row['Percentage']:.0f}% used (J${row['Remaining']:,.0f} remaining)")
                
                if over_budget.empty and warning_budget.empty:
                    st.success("✅ **All categories within budget! Great job!**")
    
    else:
        st.info("📊 Upload transaction data in Spending Analysis to see your budget performance")
    
    st.markdown("</div>", unsafe_allow_html=True)
