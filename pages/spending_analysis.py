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
    save_user_preferences,
    create_connection
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
from io import BytesIO


# DIAGNOSTIC FUNCTION
def file_diagnostic_page():
    """Comprehensive file processing diagnostic"""
    import pdfplumber
    import re
    from data_processing import process_pdf_ncb
    
    st.title("🔍 File Processing Diagnostic Tool")
    st.info("This will show you exactly what's happening with each uploaded file")
    
    connection = create_connection()
    if not connection:
        st.error("Cannot connect to database")
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, filename, file_type, file_data, upload_date 
               FROM user_files 
               WHERE user_id = %s 
               ORDER BY filename""",
            (st.session_state.user['id'],)
        )
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        
        st.success(f"📁 Found {len(files)} files in database")
        
        summary_data = []
        
        for idx, file_info in enumerate(files):
            filename = file_info['filename']
            
            st.markdown("---")
            with st.expander(f"📄 {idx+1}. {filename}", expanded=False):
                try:
                    file_bytes = BytesIO(file_info['file_data'])
                    file_size = len(file_info['file_data'])
                    
                    st.write(f"**File Info:**")
                    st.write(f"- Size: {file_size:,} bytes")
                    st.write(f"- Type: {file_info['file_type']}")
                    
                    file_bytes.seek(0)
                    with pdfplumber.open(file_bytes) as pdf:
                        st.write(f"- Pages: {len(pdf.pages)}")
                        
                        first_page_text = pdf.pages[0].extract_text()
                        lines = first_page_text.split('\n')[:40]
                        
                        st.write("**📄 First 40 lines:**")
                        st.code('\n'.join(f"{i:3d}: {line}" for i, line in enumerate(lines, 1)))
                        
                        st.write("**🔍 Year Detection:**")
                        year_found = None
                        year_patterns = [
                            (r'P\.?O\.?,?\s*\d{2}-\d{2}-(\d{4})', 'P.O. line'),
                            (r'\d{2}/[A-Za-z]{3}/(\d{4})', 'Transaction date'),
                            (r'\b(202[0-9])\b', 'Any 202X'),
                        ]
                        
                        for pattern, desc in year_patterns:
                            matches = re.findall(pattern, first_page_text, re.IGNORECASE)
                            if matches:
                                year_found = matches[0][-1] if isinstance(matches[0], tuple) else matches[0]
                                st.success(f"✅ Found: **{year_found}** ({desc})")
                                break
                        
                        if not year_found:
                            st.error("❌ No year detected!")
                    
                    st.write("**📊 Processing:**")
                    file_bytes.seek(0)
                    df = process_pdf_ncb(file_bytes)
                    
                    if df.empty:
                        st.error("❌ FAILED - 0 transactions")
                        summary_data.append({
                            'Filename': filename,
                            'Status': '❌ FAILED',
                            'Transactions': 0,
                            'Year': year_found or 'None'
                        })
                    else:
                        st.success(f"✅ SUCCESS - {len(df)} transactions")
                        st.write(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
                        st.dataframe(df[['Date', 'Description', 'Amount']].head(5))
                        summary_data.append({
                            'Filename': filename,
                            'Status': '✅ SUCCESS',
                            'Transactions': len(df),
                            'Year': year_found or 'Auto'
                        })
                    
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    summary_data.append({
                        'Filename': filename,
                        'Status': '❌ ERROR',
                        'Transactions': 0,
                        'Year': 'N/A'
                    })
        
        st.markdown("---")
        st.markdown("## 📊 Summary")
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        success_count = len([r for r in summary_data if r['Status'] == '✅ SUCCESS'])
        failed_count = len([r for r in summary_data if r['Status'].startswith('❌')])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Successful", success_count)
        with col2:
            st.metric("❌ Failed", failed_count)
        
    except Exception as e:
        st.error(f"Diagnostic error: {e}")


# HELPER FUNCTIONS
def render_category_editor():
    """Render category keyword editor"""
    with st.expander("🏷️ Customize Spending Categories", expanded=False):
        st.markdown("**Edit keywords to customize how transactions are categorized**")
        st.caption("Add keywords separated by commas. Transactions matching these keywords will be assigned to the category.")
        
        prefs = get_user_preferences(st.session_state.user['id'])
        if prefs and prefs.get('category_keywords'):
            current_keywords = json.loads(prefs['category_keywords'])
        else:
            current_keywords = DEFAULT_CATEGORY_MAPPING.copy()
        
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
        
        updated_keywords['Other'] = []
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save Categories", use_container_width=True):
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


def render_cash_flow_charts(data, selected_year, selected_months):
    """Render cash flow visualization charts"""
    st.markdown("##### 💰 Cash Flow Overview")
    
    period_data = data[(data['Year'] == selected_year) & (data['Month'].isin(selected_months))]
    
    if period_data.empty:
        st.warning("No data available for selected period")
        return
    
    monthly_stats = []
    for month_num in sorted(selected_months):
        year_month = f"{selected_year}-{month_num:02d}"
        stats = calculate_monthly_stats(data, year_month)
        monthly_stats.append({
            'Month': calendar.month_name[month_num],
            'Income': stats['income'],
            'Spending': stats['spending'],
            'Savings': stats['savings']
        })
    
    stats_df = pd.DataFrame(monthly_stats)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Income',
        x=stats_df['Month'],
        y=stats_df['Income'],
        marker_color='#10b981',
        text=stats_df['Income'].apply(lambda x: f'J${x:,.0f}'),
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Spending',
        x=stats_df['Month'],
        y=stats_df['Spending'],
        marker_color='#ef4444',
        text=stats_df['Spending'].apply(lambda x: f'J${x:,.0f}'),
        textposition='outside'
    ))
    
    fig.add_trace(go.Scatter(
        name='Net Savings',
        x=stats_df['Month'],
        y=stats_df['Savings'],
        mode='lines+markers',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=10),
        text=stats_df['Savings'].apply(lambda x: f'J${x:,.0f}'),
        textposition='top center'
    ))
    
    fig.update_layout(
        title=f'Cash Flow Analysis - {selected_year}',
        xaxis_title='Month',
        yaxis_title='Amount (J$)',
        barmode='group',
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_income = stats_df['Income'].sum()
    total_spending = stats_df['Spending'].sum()
    total_savings = stats_df['Savings'].sum()
    avg_savings = stats_df['Savings'].mean()
    
    with col1:
        st.metric("Total Income", f"J${total_income:,.0f}")
    with col2:
        st.metric("Total Spending", f"J${total_spending:,.0f}")
    with col3:
        st.metric("Total Savings", f"J${total_savings:,.0f}")
    with col4:
        st.metric("Avg Monthly Savings", f"J${avg_savings:,.0f}")


def render_monthly_analysis(data, year_month, month_name):
    """Render detailed analysis for a specific month"""
    month_data = data[data['YearMonth'] == year_month]
    
    if month_data.empty:
        st.warning("No data for this month")
        return
    
    stats = calculate_monthly_stats(data, year_month)
    summary = get_spending_by_category(data, year_month)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Income", f"J${stats['income']:,.0f}")
    with col2:
        st.metric("💸 Spending", f"J${stats['spending']:,.0f}")
    with col3:
        st.metric("🎯 Savings", f"J${stats['savings']:,.0f}")
    
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
                
                over_budget = comparison[comparison['Amount'] > comparison['Budget']]
                if not over_budget.empty:
                    st.warning(f"⚠️ Over budget in {len(over_budget)} categories")
                    for _, row in over_budget.iterrows():
                        st.caption(
                            f"**{row['Spending Category']}**: "
                            f"J${row['Amount']:,.0f} / J${row['Budget']:,.0f} "
                            f"(+J${row['Amount'] - row['Budget']:,.0f})"
                        )
        
        st.markdown("##### 📋 Detailed Breakdown")
        summary_display = summary.copy()
        summary_display['Amount'] = summary_display['Amount'].apply(lambda x: f"J${x:,.2f}")
        summary_display['Percentage'] = summary_display['Percentage'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(summary_display, use_container_width=True, hide_index=True)


def render_aggregate_analysis(data, selected_year, selected_months):
    """Render aggregate analysis for multiple months"""
    st.markdown("##### 📊 Aggregate Analysis")
    
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


def render_analysis_section(data):
    """Render the main analysis section"""
    
    if data.empty:
        st.error("❌ No data to analyze")
        return
    
    st.markdown("##### 📅 Select Analysis Period")
    
    available_years = sorted(data['Year'].dropna().unique())
    if len(available_years) == 0:
        st.error("❌ No valid years found in data")
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        analysis_type = st.selectbox(
            "Period Type",
            ["Specific Months", "Last 3 Months", "Last 6 Months", "All Time"],
            key="analysis_type"
        )
    
    with col2:
        if len(available_years) > 1:
            selected_year = st.selectbox(
                "Select Year",
                available_years,
                index=len(available_years) - 1,
                key="selected_year"
            )
        else:
            selected_year = int(available_years[0])
            st.info(f"📅 Year: {selected_year}")
    
    year_data = data[data['Year'] == selected_year]
    available_months_nums = sorted([int(m) for m in year_data['Month'].dropna().unique()])
    
    if len(available_months_nums) == 0:
        st.error(f"❌ No data found for year {selected_year}")
        return
    
    available_month_names = [calendar.month_name[m] for m in available_months_nums]
    
    if analysis_type == "Specific Months":
        with col3:
            selected_month_names = st.multiselect(
                "Select Months",
                available_month_names,
                default=available_month_names,
                key="selected_months_multi"
            )
        
        if not selected_month_names:
            st.warning("⚠️ Please select at least one month")
            return
        
        month_names_full = [calendar.month_name[i] for i in range(1, 13)]
        selected_months = [month_names_full.index(name) + 1 for name in selected_month_names]
    
    elif analysis_type == "Last 3 Months":
        selected_months = available_months_nums[-3:] if len(available_months_nums) >= 3 else available_months_nums
        with col3:
            st.info(f"{len(selected_months)} months")
    
    elif analysis_type == "Last 6 Months":
        selected_months = available_months_nums[-6:] if len(available_months_nums) >= 6 else available_months_nums
        with col3:
            st.info(f"{len(selected_months)} months")
    
    else:
        selected_months = available_months_nums
        with col3:
            st.info(f"{len(selected_months)} months")
    
    period_data = data[(data['Year'] == selected_year) & (data['Month'].isin(selected_months))]
    
    if period_data.empty:
        st.error("❌ No transactions found for selected period")
        return
    
    st.success(f"✅ Analyzing {len(period_data)} transactions across {len(selected_months)} month(s)")
    
    st.markdown("---")
    render_cash_flow_charts(data, selected_year, selected_months)
    
    st.markdown("---")
    st.markdown("##### 📅 Monthly Analysis")
    
    if len(selected_months) > 0:
        tabs = st.tabs([f"📊 {calendar.month_name[m]}" for m in sorted(selected_months)])
        
        for idx, month_num in enumerate(sorted(selected_months)):
            with tabs[idx]:
                year_month = f"{selected_year}-{month_num:02d}"
                render_monthly_analysis(data, year_month, calendar.month_name[month_num])
    
    if len(selected_months) > 1:
        st.markdown("---")
        render_aggregate_analysis(data, selected_year, selected_months)
    
    st.markdown("---")
    st.markdown("#### 📥 Export Data")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        export_format = st.radio(
            "Format",
            options=["Excel", "PDF Report"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    with col2:
        if export_format == "Excel":
            excel_data = export_to_excel(period_data)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"transactions_{selected_year}_{analysis_type.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
        else:
            try:
                from pdf_generator import create_comprehensive_pdf
                
                pdf_bytes = create_comprehensive_pdf(
                    data=data,
                    selected_year=int(selected_year),
                    selected_months=[int(m) for m in selected_months],
                    analysis_type=analysis_type,
                    user_id=st.session_state.user['id']
                )
                
                period_label = f"{analysis_type}_{selected_year}".replace(" ", "_")
                
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=f"Finance_Report_{period_label}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
                
            except Exception as e:
                st.error(f"❌ Error generating PDF: {e}")


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


def spending_analysis_page():
    """Main spending analysis page with flowing layout"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)

    # Check if diagnostic mode
    if st.session_state.get('show_diagnostic', False):
        file_diagnostic_page()
        if st.button("← Back to Spending Analysis"):
            st.session_state.show_diagnostic = False
            st.rerun()
        return  # Don't show the rest of the page
    
    # Header with back button
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("### 📊 Spending Analysis")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    with col3:
        if st.button("🔍 Diagnostic", use_container_width=True):
            st.session_state.show_diagnostic = True
            st.rerun()
    
    st.markdown("---")
    
    # FILE UPLOAD SECTION
    st.markdown("#### 📁 Upload Bank Statements")
    st.info("💡 Upload JMMB CSV or NCB PDF bank statements to analyze your spending")
    
    # Initialize upload state if not exists
    if 'files_uploaded' not in st.session_state:
        st.session_state.files_uploaded = False
    
    # File uploader with unique key that changes after upload
    uploader_key = f"file_uploader_{st.session_state.get('upload_counter', 0)}"
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['csv', 'pdf'],
        accept_multiple_files=True,
        key=uploader_key,
        help="Select one or more CSV or PDF files from your bank"
    )
    
    if uploaded_files:
        # Show file list
        st.write(f"**Selected files:** {len(uploaded_files)}")
        for file in uploaded_files:
            file_icon = "📄" if file.name.endswith('.pdf') else "📊"
            st.caption(f"{file_icon} {file.name}")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("📤 Upload All Files", type="primary", use_container_width=True):
                success_count = 0
                error_count = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {file.name}...")
                    
                    try:
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
                    except Exception as e:
                        st.error(f"Error processing {file.name}: {e}")
                        error_count += 1
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                progress_bar.empty()
                status_text.empty()
                
                if success_count > 0:
                    st.success(f"✅ Successfully uploaded {success_count} file(s)")
                    clear_data_cache()
                    
                    # Clear the uploader by incrementing counter
                    if 'upload_counter' not in st.session_state:
                        st.session_state.upload_counter = 0
                    st.session_state.upload_counter += 1
                    st.session_state.files_uploaded = True
                    
                    st.rerun()
                
                if error_count > 0:
                    st.error(f"❌ Failed to upload {error_count} file(s)")
        
        with col2:
            if st.button("🗑️ Clear Selection", use_container_width=True):
                # Clear by incrementing counter
                if 'upload_counter' not in st.session_state:
                    st.session_state.upload_counter = 0
                st.session_state.upload_counter += 1
                st.rerun()
    
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
            # Ensure Date is datetime and create required columns
            if 'Date' in data.columns:
                data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
                data = data.dropna(subset=['Date'])
                
                # Create required columns if missing
                if 'Year' not in data.columns:
                    data['Year'] = data['Date'].dt.year
                if 'Month' not in data.columns:
                    data['Month'] = data['Date'].dt.month
                if 'YearMonth' not in data.columns:
                    data['YearMonth'] = data['Date'].dt.strftime('%Y-%m')
                
                # Ensure Spending Category exists
                if 'Spending Category' not in data.columns:
                    from data_processing import categorize_transactions
                    data = categorize_transactions(data)
                
                st.success(f"✅ Loaded {len(data)} transactions from {len(data['YearMonth'].unique())} months")
                
                # NOW render the analysis
                render_analysis_section(data)
            else:
                st.error("❌ No Date column found in data")
    
    st.markdown("</div>", unsafe_allow_html=True)
