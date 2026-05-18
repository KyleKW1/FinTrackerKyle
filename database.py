# database.py
"""
Database connection and operations module
Handles all database interactions including user management and file storage
"""

import mysql.connector
from mysql.connector import Error
import streamlit as st
import json
import ssl

# Import config - with fallback
try:
    from config import DB_CONFIG
except ImportError:
    st.error("config.py not found! Please create it with your database credentials.")
    st.stop()


def create_connection():
    """Create database connection with SSL fix"""
    try:
        # Create connection config with SSL disabled for Streamlit Cloud
        connection_config = {
            'host': DB_CONFIG['host'],
            'port': DB_CONFIG['port'],
            'user': DB_CONFIG['user'],
            'password': DB_CONFIG['password'],
            'database': DB_CONFIG['database'],
            'connection_timeout': 30,
            'autocommit': False,
            'ssl_disabled': True  # Disable SSL verification
        }
        
        connection = mysql.connector.connect(**connection_config)
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None


# ============================================
# USER OPERATIONS
# ============================================

def get_user_by_username(username):
    """Get user by username"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        return user
    except Error as e:
        st.error(f"Error fetching user: {e}")
        if connection:
            connection.close()
        return None


def get_user_by_email(email):
    """Get user by email"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        return user
    except Error as e:
        st.error(f"Error fetching user: {e}")
        if connection:
            connection.close()
        return None


def create_user(username, email, password_hash):
    """Create new user"""
    connection = create_connection()
    if not connection:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True, "Registration successful!"
    except mysql.connector.IntegrityError:
        if connection:
            connection.close()
        return False, "Username or email already exists"
    except Error as e:
        if connection:
            connection.close()
        return False, f"Registration error: {e}"


def update_last_login(user_id):
    """Update user's last login timestamp"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        if connection:
            connection.close()
        return False


def update_user_password(user_id, new_password_hash):
    """Update user password"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_password_hash, user_id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        if connection:
            connection.close()
        return False


# ============================================
# FILE OPERATIONS
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
        if connection:
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
        if connection:
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
        if connection:
            connection.close()
        return [], 0


def get_all_user_files(user_id):
    """Get all user files (for data loading)"""
    connection = create_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, file_data, file_type, filename FROM user_files WHERE user_id = %s",
            (user_id,)
        )
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        return files
    except Error as e:
        st.error(f"Error loading data: {e}")
        if connection:
            connection.close()
        return []


# ============================================
# PREFERENCES OPERATIONS
# ============================================

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
        if connection:
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
        if connection:
            connection.close()
        return False


# ============================================
# MONTHLY SUMMARIES
# ============================================

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
        if connection:
            connection.close()
        return None


def save_monthly_summary(user_id, year_month, total_income, total_spending, net_savings):
    """Compute and store monthly summary"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO monthly_summaries (user_id, year_month, total_income, total_spending, net_savings)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE total_income = %s, total_spending = %s, net_savings = %s""",
            (user_id, year_month, total_income, total_spending, net_savings, 
             total_income, total_spending, net_savings)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        if connection:
            connection.close()
        return False



# ═══════════════════════════════════════════════════════════════════════════
# MULTI-ACCOUNT EMAIL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
 
def get_all_email_accounts(user_id: int) -> list:
    """
    Return all active email accounts for this user from the email_accounts table.
    Falls back gracefully to the legacy email_sync_settings table if the new
    table does not yet exist.
    """
    connection = create_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, email_address, app_password, provider, sync_days, last_sync
              FROM email_accounts
             WHERE user_id = %s AND is_active = 1
             ORDER BY created_at ASC
        """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        return rows
    except Error:
        # Table doesn't exist yet — return empty so caller falls back
        if connection:
            connection.close()
        return []
 
 
def add_email_account(
    user_id: int,
    email_address: str,
    app_password: str,
    sync_days: int = 90,
    provider: str = "auto",
) -> bool:
    """
    Insert or update an email account for this user.
    Uses ON DUPLICATE KEY UPDATE so re-saving with a new password just updates it.
    """
    connection = create_connection()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO email_accounts
                (user_id, email_address, app_password, provider, sync_days)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                app_password  = VALUES(app_password),
                provider      = VALUES(provider),
                sync_days     = VALUES(sync_days),
                is_active     = 1
        """, (user_id, email_address.strip(), app_password.strip(),
              provider, sync_days))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error:
        if connection:
            connection.close()
        return False
 
 
def remove_email_account(user_id: int, email_address: str) -> bool:
    """Soft-delete (deactivate) one email account for this user."""
    connection = create_connection()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE email_accounts
               SET is_active = 0
             WHERE user_id = %s AND email_address = %s
        """, (user_id, email_address))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error:
        if connection:
            connection.close()
        return False
 
 
def update_account_last_sync(user_id: int, email_address: str) -> None:
    """Stamp last_sync = NOW() for one specific account."""
    connection = create_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE email_accounts
               SET last_sync = CURRENT_TIMESTAMP
             WHERE user_id = %s AND email_address = %s
        """, (user_id, email_address))
        connection.commit()
        cursor.close()
        connection.close()
    except Error:
        if connection:
            connection.close()
 
 
# ═══════════════════════════════════════════════════════════════════════════
# UPDATED save_email_transactions
# Replace the existing save_email_transactions function with this version.
# It now also stores spending_category and is_subscription.
# ═══════════════════════════════════════════════════════════════════════════
 
def save_email_transactions_v2(user_id: int, transactions: list) -> int:
    """
    Insert new email-parsed transactions.
    Silently ignores exact duplicates (same user / date / description / amount).
    Returns the number of rows actually inserted.
 
    This version stores the richer fields produced by the new email_scanner:
        spending_category  →  used by Budget vs Actual page
        is_subscription    →  used by Subscription Tracker
    """
    connection = create_connection()
    if not connection:
        return 0
    added = 0
    try:
        cursor = connection.cursor()
        for tx in transactions:
            try:
                cursor.execute("""
                    INSERT IGNORE INTO email_transactions
                        (user_id, tx_date, description, amount,
                         category, spending_category, is_subscription,
                         email_subject, sender)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    tx["date"],
                    tx.get("description", "Bank Transaction")[:500],
                    tx["amount"],
                    tx.get("category", "Debit"),
                    tx.get("spending_category", "Other")[:100],
                    1 if tx.get("is_subscription") else 0,
                    tx.get("subject", "")[:500],
                    tx.get("sender",  "")[:200],
                ))
                if cursor.rowcount:
                    added += 1
            except Error:
                continue
        connection.commit()
        cursor.close()
        connection.close()
    except Error:
        if connection:
            connection.close()
    return added
 
 
# Monkey-patch: make save_email_transactions point to the v2 version
# so all existing callers automatically get the richer save without
# any other code changes needed.
save_email_transactions = save_email_transactions_v2
 
 
# ═══════════════════════════════════════════════════════════════════════════
# UPDATED get_email_transactions
# Replace the existing get_email_transactions function with this version.
# It now also returns spending_category and is_subscription.
# ═══════════════════════════════════════════════════════════════════════════
 
def get_email_transactions_v2(user_id: int) -> list:
    """
    Return all email-synced transactions for this user.
    The spending_category column means data_loader can skip the slow
    categorize_transactions() pass for these rows.
    """
    connection = create_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT tx_date          AS Date,
                   description      AS Description,
                   amount           AS Amount,
                   category         AS Category,
                   spending_category AS `Spending Category`,
                   is_subscription  AS is_subscription,
                   'email'          AS source
              FROM email_transactions
             WHERE user_id = %s
             ORDER BY tx_date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        return rows
    except Error:
        if connection:
            connection.close()
        return []
 
 
# Same monkey-patch pattern — no other file needs changing.
get_email_transactions = get_email_transactions_v2
 
