# pages/spending_analysis.py
"""
Spending Analysis page - unified flowing layout
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_all_user_data, clear_data_cache
from database import (
    save_user_file, 
    delete_user_file, 
    get_user_files_paginated
)
from utils import (
    calculate_monthly_stats,
    get_spending_by_category,
    export_to_excel
)
from config import FILES_PER_PAGE


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
    # Add this section to your spending_analysis.py after line 95 (after the "DATA VISUALIZATION SECTION" comment)
# This is for debugging - remove once working

# DEBUG SECTION - TEMPORARY
st.markdown("---")
st.markdown("#### 🔍 Debug Information")

with st.expander("Click to see debug info"):
    st.write("**User ID:**", st.session_state.user['id'])
    
    # Check database connection
    from database import get_all_user_files
    files_in_db = get_all_user_files(st.session_state.user['id'])
    st.write(f"**Files in database:** {len(files_in_db)}")
    
    if files_in_db:
        for i, file in enumerate(files_in_db[:3]):  # Show first 3
            st.write(f"File {i+1}:")
            st.write(f"  - Filename: {file.get('filename', 'N/A')}")
            st.write(f"  - Type: {file.get('file_type', 'N/A')}")
            st.write(f"  - Data size: {len(file.get('file_data', b''))} bytes")
    
    # Try to load data
    st.write("**Attempting to load data...**")
    try:
        from data_loader import load_all_user_data
        test_data = load_all_user_data(st.session_state.user['id'])
        st.write(f"**Data loaded:** {len(test_data)} rows")
        
        if not test_data.empty:
            st.write("**Columns:**", list(test_data.columns))
            st.write("**First few rows:**")
            st.dataframe(test_data.head())
        else:
            st.error("Data is empty after processing")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        import traceback
        st.code(traceback.format_exc())

st.markdown("---")
# END DEBUG SECTION
    
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
    
    # Load data without showing the cache message
    with st.spinner("Loading your data..."):
        data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.warning("📊 No data available yet. Upload files above to see your spending analysis.")
    else:
        # Month selector
        available_months = sorted(data['YearMonth'].unique(), reverse=True)
        selected_month = st.selectbox("📅 Select Month", available_months)
        
        month_data = data[data['YearMonth'] == selected_month]
        
        if not month_data.empty:
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
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### 🥧 Spending Distribution")
                    fig_pie = px.pie(
                        summary,
                        values='Amount',
                        names='Spending Category',
                        hole=0.4
                    )
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.markdown("##### 📊 Category Breakdown")
                    fig_bar = px.bar(
                        summary,
                        x='Spending Category',
                        y='Amount',
                        color='Amount',
                        color_continuous_scale='Blues'
                    )
                    fig_bar.update_layout(
                        height=400,
                        showlegend=False,
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                # Spending table
                st.markdown("##### 📋 Detailed Breakdown")
                summary_display = summary.copy()
                summary_display['Amount'] = summary_display['Amount'].apply(lambda x: f"J${x:,.2f}")
                summary_display['Percentage'] = summary_display['Percentage'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(summary_display, use_container_width=True, hide_index=True)
            
            # Export options
            st.markdown("---")
            st.markdown("#### 📥 Export Data")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                excel_data = export_to_excel(month_data)
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"transactions_{selected_month}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col2:
                csv_data = month_data.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"transactions_{selected_month}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    st.markdown("</div>", unsafe_allow_html=True)


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
