import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import re
import os
import pandas as pd
import plotly.express as px 
import calendar
import smtplib
from email.message import EmailMessage
from io import BytesIO
import tempfile
from PIL import Image
import pdfplumber
from functools import lru_cache
from datetime import datetime, timedelta
import json
import pickle
from typing import Optional, List  # ← ADD THIS LINE IF MISSING
import socket

try:
    import pdfkit
    PDFKIT_INSTALLED = True
except ImportError:
    PDFKIT_INSTALLED = False

from fpdf import FPDF

import mysql.connector
from mysql.connector import Error
import hashlib
import re
import streamlit as st
import socket

# Configuration - Aiven Cloud MySQL
DB_CONFIG = {
    'host': 'mysql-11beff9b-kamarwatson36-874b.g.aivencloud.com',
    'port': 11510,
    'user': 'avnadmin',
    'password': 'AVNS_Dxyg2mu3MEiRoVyasff',
    'database': 'defaultdb',
    'ssl_disabled': False,  # SSL REQUIRED for Aiven
    'ssl_verify_cert': True,
    'ssl_verify_identity': True
}

def test_port_connection(host, port):
    """Test if port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False

def create_connection():
    """Create a database connection with enhanced error handling"""
    
    # First, test if port is reachable
    if not test_port_connection(DB_CONFIG['host'], DB_CONFIG['port']):
        st.error(f"Cannot reach {DB_CONFIG['host']}:{DB_CONFIG['port']}. "
                f"Please check:\n"
                f"1. MySQL server is running\n"
                f"2. Port number is correct (default: 3306)\n"
                f"3. Firewall settings\n"
                f"4. If using SSH tunnel, ensure it's active")
        return None
    
    try:
        # Aiven requires SSL - configure accordingly
        ssl_config = {
            'ssl_disabled': False
        }
        
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            ssl_disabled=ssl_config['ssl_disabled'],
            pool_name="mypool",
            pool_size=5,
            connection_timeout=30,  # Increased for cloud connections
            autocommit=False
        )
        return connection
    except mysql.connector.errors.ProgrammingError as e:
        st.error(f"Database '{DB_CONFIG['database']}' does not exist or credentials are incorrect: {e}")
        return None
    except mysql.connector.errors.DatabaseError as e:
        st.error(f"Database access error: {e}")
        return None
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database with optimized schema and indexes"""
    
    # Test connection first
    if not test_port_connection(DB_CONFIG['host'], DB_CONFIG['port']):
        st.error(f"MySQL server is not accessible at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        return False
    
    try:
        # Connect without database first for Aiven
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],  # Aiven uses 'defaultdb'
            ssl_disabled=False,
            connection_timeout=30
        )
        cursor = conn.cursor()
        
        # Use the default database (already connected to 'defaultdb')
        # No need to create database on Aiven
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                INDEX idx_username (username),
                INDEX idx_email (email)
            )
        """)
        
        # User files table with indexes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_data LONGBLOB NOT NULL,
                file_type VARCHAR(10) NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_files_user_id (user_id),
                INDEX idx_user_files_upload_date (upload_date)
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                category_keywords TEXT,
                monthly_budgets TEXT,
                savings_goal DECIMAL(10,2) DEFAULT 5000,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_preferences_user_id (user_id)
            )
        """)
        
        # Monthly summaries table for pre-computed data
        # Use quoted identifiers and more compatible definitions to avoid syntax issues on different MySQL versions.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `monthly_summaries` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `user_id` INT NOT NULL,
                `year_month` VARCHAR(7) NOT NULL,
                `total_income` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                `total_spending` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                `category_breakdown` TEXT,
                `transaction_count` INT NOT NULL DEFAULT 0,
                `computed_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY `unique_user_month` (`user_id`, `year_month`),
                KEY `idx_monthly_summaries` (`user_id`, `year_month`),
                CONSTRAINT `fk_monthly_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Database initialized successfully!")
        return True
    except mysql.connector.errors.ProgrammingError as e:
        st.error(f"Database permission error: {e}\n"
                f"Make sure user '{DB_CONFIG['user']}' has CREATE DATABASE privileges")
        return False
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

# Diagnostic function
def run_diagnostics():
    """Run connection diagnostics"""
    st.write("### Database Connection Diagnostics")
    st.write(f"**Host:** {DB_CONFIG['host']}")
    st.write(f"**Port:** {DB_CONFIG['port']}")
    st.write(f"**Database:** {DB_CONFIG['database']}")
    
    if test_port_connection(DB_CONFIG['host'], DB_CONFIG['port']):
        st.success(f"✓ Port {DB_CONFIG['port']} is reachable")
    else:
        st.error(f"✗ Port {DB_CONFIG['port']} is NOT reachable")
        return
    
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            ssl_disabled=False,
            connection_timeout=30
        )
        st.success("✓ Credentials are valid")
        conn.close()
    except Error as e:
        st.error(f"✗ Connection failed: {e}")




# ============================================
# OPTIMIZED FILE STORAGE FUNCTIONS
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
        
        # Invalidate cache
        invalidate_user_cache(user_id)
        return True
    except Error as e:
        st.error(f"Error saving file: {e}")
        connection.close()
        return False

def get_user_files_paginated(user_id, page=0, page_size=10):
    """Get files with pagination for better performance"""
    connection = create_connection()
    if not connection:
        return [], 0
    
    try:
        cursor = connection.cursor(dictionary=True)
        offset = page * page_size
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) as total FROM user_files WHERE user_id = %s",
            (user_id,)
        )
        total = cursor.fetchone()['total']
        
        # Get paginated results
        cursor.execute(
            """SELECT id, filename, file_type, upload_date 
               FROM user_files 
               WHERE user_id = %s 
               ORDER BY upload_date DESC 
               LIMIT %s OFFSET %s""",
            (user_id, page_size, offset)
        )
        files = cursor.fetchall()
        
        cursor.close()
        connection.close()
        return files, total
    except Error as e:
        st.error(f"Error retrieving files: {e}")
        connection.close()
        return [], 0

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
        
        # Invalidate cache
        invalidate_user_cache(user_id)
        return deleted
    except Error as e:
        st.error(f"Error deleting file: {e}")
        connection.close()
        return False

# ============================================
# CACHING SYSTEM
# ============================================

def get_cache_key(user_id, cache_type='data'):
    """Generate cache key"""
    return f'user_{user_id}_{cache_type}'

def get_cached_data(user_id):
    """Get cached user data from session state"""
    cache_key = get_cache_key(user_id, 'data')
    time_key = get_cache_key(user_id, 'time')
    
    if cache_key in st.session_state:
        cache_time = st.session_state.get(time_key)
        if cache_time and (datetime.now() - cache_time).seconds < 300:  # 5 min cache
            return st.session_state[cache_key]
    
    return None

def set_cached_data(user_id, data):
    """Set cached user data in session state"""
    cache_key = get_cache_key(user_id, 'data')
    time_key = get_cache_key(user_id, 'time')
    
    st.session_state[cache_key] = data
    st.session_state[time_key] = datetime.now()

def invalidate_user_cache(user_id):
    """Invalidate user cache"""
    cache_key = get_cache_key(user_id, 'data')
    time_key = get_cache_key(user_id, 'time')
    
    if cache_key in st.session_state:
        del st.session_state[cache_key]
    if time_key in st.session_state:
        del st.session_state[time_key]

# ============================================
# OPTIMIZED DATA PROCESSING
# ============================================

@lru_cache(maxsize=1000)
def classify_expense_cached(description, category_keywords_json):
    """Cached expense classification - O(1) for repeated items"""
    category_keywords = json.loads(category_keywords_json)
    desc = str(description).lower()
    
    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw in desc:
                return category
    return 'Uncategorized'

def process_csv(file):
    """Process CSV file"""
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
def process_uploaded_file(file, filename):
    """
    Process uploaded files - auto-detect format (JMMB CSV, NCB PDF, etc.)
    
    Args:
        file: File object from st.file_uploader
        filename: Name of the file
        
    Returns:
        pd.DataFrame with columns: Date, Description, Amount, Category
    """
    file_type = filename.split('.')[-1].lower()
    
    try:
        if file_type == 'csv':
            # Your existing CSV processor
            df = process_csv(file)
            
        elif file_type == 'pdf':
            # Detect which bank's PDF format
            file_bytes = file.read()
            text_sample = ""
            
            try:
                with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                    # Get first page to identify bank
                    if len(pdf.pages) > 0:
                        text_sample = pdf.pages[0].extract_text().lower()
            except:
                pass
            
            # Reset file pointer
            file.seek(0)
            
            # Detect NCB format by looking for "NCB" or characteristic patterns
            if "ncb" in text_sample or "national commercial bank" in text_sample:
                st.info("📊 Detected NCB Bank statement format")
                df = process_pdf_ncb(file)
            else:
                # Fallback to generic PDF processor
                st.info("📊 Processing generic PDF format")
                df = process_pdf(file)
        else:
            st.error(f"Unsupported file type: {file_type}")
            return pd.DataFrame()
        
        return df
        
    except Exception as e:
        st.error(f"Error processing {filename}: {str(e)}")
        return pd.DataFrame()


# REPLACE your existing process_pdf_ncb function with this corrected version

def parse_ncb_transaction_line(line: str, year: str = "2024") -> Optional[List]:
    """
    Parse a transaction line from NCB bank statement.
    
    Format: DD/Mon Description Amount Balance
    Example: 27/Sep ABM VMBS UTECH BR,237 OLD KINGSTON -55,000.00 11,357.94
    
    Args:
        line: Raw text line from NCB PDF
        year: Year to append to date (default: 2024)
        
    Returns:
        List containing [date, description, amount, category] or None
    """
    line = line.strip()
    if not line:
        return None
    
    # Check if line starts with a date pattern (DD/Mon)
    date_pattern = r'^(\d{1,2}/[A-Za-z]{3})\s+'
    match = re.match(date_pattern, line)
    
    if not match:
        return None
    
    try:
        date_str = match.group(1)
        remaining = line[match.end():].strip()
        
        # Split remaining into parts
        parts = remaining.split()
        if len(parts) < 2:
            return None
        
        # Last part is balance, second-to-last is transaction amount
        balance = parts[-1]
        amount_str = parts[-2]
        
        # Description is everything except the last two parts
        description = " ".join(parts[:-2])
        
        # Clean and convert amount
        amount_clean = amount_str.replace(',', '').replace('J$', '')
        
        # Determine if debit or credit based on negative sign
        is_negative = amount_clean.startswith('-')
        amount = abs(float(amount_clean))
        category = 'Debit' if is_negative else 'Credit'
        
        # Convert date to standard format
        full_date = f"{date_str}/{year}"
        
        return [full_date, description, amount, category]
        
    except (ValueError, IndexError) as e:
        return None


def process_pdf_ncb(file) -> pd.DataFrame:
    """
    Process NCB (National Commercial Bank) PDF statement file.
    
    Args:
        file: Uploaded PDF file object or BytesIO object
        
    Returns:
        DataFrame with columns: Date, Description, Amount, Category
    """
    try:
        transactions = []
        year = "2024"  # Default year
        
        # Handle both file uploads and BytesIO objects
        if isinstance(file, BytesIO):
            pdf_file = file
        else:
            pdf_file = BytesIO(file.read()) if hasattr(file, 'read') else BytesIO(file)
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                
                if not text:
                    continue
                
                # Try to extract year from the statement date if on first page
                if page_num == 1:
                    year_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', text)
                    if year_match:
                        year = year_match.group(3)
                
                # Process each line
                for line in text.split('\n'):
                    line = line.strip()
                    
                    # Skip empty lines and common footer text
                    if not line or 'CONTINUED' in line or 'END OF STATEMENT' in line:
                        continue
                    
                    # Skip lines that are clearly headers
                    skip_patterns = [
                        'JAMAICA',
                        'REGULAR SAVINGS',
                        'CURRENT ACCOUNT',
                        'SAVINGS ACCOUNT',
                        'JMD',
                        'USD',
                        r'MA \d{2}-\d{2}',
                        r'^\d{9}$',
                        r'^\d{2}-\d{2}-\d{4}$',
                        'P.O.',
                        'NATIONAL COMMERCIAL BANK',
                        'NCB',
                    ]
                    
                    should_skip = False
                    for pattern in skip_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            should_skip = True
                            break
                    
                    # Skip location names (all caps, no numbers)
                    if line.isupper() and not any(char.isdigit() for char in line) and len(line.split()) <= 3:
                        should_skip = True
                    
                    # Skip customer names
                    if re.match(r'^(MR|MRS|MS|DR|MISS)\s+[A-Z]', line):
                        should_skip = True
                    
                    if should_skip:
                        continue
                    
                    parsed = parse_ncb_transaction_line(line, year)
                    if parsed:
                        transactions.append(parsed)
        
        # Create DataFrame
        if not transactions:
            st.warning("No transactions found in NCB PDF file.")
            return pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Category'])
        
        df = pd.DataFrame(transactions, columns=['Date', 'Description', 'Amount', 'Category'])
        
        # Convert date to datetime
        try:
            df['Date'] = pd.to_datetime(df['Date'], format='%d/%b/%Y', errors='coerce')
        except Exception as e:
            st.error(f"Date conversion error: {e}")
        
        # Remove duplicates
        df_before = len(df)
        df = df.drop_duplicates()
        df_after = len(df)
        
        if df_before > df_after:
            st.info(f"Removed {df_before - df_after} duplicate transactions.")
        
        st.success(f"✅ Successfully extracted {len(df)} transactions from NCB PDF.")
        return df
        
    except Exception as e:
        st.error(f"NCB PDF Processing Error: {str(e)}")
        import traceback
        st.error(f"Details: {traceback.format_exc()}")
        return pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Category'])


def process_pdf(file):
    """Process PDF file"""
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

def load_all_user_data(user_id):
    """Load all user data with caching and proper file type detection"""
    # Check cache first
    cached_data = get_cached_data(user_id)
    if cached_data is not None:
        return cached_data
    
    # Load from database
    connection = create_connection()
    if not connection:
        return pd.DataFrame()
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, file_data, file_type, filename FROM user_files WHERE user_id = %s",
            (user_id,)
        )
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        
        all_data = []
        
        for file_info in files:
            try:
                file_bytes = BytesIO(file_info['file_data'])
                filename = file_info.get('filename', '')
                
                # Determine file type - check both file_type column and filename
                file_type = file_info['file_type'].lower()
                
                if file_type == 'pdf':
                    # Check if it's an NCB PDF by filename
                    if 'ncb' in filename.lower():
                        df = process_pdf_ncb(file_bytes)
                    else:
                        # Try to detect from content
                        try:
                            file_bytes.seek(0)
                            with pdfplumber.open(file_bytes) as pdf:
                                first_page_text = pdf.pages[0].extract_text().lower()
                                if 'ncb' in first_page_text or 'national commercial bank' in first_page_text:
                                    file_bytes.seek(0)
                                    df = process_pdf_ncb(file_bytes)
                                else:
                                    file_bytes.seek(0)
                                    df = process_pdf(file_bytes)
                        except:
                            file_bytes.seek(0)
                            df = process_pdf(file_bytes)
                            
                elif file_type == 'csv':
                    df = process_csv(file_bytes)
                else:
                    continue
                
                if not df.empty:
                    all_data.append(df)
                    
            except Exception as e:
                st.warning(f"Error processing {filename}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        # Concatenate all data
        result = pd.concat(all_data, ignore_index=True)
        
        # Convert dates
        result['Date'] = pd.to_datetime(result['Date'], errors='coerce')
        result = result.dropna(subset=['Date'])
        
        # Add month columns
        result['Month-Year'] = result['Date'].dt.strftime('%B %Y')
        result['Month-Name'] = result['Date'].dt.strftime('%B')
        result['YearMonth'] = result['Date'].dt.to_period('M').astype(str)
        
        # Cache the result
        set_cached_data(user_id, result)
        
        return result
        
    except Error as e:
        st.error(f"Error loading data: {e}")
        connection.close()
        return pd.DataFrame()

# ============================================
# PRE-COMPUTED SUMMARIES
# ============================================
def compute_monthly_summary(user_id, year_month, df):
    """Compute and store monthly summary (robust quoting + VALUES() in UPDATE)"""
    connection = create_connection()
    if not connection:
        return False

    try:
        # Filter data for the month
        month_data = df[df['YearMonth'] == year_month]

        if month_data.empty:
            return False

        total_income = float(month_data[month_data['Category'] == 'Credit']['Amount'].sum())
        total_spending = float(month_data[month_data['Category'] == 'Debit']['Amount'].sum())

        # Compute category breakdown safely (ensure keys are serializable)
        spending_by_category = month_data[month_data['Category'] == 'Debit'].groupby('Spending Category')['Amount'].sum()
        category_breakdown = json.dumps({str(k): float(v) for k, v in spending_by_category.to_dict().items()})

        transaction_count = int(len(month_data))

        cursor = connection.cursor()
        sql = """
            INSERT INTO `monthly_summaries`
            (`user_id`, `year_month`, `total_income`, `total_spending`, `category_breakdown`, `transaction_count`)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                `total_income` = VALUES(`total_income`),
                `total_spending` = VALUES(`total_spending`),
                `category_breakdown` = VALUES(`category_breakdown`),
                `transaction_count` = VALUES(`transaction_count`),
                `computed_at` = CURRENT_TIMESTAMP
        """
        params = (user_id, year_month, total_income, total_spending, category_breakdown, transaction_count)
        cursor.execute(sql, params)

        connection.commit()
        cursor.close()
        connection.close()
        return True

    except Error as e:
        # Show the SQL and params to make debugging easier (do NOT log passwords)
        try:
            st.error(f"Error computing summary: {e}")
            st.error(f"SQL: {sql}")
            st.error(f"Params: {params}")
        except Exception:
            st.error(f"Error computing summary (and failed to show SQL): {e}")
        connection.close()
        return False


def get_monthly_summary(user_id, year_month):
    """Get pre-computed monthly summary (quoted identifiers)"""
    connection = create_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        sql = """
            SELECT `total_income`, `total_spending`, `category_breakdown`,
                   `transaction_count`, `computed_at`
            FROM `monthly_summaries`
            WHERE `user_id` = %s AND `year_month` = %s
        """
        cursor.execute(sql, (user_id, year_month))

        summary = cursor.fetchone()
        cursor.close()
        connection.close()

        if summary and summary.get('category_breakdown'):
            try:
                summary['category_breakdown'] = json.loads(summary['category_breakdown'])
            except Exception:
                # If stored value is not JSON, leave as-is
                pass
            return summary

        return None

    except Error as e:
        try:
            st.error(f"Error retrieving summary: {e}")
            st.error(f"SQL: {sql}")
            st.error(f"Params: {(user_id, year_month)}")
        except Exception:
            st.error(f"Error retrieving summary: {e}")
        connection.close()
        return None
# ============================================
# USER PREFERENCES
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

# ============================================
# HELPER FUNCTIONS
# ============================================

def send_email_alert(receiver_email, subject, body, sender_email, sender_password, smtp_server, smtp_port=587):
    """Send email alerts"""
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
            st.info("📌 Gmail users must use App Passwords")
        return False
    except Exception as e:
        st.error(f"❌ Email Error: {str(e)}")
        return False

def export_to_excel(df):
    """Export data to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')
    processed_data = output.getvalue()
    return processed_data

def export_to_pdf(text_report):
    """Export report to PDF"""
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

# ============================================
# MAIN APP
# ============================================
def main_app():
    """Display main application with optimizations"""
    
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

    st.title("💼 Welcome to Finance Hub")
    st.markdown("Choose a feature below to get started:")

    option = st.radio(
        "What would you like to do?",
        ["📊 Spending Analysis", "📅 Budget Planner", "🌐 Network Analysis"],
        index=0
    )

    if option == "📊 Spending Analysis":
        st.markdown("### 📊 Spending Analysis")
        st.title("Personal Finance Tracker")

        st.markdown("---")

        # File Management with Pagination
        st.subheader("📁 Your Files")

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
                            st.markdown(f"**{file['filename']}**")
                            st.caption(f"Uploaded: {str(file['upload_date'])[:19]}")
                            st.caption(f"Type: {file['file_type'].upper()}")
                            if st.button(f"🗑️ Delete", key=f"del_{file['id']}"):
                                if delete_user_file(file['id'], st.session_state.user['id']):
                                    st.success(f"Deleted {file['filename']}")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete file")
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.session_state.file_page > 0:
                    if st.button("⬅️ Previous"):
                        st.session_state.file_page -= 1
                        st.rerun()
            with col3:
                max_pages = (total_files - 1) // 9
                if st.session_state.file_page < max_pages:
                    if st.button("Next ➡️"):
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
                st.info(f"📁 {len(uploaded_files)} file(s) selected for upload")
                
                if st.button("💾 Save Files to Account", type="primary"):
                    success_count = 0
                    error_list = []
                    
                    for file in uploaded_files:
                        try:
                            file_data = file.read()
                            file_type = file.name.split('.')[-1].lower()
                            st.write(f"Processing {file.name}...")
                            
                            if save_user_file(st.session_state.user['id'], file.name, file_data, file_type):
                                success_count += 1
                                st.success(f"✅ {file.name}")
                            else:
                                error_list.append(f"{file.name} - Save failed")
                        except Exception as e:
                            error_list.append(f"{file.name} - {str(e)}")
                    
                    st.markdown("---")
                    
                    if success_count > 0:
                        st.success(f"✅ Successfully saved {success_count} file(s)!")
                        st.info("Processing files... Please wait a moment and refresh the page.")
                        import time
                        time.sleep(1)
                        st.rerun()
                    
                    if error_list:
                        st.error(f"❌ Failed to save {len(error_list)} file(s):")
                        for error in error_list:
                            st.error(f"  • {error}")

        st.markdown("---")

        # Load all user data
        with st.spinner("Loading your financial data..."):
            data = load_all_user_data(st.session_state.user['id'])

        if data.empty:
            st.warning("⚠️ No transactions found.")
            st.info("📤 Upload your bank statements using the form above to get started!")
            st.stop()

        st.success(f"✅ Loaded {len(data):,} transactions")
        st.info(f"📅 Data from {len(data['Month-Year'].unique())} month(s)")

        # Load user preferences
        user_prefs = get_user_preferences(st.session_state.user['id'])
        

        default_mapping = {
            "Food": ["juici", "kfc", "restaurant", "burger", "pizza","subway", "mcdonald", "starbucks", "diner", "grill", "v.o.d.a. foods", "cafe blue", "tutti frutti", "popeyesohr","ribbiz lounge", "beifang kitchen"],
            "Grocery": ["hi-lo", "supermarket", "wholesale","grocery", "market", "walmart", "costco","shoppers fair"],
            "Utilities": ["jps", "nwc", "flow", "internet", "light", "water","electric", "cable", "wifi"],
            "Transport": ["uber", "taxi", "gas","shell", "parking", "lyft", "bus"],
            "Income": ["remitly", "deposit", "transfer", "payroll","salary", "refund"],
            "Home Improvement": ["lumber depot limited", "ping's fabric"],
            "Retail": ["boss destinations", "n k wholesale liquor stor","digicel ding"],
            "Miscellaneous": ["atm", "fee", "charge"],
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
        
        if user_prefs:
            saved_categories = json.loads(user_prefs['category_keywords']) if user_prefs['category_keywords'] else default_mapping
            saved_budgets = json.loads(user_prefs['monthly_budgets']) if user_prefs['monthly_budgets'] else default_budgets
            saved_goal = float(user_prefs['savings_goal']) if user_prefs['savings_goal'] else default_savings_goal
        else:
            saved_categories = default_mapping
            saved_budgets = default_budgets
            saved_goal = default_savings_goal

        # Sidebar: Categories and Budgets
        st.sidebar.header("🗂 Customize Categories and Budgets")
        
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

        # Email notification settings
        st.sidebar.subheader("📧 Email Alerts")
        enable_email = st.sidebar.checkbox("Enable Email Notifications")
        
        if enable_email:
            email_provider = st.sidebar.selectbox("Provider", ["Gmail", "Outlook", "Yahoo", "Custom"])
            
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

        # Apply spending categories
        category_json = json.dumps(CATEGORY_KEYWORDS)
        data['Spending Category'] = data['Description'].apply(
            lambda x: classify_expense_cached(x, category_json)
        )

        # Trend Analysis
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

        # Monthly Analysis
        st.header("📅 Monthly Analysis")
        
        available_months_list = sorted(data['Month-Name'].unique(), 
                                      key=lambda x: list(calendar.month_name).index(x))
        
        selected_month = st.selectbox("Select Month", available_months_list)
        
        month_data = data[data['Month-Name'] == selected_month].copy()
        
        if not month_data.empty:
            year_month = month_data['YearMonth'].iloc[0]
            summary_cached = get_monthly_summary(st.session_state.user['id'], year_month)
            
            if not summary_cached:
                compute_monthly_summary(st.session_state.user['id'], year_month, data)
                summary_cached = get_monthly_summary(st.session_state.user['id'], year_month)
            
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
            st.dataframe(month_data[['Date', 'Description', 'Amount', 'Category', 'Spending Category']])

            st.subheader(f"📈 Spending Breakdown for {selected_month}")
            spend = month_data[month_data['Category'] == 'Debit']
            
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
                st.markdown(f"**Savings Goal:** J${SAVINGS_GOAL:,.2f}")
                st.markdown(f"**Actual Savings:** J${month_savings:,.2f}")

                if month_savings >= SAVINGS_GOAL:
                    st.success(f"🎉 Congrats! You've met your savings goal by J${month_savings - SAVINGS_GOAL:,.2f}!")
                else:
                    st.warning(f"You are J${SAVINGS_GOAL - month_savings:,.2f} below your savings goal.")

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
                for idx, row in month_data.iterrows():
                    report_text += f"{row['Date'].date()} | {row['Description']} | J${row['Amount']:,.2f} | {row['Category']} | {row['Spending Category']}\n"

                report_text += "\nSpending Summary:\n"
                for idx, row in summary.iterrows():
                    report_text += f"{row['Spending Category']}: J${row['Amount']:,.2f} ({row['Percentage']:.2f}%)\n"

                export_format = st.selectbox("Select export format", options=["Excel", "PDF"])

                if st.button("Download Report"):
                    if export_format == "Excel":
                        excel_bytes = export_to_excel(month_data)
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
        st.markdown("### 📅 Budget Planner")
        st.title("📋 Budget Dashboard")
        st.info("Budget planner feature - Upload your budget Excel file to get started!")

    elif option == "🌐 Network Analysis":
        st.markdown("### 🌐 Network Analysis")
        st.info("Network analysis feature coming soon! This will show transaction patterns and relationships.")



# ============================================
# MAIN APPLICATION
# ============================================

def main():
    st.set_page_config(
        page_title="Finance Hub",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded"
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
