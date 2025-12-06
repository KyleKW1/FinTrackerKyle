# pages/__init__.py
"""
Pages module - exports all page rendering functions
"""

# Use relative imports (. means current package)
from .auth_pages import login_page, register_page
from .dashboard import dashboard_page

# Try to import spending_analysis (optional)
try:
    from .spending_analysis import spending_analysis_page
    HAS_SPENDING_ANALYSIS = True
except ImportError as e:
    HAS_SPENDING_ANALYSIS = False
    print(f"Warning: spending_analysis not available: {e}")
    
    # Create placeholder function
    def spending_analysis_page():
        import streamlit as st
        st.error("⚠️ Spending Analysis page not yet created")
        st.info("Create pages/spending_analysis.py to enable this feature")
        if st.button("← Back to Dashboard"):
            st.session_state.selected_feature = None
            st.rerun()

# Export all functions
__all__ = [
    'login_page',
    'register_page', 
    'dashboard_page',
    'spending_analysis_page',
]
