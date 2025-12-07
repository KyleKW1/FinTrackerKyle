# app.py
"""
Main application entry point
Handles routing and page rendering
"""

import streamlit as st
from config import APP_TITLE, APP_ICON, DEFAULT_CATEGORY_MAPPING, DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
from auth import init_session_state, logout
from styles import apply_custom_styles
from pages.auth_pages import login_page, register_page
from pages.dashboard import dashboard_page
from password_reset import forgot_password_page, reset_password_page
from database import get_user_preferences, save_user_preferences
from data_loader import clear_data_cache
import json


def main():
    """Main application function"""
    # Page config
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    #init_session_state()
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'selected_feature' not in st.session_state:
        st.session_state.selected_feature = None
    if 'file_page' not in st.session_state:
        st.session_state.file_page = 0
    
    # Apply custom styles
    apply_custom_styles()
    
    # Handle query params for password reset
    try:
        if hasattr(st, 'query_params'):
            query_params = st.query_params
            if 'reset_token' in query_params:
                if 'reset_token' not in st.session_state:
                    st.session_state.reset_token = query_params['reset_token']
                    st.session_state.page = 'reset'
    except Exception as e:
        print(f"Query param error: {e}")
    
    # Route to appropriate page
    if not st.session_state.authenticated:
        if st.session_state.page == 'register':
            register_page()
        elif st.session_state.page == 'forgot':
            forgot_password_page()
        elif st.session_state.page == 'reset':
            reset_password_page()
        else:
            login_page()
    else:
        # Render sidebar
        render_sidebar()
        
        # Render main dashboard
        dashboard_page()


def render_sidebar():
    """Render the sidebar for authenticated users"""
    with st.sidebar:
        # User info
        st.markdown(f"""
            <div style='padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 12px; margin-bottom: 1rem;'>
                <h3 style='margin: 0;'>👤 {st.session_state.user['username']}</h3>
                <p style='margin: 0.5rem 0 0 0; opacity: 0.8;'>📧 {st.session_state.user['email']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user.get('last_login'):
            last_login = str(st.session_state.user['last_login'])
            st.caption(f"Last login: {last_login[:19]}")
        
        st.markdown("---")
        
        # Settings expander
        with st.expander("⚙️ Settings", expanded=False):
            render_settings()
        
        st.markdown("---")
        
        # Alerts expander
        with st.expander("📧 Budget Alerts", expanded=False):
            render_alerts()
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            logout()


def render_settings():
    """Render settings in sidebar"""
    st.markdown("##### 💰 Monthly Savings Goal")
    
    # Load existing preferences
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
    
    # Savings goal input
    new_savings_goal = st.number_input(
        "Target Monthly Savings (J$)",
        min_value=0,
        value=int(savings_goal),
        step=500,
        key="sidebar_savings_goal"
    )
    
    st.markdown("##### 💵 Category Budgets")
    st.caption("Set monthly spending limits")
    
    # Show top 5 categories with inputs
    top_categories = ["Food", "Grocery", "Utilities", "Transport", "Miscellaneous"]
    new_budgets = monthly_budgets.copy()
    
    for category in top_categories:
        new_budgets[category] = st.number_input(
            f"{category}",
            min_value=0,
            value=int(monthly_budgets.get(category, 0)),
            step=500,
            key=f"sidebar_budget_{category}"
        )
    
    # Save button
    if st.button("💾 Save Settings", use_container_width=True, key="save_settings"):
        if save_user_preferences(
            st.session_state.user['id'],
            category_keywords,
            new_budgets,
            new_savings_goal
        ):
            st.success("✅ Settings saved!")
            clear_data_cache()
        else:
            st.error("❌ Failed to save")


def render_alerts():
    """Render alerts section in sidebar"""
    from data_loader import load_all_user_data
    from utils import get_spending_by_category, send_email_alert
    
    st.markdown("##### 📧 Budget Alerts")
    
    # Load data
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.info("Upload data to see alerts")
        return
    
    prefs = get_user_preferences(st.session_state.user['id'])
    if not prefs or not prefs.get('monthly_budgets'):
        st.warning("Set budgets first")
        if st.button("Go to Budget Planner", key="goto_budget_planner", use_container_width=True):
            st.session_state.selected_feature = 'planner'
            st.rerun()
        return
    
    # Get latest month
    available_months = sorted(data['YearMonth'].unique(), reverse=True)
    if not available_months:
        return
    
    latest_month = available_months[0]
    
    # Check for overspending
    budgets = json.loads(prefs['monthly_budgets'])
    summary = get_spending_by_category(data, latest_month)
    
    if summary.empty:
        return
    
    # Calculate comparison
    over_budget_categories = []
    warning_categories = []
    
    for category in budgets.keys():
        if category in ['Income', 'Other']:
            continue
        
        budget = budgets[category]
        actual = summary[summary['Spending Category'] == category]['Amount'].sum()
        
        if budget > 0:
            percentage = (actual / budget) * 100
            
            if percentage > 100:
                over_budget_categories.append({
                    'Category': category,
                    'Budget': budget,
                    'Actual': actual,
                    'Percentage': percentage
                })
            elif percentage > 80:
                warning_categories.append({
                    'Category': category,
                    'Budget': budget,
                    'Actual': actual,
                    'Percentage': percentage
                })
    
    # Display status
    if over_budget_categories:
        st.error(f"⚠️ {len(over_budget_categories)} over budget!")
        for cat in over_budget_categories[:3]:  # Show top 3
            st.caption(f"**{cat['Category']}**: {cat['Percentage']:.0f}%")
    elif warning_categories:
        st.warning(f"⚡ {len(warning_categories)} near limit")
        for cat in warning_categories[:3]:
            st.caption(f"**{cat['Category']}**: {cat['Percentage']:.0f}%")
    else:
        st.success("✅ All within budget!")
    
    # Email alert option if over budget
    if over_budget_categories:
        with st.expander("Send Email Alert", expanded=False):
            recipient_email = st.text_input(
                "Email",
                value=st.session_state.user['email'],
                key="alert_email"
            )
            
            if st.button("📧 Send Alert", use_container_width=True, key="send_alert_btn"):
                if recipient_email:
                    # Generate email body
                    body_lines = [
                        f"Dear {st.session_state.user['username']},\n",
                        f"Budget Alert for {latest_month}:\n\n",
                        "Categories over budget:\n"
                    ]
                    
                    for cat in over_budget_categories:
                        body_lines.append(
                            f"- {cat['Category']}: J${cat['Actual']:,.0f} / J${cat['Budget']:,.0f} ({cat['Percentage']:.0f}%)"
                        )
                    
                    body_lines.append("\n\nPlease review your spending.\n\nBest regards,\nFinance Hub")
                    
                    if send_email_alert(
                        recipient_email,
                        f"Budget Alert - {latest_month}",
                        "\n".join(body_lines)
                    ):
                        st.success("✅ Email sent!")
                    else:
                        st.error("❌ Failed to send email")

# Add this temporarily to your app.py or create a diagnostic page
"""
DIAGNOSTIC PAGE - Add this to see what's happening with your data
"""

import streamlit as st
import pandas as pd
from data_loader import load_all_user_data
from database import get_all_user_files

def diagnostic_page():
    """Debug page to see what's happening with data loading"""
    st.title("🔍 Data Diagnostic Tool")
    
    if st.button("🔄 Refresh Data (Clear Cache)"):
        from data_loader import clear_data_cache
        clear_data_cache()
        st.success("Cache cleared! Reload the page.")
        st.rerun()
    
    st.markdown("---")
    
    # Check files in database
    st.subheader("📁 Files in Database")
    files = get_all_user_files(st.session_state.user['id'])
    
    if not files:
        st.error("No files found in database!")
        return
    
    st.success(f"Found {len(files)} files in database")
    
    for idx, file_info in enumerate(files):
        with st.expander(f"📄 File {idx+1}: {file_info.get('filename', 'Unknown')}"):
            st.write(f"**Type:** {file_info['file_type']}")
            st.write(f"**Size:** {len(file_info['file_data'])} bytes")
            
            # Try to process this specific file
            try:
                from io import BytesIO
                from data_processing import process_csv, process_pdf_ncb, extract_from_pdf, standardize_dataframe_columns
                import pdfplumber
                
                file_bytes = BytesIO(file_info['file_data'])
                filename = file_info.get('filename', '')
                file_type = file_info['file_type'].lower()
                
                # For PDFs, show raw content first with search
                if file_type == 'pdf':
                    try:
                        file_bytes.seek(0)
                        with pdfplumber.open(file_bytes) as pdf:
                            first_page = pdf.pages[0].extract_text()
                            
                            # Show year detection
                            st.write("**🔍 Year Detection:**")
                            year_found = None
                            year_patterns = [
                                (r'(\d{2}/[A-Za-z]{3}/(\d{4}))', 'Full date format'),
                                (r'Statement.*?(\d{4})', 'Statement date'),
                                (r'\b(202[0-9])\b', 'Any 202X year'),
                            ]
                            
                            for pattern, desc in year_patterns:
                                matches = re.findall(pattern, first_page)
                                if matches:
                                    if isinstance(matches[0], tuple):
                                        year_found = matches[0][-1]
                                    else:
                                        year_found = matches[0]
                                    st.success(f"Found year {year_found} using: {desc}")
                                    break
                            
                            if not year_found:
                                st.error("❌ Could not detect year from PDF!")
                            
                            # Show first lines that look like transactions
                            st.write("**📄 Lines that look like transactions:**")
                            transaction_pattern = r'\d{2}/[A-Za-z]{3}\s+.+?\s+[\d,]+\.\d{2}'
                            potential_transactions = [line for line in first_page.split('\n') 
                                                     if re.search(transaction_pattern, line)]
                            
                            if potential_transactions:
                                st.code('\n'.join(potential_transactions[:10]))
                                st.info(f"Found {len(potential_transactions)} potential transaction lines")
                            else:
                                st.error("❌ No lines matching transaction pattern!")
                                st.write("**First 30 lines of PDF:**")
                                st.code('\n'.join(first_page.split('\n')[:30]))
                            
                    except Exception as e:
                        st.error(f"Could not extract text: {e}")
                    
                    file_bytes.seek(0)  # Reset for processing
                
                if file_type == 'pdf':
                    if 'ncb' in filename.lower():
                        df = process_pdf_ncb(file_bytes)
                    else:
                        df = extract_from_pdf(file_bytes)
                elif file_type == 'csv':
                    df = process_csv(file_bytes)
                else:
                    st.error("Unknown file type")
                    continue
                
                if df.empty:
                    st.error("❌ No data extracted from this file")
                else:
                    st.success(f"✅ Extracted {len(df)} rows")
                    
                    # Standardize
                    df = standardize_dataframe_columns(df)
                    st.info(f"After standardization: {len(df)} rows")
                    
                    # Check for Date column
                    if 'Date' in df.columns:
                        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                        valid_dates = df['Date'].notna().sum()
                        st.write(f"**Valid dates:** {valid_dates}/{len(df)}")
                        
                        if valid_dates > 0:
                            df_with_dates = df.dropna(subset=['Date'])
                            df_with_dates['YearMonth'] = df_with_dates['Date'].dt.strftime('%Y-%m')
                            df_with_dates['Year'] = df_with_dates['Date'].dt.year
                            df_with_dates['Month'] = df_with_dates['Date'].dt.month
                            
                            st.write(f"**Date range:** {df_with_dates['Date'].min()} to {df_with_dates['Date'].max()}")
                            
                            # Show months
                            unique_months = sorted(df_with_dates['YearMonth'].unique())
                            st.write(f"**Months in this file:** {unique_months}")
                            
                            # Show sample data
                            st.write("**Sample data:**")
                            st.dataframe(df_with_dates[['Date', 'Description', 'Amount', 'YearMonth']].head(10))
                    else:
                        st.error("❌ No Date column found!")
                        st.write("Columns:", list(df.columns))
                        st.dataframe(df.head(5))
                        
            except Exception as e:
                st.error(f"Error processing file: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Load combined data
    st.subheader("📊 Combined Dataset")
    
    try:
        data = load_all_user_data(st.session_state.user['id'])
        
        if data.empty:
            st.error("❌ Combined dataset is EMPTY!")
            st.warning("Check the processing logs above to see where data is being lost.")
        else:
            st.success(f"✅ Combined dataset has {len(data)} rows")
            
            # Check for required columns
            st.write("**Columns in dataset:**")
            st.write(list(data.columns))
            
            # Check dates
            if 'Date' in data.columns:
                st.write(f"**Date range:** {data['Date'].min()} to {data['Date'].max()}")
            else:
                st.error("❌ No Date column in combined data!")
            
            # Check for Year/Month columns
            if 'Year' in data.columns:
                years = sorted(data['Year'].unique())
                st.write(f"**Years:** {years}")
            else:
                st.error("❌ No Year column!")
            
            if 'Month' in data.columns:
                months = sorted(data['Month'].unique())
                st.write(f"**Month numbers:** {months}")
            else:
                st.error("❌ No Month column!")
            
            if 'YearMonth' in data.columns:
                year_months = sorted(data['YearMonth'].unique())
                st.write(f"**Year-Months:** {year_months}")
                
                # Count per month
                st.write("**Transactions per month:**")
                month_counts = data.groupby('YearMonth').size().reset_index(name='Count')
                st.dataframe(month_counts)
            else:
                st.error("❌ No YearMonth column!")
            
            # Show sample
            st.write("**Sample of combined data:**")
            display_cols = ['Date', 'Description', 'Amount']
            if 'YearMonth' in data.columns:
                display_cols.append('YearMonth')
            if 'Year' in data.columns:
                display_cols.append('Year')
            if 'Month' in data.columns:
                display_cols.append('Month')
            
            available_cols = [col for col in display_cols if col in data.columns]
            st.dataframe(data[available_cols].head(20))
            
    except Exception as e:
        st.error(f"Error loading combined data: {e}")
        import traceback
        st.code(traceback.format_exc())



# Add this to your dashboard or create a temporary button to access it
if st.session_state.authenticated:
    if st.sidebar.button("🔍 Open Diagnostic Tool"):
        diagnostic_page()


if __name__ == "__main__":
    main()
