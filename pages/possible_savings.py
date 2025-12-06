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


def calculate_roundup_savings(amount, round_to):
    """Calculate how much would be saved by rounding up to nearest value"""
    import math
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
    # ROUND-UP SETTINGS
    # ==========================================
    st.markdown("#### ⚙️ Round-Up Settings")
    st.info("💡 Auto-save by rounding up each purchase to the nearest dollar amount. The difference goes to savings!")
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        st.markdown("##### 🎯 Select Round-Up Amount")
        round_up_options = {
            "Round to nearest J$1": 1,
            "Round to nearest J$10": 10,
            "Round to nearest J$100": 100,
            "Round to nearest J$1,000": 1000
        }
        
        selected_roundup = st.radio(
            "Choose your round-up level",
            options=list(round_up_options.keys()),
            key="roundup_selection",
            help="Higher round-ups = faster savings, but larger impact per transaction"
        )
        
        round_to = round_up_options[selected_roundup]
    
    with col2:
        st.markdown("##### 📅 Analysis Period")
        available_years = sorted(data['Year'].unique(), reverse=True)
        
        selected_year = st.selectbox(
            "Year",
            available_years,
            key="savings_year"
        )
        
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
    
    # ==========================================
    # CALCULATE SAVINGS
    # ==========================================
    st.markdown("---")
    
    # Calculate round-up for each transaction
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
    # SAVINGS SUMMARY
    # ==========================================
    st.markdown("#### 💎 Your Potential Savings")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Total Savings</div>
                <div style='font-size: 2rem; font-weight: 700;'>J${total_savings:,.0f}</div>
                <div style='font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;'>Over {len(selected_months)} month(s)</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        monthly_avg = total_savings / len(selected_months) if selected_months else 0
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Monthly Average</div>
                <div style='font-size: 2rem; font-weight: 700;'>J${monthly_avg:,.0f}</div>
                <div style='font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;'>Per month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Per Transaction</div>
                <div style='font-size: 2rem; font-weight: 700;'>J${avg_savings_per_transaction:,.2f}</div>
                <div style='font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;'>Average round-up</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        yearly_projection = monthly_avg * 12
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Yearly Projection</div>
                <div style='font-size: 2rem; font-weight: 700;'>J${yearly_projection:,.0f}</div>
                <div style='font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;'>Estimated annual</div>
            </div>
        """, unsafe_allow_html=True)
    
    # ==========================================
    # MONTHLY SAVINGS CHART
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📈 Monthly Savings Breakdown")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=monthly_df['Month'],
        y=monthly_df['Savings'],
        text=monthly_df['Savings'].apply(lambda x: f'J${x:,.0f}'),
        textposition='outside',
        marker_color='#10b981',
        name='Round-up Savings',
        hovertemplate='<b>%{x}</b><br>Savings: J$%{y:,.0f}<br><extra></extra>'
    ))
    
    # Add average line
    fig.add_hline(
        y=monthly_avg,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Average: J${monthly_avg:,.0f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=f'Round-up Savings by Month ({selected_roundup})',
        xaxis_title='Month',
        yaxis_title='Savings (J$)',
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # SAVINGS DISTRIBUTION
    # ==========================================
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💳 Savings by Category")
        
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
    
    with col2:
        st.markdown("#### 📊 Savings Distribution")
        
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
    # TOP SAVINGS TRANSACTIONS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🏆 Top Savings Opportunities")
    st.caption("Transactions that would have saved you the most with round-up")
    
    top_savings = spending_data.nlargest(10, 'Roundup_Savings')[
        ['Date', 'Description', 'Amount', 'Roundup_Savings', 'Spending Category']
    ]
    
    for idx, row in top_savings.iterrows():
        original = row['Amount']
        rounded = original + row['Roundup_Savings']
        
        st.markdown(f"""
            <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #10b981;'>
                <div style='display: flex; justify-content: space-between; align-items: start;'>
                    <div style='flex: 1;'>
                        <div style='font-weight: 600; color: #111827; margin-bottom: 0.25rem;'>
                            {row['Description'][:50]}
                        </div>
                        <div style='font-size: 0.85rem; color: #6b7280;'>
                            {row['Date'].strftime('%Y-%m-%d')} • {row['Spending Category']}
                        </div>
                    </div>
                    <div style='text-align: right; margin-left: 1rem;'>
                        <div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.25rem;'>
                            J${original:,.2f} → J${rounded:,.2f}
                        </div>
                        <div style='font-size: 1.1rem; font-weight: 700; color: #10b981;'>
                            +J${row['Roundup_Savings']:,.2f}
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # ==========================================
    # COMPARISON WITH OTHER ROUND-UPS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🔄 Compare Round-Up Options")
    st.caption("See how different round-up amounts would affect your savings")
    
    comparison_data = []
    for label, amount in round_up_options.items():
        period_savings = spending_data['Amount'].apply(
            lambda x: calculate_roundup_savings(x, amount)
        ).sum()
        
        comparison_data.append({
            'Round-Up Level': label,
            'Total Savings': period_savings,
            'Monthly Average': period_savings / len(selected_months) if selected_months else 0,
            'Yearly Projection': (period_savings / len(selected_months) * 12) if selected_months else 0
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Total Savings',
        x=comparison_df['Round-Up Level'],
        y=comparison_df['Total Savings'],
        text=comparison_df['Total Savings'].apply(lambda x: f'J${x:,.0f}'),
        textposition='outside',
        marker_color=['#10b981' if row == selected_roundup else '#d1fae5' 
                      for row in comparison_df['Round-Up Level']]
    ))
    
    fig.update_layout(
        title='Savings Comparison Across Round-Up Options',
        xaxis_title='Round-Up Level',
        yaxis_title='Total Savings (J$)',
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Comparison table
    st.markdown("##### 📋 Detailed Comparison")
    
    for idx, row in comparison_df.iterrows():
        is_selected = row['Round-Up Level'] == selected_roundup
        border_color = '#10b981' if is_selected else '#e5e7eb'
        bg_color = '#f0fdf4' if is_selected else 'white'
        
        st.markdown(f"""
            <div style='background: {bg_color}; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border: 2px solid {border_color};'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div style='font-weight: 600; color: #111827;'>
                        {row['Round-Up Level']} {'✓' if is_selected else ''}
                    </div>
                    <div style='display: flex; gap: 2rem;'>
                        <div style='text-align: center;'>
                            <div style='font-size: 0.75rem; color: #6b7280;'>Total</div>
                            <div style='font-weight: 600; color: #111827;'>J${row['Total Savings']:,.0f}</div>
                        </div>
                        <div style='text-align: center;'>
                            <div style='font-size: 0.75rem; color: #6b7280;'>Monthly</div>
                            <div style='font-weight: 600; color: #111827;'>J${row['Monthly Average']:,.0f}</div>
                        </div>
                        <div style='text-align: center;'>
                            <div style='font-size: 0.75rem; color: #6b7280;'>Yearly</div>
                            <div style='font-weight: 600; color: #10b981;'>J${row['Yearly Projection']:,.0f}</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
