# app.py - DIAGNOSTIC VERSION
"""
Main application entry point with detailed error checking
"""

import streamlit as st
import sys
import os

# Print diagnostic information
st.write("### 🔍 Diagnostic Information")
st.write(f"**Python Version:** {sys.version}")
st.write(f"**Current Directory:** {os.getcwd()}")
st.write(f"**Python Path:** {sys.path}")

# Check if pages directory exists
pages_exists = os.path.exists('pages')
st.write(f"**Pages directory exists:** {pages_exists}")

if pages_exists:
    pages_contents = os.listdir('pages')
    st.write(f"**Pages directory contents:** {pages_contents}")
    
    # Check for __init__.py
    has_init = '__init__.py' in pages_contents
    st.write(f"**Has __init__.py:** {has_init}")

st.write("---")

# Try imports one by one with error catching
st.write("### 📦 Import Testing")

# Test 1: Import config
try:
    from config import APP_TITLE, APP_ICON
    st.success("✅ config module imported successfully")
except Exception as e:
    st.error(f"❌ Error importing config: {e}")
    st.stop()

# Test 2: Import auth
try:
    from auth import init_session_state, logout
    st.success("✅ auth module imported successfully")
except Exception as e:
    st.error(f"❌ Error importing auth: {e}")
    st.stop()

# Test 3: Import styles
try:
    from styles import apply_custom_styles
    st.success("✅ styles module imported successfully")
except Exception as e:
    st.error(f"❌ Error importing styles: {e}")
    st.stop()

# Test 4: Import password_reset
try:
    from password_reset import forgot_password_page, reset_password_page
    st.success("✅ password_reset module imported successfully")
except Exception as e:
    st.error(f"❌ Error importing password_reset: {e}")
    st.stop()

# Test 5: Import pages.auth_pages
try:
    from pages.auth_pages import login_page, register_page
    st.success("✅ pages.auth_pages imported successfully")
except Exception as e:
    st.error(f"❌ Error importing pages.auth_pages: {e}")
    st.write("**Error details:**")
    st.code(str(e))
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# Test 6: Import pages.dashboard
try:
    from pages.dashboard import dashboard_page
    st.success("✅ pages.dashboard imported successfully")
except Exception as e:
    st.error(f"❌ Error importing pages.dashboard: {e}")
    st.write("**Error details:**")
    st.code(str(e))
    import traceback
    st.code(traceback.format_exc())
    st.stop()

st.write("---")
st.success("### ✅ All imports successful!")
st.info("Replace this diagnostic version with the actual app.py once imports work")

# Simple test of functionality
st.write("### 🧪 Function Test")

try:
    init_session_state()
    st.success("✅ Session state initialized")
except Exception as e:
    st.error(f"❌ Error initializing session state: {e}")

try:
    apply_custom_styles()
    st.success("✅ Styles applied")
except Exception as e:
    st.error(f"❌ Error applying styles: {e}")
