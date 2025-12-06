# config.py
"""
Configuration file for Finance Hub application
Uses environment variables for sensitive data - NEVER commit credentials!
"""

import os
import streamlit as st

# ============================================
# DATABASE CONFIGURATION - SECURE VERSION
# ============================================
# Use Streamlit secrets in production, environment variables locally
DB_CONFIG = {
    'host': st.secrets.get("DB_HOST", os.getenv("DB_HOST", "")),
    'port': int(st.secrets.get("DB_PORT", os.getenv("DB_PORT", 11510))),
    'user': st.secrets.get("DB_USER", os.getenv("DB_USER", "")),
    'password': st.secrets.get("DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
    'database': st.secrets.get("DB_NAME", os.getenv("DB_NAME", "defaultdb")),
    'ssl_disabled': False,
    'ssl_verify_cert': True,
    'ssl_verify_identity': True,
    'connection_timeout': 30,
    'autocommit': False
}

# ============================================
# EMAIL CONFIGURATION - SECURE VERSION
# ============================================
EMAIL_CONFIG = {
    'sender_email': st.secrets.get("EMAIL_USER", os.getenv("EMAIL_USER", "")),
    'sender_password': st.secrets.get("EMAIL_PASSWORD", os.getenv("EMAIL_PASSWORD", "")),
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

# ============================================
# VALIDATE CONFIGURATION
# ============================================
def validate_config():
    """Validate that all required configuration is present"""
    required_db = ['host', 'user', 'password', 'database']
    required_email = ['sender_email', 'sender_password']
    
    missing = []
    
    for key in required_db:
        if not DB_CONFIG.get(key):
            missing.append(f"DB_{key.upper()}")
    
    for key in required_email:
        if not EMAIL_CONFIG.get(key):
            missing.append(f"EMAIL_{key.upper()}")
    
    if missing:
        st.error(f"❌ Missing configuration: {', '.join(missing)}")
        st.info("Please configure secrets in Streamlit Cloud or set environment variables locally")
        return False
    
    return True

# ============================================
# DEFAULT CATEGORY MAPPINGS
# ============================================
DEFAULT_CATEGORY_MAPPING = {
    "Food": ["juici", "kfc", "restaurant", "burger", "pizza", "subway", 
             "mcdonald", "starbucks", "cafe blue", "tim hortons"],
    "Grocery": ["hi-lo", "supermarket", "wholesale", "grocery", "market", 
                "walmart", "costco", "shoppers fair"],
    "Utilities": ["jps", "nwc", "flow", "internet", "light", "water", 
                  "electric", "cable", "wifi", "bill payment"],
    "Transport": ["uber", "ubr", "taxi", "gas", "shell", "parking", 
                  "lyft", "bus", "knutsford express"],
    "Income": ["remitly", "deposit", "transfer", "payroll", "salary", 
               "refund", "interest"],
    "Home Improvement": ["lumber depot", "ping's fabric"],
    "Retail & Entertainment": ["digicel", "macys", "bumble", "duty free"],
    "Miscellaneous": ["atm", "abm", "fee", "charge", "gct"],
    "Other": []
}

# Default Monthly Budgets
DEFAULT_BUDGETS = {
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

# Default Savings Goal
DEFAULT_SAVINGS_GOAL = 5000

# Pagination Settings
FILES_PER_PAGE = 9

# App Settings
APP_TITLE = "Finance Hub"
APP_ICON = "💼"
