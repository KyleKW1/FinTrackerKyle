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
# FILE MANAGEMENT FUNCTIONS
# ============================================

def save_user_file(user_id, filename, file_data, file_type):
    """Save uploaded file to database"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO user_files (user_id, filename, file_data, file_type) VALUES (%s, %s, %s, %s)",
            (user_id, filename, file_data, file_type)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error saving file: {e}")
        connection.close()
        return False

def delete_user_file(file_id, user_id):
    """Delete a user's file"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM user_files WHERE id = %s AND user_id = %s",
            (file_id, user_id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error deleting file: {e}")
        connection.close()
        return False

def get_user_files_paginated(user_id, page=0, page_size=9):
    """Get user files with pagination"""
    connection = create_connection()
    if not connection:
        return [], 0
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total FROM user_files WHERE user_id = %s", (user_id,))
        total_files = cursor.fetchone()['total']
        
        offset = page * page_size
        cursor.execute(
            "SELECT id, filename, file_type, upload_date FROM user_files WHERE user_id = %s ORDER BY upload_date DESC LIMIT %s OFFSET %s",
            (user_id, page_size, offset)
        )
        files = cursor.fetchall()
        
        cursor.close()
        connection.close()
        return files, total_files
    except Error as e:
        st.error(f"Error retrieving files: {e}")
        connection.close()
        return [], 0

def load_all_user_data(user_id):
    """Load all user transaction data from files"""
    connection = create_connection()
    if not connection:
        return pd.DataFrame()
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT file_data, file_type FROM user_files WHERE user_id = %s",
            (user_id,)
        )
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        
        all_data = []
        for file_info in files:
            file_data = file_info['file_data']
            file_type = file_info['file_type']
            
            try:
                if file_type == 'csv':
                    df = pd.read_csv(BytesIO(file_data))
                elif file_type == 'pdf':
                    df = extract_from_pdf(BytesIO(file_data))
                else:
                    continue
                
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                st.warning(f"Could not process file: {e}")
                continue
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = process_dataframe(combined_df)
            return combined_df
        else:
            return pd.DataFrame()
            
    except Error as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def extract_from_pdf(pdf_file):
    """Extract transaction data from PDF"""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() + "\n"
        
        lines = all_text.split('\n')
        data = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    date_str = parts[0]
                    description = ' '.join(parts[1:-2])
                    amount = float(parts[-1].replace(',', '').replace('$', ''))
                    category = 'Debit' if amount < 0 else 'Credit'
                    
                    data.append({
                        'Date': date_str,
                        'Description': description,
                        'Amount': abs(amount),
                        'Category': category
                    })
                except:
                    continue
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return pd.DataFrame()

def process_dataframe(df):
    """Process and standardize dataframe"""
    # Standardize column names first
    df = standardize_dataframe_columns(df)
    
    # Convert Date column
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df['Month-Name'] = df['Date'].dt.month_name()
        df['Month-Year'] = df['Date'].dt.strftime('%B %Y')
        df['YearMonth'] = df['Date'].dt.strftime('%Y-%m')
    
    # Ensure Amount is numeric (it's already been converted in standardize_dataframe_columns)
    if 'Amount' in df.columns:
        df = df.dropna(subset=['Amount'])
    
    # Ensure Description exists and is string
    if 'Description' in df.columns:
        df['Description'] = df['Description'].astype(str).fillna('Unknown')
    
    return df


def process_dataframe(df):
    """Process and standardize dataframe"""
    # Standardize column names first
    df = standardize_dataframe_columns(df)
    
    # Convert Date column
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df['Month-Name'] = df['Date'].dt.month_name()
        df['Month-Year'] = df['Date'].dt.strftime('%B %Y')
        df['YearMonth'] = df['Date'].dt.strftime('%Y-%m')
    
    # Amount is already numeric from standardize_dataframe_columns
    if 'Amount' in df.columns:
        df = df.dropna(subset=['Amount'])
        # Just ensure it's float type (it should already be)
        df['Amount'] = df['Amount'].astype(float)
    
    # Ensure Description exists and is string
    if 'Description' in df.columns:
        df['Description'] = df['Description'].astype(str).fillna('Unknown')
    
    return df

def get_user_preferences(user_id):
    """Get user preferences"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM user_preferences WHERE user_id = %s",
            (user_id,)
        )
        prefs = cursor.fetchone()
        cursor.close()
        connection.close()
        return prefs
    except Error as e:
        connection.close()
        return None

def save_user_preferences(user_id, category_keywords, monthly_budgets, savings_goal):
    """Save user preferences"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        cursor.execute("SELECT id FROM user_preferences WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone()
        
        category_json = json.dumps(category_keywords)
        budgets_json = json.dumps(monthly_budgets)
        
        if exists:
            cursor.execute(
                "UPDATE user_preferences SET category_keywords = %s, monthly_budgets = %s, savings_goal = %s WHERE user_id = %s",
                (category_json, budgets_json, savings_goal, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO user_preferences (user_id, category_keywords, monthly_budgets, savings_goal) VALUES (%s, %s, %s, %s)",
                (user_id, category_json, budgets_json, savings_goal)
            )
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error saving preferences: {e}")
        connection.close()
        return False

def get_monthly_summary(user_id, year_month):
    """Get cached monthly summary"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM monthly_summaries WHERE user_id = %s AND year_month = %s",
            (user_id, year_month)
        )
        summary = cursor.fetchone()
        cursor.close()
        connection.close()
        return summary
    except Error as e:
        connection.close()
        return None

def compute_monthly_summary(user_id, year_month, data):
    """Compute and store monthly summary"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        month_data = data[data['YearMonth'] == year_month]
        
        total_income = month_data[month_data['Category'] == 'Credit']['Amount'].sum()
        total_spending = month_data[month_data['Category'] == 'Debit']['Amount'].sum()
        net_savings = total_income - total_spending
        
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO monthly_summaries (user_id, year_month, total_income, total_spending, net_savings)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE total_income = %s, total_spending = %s, net_savings = %s""",
            (user_id, year_month, total_income, total_spending, net_savings, total_income, total_spending, net_savings)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        connection.close()
        return False

@lru_cache(maxsize=1000)
def classify_expense_cached(description, category_json):
    """Cached expense classification"""
    category_keywords = json.loads(category_json)
    desc_lower = description.lower()
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category
    return "Other"

def send_email_alert(to_email, subject, body, sender_email, sender_password, smtp_server, smtp_port):
    """Send email alerts"""
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        msg.set_content(body)
        
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
        
        st.success("✅ Email alert sent successfully!")
        return True
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
        return False

def export_to_excel(df):
    """Export dataframe to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')
    return output.getvalue()

def export_to_pdf(text):
    """Export text to PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.cell(200, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    return bytes(pdf.output())


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

    # Calculate real stats from user data
    user_data = load_all_user_data(st.session_state.user['id'])
    
    if not user_data.empty and all(col in user_data.columns for col in ['Date', 'Amount', 'Category', 'YearMonth']):
        # Get current and previous month data
        available_months = sorted(user_data['YearMonth'].unique())
        
        if len(available_months) >= 1:
            current_month = available_months[-1]
            current_data = user_data[user_data['YearMonth'] == current_month]
            
            current_income = float(current_data[current_data['Category'] == 'Credit']['Amount'].sum())
            current_spending = float(current_data[current_data['Category'] == 'Debit']['Amount'].sum())
            current_savings = float(current_income - current_spending)
            
            # Calculate percentage changes if previous month exists
            if len(available_months) >= 2:
                prev_month = available_months[-2]
                prev_data = user_data[user_data['YearMonth'] == prev_month]
                
                prev_income = prev_data[prev_data['Category'] == 'Credit']['Amount'].sum()
                prev_spending = prev_data[prev_data['Category'] == 'Debit']['Amount'].sum()
                prev_savings = prev_income - prev_spending
                
                prev_income = float(prev_data[prev_data['Category'] == 'Credit']['Amount'].sum())
                prev_spending = float(prev_data[prev_data['Category'] == 'Debit']['Amount'].sum())
                prev_savings = float(prev_income - prev_spending)
                
                income_arrow = "↑" if income_change > 0 else "↓"
                spending_arrow = "↑" if spending_change > 0 else "↓"
                savings_arrow = "↑" if savings_change > 0 else "↓"
                
                income_class = "positive" if income_change > 0 else "negative"
                spending_class = "negative" if spending_change > 0 else "positive"
                savings_class = "positive" if savings_change > 0 else "negative"
            else:
                income_change = spending_change = savings_change = 0
                income_arrow = spending_arrow = savings_arrow = ""
                income_class = spending_class = savings_class = "positive"
        else:
            current_income = current_spending = current_savings = 0
            income_change = spending_change = savings_change = 0
            income_arrow = spending_arrow = savings_arrow = ""
            income_class = spending_class = savings_class = "positive"
    else:
        current_income = current_spending = current_savings = 0
        income_change = spending_change = savings_change = 0
        income_arrow = spending_arrow = savings_arrow = ""
        income_class = spending_class = savings_class = "positive"
    
    # Display real stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="stat-card income">
                <div class="stat-title">💰 Total Income</div>
                <div class="stat-value">J${current_income:,.0f}</div>
                <div class="stat-change {income_class}">{income_arrow} {abs(income_change):.1f}% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card spending">
                <div class="stat-title">💸 Total Spending</div>
                <div class="stat-value">J${current_spending:,.0f}</div>
                <div class="stat-change {spending_class}">{spending_arrow} {abs(spending_change):.1f}% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card savings">
                <div class="stat-title">🎯 Net Savings</div>
                <div class="stat-value">J${current_savings:,.0f}</div>
                <div class="stat-change {savings_class}">{savings_arrow} {abs(savings_change):.1f}% from last month</div>
            </div>
        """, unsafe_allow_html=True)

    
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

def standardize_dataframe_columns(df):
    """Standardize column names from different bank formats"""
    df = df.copy()
    
    column_mappings = {
        'description': 'Description',
        'desc': 'Description',
        'transaction description': 'Description',
        'details': 'Description',
        'narrative': 'Narrative',
        'particulars': 'Particulars',
        
        'amount': 'Amount',
        'transaction amount': 'Amount',
        'value': 'Amount',
        'debit': 'Amount',
        'credit': 'Amount',
        'total amount': 'Amount',
        
        'date': 'Date',
        'transaction date': 'Date',
        'posting date': 'Date',
        'value date': 'Date',
        'trans date': 'Date',
        
        'type': 'Category',
        'transaction type': 'Category',
        'trans type': 'Category',
        'dr/cr': 'Category',
    }
    
    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=column_mappings)
    
    # Handle Description
    if 'Description' not in df.columns:
        if len(df.columns) >= 2:
            df['Description'] = df.iloc[:, 1].astype(str)
        else:
            df['Description'] = 'Unknown'
    
    # Handle Date
    if 'Date' not in df.columns:
        if len(df.columns) >= 1:
            df['Date'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        else:
            df['Date'] = pd.Timestamp.now()
    
    # Handle Amount
    if 'Amount' not in df.columns:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            df['Amount'] = df[numeric_cols[0]].apply(lambda x: float(x) if pd.notna(x) else 0.0)
        else:
            for col in df.columns:
                try:
                    test_series = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce')
                    if test_series.notna().sum() > len(df) * 0.5:
                        df['Amount'] = test_series.fillna(0.0).abs()
                        break
                except:
                    continue
            else:
                df['Amount'] = 0.0
    else:
        def safe_float_convert(x):
            try:
                if pd.isna(x):
                    return 0.0
                if isinstance(x, str):
                    x = x.replace('$', '').replace(',', '').replace('J', '').strip()
                return float(x)
            except (ValueError, TypeError):
                return 0.0
        
        df['Amount'] = df['Amount'].apply(safe_float_convert)
    
    # Ensure Amount is positive
    df['Amount'] = df['Amount'].abs()
    
    # Handle Category - use trans type if it exists
    if 'Category' in df.columns:
        # Map the values from trans type
        def map_category(val):
            if pd.isna(val):
                return 'Debit'
            val_str = str(val).upper().strip()
            if val_str in ['CR', 'CREDIT', 'C', 'DEP', 'DEPOSIT']:
                return 'Credit'
            elif val_str in ['DR', 'DEBIT', 'D', 'WD', 'WITHDRAWAL']:
                return 'Debit'
            else:
                return 'Debit'
        
        df['Category'] = df['Category'].apply(map_category)
    else:
        # No category column, use amount-based logic
        df['Category'] = df['Amount'].apply(lambda x: 'Credit' if x >= 0 else 'Debit')
    
    return df
    
def show_spending_analysis():
    """Enhanced spending analysis with full functionality"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)
    st.markdown("### 📊 Spending Analysis")
    
    # File Management Section
    st.markdown("#### 📁 Your Files")
    
    if 'file_page' not in st.session_state:
        st.session_state.file_page = 0
    
    user_files, total_files = get_user_files_paginated(
        st.session_state.user['id'], 
        page=st.session_state.file_page, 
        page_size=9
    )
    
    if total_files > 0:
        st.markdown(f"**You have {total_files} stored file(s)** (Showing page {st.session_state.file_page + 1})")
        
        # Display files in grid
        for i in range(0, len(user_files), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(user_files):
                    file = user_files[i + j]
                    with col:
                        st.markdown(f"""
                            <div class="file-card">
                                <strong>{file['filename']}</strong><br>
                                <small>Uploaded: {str(file['upload_date'])[:19]}</small><br>
                                <small>Type: {file['file_type'].upper()}</small>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"🗑️ Delete", key=f"del_{file['id']}", use_container_width=True):
                            if delete_user_file(file['id'], st.session_state.user['id']):
                                st.success(f"Deleted {file['filename']}")
                                st.rerun()
                            else:
                                st.error("Failed to delete file")
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.file_page > 0:
                if st.button("⬅️ Previous", use_container_width=True):
                    st.session_state.file_page -= 1
                    st.rerun()
        with col3:
            max_pages = (total_files - 1) // 9
            if st.session_state.file_page < max_pages:
                if st.button("Next ➡️", use_container_width=True):
                    st.session_state.file_page += 1
                    st.rerun()
        
        st.markdown("---")
    else:
        st.info("No files uploaded yet. Upload your first file below!")
    
    # File Upload Section
    with st.expander("📤 Upload New Files", expanded=not user_files):
        uploaded_files = st.file_uploader(
            "Upload CSV or PDF files",
            type=["csv", "pdf"],
            accept_multiple_files=True,
            key="file_uploader"
        )
        
        if uploaded_files:
            if st.button("💾 Save Files to Account", use_container_width=True):
                success_count = 0
                for file in uploaded_files:
                    file_data = file.read()
                    file_type = file.name.split('.')[-1].lower()
                    
                    if save_user_file(st.session_state.user['id'], file.name, file_data, file_type):
                        success_count += 1
                    file.seek(0)
                
                if success_count > 0:
                    st.success(f"✅ Saved {success_count} file(s) to your account!")
                    st.rerun()
    
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading your financial data..."):
        data = load_all_user_data(st.session_state.user['id'])
    
    if data.empty:
        st.info("Upload your bank CSV or PDF statements to get started.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Debug: Show columns (you can remove this after testing)
    with st.expander("🔍 Debug: Data Preview", expanded=False):
        st.write("**Available Columns:**", list(data.columns))
        st.write("**Sample Data:**")
        st.dataframe(data.head(3))
    
    # Ensure required columns exist
    required_columns = ['Date', 'Description', 'Amount', 'Category']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
        st.info("Please ensure your CSV has columns for: Date, Description, Amount, and Category")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Load preferences
    user_prefs = get_user_preferences(st.session_state.user['id'])
    
    default_mapping = {
        "Food": ["juici", "kfc", "restaurant", "burger", "pizza", "subway", "mcdonald", "starbucks", "diner", "grill", "v.o.d.a. foods", "cafe blue", "tutti frutti", "popeyesohr", "ribbiz lounge", "beifang kitchen"],
        "Grocery": ["hi-lo", "supermarket", "wholesale", "grocery", "market", "walmart", "costco", "shoppers fair"],
        "Utilities": ["jps", "nwc", "flow", "internet", "light", "water", "electric", "cable", "wifi", "BPYMT"],
        "Transport": ["uber", "taxi", "gas", "shell", "parking", "lyft", "bus"],
        "Income": ["remitly", "deposit", "transfer", "payroll", "salary", "refund", "ELink TRF-FR"],
        "Home Improvement": ["lumber depot limited", "ping's fabric"],
        "Retail & Entertainment": ["boss destinations", "n k wholesale liquor stor", "digicel ding"],
        "Miscellaneous": ["atm", "fee", "charge", "GCT"],
        "Other": ["ELink TRF-To"]
    }
    
    default_budgets = {
        "Food": 15000,
        "Grocery": 10000,
        "Utilities": 8000,
        "Transport": 6000,
        "Miscellaneous": 5000,
        "Income": 0,
        "Retail & Entertainment": 0,
        "Home Improvement": 0,
        "Other": 0
    }
    
    default_savings_goal = 5000
    
    if user_prefs:
        saved_categories = json.loads(user_prefs['category_keywords']) if user_prefs['category_keywords'] else default_mapping
        saved_budgets = json.loads(user_prefs['monthly_budgets']) if user_prefs['monthly_budgets'] else default_budgets
        saved_goal = float(user_prefs['savings_goal']) if user_prefs['savings_goal'] else default_savings_goal
    else:
        saved_categories = default_mapping
        saved_budgets = default_budgets
        saved_goal = default_savings_goal
    
    # Sidebar for preferences
    st.sidebar.header("🗂 Customize Categories and Budgets")
    
    CATEGORY_KEYWORDS = {}
    st.sidebar.markdown("### Edit Categories and Keywords")
    for category, keywords in saved_categories.items():
        with st.sidebar.expander(f"{category} Keywords", expanded=False):
            kw_text = st.sidebar.text_area(
                label=f"Keywords for {category} (comma separated)",
                value=", ".join(keywords),
                key=f"kw_{category}"
            )
            CATEGORY_KEYWORDS[category] = [kw.strip().lower() for kw in kw_text.split(",") if kw.strip()]
    
    st.sidebar.markdown("### 💸 Set Monthly Budgets (J$)")
    MONTHLY_BUDGETS = {}
    for category in CATEGORY_KEYWORDS.keys():
        budget_value = saved_budgets.get(category, 0)
        MONTHLY_BUDGETS[category] = st.sidebar.number_input(
            label=f"Budget for {category}",
            min_value=0,
            value=int(budget_value),
            step=500,
            key=f"budget_{category}"
        )
    
    st.sidebar.markdown("### 🎯 Set Monthly Savings Goal (J$)")
    SAVINGS_GOAL = st.sidebar.number_input(
        "Savings Goal Amount (J$)", min_value=0, value=int(saved_goal), step=500
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Save Preferences", use_container_width=True):
        if save_user_preferences(
            st.session_state.user['id'],
            CATEGORY_KEYWORDS,
            MONTHLY_BUDGETS,
            SAVINGS_GOAL
        ):
            st.sidebar.success("✅ Preferences saved!")
            classify_expense_cached.cache_clear()
        else:
            st.sidebar.error("❌ Failed to save preferences")
    
    # Email settings
    st.sidebar.subheader("📧 Email Alerts")
    enable_email = st.sidebar.checkbox("Enable Email Notifications")
    
    if enable_email:
        email_provider = st.sidebar.selectbox(
            "Provider",
            ["Gmail", "Outlook", "Yahoo", "Custom"]
        )
        
        if email_provider == "Gmail":
            smtp_server = "smtp.gmail.com"
            smtp_port = 465
            st.sidebar.info("⚠️ Use App Password")
        elif email_provider == "Outlook":
            smtp_server = "smtp-mail.outlook.com"
            smtp_port = 587
        elif email_provider == "Yahoo":
            smtp_server = "smtp.mail.yahoo.com"
            smtp_port = 587
        else:
            smtp_server = st.sidebar.text_input("SMTP Server")
            smtp_port = st.sidebar.number_input("Port", value=587)
        
        sender_email = st.sidebar.text_input("Your Email")
        sender_password = st.sidebar.text_input("Password", type="password")
        notify_email = st.sidebar.text_input("Send Alerts To")
    
    # Apply categories
    category_json = json.dumps(CATEGORY_KEYWORDS)
    data['Spending Category'] = data['Description'].apply(
        lambda x: classify_expense_cached(x, category_json)
    )
    
    # Trend Analysis
    st.markdown("#### 📈 Spending Trends")
    
    available_months = sorted(data['Month-Year'].unique(), 
                            key=lambda x: pd.to_datetime(x, format='%B %Y'))
    
    if len(available_months) > 0:
        period_type = st.radio(
            "Select Analysis Period",
            ["All Time", "Specific Months", "Last 3 Months", "Last 6 Months"],
            horizontal=True
        )
        
        if period_type == "All Time":
            trend_data = data.copy()
        elif period_type == "Specific Months":
            selected_months = st.multiselect(
                "Select months to analyze",
                options=available_months,
                default=available_months[-2:] if len(available_months) >= 2 else available_months
            )
            trend_data = data[data['Month-Year'].isin(selected_months)]
        elif period_type == "Last 3 Months":
            last_3_months = available_months[-3:] if len(available_months) >= 3 else available_months
            trend_data = data[data['Month-Year'].isin(last_3_months)]
        else:
            last_6_months = available_months[-6:] if len(available_months) >= 6 else available_months
            trend_data = data[data['Month-Year'].isin(last_6_months)]
        
        if not trend_data.empty:
            monthly_summary = trend_data.groupby(['Month-Year', 'Category'])['Amount'].sum().unstack(fill_value=0)
            
            if 'Credit' not in monthly_summary.columns:
                monthly_summary['Credit'] = 0
            if 'Debit' not in monthly_summary.columns:
                monthly_summary['Debit'] = 0
            
            monthly_summary['Net Flow'] = monthly_summary['Credit'] - monthly_summary['Debit']
            monthly_summary = monthly_summary.reset_index()
            
            monthly_summary['Date_Sort'] = pd.to_datetime(monthly_summary['Month-Year'], format='%B %Y')
            monthly_summary = monthly_summary.sort_values('Date_Sort')
            
            fig = px.bar(
                monthly_summary,
                x='Month-Year',
                y=['Credit', 'Debit'],
                barmode='group',
                title="Income vs Spending by Month",
                labels={'value': 'Amount (J$)', 'variable': 'Type'},
                color_discrete_map={'Credit': '#10b981', 'Debit': '#ef4444'}
            )
            fig.update_layout(yaxis_tickprefix="J$", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            fig_net = px.line(
                monthly_summary,
                x='Month-Year',
                y='Net Flow',
                title="Monthly Net Cash Flow",
                markers=True
            )
            fig_net.update_layout(yaxis_tickprefix="J$", height=350)
            fig_net.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_net, use_container_width=True)
    
    st.markdown("---")
    
    # Monthly Analysis
    st.markdown("#### 📅 Monthly Analysis")
    
    available_months_list = sorted(data['Month-Name'].unique(), 
                                  key=lambda x: list(calendar.month_name).index(x))
    
    selected_month = st.selectbox("Select Month", available_months_list)
    
    month_data = data[data['Month-Name'] == selected_month].copy()
    
    if not month_data.empty:
        # Get summary
        year_month = month_data['YearMonth'].iloc[0]
        summary_cached = get_monthly_summary(st.session_state.user['id'], year_month)
        
        if not summary_cached:
            compute_monthly_summary(st.session_state.user['id'], year_month, data)
            summary_cached = get_monthly_summary(st.session_state.user['id'], year_month)
        
        # Display metrics
        month_income = month_data[month_data['Category'] == 'Credit']['Amount'].sum()
        month_spending = month_data[month_data['Category'] == 'Debit']['Amount'].sum()
        month_savings = month_income - month_spending
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
                <div class="metric-container green">
                    <div class="stat-title">💰 Income - {selected_month}</div>
                    <div class="stat-value">J${month_income:,.0f}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div class="metric-container red">
                    <div class="stat-title">💸 Spending - {selected_month}</div>
                    <div class="stat-value">J${month_spending:,.0f}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            color_class = "green" if month_savings >= 0 else "red"
            st.markdown(f"""
                <div class="metric-container {color_class}">
                    <div class="stat-title">🎯 Savings - {selected_month}</div>
                    <div class="stat-value">J${month_savings:,.0f}</div>
                    <div class="stat-change">Goal: J${SAVINGS_GOAL:,.0f}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Transactions
        st.markdown(f"#### 📄 Transactions in {selected_month}")
        st.dataframe(
            month_data[['Date', 'Description', 'Amount', 'Category', 'Spending Category']],
            use_container_width=True
        )
        
        st.markdown("---")
        
        # Spending breakdown
        st.markdown(f"#### 📈 Spending Breakdown for {selected_month}")
        spend = month_data[month_data['Category'] == 'Debit']
        
        if not spend.empty:
            summary = spend.groupby('Spending Category')['Amount'].sum().reset_index()
            summary['Percentage'] = 100 * summary['Amount'] / summary['Amount'].sum()
            st.dataframe(
                summary.style.format({"Amount": "J${:,.2f}", "Percentage": "{:.2f}%"}),
                use_container_width=True
            )
            
            fig = px.pie(
                summary,
                names='Spending Category',
                values='Amount',
                title=f"{selected_month} Spending Distribution",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Budget comparison
            st.markdown(f"#### 📏 Budget vs. Actual - {selected_month}")
            budget_df = pd.DataFrame.from_dict(MONTHLY_BUDGETS, orient='index', columns=['Budget']).reset_index()
            budget_df.rename(columns={'index': 'Spending Category'}, inplace=True)
            comparison = pd.merge(budget_df, summary, on='Spending Category', how='left')
            comparison['Amount'] = comparison['Amount'].fillna(0)
            comparison['Difference'] = comparison['Budget'] - comparison['Amount']
            comparison['Status'] = comparison.apply(
                lambda row: "Over Budget" if row['Amount'] > row['Budget'] else "Within Budget", axis=1
            )
            
            st.dataframe(
                comparison.style.format({"Budget": "J${:,.0f}", "Amount": "J${:,.0f}", "Difference": "J${:,.0f}"}),
                use_container_width=True
            )
            
            fig = px.bar(
                comparison,
                x='Spending Category',
                y=['Budget', 'Amount'],
                barmode='group',
                title="Budget vs. Actual Spending by Category",
                labels={"value": "J$", "variable": "Type"},
                text_auto=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Savings goal check
            st.markdown(f"#### 🎯 Savings Goal Check for {selected_month}")
            st.markdown(f"**Savings Goal:** J${SAVINGS_GOAL:,.2f}")
            st.markdown(f"**Actual Savings:** J${month_savings:,.2f}")
            
            if month_savings >= SAVINGS_GOAL:
                st.success(f"🎉 Congrats! You've met your savings goal by J${month_savings - SAVINGS_GOAL:,.2f}!")
            else:
                st.warning(f"You are J${SAVINGS_GOAL - month_savings:,.2f} below your savings goal.")
            
            # Email alerts
            if enable_email and notify_email and sender_email and sender_password:
                overspent = comparison[comparison['Amount'] > comparison['Budget']]
                if not overspent.empty:
                    subject = f"Finance Tracker Alert: Overspending in {selected_month}"
                    body_lines = [f"Dear user,\n\nYou have overspent in the following categories for {selected_month}:\n"]
                    for _, row in overspent.iterrows():
                        body_lines.append(
                            f"- {row['Spending Category']}: Spent J${row['Amount']:.2f} (Budget: J${row['Budget']:.2f})")
                    body_lines.append("\nPlease review your budget.")
                    body = "\n".join(body_lines)
                    
                    if st.button("📧 Send Alert Email", use_container_width=True):
                        send_email_alert(
                            notify_email,
                            subject,
                            body,
                            sender_email,
                            sender_password,
                            smtp_server,
                            smtp_port
                        )
            
            # Export reports
            st.markdown("---")
            st.markdown("#### 📤 Export Reports")
            
            report_text = f"Finance Report - {selected_month}\n\nTransactions:\n"
            for idx, row in month_data.iterrows():
                report_text += f"{row['Date'].date()} | {row['Description']} | J${row['Amount']:,.2f} | {row['Category']} | {row['Spending Category']}\n"
            
            report_text += "\nSpending Summary:\n"
            for idx, row in summary.iterrows():
                report_text += f"{row['Spending Category']}: J${row['Amount']:,.2f} ({row['Percentage']:.2f}%)\n"
            
            export_format = st.selectbox("Select export format", options=["Excel", "PDF"])
            
            if st.button("Download Report", use_container_width=True):
                if export_format == "Excel":
                    excel_bytes = export_to_excel(month_data)
                    st.download_button(
                        label="📥 Download Excel File",
                        data=excel_bytes,
                        file_name=f"Finance_Report_{selected_month}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    pdf_bytes = export_to_pdf(report_text)
                    st.download_button(
                        label="📥 Download PDF File",
                        data=pdf_bytes,
                        file_name=f"Finance_Report_{selected_month}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.info(f"No spending transactions found for {selected_month}")
    
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
