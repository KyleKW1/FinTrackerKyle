import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import re
import os

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Finance Hub",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark blue theme with CSS
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: #050f40 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #002266 !important;
        }
        body {
            color: ##51ff00 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================
# DATABASE CONFIGURATION
# ============================================

try:
    DB_CONFIG = {
        'host': st.secrets["mysql"]["host"],
        'port': int(st.secrets["mysql"]["port"]),
        'user': st.secrets["mysql"]["user"],
        'password': st.secrets["mysql"]["password"],
        'database': st.secrets["mysql"]["database"],
        'ssl_disabled': False,
        'ssl_verify_cert': False,
        'ssl_verify_identity': False
    }
except (KeyError, FileNotFoundError):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    DB_CONFIG = {
        'host': os.getenv('MYSQL_HOST') or 'mysql-11beff9b-kamarwatson36-874b.g.aivencloud.com',
        'port': int(os.getenv('MYSQL_PORT') or '11510'),
        'user': os.getenv('MYSQL_USER') or 'avnadmin',
        'password': os.getenv('MYSQL_PASSWORD') or 'AVNS_Dxyg2mu3MEiRoVyasff',
        'database': os.getenv('MYSQL_DATABASE') or 'defaultdb',
        'ssl_disabled': False,
        'ssl_verify_cert': False,
        'ssl_verify_identity': False
    }

# ============================================
# DATABASE FUNCTIONS
# ============================================

def create_connection():
    """Create a database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            ssl_disabled=DB_CONFIG.get('ssl_disabled', False),
            ssl_verify_cert=DB_CONFIG.get('ssl_verify_cert', False),
            ssl_verify_identity=DB_CONFIG.get('ssl_verify_identity', False)
        )
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database and create users table if it doesn't exist"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            ssl_disabled=DB_CONFIG.get('ssl_disabled', False),
            ssl_verify_cert=DB_CONFIG.get('ssl_verify_cert', False),
            ssl_verify_identity=DB_CONFIG.get('ssl_verify_identity', False)
        )
        cursor = conn.cursor()
        
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_data LONGBLOB NOT NULL,
                file_type VARCHAR(10) NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                category_keywords TEXT,
                monthly_budgets TEXT,
                savings_goal DECIMAL(10,2) DEFAULT 5000,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
        connection.close()
        return False, "Username or email already exists"
    except Error as e:
        connection.close()
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
# FILE STORAGE FUNCTIONS
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

def get_user_files(user_id):
    """Get all files for a user"""
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, filename, file_type, upload_date FROM user_files WHERE user_id = %s ORDER BY upload_date DESC",
            (user_id,)
        )
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        return files
    except Error as e:
        st.error(f"Error retrieving files: {e}")
        connection.close()
        return []

def get_file_data(file_id, user_id):
    """Get file data from database"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT file_data, filename, file_type FROM user_files WHERE id = %s AND user_id = %s",
            (file_id, user_id)
        )
        file_data = cursor.fetchone()
        cursor.close()
        connection.close()
        return file_data
    except Error as e:
        st.error(f"Error retrieving file: {e}")
        connection.close()
        return None

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
        deleted = cursor.rowcount > 0
        cursor.close()
        connection.close()
        return deleted
    except Error as e:
        st.error(f"Error deleting file: {e}")
        connection.close()
        return False

# ============================================
# USER PREFERENCES FUNCTIONS
# ============================================

def get_user_preferences(user_id):
    """Get user's saved preferences"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT category_keywords, monthly_budgets, savings_goal FROM user_preferences WHERE user_id = %s",
            (user_id,)
        )
        prefs = cursor.fetchone()
        cursor.close()
        connection.close()
        return prefs
    except Error as e:
        st.error(f"Error retrieving preferences: {e}")
        connection.close()
        return None

def save_user_preferences(user_id, category_keywords, monthly_budgets, savings_goal):
    """Save user's preferences"""
    import json
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        category_json = json.dumps(category_keywords)
        budgets_json = json.dumps(monthly_budgets)
        
        cursor.execute("SELECT id FROM user_preferences WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE user_preferences 
                SET category_keywords = %s, monthly_budgets = %s, savings_goal = %s
                WHERE user_id = %s
            """, (category_json, budgets_json, float(savings_goal), user_id))
        else:
            cursor.execute("""
                INSERT INTO user_preferences (user_id, category_keywords, monthly_budgets, savings_goal)
                VALUES (%s, %s, %s, %s)
            """, (user_id, category_json, budgets_json, float(savings_goal)))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error saving preferences: {e}")
        if connection:
            connection.close()
        return False

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
    if 'selected_option' not in st.session_state:
        st.session_state.selected_option = None

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'login'
    st.session_state.selected_option = None
    st.rerun()

# ============================================
# UI PAGES
# ============================================

def login_page():
    """Display login page"""
    st.markdown("<h1 style='text-align: center;'>🔐 Finance Hub Login</h1>", unsafe_allow_html=True)
    
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
        st.info("💡 **Demo:** Create a new account to get started!")

def register_page():
    """Display registration page"""
    st.markdown("<h1 style='text-align: center;'>📝 Register New Account</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        username = st.text_input("Username", key="reg_username", help="Minimum 3 characters")
        email = st.text_input("Email", key="reg_email", help="Valid email address")
        password = st.text_input("Password", type="password", key="reg_password", help="Minimum 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Create Account", use_container_width=True):
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
                        st.balloons()
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
    """Display main application - Your Finance Hub"""
    import pandas as pd
    import plotly.express as px
    import calendar
    import smtplib
    from email.message import EmailMessage
    from io import BytesIO
    import tempfile
    from PIL import Image
    import pdfplumber

    try:
        import pdfkit
        PDFKIT_INSTALLED = True
    except ImportError:
        PDFKIT_INSTALLED = False

    from fpdf import FPDF

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.markdown(f"📧 {st.session_state.user['email']}")
        if st.session_state.user.get('last_login'):
            last_login = str(st.session_state.user['last_login'])
            st.caption(f"Last login: {last_login[:19]}")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        st.markdown("---")

    # Centered title
    st.markdown("<h1 style='text-align: center;'>💼 Welcome to Finance Hub</h1>", unsafe_allow_html=True)

    # Feature selection with buttons instead of radio - only show when no option selected
    if st.session_state.selected_option is None:
        st.markdown("<p style='text-align: center; font-size: 16px;'>Choose a feature below to get started:</p>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Spending Analysis", use_container_width=True, key="btn_spending"):
                st.session_state.selected_option = "📊 Spending Analysis"
                st.rerun()
        
        with col2:
            if st.button("📅 Budget Planner", use_container_width=True, key="btn_budget"):
                st.session_state.selected_option = "📅 Budget Planner"
                st.rerun()
        
        with col3:
            if st.button("🌐 Network Analysis", use_container_width=True, key="btn_network"):
                st.session_state.selected_option = "🌐 Network Analysis"
                st.rerun()
        st.stop()

    option = st.session_state.selected_option

    # Add back button
    if st.button("← Back to Menu"):
        st.session_state.selected_option = None
        st.rerun()

    st.markdown("---")

    # Helper Functions
    def process_csv(file):
        try:
            df = pd.read_csv(file)
            df.rename(columns={
                'TRANS DATE': 'Date',
                'DETAILS': 'Description',
                'TOTAL AMOUNT': 'Amount',
                'TRANS TYPE': 'Category'
            }, inplace=True)
            df = df[['Date', 'Description', 'Amount', 'Category']]
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df['Category'] = df['Amount'].apply(lambda x: 'Debit' if x < 0 else 'Credit')
            df['Amount'] = df['Amount'].abs()
            return df
        except Exception as e:
            st.error(f"CSV Error: {e}")
            return pd.DataFrame()

    def process_pdf(file):
        try:
            data = []
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    for line in text.split('\n'):
                        if "POS" in line or "TRF" in line or "PURCHASE" in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                date = parts[0]
                                desc = " ".join(parts[1:-2])
                                amt = parts[-2].replace('J$', '').replace(',', '')
                                cat = 'Debit' if '-' in parts[-2] else 'Credit'
                                data.append([date, desc, abs(float(amt)), cat])
            df = pd.DataFrame(data, columns=['Date', 'Description', 'Amount', 'Category'])
            return df
        except Exception as e:
            st.error(f"PDF Error: {e}")
            return pd.DataFrame()

    def classify_expense(description, mapping):
        desc = description.lower()
        for category, keywords in mapping.items():
            for kw in keywords:
                if kw in desc:
                    return category
        return 'Uncategorized'

    def send_email_alert(receiver_email, subject, body, sender_email, sender_password, smtp_server, smtp_port=587):
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = receiver_email

            if 'gmail' in smtp_server.lower():
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    st.success("✅ Email sent successfully!")
            else:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    st.success("✅ Email sent successfully!")
            
            return True

        except smtplib.SMTPAuthenticationError:
            st.error("❌ Authentication Failed - Check your email credentials")
            if 'gmail' in smtp_server.lower():
                st.info("📌 Gmail users must use App Passwords, not regular passwords")
            return False
        except Exception as e:
            st.error(f"❌ Email Error: {str(e)}")
            return False

    def export_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        processed_data = output.getvalue()
        return processed_data

    def export_to_pdf(text_report):
        if PDFKIT_INSTALLED:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
                f.write(text_report.encode('utf-8'))
                f.flush()
                pdf_file = f.name.replace('.html', '.pdf')
                pdfkit.from_file(f.name, pdf_file)
                with open(pdf_file, 'rb') as pdf_f:
                    pdf_bytes = pdf_f.read()
                os.unlink(f.name)
                os.unlink(pdf_file)
                return pdf_bytes
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            for line in text_report.split('\n'):
                pdf.cell(0, 10, line.encode('latin-1', 'ignore').decode('latin-1'), ln=True)
                
            return pdf.output(dest='S').encode('latin1')

    if option == "📊 Spending Analysis":
        st.subheader("📊 Spending Analysis")
        
        # File Management Section
        st.subheader("📁 Your Files")
        
        user_files = get_user_files(st.session_state.user['id'])
        
        if user_files:
            st.markdown(f"**You have {len(user_files)} stored file(s)**")
            
            for i in range(0, len(user_files), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(user_files):
                        file = user_files[i + j]
                        with col:
                            st.markdown(f"**{file['filename']}**")
                            st.caption(f"Uploaded: {str(file['upload_date'])[:19]}")
                            st.caption(f"Type: {file['file_type'].upper()}")
                            if st.button(f"🗑️ Delete", key=f"del_{file['id']}"):
                                if delete_user_file(file['id'], st.session_state.user['id']):
                                    st.success(f"Deleted {file['filename']}")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete file")
            st.markdown("---")
        else:
            st.info("No files uploaded yet. Upload your first file below!")

        with st.expander("📤 Upload New Files", expanded=not user_files):
            uploaded_files = st.file_uploader(
                "Upload CSV or PDF files",
                type=["csv", "pdf"],
                accept_multiple_files=True,
                key="file_uploader"
            )

            if uploaded_files:
                if st.button("💾 Save Files to Account"):
                    success_count = 0
                    for file in uploaded_files:
                        file_data = file.read()
                        file_type = file.name.split('.')[-1].lower()
                        
                        existing_files = [f['filename'] for f in user_files]
                        if file.name in existing_files:
                            st.warning(f"⚠️ {file.name} already exists. Skipping...")
                            continue
                        
                        if save_user_file(st.session_state.user['id'], file.name, file_data, file_type):
                            success_count += 1
                        file.seek(0)
                    
                    if success_count > 0:
                        st.success(f"✅ Saved {success_count} file(s) to your account!")
                        st.rerun()

        st.markdown("---")

        data = pd.DataFrame()
        user_files = get_user_files(st.session_state.user['id'])
        
        if user_files:
            for file_info in user_files:
                file_data = get_file_data(file_info['id'], st.session_state.user['id'])
                if file_data:
                    file_bytes = BytesIO(file_data['file_data'])
                    
                    if file_data['file_type'] == 'csv':
                        df = process_csv(file_bytes)
                        data = pd.concat([data, df], ignore_index=True)
                    elif file_data['file_type'] == 'pdf':
                        df = process_pdf(file_bytes)
                        data = pd.concat([data, df], ignore_index=True)

        if data.empty:
            st.info("Upload your bank CSV or PDF statements to get started.")
            st.stop()

        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        
        data['Month-Year'] = data['Date'].dt.strftime('%B %Y')
        data['Month-Name'] = data['Date'].dt.strftime('%B')

        st.sidebar.header("🗂 Customize Categories and Budgets")

        default_mapping = {
            "Food": ["juici", "kfc", "restaurant", "burger", "pizza"],
            "Grocery": ["hi-lo", "supermarket", "wholesale"],
            "Utilities": ["jps", "nwc", "flow", "internet", "light", "water"],
            "Transport": ["uber", "taxi", "gas"],
            "Income": ["remitly", "deposit", "transfer", "payroll"],
            "Miscellaneous": ["atm"],
            "Other": []
        }
        
        default_budgets = {
            "Food": 15000,
            "Grocery": 10000,
            "Utilities": 8000,
            "Transport": 6000,
            "Miscellaneous": 5000,
            "Income": 0,
            "Other": 0
        }
        
        default_savings_goal = 5000

        import json
        user_prefs = get_user_preferences(st.session_state.user['id'])
        
        if user_prefs:
            saved_categories = json.loads(user_prefs['category_keywords']) if user_prefs['category_keywords'] else default_mapping
            saved_budgets = json.loads(user_prefs['monthly_budgets']) if user_prefs['monthly_budgets'] else default_budgets
            saved_goal = float(user_prefs['savings_goal']) if user_prefs['savings_goal'] else default_savings_goal
        else:
            saved_categories = default_mapping
            saved_budgets = default_budgets
            saved_goal = default_savings_goal

        CATEGORY_KEYWORDS = {}

        st.sidebar.markdown("### Edit Categories and Keywords")
        for category, keywords in saved_categories.items():
            with st.sidebar.expander(f"{category} Keywords", expanded=False):
                kw_text = st.text_area(
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
        savings_goal_input = st.sidebar.number_input(
            "Savings Goal Amount (J$)", min_value=0, value=int(saved_goal), step=500
        )
        SAVINGS_GOAL = savings_goal_input
        
        st.sidebar.markdown("---")
        if st.sidebar.button("💾 Save Preferences", use_container_width=True):
            if save_user_preferences(
                st.session_state.user['id'],
                CATEGORY_KEYWORDS,
                MONTHLY_BUDGETS,
                SAVINGS_GOAL
            ):
                st.sidebar.success("✅ Preferences saved!")
            else:
                st.sidebar.error("❌ Failed to save preferences")

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
                st.sidebar.info("⚠️ Use App Password, not regular password")
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

        # Apply spending categories
        data['Spending Category'] = data['Description'].apply(
            lambda x: classify_expense(x, CATEGORY_KEYWORDS)
        )

        # ---------- Trend Analysis ----------
        
        st.header("📈 Spending Trends")
        
        available_months = sorted(data['Month-Year'].unique(), 
                                key=lambda x: pd.to_datetime(x, format='%B %Y'))
        
        if len(available_months) > 0:
            period_type = st.radio(
                "Select Analysis Period",
                ["All Time", "Specific Months", "Last 3 Months", "Last 6 Months"]
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
                    color_discrete_map={'Credit': 'green', 'Debit': 'red'}
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

        # ---------- Monthly Analysis ----------
        
        st.header("📅 Monthly Analysis")
        
        available_months_list = sorted(data['Month-Name'].unique(), 
                                      key=lambda x: list(calendar.month_name).index(x))
        
        selected_month = st.selectbox("Select Month", available_months_list)
        
        month_data = data[data['Month-Name'] == selected_month].copy()
        filtered = month_data
        
        if not month_data.empty:
            col1, col2, col3 = st.columns(3)
            
            month_income = month_data[month_data['Category'] == 'Credit']['Amount'].sum()
            month_spending = month_data[month_data['Category'] == 'Debit']['Amount'].sum()
            month_savings = month_income - month_spending
            
            with col1:
                st.metric(f"Income - {selected_month}", f"J${month_income:,.0f}")
            with col2:
                st.metric(f"Spending - {selected_month}", f"J${month_spending:,.0f}")
            with col3:
                delta_color = "normal" if month_savings >= 0 else "inverse"
                st.metric(f"Savings - {selected_month}", f"J${month_savings:,.0f}",
                         delta=f"Goal: J${SAVINGS_GOAL:,.0f}", delta_color=delta_color)
            
            st.subheader(f"📄 Transactions in {selected_month}")
            st.dataframe(filtered[['Date', 'Description', 'Amount', 'Category', 'Spending Category']])

            st.subheader(f"📈 Spending Breakdown for {selected_month}")
            spend = filtered[filtered['Category'] == 'Debit']
            if not spend.empty:
                summary = spend.groupby('Spending Category')['Amount'].sum().reset_index()
                summary['Percentage'] = 100 * summary['Amount'] / summary['Amount'].sum()
                st.dataframe(summary.style.format({"Amount": "J${:,.2f}", "Percentage": "{:.2f}%"}))

                fig = px.pie(
                    summary,
                    names='Spending Category',
                    values='Amount',
                    title=f"{selected_month} Spending Distribution",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader(f"📏 Budget vs. Actual - {selected_month}")
                budget_df = pd.DataFrame.from_dict(MONTHLY_BUDGETS, orient='index', columns=['Budget']).reset_index()
                budget_df.rename(columns={'index': 'Spending Category'}, inplace=True)
                comparison = pd.merge(budget_df, summary, on='Spending Category', how='left')
                comparison['Amount'] = comparison['Amount'].fillna(0)
                comparison['Difference'] = comparison['Budget'] - comparison['Amount']
                comparison['Status'] = comparison.apply(
                    lambda row: "Over Budget" if row['Amount'] > row['Budget'] else "Within Budget", axis=1
                )

                st.dataframe(
                    comparison.style.format({"Budget": "J${:,.0f}", "Amount": "J${:,.0f}", "Difference": "J${:,.0f}"})
                    .apply(lambda s: ['color: red;' if 'Over' in str(v) else '' for v in s], subset=['Status'])
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

                st.subheader(f"🎯 Savings Goal Check for {selected_month}")

                total_income = filtered[filtered['Category'] == 'Credit']['Amount'].sum()
                total_spending = filtered[filtered['Category'] == 'Debit']['Amount'].sum()
                actual_savings = total_income - total_spending

                st.markdown(f"**Savings Goal:** J${SAVINGS_GOAL:,.2f}")
                st.markdown(f"**Actual Savings:** J${actual_savings:,.2f}")

                if actual_savings >= SAVINGS_GOAL:
                    st.success(f"🎉 Congrats! You've met your savings goal by J${actual_savings - SAVINGS_GOAL:,.2f}!")
                else:
                    st.warning(f"You are J${SAVINGS_GOAL - actual_savings:,.2f} below your savings goal.")

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
                        
                        if st.button("📧 Send Alert Email"):
                            send_email_alert(
                                notify_email,
                                subject,
                                body,
                                sender_email,
                                sender_password,
                                smtp_server,
                                smtp_port
                            )

                st.subheader("📤 Export Reports")

                report_text = f"Finance Report - {selected_month}\n\nTransactions:\n"
                for idx, row in filtered.iterrows():
                    report_text += f"{row['Date'].date()} | {row['Description']} | J${row['Amount']:,.2f} | {row['Category']} | {row['Spending Category']}\n"

                report_text += "\nSpending Summary:\n"
                for idx, row in summary.iterrows():
                    report_text += f"{row['Spending Category']}: J${row['Amount']:,.2f} ({row['Percentage']:.2f}%)\n"

                report_text += "\nBudget vs Actual:\n"
                for idx, row in comparison.iterrows():
                    report_text += f"{row['Spending Category']}: Budget J${row['Budget']:,.2f}, Actual J${row['Amount']:,.2f}, Status: {row['Status']}\n"

                export_format = st.selectbox("Select export format", options=["Excel", "PDF"])

                if st.button("Download Report"):
                    if export_format == "Excel":
                        excel_bytes = export_to_excel(filtered)
                        st.download_button(
                            label="Download Excel File",
                            data=excel_bytes,
                            file_name=f"Finance_Report_{selected_month}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        pdf_bytes = export_to_pdf(report_text)
                        st.download_button(
                            label="Download PDF File",
                            data=pdf_bytes,
                            file_name=f"Finance_Report_{selected_month}.pdf",
                            mime="application/pdf"
                        )
            else:
                st.info(f"No spending transactions found for {selected_month}")

    elif option == "📅 Budget Planner":
        st.subheader("📅 Budget Planner")
        st.info("Budget planner feature available. Upload your budget spreadsheet to get started.")

    elif option == "🌐 Network Analysis":
        st.subheader("🌐 Network Analysis")
        st.info("Network analysis feature coming soon! This will show transaction patterns and relationships.")

# ============================================
# MAIN APPLICATION
# ============================================

def main():
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
