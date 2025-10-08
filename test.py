import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import re

# ============================================
# DATABASE CONFIGURATION
# ============================================

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Change to your MySQL username
    'password': 'your_password',  # Change to your MySQL password
    'database': 'finance_hub'
}

# ============================================
# DATABASE FUNCTIONS
# ============================================

def create_connection():
    """Create a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database and create users table if it doesn't exist"""
    try:
        # Connect without database to create it if needed
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        st.error(f"Database initialization error: {e}")
        return False

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(username, email, password):
    """Register a new user"""
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
        return False, "Username or email already exists"
    except Error as e:
        return False, f"Registration error: {e}"

def authenticate_user(username, password):
    """Authenticate user login"""
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
            # Update last login
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
        return False, None

# ============================================
# SESSION STATE MANAGEMENT
# ============================================

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'login'
    st.rerun()

# ============================================
# UI PAGES
# ============================================

def login_page():
    """Display login page"""
    st.title("🔐 Finance Hub Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Login", use_container_width=True):
                if username and password:
                    success, user = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
        
        with col_btn2:
            if st.button("Register", use_container_width=True):
                st.session_state.page = 'register'
                st.rerun()
        
        st.markdown("---")

def register_page():
    """Display registration page"""
    st.title("📝 Register New Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Create Account", use_container_width=True):
                # Validation
                if not username or not email or not password:
                    st.error("All fields are required")
                elif len(username) < 3:
                    st.error("Username must be at least 3 characters")
                elif not validate_email(email):
                    st.error("Invalid email format")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(username, email, password)
                    if success:
                        st.success(message)
                        st.info("Please login with your new account")
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(message)
        
        with col_btn2:
            if st.button("Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()
        
        st.markdown("---")

def main_app():
    """Display main application (your existing Finance Hub)"""
    # Sidebar user info
    with st.sidebar:
        st.markdown(f"### 👤 Welcome, {st.session_state.user['username']}!")
        st.markdown(f"**Email:** {st.session_state.user['email']}")
        if st.button("Logout", use_container_width=True):
            logout()
        st.markdown("---")
    
    # Your existing Finance Hub code goes here
    st.title("💼 Welcome to Finance Hub")
    st.markdown("Choose a feature below to get started:")
    
    option = st.radio(
        "What would you like to do?",
        ["📊 Spending Analysis", "📅 Budget Planner", "🌐 Network Analysis"],
        index=0
    )
    
    if option == "📊 Spending Analysis":
        st.markdown("You selected **Spending Analysis**.")
        st.info("Your existing Spending Analysis code will go here...")
        # Insert your existing spending analysis code
    
    elif option == "📅 Budget Planner":
        st.markdown("You selected **Budget Planner**.")
        st.info("Your existing Budget Planner code will go here...")
        # Insert your existing budget planner code
    
    elif option == "🌐 Network Analysis":
        st.markdown("You selected **Network Analysis**.")
        st.info("Network analysis feature coming soon!")

# ============================================
# MAIN APPLICATION
# ============================================

def main():
    st.set_page_config(
        page_title="Finance Hub",
        page_icon="💼",
        layout="wide"
    )
    
    # Initialize database
    if 'db_initialized' not in st.session_state:
        if init_database():
            st.session_state.db_initialized = True
        else:
            st.error("Failed to initialize database. Please check your MySQL configuration.")
            st.stop()
    
    # Initialize session state
    init_session_state()
    
    # Route to appropriate page
    if not st.session_state.authenticated:
        if st.session_state.page == 'register':
            register_page()
        else:
            login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
