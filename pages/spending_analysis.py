# pages/spending_analysis.py
"""
Spending Analysis page - enhanced with editable categories and improved charts
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
    get_user_preferences,
    save_user_preferences
)
from utils import (
    calculate_monthly_stats,
    get_spending_by_category,
    export_to_excel,
    compare_budget_vs_actual
)
from config import FILES_PER_PAGE, DEFAULT_CATEGORY_MAPPING, DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
import json
from datetime import datetime
import calendar


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
    
    # CATEGORY CUSTOMIZATION SECTION
    st.markdown("---")
    render_category_editor()
    
    # DATA VISUALIZATION SECTION
    st.markdown("---")
    st.markdown("#### 📈 Spending Visualizations")
    
    # Load data
    with st.spinner("Loading your data..."):
        data = load_all_user_data(st.session_state.user['id'])
        
        if data.empty:
            st.warning("📊 No data available yet. Upload files above to see your spending analysis.")
        else:
            # ✅ ADD YEAR AND MONTH COLUMNS (like Test3.py does)
            if 'Year' not in data.columns and 'Date' in data.columns:
                data['Year'] = pd.to_datetime(data['Date']).dt.year
                if 'Month' not in data.columns and 'Date' in data.columns:
                    data['Month'] = pd.to_datetime(data['Date']).dt.month
                    #st.success(f"✅ Loaded {len(data)} transactions from {len(data['YearMonth'].unique())} months")
                    render_analysis_section(data)
    
    st.markdown("</div>", unsafe_allow_html=True)




def render_category_editor():
    """Render category keyword editor"""
    with st.expander("🏷️ Customize Spending Categories", expanded=False):
        st.markdown("**Edit keywords to customize how transactions are categorized**")
        st.caption("Add keywords separated by commas. Transactions matching these keywords will be assigned to the category.")
        
        # Load current preferences
        prefs = get_user_preferences(st.session_state.user['id'])
        if prefs and prefs.get('category_keywords'):
            current_keywords = json.loads(prefs['category_keywords'])
        else:
            current_keywords = DEFAULT_CATEGORY_MAPPING.copy()
        
        # Create editable fields for each category
        updated_keywords = {}
        
        col1, col2 = st.columns(2)
        
        categories = list(DEFAULT_CATEGORY_MAPPING.keys())
        mid_point = len(categories) // 2
        
        with col1:
            for category in categories[:mid_point]:
                if category == 'Other':
                    continue
                keywords_str = ', '.join(current_keywords.get(category, []))
                new_keywords = st.text_area(
                    f"**{category}**",
                    value=keywords_str,
                    height=80,
                    key=f"cat_{category}",
                    help=f"Keywords for {category} category"
                )
                updated_keywords[category] = [k.strip() for k in new_keywords.split(',') if k.strip()]
        
        with col2:
            for category in categories[mid_point:]:
                if category == 'Other':
                    continue
                keywords_str = ', '.join(current_keywords.get(category, []))
                new_keywords = st.text_area(
                    f"**{category}**",
                    value=keywords_str,
                    height=80,
                    key=f"cat_{category}",
                    help=f"Keywords for {category} category"
                )
                updated_keywords[category] = [k.strip() for k in new_keywords.split(',') if k.strip()]
        
        updated_keywords['Other'] = []  # Other is always empty
        
        # Save button
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save Categories", use_container_width=True):
                # Get current budgets and savings goal
                budgets = json.loads(prefs['monthly_budgets']) if prefs and prefs.get('monthly_budgets') else DEFAULT_BUDGETS
                savings_goal = prefs.get('savings_goal', DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
                
                if save_user_preferences(
                    st.session_state.user['id'],
                    updated_keywords,
                    budgets,
                    savings_goal
                ):
                    st.success("✅ Categories saved! Refreshing data...")
                    clear_data_cache()
                    st.rerun()
                else:
                    st.error("❌ Failed to save")
        
        with col2:
            if st.button("🔄 Reset to Defaults", use_container_width=True):
                budgets = json.loads(prefs['monthly_budgets']) if prefs and prefs.get('monthly_budgets') else DEFAULT_BUDGETS
                savings_goal = prefs.get('savings_goal', DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
                
                if save_user_preferences(
                    st.session_state.user['id'],
                    DEFAULT_CATEGORY_MAPPING,
                    budgets,
                    savings_goal
                ):
                    st.success("✅ Reset to defaults!")
                    clear_data_cache()
                    st.rerun()


def render_analysis_section(data):
    """Render the main analysis section"""
    # SMART MONTH/YEAR SELECTOR
    st.markdown("##### 📅 Select Analysis Period")
    
    # Make sure we have the required columns
    if 'Year' not in data.columns:
        data['Year'] = pd.to_datetime(data['Date']).dt.year
    if 'Month' not in data.columns:
        data['Month'] = pd.to_datetime(data['Date']).dt.month
    
    # Extract years from data
    available_years = sorted(data['Year'].unique())
    
    if not available_years:
        st.error("No valid years found in data")
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        analysis_type = st.selectbox(
            "Period Type",
            ["Specific Months", "Last 3 Months", "Last 6 Months", "All Time"],
            key="analysis_type"
        )
    
    with col2:
        # Year selector (only if multiple years)
        if len(available_years) > 1:
            selected_year = st.selectbox(
                "Select Year",
                available_years,
                index=len(available_years) - 1,  # Default to most recent year
                key="selected_year"
            )
        else:
            selected_year = available_years[0]
            st.info(f"📅 Showing data for {selected_year}")
    
    # Month names
    month_names = [calendar.month_name[i] for i in range(1, 13)]
    
    # Get available months for selected year
    year_data = data[data['Year'] == selected_year]
    available_months_nums = sorted(year_data['Month'].unique())
    
    if not available_months_nums:
        st.warning(f"No data available for year {selected_year}")
        return
    
    available_month_names = [calendar.month_name[m] for m in available_months_nums]
    
    # Determine selected months based on analysis type
    if analysis_type == "Specific Months":
        with col3:
            selected_month_names = st.multiselect(
                "Select Months",
                available_month_names,
                default=[available_month_names[-1]] if available_month_names else [],
                key="selected_months_multi"
            )
        
        if not selected_month_names:
            st.warning("Please select at least one month")
            return
        
        # Convert back to month numbers
        selected_months = [month_names.index(name) + 1 for name in selected_month_names]
    
    elif analysis_type == "Last 3 Months":
        selected_months = available_months_nums[-3:] if len(available_months_nums) >= 3 else available_months_nums
        selected_month_names = [calendar.month_name[m] for m in selected_months]
    
    elif analysis_type == "Last 6 Months":
        selected_months = available_months_nums[-6:] if len(available_months_nums) >= 6 else available_months_nums
        selected_month_names = [calendar.month_name[m] for m in selected_months]
    
    else:  # All Time
        selected_months = available_months_nums
        selected_month_names = [calendar.month_name[m] for m in selected_months]
    
    # Filter data
    period_data = data[(data['Year'] == selected_year) & (data['Month'].isin(selected_months))]
    
    if period_data.empty:
        st.warning("No data available for selected period")
        return
    
    #st.success(f"📊 Analyzing {len(selected_months)} month(s): {', '.join(selected_month_names)} in {selected_year}")
    #st.info(f"Total transactions: {len(period_data)}")
    
    # CASH FLOW CHARTS
    st.markdown("---")
    render_cash_flow_charts(data, selected_year, selected_months)
    
    # MONTHLY ANALYSIS TABS
    st.markdown("---")
    st.markdown("##### 📅 Monthly Analysis")
    
    if len(selected_months) > 0:
        tabs = st.tabs([f"📊 {calendar.month_name[m]}" for m in sorted(selected_months)])
        
        for idx, month_num in enumerate(sorted(selected_months)):
            with tabs[idx]:
                year_month = f"{selected_year}-{month_num:02d}"
                render_monthly_analysis(data, year_month, calendar.month_name[month_num])
    
    # AGGREGATE ANALYSIS
    if len(selected_months) > 1:
        st.markdown("---")
        render_aggregate_analysis(data, selected_year, selected_months)
    
    # EXPORT OPTIONS
    st.markdown("---")
    st.markdown("#### 📥 Export Data")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        excel_data = export_to_excel(period_data)
        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name=f"transactions_{selected_year}_{analysis_type.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        csv_data = period_data.to_csv(index=False)
        st.download_button(
            label="📄 Download CSV",
            data=csv_data,
            file_name=f"transactions_{selected_year}_{analysis_type.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )

def render_cash_flow_charts(data, selected_year, selected_months):
    """Render separate income/spending and net cash flow charts"""
    st.markdown("##### 💰 Financial Overview")
    
    # Prepare data
    cash_flow_data = []
    for month_num in sorted(selected_months):
        year_month = f"{selected_year}-{month_num:02d}"
        stats = calculate_monthly_stats(data, year_month)
        cash_flow_data.append({
            'Month': calendar.month_name[month_num],
            'Income': stats['income'],
            'Spending': stats['spending'],
            'Savings': stats['savings']
        })
    
    cash_flow_df = pd.DataFrame(cash_flow_data)
    
    if cash_flow_df.empty:
        return
    
    col1, col2 = st.columns(2)
    
    # Chart 1: Income vs Spending (Bar Chart)
    with col1:
        st.markdown("**💵 Income vs Spending**")
        
        fig_bars = go.Figure()
        
        fig_bars.add_trace(go.Bar(
            name='Income',
            x=cash_flow_df['Month'],
            y=cash_flow_df['Income'],
            marker_color='#10b981',
            text=cash_flow_df['Income'].apply(lambda x: f'J${x:,.0f}'),
            textposition='outside'
        ))
        
        fig_bars.add_trace(go.Bar(
            name='Spending',
            x=cash_flow_df['Month'],
            y=cash_flow_df['Spending'],
            marker_color='#ef4444',
            text=cash_flow_df['Spending'].apply(lambda x: f'J${x:,.0f}'),
            textposition='outside'
        ))
        
        fig_bars.update_layout(
            barmode='group',
            height=400,
            yaxis_title='Amount (J$)',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_bars, use_container_width=True)
    
    # Chart 2: Net Cash Flow (Line Chart)
    with col2:
        st.markdown("**📈 Net Cash Flow**")
        
        fig_line = go.Figure()
        
        # Add zero line
        fig_line.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add savings line
        colors = ['#10b981' if x >= 0 else '#ef4444' for x in cash_flow_df['Savings']]
        
        fig_line.add_trace(go.Scatter(
            x=cash_flow_df['Month'],
            y=cash_flow_df['Savings'],
            mode='lines+markers',
            name='Net Savings',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=10, color=colors, line=dict(color='white', width=2)),
            text=cash_flow_df['Savings'].apply(lambda x: f'J${x:,.0f}'),
            textposition='top center',
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)'
        ))
        
        fig_line.update_layout(
            height=400,
            yaxis_title='Net Savings (J$)',
            showlegend=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_line, use_container_width=True)


def render_monthly_analysis(data, year_month, month_name):
    """Render detailed analysis for a specific month"""
    month_data = data[data['YearMonth'] == year_month]
    
    if month_data.empty:
        st.warning("No data for this month")
        return
    
    # Calculate statistics
    stats = calculate_monthly_stats(data, year_month)
    summary = get_spending_by_category(data, year_month)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Income", f"J${stats['income']:,.0f}")
    
    with col2:
        st.metric("💸 Spending", f"J${stats['spending']:,.0f}")
    
    with col3:
        savings_delta = "positive" if stats['savings'] >= 0 else "negative"
        st.metric("🎯 Savings", f"J${stats['savings']:,.0f}")
    
    # Visualizations
    if not summary.empty:
        st.markdown(f"##### 📈 Spending Breakdown for {month_name}")
        
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
                st.markdown(f"##### 📏 Budget vs. Actual - {month_name}")
                
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


def render_aggregate_analysis(data, selected_year, selected_months):
    """Render aggregate analysis for multiple months"""
    st.markdown("##### 📊 Aggregate Analysis")
    
    # Calculate totals
    year_months = [f"{selected_year}-{m:02d}" for m in selected_months]
    total_income = sum([calculate_monthly_stats(data, ym)['income'] for ym in year_months])
    total_spending = sum([calculate_monthly_stats(data, ym)['spending'] for ym in year_months])
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
    for ym in year_months:
        month_summary = get_spending_by_category(data, ym)
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
