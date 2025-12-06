# pages/spending_analysis.py
"""
Spending Analysis page - enhanced with multiple analysis periods and cash flow
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_all_user_data, clear_data_cache
from database import (
    save_user_file, 
    delete_user_file, 
    get_user_files_paginated,
    get_user_preferences
)
from utils import (
    calculate_monthly_stats,
    get_spending_by_category,
    export_to_excel,
    compare_budget_vs_actual
)
from config import FILES_PER_PAGE
import json
from datetime import datetime


def format_month_display(year_month):
    """Convert YYYY-MM to 'Month Year' format"""
    try:
        date_obj = datetime.strptime(year_month, '%Y-%m')
        return date_obj.strftime('%B %Y')  # e.g., "January 2024"
    except:
        return year_month


def spending_analysis_page():
    """Main spending analysis page with flowing layout"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 📊 Spending Analysis")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    
    st.markdown("---")
    
    # FILE UPLOAD SECTION
    st.markdown("#### 📁 Upload Bank Statements")
    st.info("💡 Upload CSV or PDF bank statements to analyze your spending")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['csv', 'pdf'],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded_files:
        if st.button("📤 Upload Files", type="primary"):
            success_count = 0
            error_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, file in enumerate(uploaded_files):
                status_text.text(f"Uploading {file.name}...")
                
                file_bytes = file.read()
                file_type = file.name.split('.')[-1].lower()
                
                if save_user_file(
                    st.session_state.user['id'],
                    file.name,
                    file_bytes,
                    file_type
                ):
                    success_count += 1
                else:
                    error_count += 1
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            progress_bar.empty()
            status_text.empty()
            
            if success_count > 0:
                st.success(f"✅ Successfully uploaded {success_count} file(s)")
                clear_data_cache()
                st.rerun()
            
            if error_count > 0:
                st.error(f"❌ Failed to upload {error_count} file(s)")
    
    # YOUR FILES SECTION
    st.markdown("---")
    st.markdown("#### 📂 Your Uploaded Files")
    
    if 'file_page' not in st.session_state:
        st.session_state.file_page = 0
    
    files, total_files = get_user_files_paginated(
        st.session_state.user['id'],
        st.session_state.file_page,
        FILES_PER_PAGE
    )
    
    if total_files == 0:
        st.info("📂 No files uploaded yet. Upload your first bank statement above!")
    else:
        st.write(f"**Total files:** {total_files}")
        
        # Display files in a grid
        cols = st.columns(3)
        for idx, file in enumerate(files):
            col = cols[idx % 3]
            with col:
                display_file_card(file)
        
        # Pagination controls
        if total_files > FILES_PER_PAGE:
            display_pagination_controls(total_files, FILES_PER_PAGE)
    
    # DATA VISUALIZATION SECTION
    st.markdown("---")
    st.markdown("#### 📈 Spending Visualizations")
    
    # Load data
    with st.spinner("Loading your data..."):
        data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No data available yet. Upload files above to see your spending analysis.")
    else:
        # ANALYSIS PERIOD SELECTOR
        st.markdown("##### 📅 Select Analysis Period")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            analysis_type = st.selectbox(
                "Period Type",
                ["Specific Months", "Last 3 Months", "Last 6 Months", "All Time"],
                key="analysis_type"
            )
        
        # Get available months (YYYY-MM format for internal use)
        available_months_raw = sorted(data['YearMonth'].unique(), reverse=True)
        
        # Create display mapping
        month_display_map = {month: format_month_display(month) for month in available_months_raw}
        month_options = [month_display_map[m] for m in available_months_raw]
        
        # Determine selected months based on analysis type
        if analysis_type == "Specific Months":
            with col2:
                selected_display = st.multiselect(
                    "Select Months",
                    month_options,
                    default=[month_options[0]] if month_options else [],
                    key="selected_months"
                )
            if not selected_display:
                st.warning("Please select at least one month")
                st.markdown("</div>", unsafe_allow_html=True)
                return
            
            # Convert back to YYYY-MM format for filtering
            reverse_map = {v: k for k, v in month_display_map.items()}
            selected_months = [reverse_map[d] for d in selected_display]
        elif analysis_type == "Last 3 Months":
            selected_months = available_months_raw[:3]
            selected_display = [month_display_map[m] for m in selected_months]
        elif analysis_type == "Last 6 Months":
            selected_months = available_months_raw[:6]
            selected_display = [month_display_map[m] for m in selected_months]
        else:  # All Time
            selected_months = available_months_raw
            selected_display = [month_display_map[m] for m in selected_months]
        
        # Filter data for selected period
        period_data = data[data['YearMonth'].isin(selected_months)]
        
        if period_data.empty:
            st.warning("No data available for selected period")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        
        st.info(f"📊 Analyzing {len(selected_months)} month(s): {', '.join(selected_display)}")
        
        # MONTHLY CASH FLOW CHART
        st.markdown("---")
        st.markdown("##### 💰 Monthly Cash Flow")
        
        cash_flow_data = []
        for month in sorted(selected_months):
            stats = calculate_monthly_stats(data, month)
            cash_flow_data.append({
                'Month': format_month_display(month),
                'MonthRaw': month,
                'Income': stats['income'],
                'Spending': stats['spending'],
                'Savings': stats['savings']
            })
        
        cash_flow_df = pd.DataFrame(cash_flow_data)
        
        if not cash_flow_df.empty:
            fig_cashflow = go.Figure()
            
            fig_cashflow.add_trace(go.Bar(
                x=cash_flow_df['Month'],
                y=cash_flow_df['Income'],
                name='Income',
                marker_color='#10b981'
            ))
            
            fig_cashflow.add_trace(go.Bar(
                x=cash_flow_df['Month'],
                y=cash_flow_df['Spending'],
                name='Spending',
                marker_color='#ef4444'
            ))
            
            fig_cashflow.add_trace(go.Scatter(
                x=cash_flow_df['Month'],
                y=cash_flow_df['Savings'],
                name='Net Savings',
                mode='lines+markers',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8)
            ))
            
            fig_cashflow.update_layout(
                title='Monthly Cash Flow Trend',
                xaxis_title='Month',
                yaxis_title='Amount (J$)',
                barmode='group',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_cashflow, use_container_width=True)
        
        # MONTHLY ANALYSIS TABS
        st.markdown("---")
        st.markdown("##### 📅 Monthly Analysis")
        
        # Create tabs for each selected month with formatted names
        if len(selected_months) > 0:
            sorted_months = sorted(selected_months, reverse=True)
            tab_labels = [f"📊 {format_month_display(month)}" for month in sorted_months]
            tabs = st.tabs(tab_labels)
            
            for idx, month in enumerate(sorted_months):
                with tabs[idx]:
                    render_monthly_analysis(data, month)
        
        # AGGREGATE ANALYSIS FOR PERIOD
        if len(selected_months) > 1:
            st.markdown("---")
            st.markdown("##### 📊 Aggregate Analysis")
            
            # Calculate totals
            total_income = sum([calculate_monthly_stats(data, m)['income'] for m in selected_months])
            total_spending = sum([calculate_monthly_stats(data, m)['spending'] for m in selected_months])
            total_savings = total_income - total_spending
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Total Income", f"J${total_income:,.0f}")
            with col2:
                st.metric("💸 Total Spending", f"J${total_spending:,.0f}")
            with col3:
                st.metric("🎯 Total Savings", f"J${total_savings:,.0f}")
            
            # Aggregate category spending
            st.markdown("##### 🥧 Aggregate Spending by Category")
            
            all_spending = []
            for month in selected_months:
                month_summary = get_spending_by_category(data, month)
                if not month_summary.empty:
                    all_spending.append(month_summary)
            
            if all_spending:
                aggregate_spending = pd.concat(all_spending).groupby('Spending Category')['Amount'].sum().reset_index()
                aggregate_spending['Percentage'] = 100 * aggregate_spending['Amount'] / aggregate_spending['Amount'].sum()
                aggregate_spending = aggregate_spending.sort_values('Amount', ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_agg_pie = px.pie(
                        aggregate_spending,
                        values='Amount',
                        names='Spending Category',
                        hole=0.4,
                        title='Total Spending Distribution'
                    )
                    st.plotly_chart(fig_agg_pie, use_container_width=True)
                
                with col2:
                    fig_agg_bar = px.bar(
                        aggregate_spending,
                        x='Spending Category',
                        y='Amount',
                        color='Amount',
                        color_continuous_scale='Reds',
                        title='Category Breakdown'
                    )
                    fig_agg_bar.update_layout(showlegend=False, xaxis_tickangle=-45)
                    st.plotly_chart(fig_agg_bar, use_container_width=True)
        
        # EXPORT OPTIONS
        st.markdown("---")
        st.markdown("#### 📥 Export Data")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            excel_data = export_to_excel(period_data)
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"transactions_{analysis_type.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            csv_data = period_data.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"transactions_{analysis_type.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_monthly_analysis(data, selected_month):
    """Render detailed analysis for a specific month"""
    month_data = data[data['YearMonth'] == selected_month]
    month_display = format_month_display(selected_month)
    
    if month_data.empty:
        st.warning("No data for this month")
        return
    
    # Calculate statistics
    stats = calculate_monthly_stats(data, selected_month)
    summary = get_spending_by_category(data, selected_month)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Income", f"J${stats['income']:,.0f}")
    
    with col2:
        st.metric("💸 Spending", f"J${stats['spending']:,.0f}")
    
    with col3:
        st.metric("🎯 Savings", f"J${stats['savings']:,.0f}")
    
    # Visualizations
    if not summary.empty:
        st.markdown(f"##### 📈 Spending Breakdown for {month_display}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                summary,
                values='Amount',
                names='Spending Category',
                hole=0.4,
                title='Distribution'
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            fig_bar = px.bar(
                summary,
                x='Spending Category',
                y='Amount',
                color='Amount',
                color_continuous_scale='Blues',
                title='Category Amounts'
            )
            fig_bar.update_layout(
                height=350,
                showlegend=False,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Budget comparison
        prefs = get_user_preferences(st.session_state.user['id'])
        if prefs and prefs.get('monthly_budgets'):
            budgets = json.loads(prefs['monthly_budgets'])
            comparison = compare_budget_vs_actual(budgets, summary)
            
            if not comparison.empty:
                st.markdown(f"##### 📏 Budget vs. Actual - {month_display}")
                
                fig_comparison = go.Figure()
                
                fig_comparison.add_trace(go.Bar(
                    name='Budget',
                    x=comparison['Spending Category'],
                    y=comparison['Budget'],
                    marker_color='#3b82f6'
                ))
                
                fig_comparison.add_trace(go.Bar(
                    name='Actual',
                    x=comparison['Spending Category'],
                    y=comparison['Amount'],
                    marker_color='#ef4444'
                ))
                
                fig_comparison.update_layout(
                    barmode='group',
                    height=400,
                    xaxis_tickangle=-45,
                    yaxis_title='Amount (J$)'
                )
                
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                # Show over-budget categories
                over_budget = comparison[comparison['Amount'] > comparison['Budget']]
                if not over_budget.empty:
                    st.warning(f"⚠️ Over budget in {len(over_budget)} categories")
                    for _, row in over_budget.iterrows():
                        st.caption(
                            f"**{row['Spending Category']}**: "
                            f"J${row['Amount']:,.0f} / J${row['Budget']:,.0f} "
                            f"(+J${row['Amount'] - row['Budget']:,.0f})"
                        )
        
        # Spending table
        st.markdown("##### 📋 Detailed Breakdown")
        summary_display = summary.copy()
        summary_display['Amount'] = summary_display['Amount'].apply(lambda x: f"J${x:,.2f}")
        summary_display['Percentage'] = summary_display['Percentage'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(summary_display, use_container_width=True, hide_index=True)


def display_file_card(file):
    """Display a file card with delete button"""
    file_icon = "📄" if file['file_type'] == 'pdf' else "📊"
    
    st.markdown(f"""
        <div class="file-card">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">{file_icon}</div>
            <div style="font-weight: 600; margin-bottom: 0.25rem;">{file['filename']}</div>
            <div style="font-size: 0.75rem; color: #6b7280;">
                {file['upload_date'].strftime('%Y-%m-%d')}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Delete", key=f"del_{file['id']}", use_container_width=True):
        if delete_user_file(file['id'], st.session_state.user['id']):
            st.success("✅ File deleted")
            clear_data_cache()
            st.rerun()
        else:
            st.error("❌ Failed to delete file")


def display_pagination_controls(total_files, page_size):
    """Display pagination controls"""
    total_pages = (total_files + page_size - 1) // page_size
    current_page = st.session_state.file_page
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ First", disabled=(current_page == 0)):
            st.session_state.file_page = 0
            st.rerun()
    
    with col2:
        if st.button("◀️ Prev", disabled=(current_page == 0)):
            st.session_state.file_page = current_page - 1
            st.rerun()
    
    with col3:
        st.markdown(f"<div style='text-align: center; padding: 0.5rem;'>Page {current_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
    
    with col4:
        if st.button("Next ▶️", disabled=(current_page >= total_pages - 1)):
            st.session_state.file_page = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("Last ⏭️", disabled=(current_page >= total_pages - 1)):
            st.session_state.file_page = total_pages - 1
            st.rerun()
