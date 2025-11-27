"""
password_reset.py
Forgot Password/Username Module for Finance Hub
"""

import streamlit as st
import mysql.connector
from mysql.connector import Error
import secrets
import string
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import hashlib

# Email Configuration (imported from main app)
APP_EMAIL = "fintrackeralerts@gmail.com"
APP_EMAIL_PASSWORD = "myhdkbyrzmpvwjyb"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Database Configuration (should match your main app)
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

# ============================================
# DATABASE CONNECTION
# ============================================

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
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================
# TOKEN MANAGEMENT
# ============================================

def generate_reset_token():
    """Generate a secure random token for password reset"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def save_reset_token(email, token):
    """Save password reset token to database"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        # Token expires in 1 hour
        expiry = datetime.now() + timedelta(hours=1)
        
        # Delete any existing tokens for this email
        cursor.execute("DELETE FROM password_resets WHERE email = %s", (email,))
        
        # Insert new token
        cursor.execute(
            "INSERT INTO password_resets (email, token, expiry) VALUES (%s, %s, %s)",
            (email, token, expiry)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error saving reset token: {e}")
        connection.close()
        return False

def verify_reset_token(token):
    """Verify if reset token is valid and not expired"""
    connection = create_connection()
    if not connection:
        return False, None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT email, expiry FROM password_resets WHERE token = %s",
            (token,)
        )
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result and result['expiry'] > datetime.now():
            return True, result['email']
        return False, None
    except Error as e:
        st.error(f"Error verifying token: {e}")
        connection.close()
        return False, None

# ============================================
# PASSWORD & USERNAME RECOVERY
# ============================================

def reset_password(email, new_password):
    """Reset user password"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        password_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (password_hash, email)
        )
        connection.commit()
        
        # Delete used reset token
        cursor.execute("DELETE FROM password_resets WHERE email = %s", (email,))
        connection.commit()
        
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error resetting password: {e}")
        connection.close()
        return False

def get_username_by_email(email):
    """Retrieve username by email"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT username FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result['username'] if result else None
    except Error as e:
        st.error(f"Error retrieving username: {e}")
        connection.close()
        return None

def email_exists(email):
    """Check if email exists in database"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        exists = cursor.fetchone() is not None
        cursor.close()
        connection.close()
        return exists
    except Error as e:
        st.error(f"Error checking email: {e}")
        connection.close()
        return False

# ============================================
# EMAIL FUNCTIONS
# ============================================

def send_password_reset_email(email, token):
    """Send password reset email"""
    try:
        subject = "Finance Hub - Password Reset Request"
        body = f"""
Dear User,

You have requested to reset your password for Finance Hub.

Your password reset token is: {token}

Please copy this token and use it on the password reset page.

This token will expire in 1 hour.

If you did not request this reset, please ignore this email.

Best regards,
Finance Hub Team
"""
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = APP_EMAIL
        msg['To'] = email
        msg.set_content(body)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

def send_username_reminder_email(email, username):
    """Send username reminder email"""
    try:
        subject = "Finance Hub - Username Reminder"
        body = f"""
Dear User,

You have requested your username for Finance Hub.

Your username is: {username}

If you did not request this, please ignore this email.

Best regards,
Finance Hub Team
"""
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = APP_EMAIL
        msg['To'] = email
        msg.set_content(body)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

# ============================================
# STREAMLIT PAGES
# ============================================

def apply_custom_styles():
    """Apply custom CSS styles (imported from main app)"""
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
    </style>
    """, unsafe_allow_html=True)

def forgot_password_page():
    """Forgot password page"""
    apply_custom_styles()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">🔐 Forgot Password</h1>
                    <p class="auth-subtitle">Enter your email to receive a password reset token</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        email = st.text_input("Email Address", placeholder="your.email@example.com", key="forgot_email")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("📧 Send Reset Token", use_container_width=True):
                if not email:
                    st.error("❌ Please enter your email address")
                elif '@' not in email or '.' not in email:
                    st.error("❌ Invalid email format")
                else:
                    # Check if email exists
                    if email_exists(email):
                        # Generate and save token
                        token = generate_reset_token()
                        if save_reset_token(email, token):
                            if send_password_reset_email(email, token):
                                st.success("✅ Reset token sent to your email!")
                                st.info("💡 Check your email and copy the token")
                                st.session_state.page = 'reset_password'
                                st.session_state.reset_email = email
                                st.rerun()
                            else:
                                st.error("❌ Failed to send email. Please try again.")
                        else:
                            st.error("❌ Failed to generate reset token")
                    else:
                        # Don't reveal if email exists for security
                        st.success("✅ If that email exists, a reset token has been sent")
        
        with col_btn2:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()

def reset_password_page():
    """Reset password page"""
    apply_custom_styles()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">🔑 Reset Password</h1>
                    <p class="auth-subtitle">Enter your reset token and new password</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        token = st.text_input("Reset Token", placeholder="Enter the token from your email", key="reset_token")
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password (min 6 characters)", key="new_password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password", key="confirm_new_password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✅ Reset Password", use_container_width=True):
                if not token or not new_password or not confirm_password:
                    st.error("❌ All fields are required")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    # Verify token
                    valid, email = verify_reset_token(token)
                    if valid:
                        if reset_password(email, new_password):
                            st.success("✅ Password reset successful!")
                            st.info("Please login with your new password")
                            st.balloons()
                            st.session_state.page = 'login'
                            if 'reset_email' in st.session_state:
                                del st.session_state.reset_email
                            st.rerun()
                        else:
                            st.error("❌ Failed to reset password")
                    else:
                        st.error("❌ Invalid or expired token. Please request a new one.")
        
        with col_btn2:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                if 'reset_email' in st.session_state:
                    del st.session_state.reset_email
                st.rerun()

def forgot_username_page():
    """Forgot username page"""
    apply_custom_styles()
