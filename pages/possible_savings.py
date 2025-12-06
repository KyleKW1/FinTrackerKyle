"""
Create pages/possible_savings.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_all_user_data
from utils import calculate_monthly_stats
import calendar
import math


def calculate_roundup_savings(amount, round_to):
    """Calculate how much would be saved by rounding up to nearest value"""
    if round_to == 0:
        return 0
    rounded = math.ceil(amount / round_to) * round_to
    return rounded - amount


def possible_savings_page():
    """Possible Savings Calculator - Round-up savings simulator"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 💰 Possible Savings Calculator")
        st.caption("See how much you could save with automatic round-up on every transaction")
    with col2:
        if st.button("← Back to Budget Planner", use_container_width=True):
            st.session_state.selected_sub_feature = None
            st.rerun()
    
    st.markdown("---")
    
    # Load user data
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No transaction data available")
        st.info("Please upload files in Spending Analysis first to calculate possible savings")
        if st.button("Go to Spending Analysis", use_container_width=False):
            st.session_state.selected_feature = 'analysis'
            st.session_state.selected_sub_feature = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Ensure required columns exist
    if 'Year' not in data.columns:
        data['Year'] = pd.to_datetime(data['Date']).dt.year
    if 'Month' not in data.columns:
        data['Month'] = pd.to_datetime(data['Date']).dt.month
    
    # ==========================================
    # PERIOD SELECTION
    # ==========================================
    st.markdown("#### 📅 Select Analysis Period")
    
    col1, col2 = st.columns(2)
    
    with col1:
        available_years = sorted(data['Year'].unique(), reverse=True)
        selected_year = st.selectbox(
            "Year",
            available_years,
            key="savings_year"
        )
    
    with col2:
        period_type = st.selectbox(
            "Period",
            ["Last Month", "Last 3 Months", "Last 6 Months", "All Year"],
            key="savings_period"
        )
    
    # Filter data based on selection
    year_data = data[data['Year'] == selected_year]
    available_months = sorted(year_data['Month'].unique())
    
    if period_type == "Last Month":
        selected_months = available_months[-1:] if available_months else []
    elif period_type == "Last 3 Months":
        selected_months = available_months[-3:] if len(available_months) >= 3 else available_months
    elif period_type == "Last 6 Months":
        selected_months = available_months[-6:] if len(available_months) >= 6 else available_months
    else:  # All Year
        selected_months = available_months
    
    period_data = year_data[year_data['Month'].isin(selected_months)]
    
    # Filter only spending (debits)
    if 'Category' in period_data.columns:
        spending_data = period_data[period_data['Category'] == 'Debit'].copy()
    else:
        spending_data = period_data.copy()
    
    if spending_data.empty:
        st.warning("No spending transactions found for selected period")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    st.success(f"✅ Analyzing {len(spending_data)} spending transactions")
    
    # ==========================================
    # OVERVIEW - ALL ROUND-UP OPTIONS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🎯 Round-Up Options Overview")
    st.info("💡 Choose how you want to round up each transaction. The difference is automatically saved!")
    
    # Calculate savings for all round-up options
    roundup_options = {
        "J$1": 1,
        "J$10": 10,
        "J$100": 100,
        "J$1,000": 1000
    }
    
    savings_results = {}
    
    for label, round_amount in roundup_options.items():
        spending_data[f'roundup_{round_amount}'] = spending_data['Amount'].apply(
            lambda x: calculate_roundup_savings(x, round_amount)
        )
        savings_results[label] = {
            'total': spending_data[f'roundup_{round_amount}'].sum(),
            'per_transaction': spending_data[f'roundup_{round_amount}'].mean(),
            'monthly_avg': spending_data[f'roundup_{round_amount}'].sum() / len(selected_months) if selected_months else 0,
            'round_amount': round_amount
        }
    
    # Display savings cards for all options
    cols = st.columns(4)
    
    for idx, (label, results) in enumerate(savings_results.items()):
        with cols[idx]:
            colors = ['#10b981', '#3b82f6', '#8b5cf6', '#ef4444']
            color = colors[idx]
            
            st.markdown(f"""
                <div style='background: linear-gradient(135deg, {color} 0%, {color}dd 100%); 
                     padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                    <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>
                        Round to {label}
                    </div>
                    <div style='font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>
                        J${results['total']:,.0f}
                    </div>
                    <div style='font-size: 0.75rem; opacity: 0.8;'>
                        Avg: J${results['per_transaction']:,.2f}/transaction
                    </div>
                    <div style='font-size: 0.75rem; opacity: 0.8; margin-top: 0.25rem;'>
                        J${results['monthly_avg']:,.0f}/month
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # ==========================================
    # COMPARISON CHART
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📊 Savings Comparison")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Bar chart comparison
        fig = go.Figure()
        
        labels = list(savings_results.keys())
        totals = [results['total'] for results in savings_results.values()]
        colors_chart = ['#10b981', '#3b82f6', '#8b5cf6', '#ef4444']
        
        fig.add_trace(go.Bar(
            x=labels,
            y=totals,
            marker_color=colors_chart,
            text=[f'J${val:,.0f}' for val in totals],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Total Savings: J$%{y:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f'Total Savings by Round-Up Method ({period_type})',
            xaxis_title='Round-Up Amount',
            yaxis_title='Total Savings (J$)',
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("##### 💡 Smart Insights")
        
        best_option = max(savings_results.items(), key=lambda x: x[1]['total'])
        
        st.markdown(f"""
            <div style='background: #f0fdf4; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 1rem;'>
                <div style='font-weight: 600; color: #065f46; margin-bottom: 0.5rem;'>
                    🎯 Best Option
                </div>
                <div style='color: #047857;'>
                    Rounding to <strong>{best_option[0]}</strong> saves the most: 
                    <strong>J${best_option[1]['total']:,.0f}</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Monthly projections
        st.markdown("**Monthly Avg Savings:**")
        for label, results in savings_results.items():
            st.caption(f"• {label}: J${results['monthly_avg']:,.0f}/month")
        
        # Yearly projection
        st.markdown("---")
        st.markdown("**Annual Projection:**")
        annual_projection = best_option[1]['total'] * (12 / len(selected_months))
        st.metric(
            "Potential Yearly Savings",
            f"J${annual_projection:,.0f}",
            help=f"Based on {best_option[0]} round-up"
        )
    
    # ==========================================
    # SAVINGS GOALS VISUALIZATION
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🎯 What Could You Achieve?")
    st.caption("See how your savings could help you reach these common financial goals")
    
    # Use best option for goals calculation
    best_savings = best_option[1]['total']
    
    goals = [
        {"name": "Emergency Fund", "amount": 50000, "icon": "🏥"},
        {"name": "Vacation", "amount": 100000, "icon": "✈️"},
        {"name": "New Phone", "amount": 150000, "icon": "📱"},
        {"name": "Down Payment", "amount": 500000, "icon": "🏠"}
    ]
    
    cols = st.columns(4)
    
    for idx, goal in enumerate(goals):
        with cols[idx]:
            percentage = min((best_savings / goal['amount']) * 100, 100)
            months_needed = max(1, math.ceil((goal['amount'] - best_savings) / (best_savings / len(selected_months)))) if best_savings > 0 else 0
            
            color = '#10b981' if percentage >= 100 else '#3b82f6'
            
            st.markdown(f"""
                <div style='background: white; padding: 1rem; border-radius: 12px; border: 2px solid {color}; text-align: center;'>
                    <div style='font-size: 2rem; margin-bottom: 0.5rem;'>{goal['icon']}</div>
                    <div style='font-weight: 600; color: #111827; margin-bottom: 0.5rem;'>{goal['name']}</div>
                    <div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem;'>
                        Goal: J${goal['amount']:,}
                    </div>
                    <div style='background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 0.5rem;'>
                        <div style='background: {color}; height: 100%; width: {percentage:.0f}%;'></div>
                    </div>
                    <div style='font-size: 0.8rem; font-weight: 600; color: {color};'>
                        {percentage:.0f}% Complete
                    </div>
                    {f"<div style='font-size: 0.75rem; color: #6b7280; margin-top: 0.25rem;'>{months_needed} months to go</div>" if percentage < 100 else "<div style='font-size: 0.75rem; color: #10b981; margin-top: 0.25rem;'>✓ Goal Reached!</div>"}
                </div>
            """, unsafe_allow_html=True)
    
    # ==========================================
    # SELECT ROUND-UP FOR DETAILED ANALYSIS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🔍 Detailed Analysis")
    st.caption("Select a round-up method to see detailed breakdown")
    
    selected_roundup = st.selectbox(
        "Choose round-up method for detailed view",
        list(roundup_options.keys()),
        key="detail_roundup"
    )
    
    round_to = roundup_options[selected_roundup]
    
    # Calculate for selected round-up
    spending_data['Roundup_Savings'] = spending_data['Amount'].apply(
        lambda x: calculate_roundup_savings(x, round_to)
    )
    
    total_savings = spending_data['Roundup_Savings'].sum()
    total_transactions = len(spending_data)
    avg_savings_per_transaction = total_savings / total_transactions if total_transactions > 0 else 0
    
    # Monthly breakdown
    monthly_savings = []
    for month in selected_months:
        month_data = spending_data[spending_data['Month'] == month]
        month_savings = month_data['Roundup_Savings'].sum()
        month_transactions = len(month_data)
        
        monthly_savings.append({
            'Month': calendar.month_name[month],
            'Month_Num': month,
            'Savings': month_savings,
            'Transactions': month_transactions
        })
    
    monthly_df = pd.DataFrame(monthly_savings)
    
    # ==========================================
    # MONTHLY SAVINGS CHART
    # ==========================================
    st.markdown("##### 📈 Monthly Savings Breakdown")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_df['Month'],
        y=monthly_df['Savings'],
        mode='lines+markers',
        name='Monthly Savings',
        line=dict(color='#667eea', width=3),
        marker=dict(size=10, color='#667eea'),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)',
        hovertemplate='<b>%{x}</b><br>Savings: J$%{y:,.0f}<extra></extra>'
    ))
    
    monthly_avg = total_savings / len(selected_months) if selected_months else 0
    
    fig.add_hline(
        y=monthly_avg,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Average: J${monthly_avg:,.0f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=f'Monthly Savings Trend - {selected_roundup} Round-Up',
        xaxis_title='Month',
        yaxis_title='Savings (J$)',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # SAVINGS DISTRIBUTION
    # ==========================================
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 💳 Savings by Category")
        
        if 'Spending Category' in spending_data.columns:
            category_savings = spending_data.groupby('Spending Category')['Roundup_Savings'].sum().reset_index()
            category_savings = category_savings.sort_values('Roundup_Savings', ascending=False)
            
            fig = px.pie(
                category_savings,
                values='Roundup_Savings',
                names='Spending Category',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Savings: J$%{value:,.0f}<br>%{percent}<extra></extra>'
            )
            
            fig.update_layout(
                height=350,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Category information not available")
    
    with col2:
        st.markdown("##### 📊 Savings Distribution")
        
        # Create bins for savings amounts
        spending_data['Savings_Bin'] = pd.cut(
            spending_data['Roundup_Savings'],
            bins=[0, 1, 10, 50, 100, float('inf')],
            labels=['J$0-1', 'J$1-10', 'J$10-50', 'J$50-100', 'J$100+']
        )
        
        bin_counts = spending_data['Savings_Bin'].value_counts().reset_index()
        bin_counts.columns = ['Savings_Range', 'Count']
        
        fig = px.bar(
            bin_counts,
            x='Savings_Range',
            y='Count',
            color='Count',
            color_continuous_scale='Greens',
            text='Count'
        )
        
        fig.update_traces(
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Transactions: %{y}<extra></extra>'
        )
        
        fig.update_layout(
            title='How much each transaction would save',
            xaxis_title='Round-up Amount',
            yaxis_title='Number of Transactions',
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # EXAMPLE TRANSACTIONS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 💳 Example Round-Ups")
    st.caption(f"See how {selected_roundup} round-up works on your actual transactions")
    
    # Show sample transactions
    sample_transactions = spending_data.nlargest(10, 'Amount')[['Date', 'Description', 'Amount', 'Roundup_Savings']].copy()
    sample_transactions['Rounded_Amount'] = sample_transactions['Amount'] + sample_transactions['Roundup_Savings']
    
    for idx, row in sample_transactions.iterrows():
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        
        with col1:
            st.caption(f"📅 {row['Date'].strftime('%Y-%m-%d')}")
        
        with col2:
            st.caption(f"🏪 {row['Description'][:30]}")
        
        with col3:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='font-size: 0.75rem; color: #6b7280;'>Original</div>
                    <div style='font-weight: 600;'>J${row['Amount']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='font-size: 0.75rem; color: #6b7280;'>Rounded + Saved</div>
                    <div style='font-weight: 600; color: #10b981;'>
                        J${row['Rounded_Amount']:,.2f}
                        <span style='font-size: 0.8rem; color: #059669;'>(+J${row['Roundup_Savings']:,.2f})</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
