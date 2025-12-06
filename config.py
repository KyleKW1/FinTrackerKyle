# config.py
"""
Configuration file for Finance Hub application
Contains database settings, email settings, and app constants
"""

# Database Configuration - Aiven Cloud MySQL
DB_CONFIG = {
    'host': 'mysql-11beff9b-kamarwatson36-874b.g.aivencloud.com',
    'port': 11510,
    'user': 'avnadmin',
    'password': 'AVNS_Dxyg2mu3MEiRoVyasff',
    'database': 'defaultdb',
    'ssl_disabled': False,
    'ssl_verify_cert': True,
    'ssl_verify_identity': True,
    'connection_timeout': 30,
    'autocommit': False
}

# Email Configuration
EMAIL_CONFIG = {
    'sender_email': 'fintrackeralerts@gmail.com',
    'sender_password': 'myhdkbyrzmpvwjyb',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

# Default Category Mappings
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
