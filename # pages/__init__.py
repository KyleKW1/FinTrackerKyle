# pages/__init__.py
"""
Pages module - exports all page rendering functions
Handles missing pages gracefully
"""

# Import required pages (these MUST exist)
try:
    from .auth_pages import login_page, register_page
    from .dashboard import dashboard_page
    print("✓ Successfully imported auth_pages and dashboard")
except ImportError as e:
    print(f"ERROR importing required pages: {e}")
    import streamlit as st
    st.error(f"Critical error: Cannot import required pages: {e}")
    st.stop()

# Try to import optional pages
try:
    from .spending_analysis import spending_analysis_page
    HAS_SPENDING_ANALYSIS = True
    print("✓ Successfully imported spending_analysis")
except ImportError as e:
    print(f"WARNING: Could not import spending_analysis: {e}")
    HAS_SPENDING_ANALYSIS = False
    
    # Create a placeholder function
    def spending_analysis_page():
        import streamlit as st
        st.error("⚠️ Spending Analysis page not yet created")
        st.info("Create pages/spending_analysis.py to enable this feature")
        if st.button("← Back to Dashboard"):
            st.session_state.selected_feature = None
            st.rerun()

__all__ = [
    'login_page',
    'register_page',
    'dashboard_page',
    'spending_analysis_page',
]

print(f"Pages module loaded. HAS_SPENDING_ANALYSIS: {HAS_SPENDING_ANALYSIS}")
