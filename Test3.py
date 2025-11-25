import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import re
import pandas as pd
import plotly.express as px 
import calendar
import smtplib
from email.message import EmailMessage
from io import BytesIO
import pdfplumber
from functools import lru_cache
from datetime import datetime
import json

try:
    import pdfkit
    PDFKIT_INSTALLED = True
except ImportError:
    PDFKIT_INSTALLED = False

from fpdf import FPDF

# ============================================
# ENHANCED UI STYLING
# ============================================

def apply_custom_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Card styling */
    .stat-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border-left: 4px solid;
        margin-bottom: 1rem;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    .stat-card.income { border-left-color: #10b981; }
    .stat-card.spending { border-left-color: #ef4444; }
    .stat-card.savings { border-left-color: #3b82f6; }
    
    .stat-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
    }
    
    .stat-change {
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .stat-change.positive { color: #10b981; }
    .stat-change.negative { color: #ef4444; }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Auth container */
    .auth-container {
        background: white;
        border-radius: 24px;
        padding: 3rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        margin: 2rem auto;
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .auth-subtitle {
        color: #6b7280;
        font-size: 1rem;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1f2937 0%, #111827 100%);
    }
    
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Feature card */
    .feature-card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
        cursor: pointer;
    }
    
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
    }
    
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .feature-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
    }
    
    .feature-desc {
        font-size: 0.875rem;
        color: #6b7280;
    }
    
    /* File card */
    .file-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border: 2px solid #e5e7eb;
        transition: all 0.3s ease;
    }
    
    .file-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.1);
    }
    
    /* Content container */
    .content-container {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
    }
    
    /* Metric container */
    .metric-container {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-top: 4px solid;
    }
    
    .metric-container.green { border-top-color: #10b981; }
    .metric-container.red { border-top-color: #ef4444; }
    .metric-container.blue { border-top-color: #3b82f6; }
    
    /* Alert styling */
    .stAlert {
        border-radius: 12px;
        border: none;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    /* DataFrame styling */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Section header */
    .section-header {
        color: white;
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
        margin: 2rem 0 1rem 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: white;
        border-radius: 12px;
        font-weight: 600;
        border: 2px solid #e5e7eb;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# DATABASE CONFIGURATION (Your existing code)
# ============================================

DB_CONFIG = {
    'host': 'mysql-11beff9b-kamarwatson36-874b.g.aivencloud.com',
    'port': 11510,
    'user': 'avnadmin',
    'password': 'AVNS_Dxyg2mu3MEiRoVyasff',
    'database': 'defaultdb',
    'ssl_disabled': False,
    'ssl_verify_cert': True,
    'ssl_verify_identity': True
}

def create_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            ssl_disabled=DB_CONFIG['ssl_disabled'],
            connection_timeout=30,
            autocommit=False
        )
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(username, email, password):
    connection = create_connection()
    if not connection:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True, "Registration successful!"
    except mysql.connector.IntegrityError:
        connection.close()
        return False, "Username or email already exists"
    except Error as e:
        connection.close()
        return False, f"Registration error: {e}"

def authenticate_user(username, password):
    connection = create_connection()
    if not connection:
        return False, None
    
    try:
        cursor = connection.cursor(dictionary=True)
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password_hash = %s",
            (username, password_hash)
        )
        user = cursor.fetchone()
        if user:
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user['id'],)
            )
            connection.commit()
        cursor.close()
        connection.close()
        return user is not None, user
    except Error as e:
        st.error(f"Authentication error: {e}")
        connection.close()
        return False, None

# ============================================
# SESSION STATE
# ============================================

def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'login'
    st.rerun()

# ============================================
# ENHANCED LOGIN PAGE
# ============================================

def enhanced_login_page():
    apply_custom_styles()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">💼 Finance Hub</h1>
                    <p class="auth-subtitle">Welcome back! Please login to your account</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🚀 Login", use_container_width=True):
                if username and password:
                    success, user = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("✅ Login successful!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        with col_btn2:
            if st.button("📝 Register", use_container_width=True):
                st.session_state.page = 'register'
                st.rerun()
        
        st.info("💡 **Demo:** Create a new account to get started!")

# ============================================
# ENHANCED REGISTER PAGE
# ============================================

def enhanced_register_page():
    apply_custom_styles()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">📝 Create Account</h1>
                    <p class="auth-subtitle">Join Finance Hub and take control of your finances</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Choose a username (min 3 characters)", key="reg_username")
        email = st.text_input("Email", placeholder="your.email@example.com", key="reg_email")
        password = st.text_input("Password", type="password", placeholder="Choose a strong password (min 6 characters)", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="reg_confirm")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✨ Create Account", use_container_width=True):
                if not username or not email or not password:
                    st.error("❌ All fields are required")
                elif len(username) < 3:
                    st.error("❌ Username must be at least 3 characters")
                elif not validate_email(email):
                    st.error("❌ Invalid email format")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    success, message = register_user(username, email, password)
                    if success:
                        st.success(f"✅ {message}")
                        st.info("Please login with your new account")
                        st.balloons()
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        with col_btn2:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()

# ============================================
# ENHANCED MAIN APP
# ============================================

def enhanced_main_app():
    apply_custom_styles()
    
    # Sidebar
    with st.sidebar:
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
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
    
    # Header
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0 1rem 0;'>
            <h1 style='font-size: 3rem; font-weight: 700; color: white; margin-bottom: 0.5rem;'>
                💼 Finance Hub Dashboard
            </h1>
            <p style='font-size: 1.25rem; color: rgba(255, 255, 255, 0.9);'>
                Welcome back, {}! Your financial command center
            </p>
        </div>
    """.format(st.session_state.user['username']), unsafe_allow_html=True)
    
    # Quick stats (placeholder - replace with real data)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="stat-card income">
                <div class="stat-title">💰 Total Income</div>
                <div class="stat-value">J$45,000</div>
                <div class="stat-change positive">↑ 12% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="stat-card spending">
                <div class="stat-title">💸 Total Spending</div>
                <div class="stat-value">J$32,500</div>
                <div class="stat-change negative">↑ 5% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div class="stat-card savings">
                <div class="stat-title">🎯 Net Savings</div>
                <div class="stat-value">J$12,500</div>
                <div class="stat-change positive">↑ 28% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<h2 class='section-header'>Choose a Feature</h2>", unsafe_allow_html=True)
    
    # Feature selection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Spending Analysis</div>
                <div class="feature-desc">Track and analyze your spending patterns with detailed insights</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Analysis", key="btn_analysis", use_container_width=True):
            st.session_state.selected_feature = 'analysis'
            st.rerun()
    
    with col2:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📅</div>
                <div class="feature-title">Budget Planner</div>
                <div class="feature-desc">Create and manage your monthly budgets efficiently</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Planner", key="btn_planner", use_container_width=True):
            st.session_state.selected_feature = 'planner'
            st.rerun()
    
    with col3:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🌐</div>
                <div class="feature-title">Network Analysis</div>
                <div class="feature-desc">Visualize transaction patterns and relationships</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Network", key="btn_network", use_container_width=True):
            st.session_state.selected_feature = 'network'
            st.rerun()
    
    # Feature content (if selected)
    if 'selected_feature' in st.session_state:
        st.markdown("---")
        
        if st.session_state.selected_feature == 'analysis':
            show_spending_analysis()
        elif st.session_state.selected_feature == 'planner':
            show_budget_planner()
        elif st.session_state.selected_feature == 'network':
            show_network_analysis()

# ============================================
# FEATURE PAGES (Simplified versions)
# ============================================

def show_spending_analysis():
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    st.markdown("### 📊 Spending Analysis")
    st.info("📁 Upload your CSV or PDF bank statements to get started with analysis")
    
    uploaded_files = st.file_uploader(
        "Upload your files",
        type=["csv", "pdf"],
        accept_multiple_files=True,
        key="analysis_uploader"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        st.info("💡 Your spending analysis will appear here once files are processed")
    
    st.markdown("</div>", unsafe_allow_html=True)

def show_budget_planner():
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    st.markdown("### 📅 Budget Planner")
    st.info("🎯 Set up your monthly budgets and track your progress")
    
    categories = ["Food", "Grocery", "Utilities", "Transport", "Entertainment"]
    
    for category in categories:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.text(f"{category}")
        with col2:
            st.number_input(f"Budget", min_value=0, value=5000, step=500, key=f"budget_{category}", label_visibility="collapsed")
    
    if st.button("💾 Save Budget", use_container_width=True):
        st.success("✅ Budget saved successfully!")
    
    st.markdown("</div>", unsafe_allow_html=True)

def show_network_analysis():
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    st.markdown("### 🌐 Network Analysis")
    st.info("🔍 Visualize your transaction patterns and spending relationships")
    st.warning("⚠️ This feature requires transaction data. Please upload files in Spending Analysis first.")
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================
# MAIN FUNCTION
# ============================================

def main():
    st.set_page_config(
        page_title="Finance Hub - Enhanced",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    
    if not st.session_state.authenticated:
        if st.session_state.page == 'register':
            enhanced_register_page()
        else:
            enhanced_login_page()
    else:
        enhanced_main_app()

if __name__ == "__main__":
    main()
