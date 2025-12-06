"""
Create pages/network_analysis.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_all_user_data
from utils import calculate_monthly_stats, get_spending_by_category
import calendar
from collections import Counter


def network_analysis_page():
    """Network Analysis - Visualize transaction patterns and relationships"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🌐 Network Analysis")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    
    st.markdown("---")
    
    # Load user data
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No transaction data available")
        st.info("Please upload files in Spending Analysis first to see network visualizations")
        if st.button("Go to Spending Analysis", use_container_width=False):
            st.session_state.selected_feature = 'analysis'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Period selector
    st.markdown("#### 📅 Select Analysis Period")
    
    if 'Year' not in data.columns:
        data['Year'] = pd.to_datetime(data['Date']).dt.year
    if 'Month' not in data.columns:
        data['Month'] = pd.to_datetime(data['Date']).dt.month
    
    available_years = sorted(data['Year'].unique())
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_year = st.selectbox(
            "Year",
            available_years,
            index=len(available_years) - 1 if available_years else 0,
            key="network_year"
        )
    
    with col2:
        period_type = st.selectbox(
            "Period",
            ["Last Month", "Last 3 Months", "Last 6 Months", "All Year"],
            key="network_period"
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
    
    if period_data.empty:
        st.warning("No data available for selected period")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    st.success(f"✅ Analyzing {len(period_data)} transactions across {len(selected_months)} month(s)")
    
    # ==========================================
    # MERCHANT FREQUENCY ANALYSIS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🏪 Top Merchants")
    st.caption("Your most frequented merchants and total spending")
    
    # Get top merchants
    merchant_stats = period_data.groupby('Description').agg({
        'Amount': ['sum', 'count', 'mean']
    }).reset_index()
    merchant_stats.columns = ['Merchant', 'Total_Spent', 'Transactions', 'Avg_Transaction']
    merchant_stats = merchant_stats.sort_values('Total_Spent', ascending=False).head(15)
    
    # Create bubble chart
    fig = px.scatter(
        merchant_stats,
        x='Transactions',
        y='Total_Spent',
        size='Avg_Transaction',
        hover_data=['Merchant', 'Total_Spent', 'Transactions', 'Avg_Transaction'],
        color='Total_Spent',
        color_continuous_scale='Viridis',
        size_max=60,
        title='Merchant Spending Patterns'
    )
    
    fig.update_layout(
        xaxis_title="Number of Transactions",
        yaxis_title="Total Amount Spent (J$)",
        height=500,
        showlegend=False
    )
    
    fig.update_traces(
        textposition='top center',
        hovertemplate='<b>%{customdata[0]}</b><br>' +
                      'Total: J$%{y:,.0f}<br>' +
                      'Transactions: %{x}<br>' +
                      'Avg: J$%{customdata[3]:,.0f}<br>' +
                      '<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Top merchants table
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 💰 Highest Spending")
        top_spending = merchant_stats.head(10)
        for idx, row in top_spending.iterrows():
            st.markdown(f"""
                <div style='background: white; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid #667eea;'>
                    <div style='font-weight: 600; color: #111827;'>{row['Merchant'][:40]}</div>
                    <div style='display: flex; justify-content: space-between; margin-top: 0.25rem;'>
                        <span style='color: #6b7280; font-size: 0.85rem;'>{int(row['Transactions'])} transactions</span>
                        <span style='color: #667eea; font-weight: 600;'>J${row['Total_Spent']:,.0f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("##### 🔁 Most Frequent")
        top_frequent = merchant_stats.sort_values('Transactions', ascending=False).head(10)
        for idx, row in top_frequent.iterrows():
            st.markdown(f"""
                <div style='background: white; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid #10b981;'>
                    <div style='font-weight: 600; color: #111827;'>{row['Merchant'][:40]}</div>
                    <div style='display: flex; justify-content: space-between; margin-top: 0.25rem;'>
                        <span style='color: #10b981; font-weight: 600;'>{int(row['Transactions'])} visits</span>
                        <span style='color: #6b7280; font-size: 0.85rem;'>J${row['Total_Spent']:,.0f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # ==========================================
    # CATEGORY FLOW DIAGRAM
    # ==========================================
    st.markdown("---")
    st.markdown("#### 💸 Spending Flow by Category")
    st.caption("How your money flows through different spending categories")
    
    # Calculate category totals
    category_totals = period_data.groupby('Spending Category')['Amount'].sum().reset_index()
    category_totals = category_totals.sort_values('Amount', ascending=False)
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=category_totals['Spending Category'].tolist() + ["Total Spending"],
            color=['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0']
        ),
        link=dict(
            source=list(range(len(category_totals))),
            target=[len(category_totals)] * len(category_totals),
            value=category_totals['Amount'].tolist(),
            color='rgba(102, 126, 234, 0.3)'
        )
    )])
    
    fig.update_layout(
        title="Money Flow from Categories to Total Spending",
        height=400,
        font=dict(size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # SPENDING HEATMAP
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📊 Spending Heatmap")
    st.caption("Visual representation of spending intensity by category and month")
    
    # Create heatmap data
    heatmap_data = []
    for month in selected_months:
        month_data = period_data[period_data['Month'] == month]
        category_summary = month_data.groupby('Spending Category')['Amount'].sum().reset_index()
        
        for _, row in category_summary.iterrows():
            heatmap_data.append({
                'Month': calendar.month_abbr[month],
                'Category': row['Spending Category'],
                'Amount': row['Amount']
            })
    
    if heatmap_data:
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Pivot for heatmap
        pivot_data = heatmap_df.pivot(index='Category', columns='Month', values='Amount').fillna(0)
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale='Blues',
            text=[[f'J${val:,.0f}' for val in row] for row in pivot_data.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Amount (J$)")
        ))
        
        fig.update_layout(
            title='Spending Intensity by Category and Month',
            xaxis_title='Month',
            yaxis_title='Category',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # TRANSACTION TIMELINE
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📈 Transaction Timeline")
    st.caption("Daily spending patterns over the selected period")
    
    # Group by date
    daily_spending = period_data.groupby(period_data['Date'].dt.date)['Amount'].sum().reset_index()
    daily_spending.columns = ['Date', 'Amount']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_spending['Date'],
        y=daily_spending['Amount'],
        mode='lines+markers',
        name='Daily Spending',
        line=dict(color='#667eea', width=2),
        marker=dict(size=6, color='#667eea'),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)'
    ))
    
    # Add average line
    avg_spending = daily_spending['Amount'].mean()
    fig.add_hline(
        y=avg_spending,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Average: J${avg_spending:,.0f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title='Daily Spending Over Time',
        xaxis_title='Date',
        yaxis_title='Amount (J$)',
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # INSIGHTS & PATTERNS
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🔍 Key Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        most_expensive = period_data.nlargest(1, 'Amount').iloc[0]
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 12px; color: white;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Largest Transaction</div>
                <div style='font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;'>J${most_expensive['Amount']:,.0f}</div>
                <div style='font-size: 0.8rem; opacity: 0.8;'>{most_expensive['Description'][:30]}...</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        unique_merchants = period_data['Description'].nunique()
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 1.5rem; border-radius: 12px; color: white;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Unique Merchants</div>
                <div style='font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;'>{unique_merchants}</div>
                <div style='font-size: 0.8rem; opacity: 0.8;'>Different places visited</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_transaction = period_data['Amount'].mean()
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem; border-radius: 12px; color: white;'>
                <div style='font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;'>Avg Transaction</div>
                <div style='font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;'>J${avg_transaction:,.0f}</div>
                <div style='font-size: 0.8rem; opacity: 0.8;'>Per transaction</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
