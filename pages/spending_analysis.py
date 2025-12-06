# pages/spending_analysis.py
"""
Spending Analysis page - file management, visualization, and reporting
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
    compare_budget_vs_actual,
    generate_alert_email_body,
    send_email_alert,
    export_to_excel
)
from config import (
    DEFAULT_CATEGORY_MAPPING,
    DEFAULT_BUDGETS,
    DEFAULT_SAVINGS_GOAL,
    FILES_PER_PAGE
)
from pdf_generator import create_pdf_with_charts
import json


def spending_analysis_page():
    """Main spending analysis page"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 📊 Spending Analysis")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📁 File Management", 
        "📈 Visualizations", 
        "⚙️ Settings",
        "📧 Alerts"
    ])
    
    with tab1:
        file_management_tab()
    
    with tab2:
        visualizations_tab()
    
    with tab3:
        settings_tab()
    
    with tab4:
        alerts_tab()
    
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================
# FILE MANAGEMENT TAB
# ============================================

def file_management_tab():
    """File upload and management"""
    st.markdown("#### Upload Bank Statements")
    st.info("💡 Upload CSV or PDF bank statements to analyze your spending")
    
    # File uploader
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
    
    st.markdown("---")
    st.markdown("#### Your Files")
    
    # Get files with pagination
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


# ============================================
# VISUALIZATIONS TAB
# ============================================

def visualizations_tab():
    """Data visualization and analysis"""
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No data available. Please upload files in the File Management tab.")
        return
    
    # Month selector
    available_months = sorted(data['YearMonth'].unique(), reverse=True)
    selected_month = st.selectbox("Select Month", available_months)
    
    month_data = data[data['YearMonth'] == selected_month]
    
    if month_data.empty:
        st.warning("No data for selected month")
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
    
    st.markdown("---")
    
    # Visualizations
    if not summary.empty:
        # Pie chart
        st.markdown("#### 🥧 Spending by Category")
        fig_pie = px.pie(
            summary,
            values='Amount',
            names='Spending Category',
            title=f"Spending Distribution - {selected_month}"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Bar chart
        st.markdown("#### 📊 Category Breakdown")
        fig_bar = px.bar(
            summary,
            x='Spending Category',
            y='Amount',
            title=f"Spending by Category - {selected_month}",
            color='Amount',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Budget comparison
    prefs = get_user_preferences(st.session_state.user['id'])
    if prefs and prefs.get('monthly_budgets'):
        budgets = json.loads(prefs['monthly_budgets'])
        comparison = compare_budget_vs_actual(budgets, summary)
        
        st.markdown("#### 📋 Budget vs Actual")
        st.dataframe(comparison, use_container_width=True, hide_index=True)
    
    # Export options
    st.markdown("---")
    st.markdown("#### 📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        excel_data = export_to_excel(month_data)
        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name=f"transactions_{selected_month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        if not summary.empty and prefs:
            try:
                budgets = json.loads(prefs['monthly_budgets'])
                savings_goal = prefs.get('savings_goal', DEFAULT_SAVINGS_GOAL)
                
                pdf_data = create_pdf_with_charts(
                    month_data,
                    selected_month,
                    summary,
                    comparison if prefs else None,
                    stats['income'],
                    stats['spending'],
                    stats['savings'],
                    savings_goal
                )
                
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_data,
                    file_name=f"report_{selected_month}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")


# ============================================
# SETTINGS TAB
# ============================================

def settings_tab():
    """User preferences and settings"""
    st.markdown("#### ⚙️ Spending Categories & Budgets")
    
    # Load existing preferences or use defaults
    prefs = get_user_preferences(st.session_state.user['id'])
    
    if prefs and prefs.get('category_keywords'):
        category_keywords = json.loads(prefs['category_keywords'])
    else:
        category_keywords = DEFAULT_CATEGORY_MAPPING.copy()
    
    if prefs and prefs.get('monthly_budgets'):
        monthly_budgets = json.loads(prefs['monthly_budgets'])
    else:
        monthly_budgets = DEFAULT_BUDGETS.copy()
    
    savings_goal = prefs.get('savings_goal', DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
    
    # Category keyword editor
    st.markdown("##### 🏷️ Category Keywords")
    st.info("Add keywords to help categorize your transactions automatically")
    
    for category in category_keywords.keys():
        with st.expander(f"{category}"):
            keywords = st.text_area(
                "Keywords (comma-separated)",
                value=", ".join(category_keywords[category]),
                key=f"cat_{category}",
                height=100
            )
            category_keywords[category] = [k.strip() for k in keywords.split(",") if k.strip()]
    
    # Budget editor
    st.markdown("---")
    st.markdown("##### 💰 Monthly Budgets")
    
    cols = st.columns(2)
    for idx, category in enumerate(monthly_budgets.keys()):
        col = cols[idx % 2]
        with col:
            monthly_budgets[category] = st.number_input(
                f"{category}",
                min_value=0,
                value=int(monthly_budgets[category]),
                step=500,
                key=f"budget_{category}"
            )
    
    # Savings goal
    st.markdown("---")
    savings_goal = st.number_input(
        "🎯 Monthly Savings Goal (J$)",
        min_value=0,
        value=int(savings_goal),
        step=500
    )
    
    # Save button
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        if save_user_preferences(
            st.session_state.user['id'],
            category_keywords,
            monthly_budgets,
            savings_goal
        ):
            st.success("✅ Settings saved successfully!")
            clear_data_cache()
            st.rerun()
        else:
            st.error("❌ Failed to save settings")


# ============================================
# ALERTS TAB
# ============================================

def alerts_tab():
    """Email alerts for budget violations"""
    st.markdown("#### 📧 Budget Alerts")
    st.info("Get email notifications when you exceed your budget in any category")
    
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No data available. Upload files to enable alerts.")
        return
    
    prefs = get_user_preferences(st.session_state.user['id'])
    if not prefs or not prefs.get('monthly_budgets'):
        st.warning("⚙️ Please configure your budgets in the Settings tab first.")
        return
    
    # Month selector
    available_months = sorted(data['YearMonth'].unique(), reverse=True)
    selected_month = st.selectbox("Select Month to Check", available_months, key="alert_month")
    
    # Check for overspending
    budgets = json.loads(prefs['monthly_budgets'])
    summary = get_spending_by_category(data, selected_month)
    comparison = compare_budget_vs_actual(budgets, summary)
    
    overspent = comparison[comparison['Amount'] > comparison['Budget']]
    
    if overspent.empty:
        st.success("✅ You're within budget for all categories!")
    else:
        st.warning(f"⚠️ You've exceeded your budget in {len(overspent)} categor{'y' if len(overspent) == 1 else 'ies'}")
        st.dataframe(overspent, use_container_width=True, hide_index=True)
        
        # Email alert
        st.markdown("---")
        recipient_email = st.text_input(
            "Email Address",
            value=st.session_state.user['email'],
            placeholder="your.email@example.com"
        )
        
        if st.button("📧 Send Alert Email", type="primary", use_container_width=True):
            if recipient_email:
                email_body = generate_alert_email_body(
                    st.session_state.user['username'],
                    selected_month,
                    overspent
                )
                
                if send_email_alert(
                    recipient_email,
                    f"Budget Alert - {selected_month}",
                    email_body
                ):
                    st.success("✅ Alert email sent!")
                else:
                    st.error("❌ Failed to send email")
            else:
                st.error("Please enter an email address")
