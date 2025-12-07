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

def diagnostic_page():
    """Detailed diagnostic to see why files are failing"""
    st.title("🔍 File Processing Diagnostic")
    
    st.info("This will show you exactly what's happening with each file")
    
    connection = create_connection()
    if not connection:
        st.error("Cannot connect to database")
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, filename, file_type, file_data FROM user_files WHERE user_id = %s ORDER BY filename",
            (st.session_state.user['id'],)
        )
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        
        st.success(f"Found {len(files)} files in database")
        
        all_results = []
        
        for idx, file_info in enumerate(files):
            filename = file_info['filename']
            
            with st.expander(f"📄 {idx+1}. {filename}", expanded=False):
                try:
                    file_bytes = BytesIO(file_info['file_data'])
                    
                    st.write(f"**File size:** {len(file_info['file_data'])} bytes")
                    
                    # Try to extract text
                    file_bytes.seek(0)
                    with pdfplumber.open(file_bytes) as pdf:
                        st.write(f"**Pages:** {len(pdf.pages)}")
                        
                        # Get first page text
                        first_page_text = pdf.pages[0].extract_text()
                        
                        st.write("**🔍 Year Detection:**")
                        year_found = None
                        
                        # Try all year patterns
                        year_patterns = [
                            (r'(\d{2}/[A-Za-z]{3}/(\d{4}))', 'Full date (DD/Mon/YYYY)'),
                            (r'Statement.*?(\d{4})', 'Statement line'),
                            (r'Period.*?(\d{4})', 'Period line'),
                            (r'P\.O\.,?\s*\d{2}-\d{2}-(\d{4})', 'Address format'),
                            (r'\b(202[0-9])\b', 'Any 202X year'),
                        ]
                        
                        for pattern, desc in year_patterns:
                            matches = re.findall(pattern, first_page_text)
                            if matches:
                                if isinstance(matches[0], tuple):
                                    year_found = matches[0][-1]
                                else:
                                    year_found = matches[0]
                                st.success(f"✅ Found year: **{year_found}** (using: {desc})")
                                st.caption(f"Match: {matches[0]}")
                                break
                        
                        if not year_found:
                            st.error("❌ Could NOT detect year!")
                            st.write("**First 30 lines:**")
                            st.code('\n'.join(first_page_text.split('\n')[:30]))
                        
                        st.write("---")
                        st.write("**🔍 Transaction Line Detection:**")
                        
                        # Look for transaction patterns
                        transaction_patterns = [
                            (r'\d{2}/[A-Za-z]{3}\s+.+?\s+-?[\d,]+\.\d{2}\s+[\d,]+\.\d{2}', 'With balance'),
                            (r'\d{2}/[A-Za-z]{3}\s+.+?\s+-?[\d,]+\.\d{2}', 'Without balance'),
                        ]
                        
                        found_any = False
                        for pattern, desc in transaction_patterns:
                            matches = re.findall(pattern, first_page_text)
                            if matches:
                                st.success(f"✅ Found {len(matches)} lines matching pattern: **{desc}**")
                                st.write("**First 5 matches:**")
                                for i, match in enumerate(matches[:5], 1):
                                    st.code(f"{i}. {match}")
                                found_any = True
                                break
                        
                        if not found_any:
                            st.error("❌ Could NOT find ANY transaction patterns!")
                            st.write("**All lines from first page:**")
                            lines = first_page_text.split('\n')
                            for i, line in enumerate(lines, 1):
                                if line.strip():
                                    st.text(f"{i:3d}: {line}")
                    
                    st.write("---")
                    st.write("**📊 Processing Result:**")
                    
                    # Actually try to process it
                    file_bytes.seek(0)
                    df = process_pdf_ncb(file_bytes)
                    
                    if df.empty:
                        st.error(f"❌ **FAILED** - Extracted 0 transactions")
                        result = {
                            'filename': filename,
                            'status': 'FAILED',
                            'transactions': 0,
                            'year': year_found or 'Not detected',
                            'issue': 'No transactions extracted'
                        }
                    else:
                        st.success(f"✅ **SUCCESS** - Extracted {len(df)} transactions")
                        st.write(f"**Date range:** {df['Date'].min()} to {df['Date'].max()}")
                        st.write(f"**Sample transactions:**")
                        st.dataframe(df[['Date', 'Description', 'Amount', 'Category']].head(10))
                        
                        result = {
                            'filename': filename,
                            'status': 'SUCCESS',
                            'transactions': len(df),
                            'year': year_found or 'Auto',
                            'date_range': f"{df['Date'].min()} to {df['Date'].max()}"
                        }
                    
                    all_results.append(result)
                    
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    
                    all_results.append({
                        'filename': filename,
                        'status': 'ERROR',
                        'transactions': 0,
                        'year': 'N/A',
                        'issue': str(e)
                    })
        
        # Summary
        st.markdown("---")
        st.subheader("📊 Summary")
        
        summary_df = pd.DataFrame(all_results)
        st.dataframe(summary_df, use_container_width=True)
        
        success_count = len([r for r in all_results if r['status'] == 'SUCCESS'])
        failed_count = len([r for r in all_results if r['status'] == 'FAILED'])
        
        st.write(f"**✅ Successful:** {success_count} files")
        st.write(f"**❌ Failed:** {failed_count} files")
        
        if failed_count > 0:
            st.warning("⚠️ The files that failed need different parsing patterns. Share the output above and I'll fix them!")
        
    except Exception as e:
        st.error(f"Diagnostic error: {e}")


# Add this to your main_app() function, in the sidebar:
def main_app():
    apply_custom_styles()
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.caption(f"📧 {st.session_state.user['email']}")
        st.markdown("---")
        
        # ADD THIS BUTTON
        if st.button("🔍 Diagnostic Tool", use_container_width=True):
            st.session_state.show_diagnostic = True
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Check if diagnostic should be shown
    if st.session_state.get('show_diagnostic', False):
        if st.button("← Back to Dashboard"):
            st.session_state.show_diagnostic = False
            st.rerun()
        diagnostic_page()
        return
    


if __name__ == "__main__":
    main()
