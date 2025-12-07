# app.py
"""
Main application entry point
Handles routing and page rendering
"""

import streamlit as st
from config import APP_TITLE, APP_ICON
from auth import logout
from styles import apply_custom_styles
from pages.auth_pages import login_page, register_page
from pages.dashboard import dashboard_page
from password_reset import forgot_password_page, reset_password_page
from database import get_user_preferences, save_user_preferences
from data_loader import clear_data_cache
from config import DEFAULT_CATEGORY_MAPPING, DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
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
    
    # CRITICAL: Hide the auto-generated sidebar navigation
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        section[data-testid="stSidebarNav"] {
            display: none !important;
        }
        .css-1544g2n {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
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
    """Render clean, minimal sidebar"""
    with st.sidebar:
        # Logo/Brand
        st.markdown("""
            <div style='text-align: center; padding: 2rem 1rem 1rem 1rem;'>
                <div style='font-size: 3rem; margin-bottom: 0.5rem;'>💼</div>
                <h2 style='margin: 0; font-size: 1.5rem; font-weight: 700;'>Finance Hub</h2>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # User info card
        st.markdown(f"""
            <div style='background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1rem; margin-bottom: 1rem;'>
                <div style='display: flex; align-items: center; margin-bottom: 0.5rem;'>
                    <div style='font-size: 2rem; margin-right: 0.75rem;'>👤</div>
                    <div>
                        <div style='font-weight: 600; font-size: 1.1rem;'>{st.session_state.user['username']}</div>
                        <div style='font-size: 0.85rem; opacity: 0.8;'>{st.session_state.user['email']}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user.get('last_login'):
            last_login = str(st.session_state.user['last_login'])
            st.caption(f"🕐 Last login: {last_login[:19]}")
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("##### ⚡ Quick Actions")
        
        if st.button("📊 Analysis", use_container_width=True, key="sidebar_analysis"):
            st.session_state.selected_feature = 'analysis'
            st.rerun()
        
        if st.button("📅 Budgets", use_container_width=True, key="sidebar_budget"):
            st.session_state.selected_feature = 'planner'
            st.rerun()
        
        if st.button("🔮 Time Machine", use_container_width=True, key="sidebar_timemachine"):
            st.session_state.selected_feature = 'timemachine'
            st.rerun()
        
        if st.button("🏠 Dashboard", use_container_width=True, key="sidebar_home"):
            st.session_state.selected_feature = None
            st.rerun()
        
        st.markdown("---")
        
        # Settings (collapsed by default)
        with st.expander("⚙️ Settings"):
            render_settings_compact()
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            logout()


def render_settings_compact():
    """Render compact settings in sidebar"""
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
    st.markdown("**💰 Monthly Savings Goal**")
    new_savings_goal = st.number_input(
        "Target (J$)",
        min_value=0,
        value=int(savings_goal),
        step=500,
        key="sidebar_savings_goal",
        label_visibility="collapsed"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Top 3 budget categories
    st.markdown("**📊 Top Budget Limits**")
    new_budgets = monthly_budgets.copy()
    
    top_3 = ["Food", "Grocery", "Utilities"]
    for category in top_3:
        new_budgets[category] = st.number_input(
            category,
            min_value=0,
            value=int(monthly_budgets.get(category, 0)),
            step=500,
            key=f"sidebar_compact_{category}"
        )
    
    st.caption("💡 Edit more in Budget Planner")
    
    # Save button
    if st.button("💾 Save", use_container_width=True, key="save_sidebar_settings"):
        if save_user_preferences(
            st.session_state.user['id'],
            category_keywords,
            new_budgets,
            new_savings_goal
        ):
            st.success("✅ Saved!")
            clear_data_cache()
            st.rerun()
        else:
            st.error("❌ Failed")


if __name__ == "__main__":
    main()
