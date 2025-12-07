# pages/__init__.py
"""
Pages module - exports all page rendering functions
TEMPORARY VERSION - Time Machine disabled until syntax error is fixed
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

# TEMPORARY: Create placeholder for Time Machine (don't import the broken file)
def financial_time_machine_page():
    """Placeholder for Time Machine while we fix syntax errors"""
    import streamlit as st
    
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🔮 Financial Time Machine")
    with col2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
    
    st.markdown("---")
    
    st.warning("⚠️ Financial Time Machine temporarily disabled")
    st.info("There's a syntax error in pages/financial_time_machine.py that needs to be fixed")
    
    st.markdown("### 🔧 How to Fix:")
    st.markdown("""
    1. Delete the file: `pages/financial_time_machine.py`
    2. Create a new empty file with that name
    3. Copy the code from the minimal test version (Artifact #10)
    4. Save and redeploy
    5. Once that works, replace with the full version
    """)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Export all functions
__all__ = [
    'login_page',
    'register_page', 
    'dashboard_page',
    'spending_analysis_page',
    'financial_time_machine_page',  # Placeholder version
]
