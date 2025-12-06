# data_processing.py
"""
Data processing module - handles CSV and PDF parsing
"""

import pandas as pd
import pdfplumber
from io import BytesIO
import re
from config import DEFAULT_CATEGORY_MAPPING
from database import get_user_preferences
import streamlit as st
import json


def process_csv(file_bytes):
    """Process CSV file and return DataFrame"""
    try:
        file_bytes.seek(0)
        df = pd.read_csv(file_bytes)
        
        # Standardize columns
        df = standardize_dataframe_columns(df)
        
        # Categorize transactions
        df = categorize_transactions(df)
        
        return df
    except Exception as e:
        st.warning(f"Error processing CSV: {e}")
        return pd.DataFrame()


def process_pdf_ncb(file_bytes):
    """Process NCB PDF bank statement"""
    try:
        file_bytes.seek(0)
        transactions = []
        
        with pdfplumber.open(file_bytes) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    # NCB format: Date Description Amount
                    # Example: 01/15/2024 PURCHASE AT KFC 1,500.00
                    match = re.match(
                        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})',
                        line.strip()
                    )
                    
                    if match:
                        date_str, description, amount_str = match.groups()
                        
                        try:
                            date = pd.to_datetime(date_str, format='%m/%d/%Y')
                            amount = float(amount_str.replace(',', ''))
                            
                            # Determine if credit or debit
                            is_credit = any(word in description.lower() for word in 
                                          ['deposit', 'transfer in', 'refund', 'credit'])
                            
                            transactions.append({
                                'Date': date,
                                'Description': description.strip(),
                                'Amount': amount,
                                'Category': 'Credit' if is_credit else 'Debit'
                            })
                        except:
                            continue
        
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df = categorize_transactions(df)
        
        return df
    except Exception as e:
        st.warning(f"Error processing NCB PDF: {e}")
        return pd.DataFrame()


def extract_from_pdf(file_bytes):
    """Generic PDF extraction for other bank formats"""
    try:
        file_bytes.seek(0)
        transactions = []
        
        with pdfplumber.open(file_bytes) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    # Try to extract date, description, amount
                    # Common patterns:
                    # 01/15/2024 Description 1,500.00
                    # 2024-01-15 Description 1500.00
                    
                    # Pattern 1: MM/DD/YYYY
                    match = re.search(
                        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})',
                        line
                    )
                    
                    if not match:
                        # Pattern 2: YYYY-MM-DD
                        match = re.search(
                            r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})',
                            line
                        )
                    
                    if match:
                        date_str, description, amount_str = match.groups()
                        
                        try:
                            # Try both date formats
                            try:
                                date = pd.to_datetime(date_str, format='%m/%d/%Y')
                            except:
                                date = pd.to_datetime(date_str, format='%Y-%m-%d')
                            
                            amount = float(amount_str.replace(',', ''))
                            
                            # Determine category
                            is_credit = any(word in description.lower() for word in 
                                          ['deposit', 'transfer in', 'refund', 'credit', 'income'])
                            
                            transactions.append({
                                'Date': date,
                                'Description': description.strip(),
                                'Amount': amount,
                                'Category': 'Credit' if is_credit else 'Debit'
                            })
                        except:
                            continue
        
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df = categorize_transactions(df)
        
        return df
    except Exception as e:
        st.warning(f"Error extracting from PDF: {e}")
        return pd.DataFrame()


def standardize_dataframe_columns(df):
    """Standardize column names across different formats"""
    if df.empty:
        return df
    
    # Common column name mappings
    column_mappings = {
        'date': 'Date',
        'transaction date': 'Date',
        'posting date': 'Date',
        'trans date': 'Date',
        
        'description': 'Description',
        'details': 'Description',
        'transaction': 'Description',
        'merchant': 'Description',
        'narrative': 'Description',
        
        'amount': 'Amount',
        'value': 'Amount',
        'debit': 'Amount',
        'credit': 'Amount',
        
        'type': 'Category',
        'transaction type': 'Category',
        'category': 'Category'
    }
    
    # Rename columns
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=column_mappings)
    
    # Ensure required columns exist
    required_columns = ['Date', 'Description', 'Amount']
    
    for col in required_columns:
        if col not in df.columns:
            if col == 'Date' and 'date' in df.columns.str.lower():
                date_col = [c for c in df.columns if c.lower() == 'date'][0]
                df['Date'] = df[date_col]
            elif col == 'Description' and 'description' in df.columns.str.lower():
                desc_col = [c for c in df.columns if 'description' in c.lower()][0]
                df['Description'] = df[desc_col]
            elif col == 'Amount':
                # Try to find amount column
                amount_candidates = [c for c in df.columns if any(word in c.lower() 
                                   for word in ['amount', 'value', 'debit', 'credit'])]
                if amount_candidates:
                    df['Amount'] = df[amount_candidates[0]]
    
    # Add Category if missing
    if 'Category' not in df.columns:
        df['Category'] = 'Debit'  # Default to debit
    
    # Convert Date column
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Convert Amount to numeric
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'].astype(str).str.replace(',', ''), errors='coerce')
        df['Amount'] = df['Amount'].abs()  # Take absolute value
    
    # Clean up description
    if 'Description' in df.columns:
        df['Description'] = df['Description'].astype(str).str.strip()
    
    return df


def categorize_transactions(df):
    """Categorize transactions based on keywords"""
    if df.empty or 'Description' not in df.columns:
        return df
    
    # Get user preferences or use defaults
    try:
        if 'user' in st.session_state and st.session_state.user:
            prefs = get_user_preferences(st.session_state.user['id'])
            if prefs and prefs.get('category_keywords'):
                category_keywords = json.loads(prefs['category_keywords'])
            else:
                category_keywords = DEFAULT_CATEGORY_MAPPING
        else:
            category_keywords = DEFAULT_CATEGORY_MAPPING
    except:
        category_keywords = DEFAULT_CATEGORY_MAPPING
    
    # Initialize spending category
    df['Spending Category'] = 'Other'
    
    # Categorize each transaction
    for idx, row in df.iterrows():
        description = str(row['Description']).lower()
        
        # Skip income transactions
        if row.get('Category') == 'Credit':
            df.at[idx, 'Spending Category'] = 'Income'
            continue
        
        # Check each category's keywords
        for category, keywords in category_keywords.items():
            if any(keyword.lower() in description for keyword in keywords):
                df.at[idx, 'Spending Category'] = category
                break
    
    return df


def clean_amount(amount_str):
    """Clean and convert amount string to float"""
    try:
        # Remove currency symbols and commas
        cleaned = str(amount_str).replace('$', '').replace(',', '').replace('J', '').strip()
        
        # Handle negative signs
        if '(' in cleaned or ')' in cleaned:
            cleaned = '-' + cleaned.replace('(', '').replace(')', '')
        
        return abs(float(cleaned))
    except:
        return 0.0


def validate_dataframe(df):
    """Validate that DataFrame has required columns and data"""
    if df.empty:
        return False, "DataFrame is empty"
    
    required_cols = ['Date', 'Description', 'Amount']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        return False, f"Missing required columns: {', '.join(missing_cols)}"
    
    # Check for valid data
    if df['Date'].isna().all():
        return False, "No valid dates found"
    
    if df['Amount'].isna().all() or (df['Amount'] == 0).all():
        return False, "No valid amounts found"
    
    if df['Description'].isna().all():
        return False, "No valid descriptions found"
    
    return True, "Valid"
