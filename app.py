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
    init_session_state()
    
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
    from utils import get_spending_by_category, compare_budget_vs_actual, generate_alert_email_body, send_email_alert
    
    st.caption("Get notified when you exceed budgets")
    
    # Load data
    data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.info("📊 Upload data to see alerts")
        return
    
    prefs = get_user_preferences(st.session_state.user['id'])
    if not prefs or not prefs.get('monthly_budgets'):
        st.info("⚙️ Set budgets above first")
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
    
    comparison = compare_budget_vs_actual(budgets, summary)
    overspent = comparison[comparison['Amount'] > comparison['Budget']]
    
    if overspent.empty:
        st.success("✅ All within budget!")
    else:
        st.warning(f"⚠️ Over budget in {len(overspent)} categories")
        
        for _, row in overspent.iterrows():
            st.caption(f"**{row['Spending Category']}**: J${row['Amount']:,.0f} / J${row['Budget']:,.0f}")
        
        # Email alert
        recipient_email = st.text_input(
            "Email",
            value=st.session_state.user['email'],
            key="alert_email"
        )
        
        if st.button("📧 Send Alert", use_container_width=True, key="send_alert"):
            if recipient_email:
                email_body = generate_alert_email_body(
                    st.session_state.user['username'],
                    latest_month,
                    overspent
                )
                
                if send_email_alert(
                    recipient_email,
                    f"Budget Alert - {latest_month}",
                    email_body
                ):
                    st.success("✅ Email sent!")


if __name__ == "__main__":
    main()
