# pages/spending_analysis.py
"""
Spending Analysis page - FULL VERSION - All line number issues fixed
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
import calendar
from io import BytesIO


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
        
        cols = st.columns(2)
        
        categories = list(DEFAULT_CATEGORY_MAPPING.keys())
        mid_point = len(categories) // 2
        
        with cols[0]:
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
        
        with cols[1]:
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
        
        button_cols = st.columns(3)
        
        with button_cols[0]:
            if st.button("💾 Save Categories", use_container_width=True, key="save_cats_btn"):
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
        
        with button_cols[1]:
            if st.button("🔄 Reset to Defaults", use_container_width=True, key="reset_cats_btn"):
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
    
    metric_cols = st.columns(4)
    
    total_income = stats_df['Income'].sum()
    total_spending = stats_df['Spending'].sum()
    total_savings = stats_df['Savings'].sum()
    avg_savings = stats_df['Savings'].mean()
    
    with metric_cols[0]:
        st.metric("Total Income", f"J${total_income:,.0f}")
    with metric_cols[1]:
        st.metric("Total Spending", f"J${total_spending:,.0f}")
    with metric_cols[2]:
        st.metric("Total Savings", f"J${total_savings:,.0f}")
    with metric_cols[3]:
        st.metric("Avg Monthly Savings", f"J${avg_savings:,.0f}")


def render_monthly_analysis(data, year_month, month_name):
    """Render detailed analysis for a specific month"""
    month_data = data[data['YearMonth'] == year_month]
    
    if month_data.empty:
        st.warning("No data for this month")
        return
    
    stats = calculate_monthly_stats(data, year_month)
    summary = get_spending_by_category(data, year_month)
    
    metric_cols = st.columns(3)
    
    with metric_cols[0]:
        st.metric("💰 Income", f"J${stats['income']:,.0f}")
    with metric_cols[1]:
        st.metric("💸 Spending", f"J${stats['spending']:,.0f}")
    with metric_cols[2]:
        st.metric("🎯 Savings", f"J${stats['savings']:,.0f}")
    
    if not summary.empty:
        st.markdown(f"##### 📈 Spending Breakdown for {month_name}")
        
        chart_cols = st.columns(2)
        
        with chart_cols[0]:
            fig_pie = px.pie(
                summary,
                values='Amount',
                names='Spending Category',
                hole=0.4,
                title='Distribution'
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with chart_cols[1]:
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
    
    period_data = data[(data['Year'] == selected_year) & (data['Month'].isin(selected_months))]
    
    if period_data.empty:
        st.warning("⚠️ No data available for selected months")
        return
    
    year_months = [f"{selected_year}-{m:02d}" for m in selected_months]
    total_income = sum([calculate_monthly_stats(data, ym)['income'] for ym in year_months])
    total_spending = sum([calculate_monthly_stats(data, ym)['spending'] for ym in year_months])
    total_savings = total_income - total_spending
    
    metric_cols = st.columns(3)
    
    with metric_cols[0]:
        st.metric("💰 Total Income", f"J${total_income:,.0f}")
    with metric_cols[1]:
        st.metric("💸 Total Spending", f"J${total_spending:,.0f}")
    with metric_cols[2]:
        st.metric("🎯 Total Savings", f"J${total_savings:,.0f}")
    
    st.markdown("##### 🥧 Aggregate Spending by Category")
    
    all_spending = []
    for ym in year_months:
        month_summary = get_spending_by_category(data, ym)
        if not month_summary.empty:
            all_spending.append(month_summary)
    
    if not all_spending:
        st.info("📊 No spending data to display")
        return
    
    aggregate_spending = pd.concat(all_spending).groupby('Spending Category')['Amount'].sum().reset_index()
    aggregate_spending['Percentage'] = 100 * aggregate_spending['Amount'] / aggregate_spending['Amount'].sum()
    aggregate_spending = aggregate_spending.sort_values('Amount', ascending=False)
    
    chart_cols = st.columns(2)
    
    with chart_cols[0]:
        fig_agg_pie = px.pie(
            aggregate_spending,
            values='Amount',
            names='Spending Category',
            hole=0.4,
            title='Total Spending Distribution'
        )
        st.plotly_chart(fig_agg_pie, use_container_width=True)
    
    with chart_cols[1]:
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
    
    st.markdown("##### 📋 Detailed Breakdown")
    breakdown_display = aggregate_spending.copy()
    breakdown_display['Amount'] = breakdown_display['Amount'].apply(lambda x: f"J${x:,.2f}")
    breakdown_display['Percentage'] = breakdown_display['Percentage'].apply(lambda x: f"{x:.1f}%")
    st.dataframe(breakdown_display, use_container_width=True, hide_index=True)


def render_analysis_section(data):
    """Render the main analysis section"""
    
    if data.empty:
        st.error("❌ No data to analyze")
        return
    
    st.markdown("##### 📅 Select Analysis Period")
    
    if 'Date' in data.columns:
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        data['Year'] = data['Date'].dt.year.astype(int)
        data['Month'] = data['Date'].dt.month.astype(int)
    
    available_years = sorted([int(y) for y in data['Year'].dropna().unique()])
    
    if len(available_years) == 0:
        st.error("❌ No valid years found in data")
        return
    
    min_date = data['Date'].min()
    max_date = data['Date'].max()
    st.info(f"📊 Data available from {min_date.strftime('%B %Y')} to {max_date.strftime('%B %Y')}")
    
    selector_cols = st.columns(3)
    
    with selector_cols[0]:
        analysis_type = st.selectbox(
            "Period Type",
            ["Specific Months", "Last 3 Months", "Last 6 Months", "All Time"],
            key="analysis_type"
        )
    
    with selector_cols[1]:
        selected_year = st.selectbox(
            "Year",
            available_years,
            index=len(available_years) - 1,
            key="selected_year"
        )
    
    year_data = data[data['Year'] == selected_year]
    available_months_nums = sorted([int(m) for m in year_data['Month'].dropna().unique()])
    
    if len(available_months_nums) == 0:
        st.error(f"❌ No data found for year {selected_year}")
        return
    
    available_month_names = [calendar.month_name[m] for m in available_months_nums]
    
    if analysis_type == "Specific Months":
        with selector_cols[2]:
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
        with selector_cols[2]:
            st.info(f"{len(selected_months)} months")
    
    elif analysis_type == "Last 6 Months":
        selected_months = available_months_nums[-6:] if len(available_months_nums) >= 6 else available_months_nums
        with selector_cols[2]:
            st.info(f"{len(selected_months)} months")
    
    else:
        selected_months = available_months_nums
        with selector_cols[2]:
            st.info(f"{len(selected_months)} months")
    
    period_data = data[(data['Year'] == selected_year) & (data['Month'].isin(selected_months))]
    
    if period_data.empty:
        st.error("❌ No transactions found for selected period")
        return
    
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
    
    export_cols = st.columns(2)
    
    with export_cols[0]:
        export_format = st.radio(
            "Format",
            options=["Excel", "PDF Report"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    with export_cols[1]:
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
    
    page_cols = st.columns(5)
    
    with page_cols[0]:
        if st.button("⏮️ First", disabled=(current_page == 0), key="page_first_btn"):
            st.session_state.file_page = 0
            st.rerun()
    
    with page_cols[1]:
        if st.button("◀️ Prev", disabled=(current_page == 0), key="page_prev_btn"):
            st.session_state.file_page = current_page - 1
            st.rerun()
    
    with page_cols[2]:
        st.markdown(f"<div style='text-align: center; padding: 0.5rem;'>Page {current_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
    
    with page_cols[3]:
        if st.button("Next ▶️", disabled=(current_page >= total_pages - 1), key="page_next_btn"):
            st.session_state.file_page = current_page + 1
            st.rerun()
    
    with page_cols[4]:
        if st.button("Last ⏭️", disabled=(current_page >= total_pages - 1), key="page_last_btn"):
            st.session_state.file_page = total_pages - 1
            st.rerun()


def spending_analysis_page():
    """Main spending analysis page"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header
    header_cols = st.columns(2)
    with header_cols[0]:
        st.markdown("### 📊 Spending Analysis")
    with header_cols[1]:
        if st.button("← Back to Dashboard", use_container_width=True, key="back_dash_btn"):
            st.session_state.selected_feature = None
            st.rerun()
    
    st.markdown("---")
    
    # FILE UPLOAD
    st.markdown("#### 📁 Upload Bank Statements")
    st.info("💡 Upload JMMB CSV or NCB PDF bank statements to analyze your spending")
    
    # Initialize session state
    if 'upload_counter' not in st.session_state:
        st.session_state.upload_counter = 0
    
    uploader_key = f"file_uploader_{st.session_state.upload_counter}"
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['csv', 'pdf'],
        accept_multiple_files=True,
        key=uploader_key,
        help="Select one or more CSV or PDF files from your bank"
    )
    
    if uploaded_files:
        st.write(f"**Selected files:** {len(uploaded_files)}")
        for file in uploaded_files:
            file_icon = "📄" if file.name.endswith('.pdf') else "📊"
            st.caption(f"{file_icon} {file.name}")
        
        upload_btn_cols = st.columns(3)
        
        with upload_btn_cols[0]:
            if st.button("📤 Upload All Files", type="primary", use_container_width=True, key="upload_btn"):
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
                    st.session_state.upload_counter += 1
                    st.rerun()
                
                if error_count > 0:
                    st.error(f"❌ Failed to upload {error_count} file(s)")
        
        with upload_btn_cols[1]:
            if st.button("🗑️ Clear Selection", use_container_width=True, key="clear_btn"):
                st.session_state.upload_counter += 1
                st.rerun()
    
    # YOUR FILES
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
        
        file_cols = st.columns(3)
        for idx, file in enumerate(files):
            col = file_cols[idx % 3]
            with col:
                display_file_card(file)
        
        if total_files > FILES_PER_PAGE:
            display_pagination_controls(total_files, FILES_PER_PAGE)
    
    # CATEGORY EDITOR
    st.markdown("---")
    render_category_editor()
    
    # DATA VISUALIZATION
    st.markdown("---")
    st.markdown("#### 📈 Spending Visualizations")
    
    with st.spinner("Loading your data..."):
        data = load_all_user_data(st.session_state.user['id'])
        
        if data.empty:
            st.warning("📊 No data available yet. Upload files above to see your spending analysis.")
        else:
            if 'Date' in data.columns:
                data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
                data = data.dropna(subset=['Date'])
                
                if 'Year' not in data.columns:
                    data['Year'] = data['Date'].dt.year
                if 'Month' not in data.columns:
                    data['Month'] = data['Date'].dt.month
                if 'YearMonth' not in data.columns:
                    data['YearMonth'] = data['Date'].dt.strftime('%Y-%m')
                
                if 'Spending Category' not in data.columns:
                    from data_processing import categorize_transactions
                    data = categorize_transactions(data)
                
                render_analysis_section(data)
            else:
                st.error("❌ No Date column found in data")
    
    st.markdown("</div>", unsafe_allow_html=True)
