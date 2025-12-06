# data_processing.py
"""
Data processing module - handles CSV and PDF parsing with enhanced extraction
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
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                file_bytes.seek(0)
                df = pd.read_csv(file_bytes, encoding=encoding)
                break
            except:
                continue
        
        if df is None:
            return pd.DataFrame()
        
        # Standardize columns
        df = standardize_dataframe_columns(df)
        
        # Categorize transactions - ALWAYS call this
        df = categorize_transactions(df)
        
        return df
    except Exception as e:
        print(f"Error processing CSV: {e}")
        return pd.DataFrame()


def extract_from_pdf(file_bytes):
    """Enhanced PDF extraction with multiple strategies"""
    try:
        file_bytes.seek(0)
        transactions = []
        
        with pdfplumber.open(file_bytes) as pdf:
            for page in pdf.pages:
                # Strategy 1: Try table extraction first
                tables = page.extract_tables()
                if tables:
                    transactions.extend(extract_from_tables(tables))
                
                # Strategy 2: Try text extraction with multiple patterns
                text = page.extract_text()
                if text:
                    transactions.extend(extract_from_text(text))
        
        if not transactions:
            return pd.DataFrame()
        
        # Remove duplicates
        df = pd.DataFrame(transactions)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'])
        
        # ALWAYS categorize after creating DataFrame
        df = categorize_transactions(df)
        
        return df
    except Exception as e:
        print(f"Error extracting from PDF: {e}")
        return pd.DataFrame()


def extract_from_tables(tables):
    """Extract transactions from PDF tables"""
    transactions = []
    
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Try to identify header row
        header_row = None
        for i, row in enumerate(table[:3]):  # Check first 3 rows for headers
            row_str = ' '.join([str(cell).lower() for cell in row if cell])
            if any(word in row_str for word in ['date', 'description', 'amount', 'particulars', 'details']):
                header_row = i
                break
        
        if header_row is None:
            header_row = 0
        
        headers = table[header_row]
        
        # Find column indices
        date_idx = find_column_index(headers, ['date', 'trans date', 'posting date'])
        desc_idx = find_column_index(headers, ['description', 'particulars', 'details', 'narrative'])
        amount_idx = find_column_index(headers, ['amount', 'debit', 'credit', 'value'])
        
        if date_idx is None or desc_idx is None or amount_idx is None:
            continue
        
        # Extract data rows
        for row in table[header_row + 1:]:
            try:
                if len(row) <= max(date_idx, desc_idx, amount_idx):
                    continue
                
                date_str = str(row[date_idx]).strip()
                description = str(row[desc_idx]).strip()
                amount_str = str(row[amount_idx]).strip()
                
                if not date_str or not description or not amount_str:
                    continue
                if date_str in ['None', 'nan', '']:
                    continue
                
                # Parse date
                date = parse_date(date_str)
                if date is None:
                    continue
                
                # Parse amount
                amount = parse_amount(amount_str)
                if amount <= 0:
                    continue
                
                # Determine category
                is_credit = any(word in description.lower() for word in 
                              ['deposit', 'transfer in', 'refund', 'credit', 'salary', 'income'])
                
                transactions.append({
                    'Date': date,
                    'Description': description,
                    'Amount': amount,
                    'Category': 'Credit' if is_credit else 'Debit'
                })
            except:
                continue
    
    return transactions


def extract_from_text(text):
    """Extract transactions from PDF text with multiple patterns"""
    transactions = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Skip header lines
        if any(word in line.lower() for word in ['statement', 'account', 'balance', 'page']):
            continue
        
        # Pattern matching with multiple formats
        patterns = [
            # MM/DD/YYYY or DD/MM/YYYY with description and amount
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})(?:\s|$)',
            # YYYY-MM-DD with description and amount
            r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})(?:\s|$)',
            # DD-MMM-YYYY (15-Jan-2024)
            r'(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})(?:\s|$)',
            # MMM DD, YYYY (Jan 15, 2024)
            r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})\s+(.+?)\s+([\d,]+\.\d{2})(?:\s|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                date_str, description, amount_str = match.groups()
                
                try:
                    date = parse_date(date_str)
                    if date is None:
                        continue
                    
                    amount = parse_amount(amount_str)
                    if amount <= 0:
                        continue
                    
                    description = description.strip()
                    if len(description) < 3:
                        continue
                    
                    is_credit = any(word in description.lower() for word in 
                                  ['deposit', 'transfer in', 'refund', 'credit', 'salary', 'income'])
                    
                    transactions.append({
                        'Date': date,
                        'Description': description,
                        'Amount': amount,
                        'Category': 'Credit' if is_credit else 'Debit'
                    })
                    break
                except:
                    continue
    
    return transactions


def find_column_index(headers, possible_names):
    """Find column index by matching possible header names"""
    for i, header in enumerate(headers):
        if not header:
            continue
        header_lower = str(header).lower().strip()
        for name in possible_names:
            if name in header_lower:
                return i
    return None


def parse_date(date_str):
    """Parse date string with multiple formats"""
    date_str = str(date_str).strip()
    
    if not date_str or date_str in ['None', 'nan', '']:
        return None
    
    formats = [
        '%m/%d/%Y', '%d/%m/%Y',  # 01/15/2024 or 15/01/2024
        '%Y-%m-%d',              # 2024-01-15
        '%d-%b-%Y', '%d-%B-%Y',  # 15-Jan-2024 or 15-January-2024
        '%b %d, %Y', '%B %d, %Y',# Jan 15, 2024 or January 15, 2024
        '%m-%d-%Y', '%d-%m-%Y',  # 01-15-2024 or 15-01-2024
    ]
    
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    
    # Try pandas auto-detection as last resort
    try:
        date = pd.to_datetime(date_str)
        # Validate year is reasonable (between 2000 and 2100)
        if 2000 <= date.year <= 2100:
            return date
    except:
        pass
    
    return None


def parse_amount(amount_str):
    """Parse amount string"""
    try:
        # Remove currency symbols, commas, and spaces
        cleaned = str(amount_str).replace('$', '').replace(',', '').replace('J', '').replace(' ', '').strip()
        
        if not cleaned or cleaned in ['None', 'nan', '']:
            return 0.0
        
        # Handle parentheses (negative)
        if '(' in cleaned or ')' in cleaned:
            cleaned = cleaned.replace('(', '').replace(')', '')
            return abs(float(cleaned))
        
        # Handle minus sign
        cleaned = cleaned.replace('-', '')
        
        return abs(float(cleaned))
    except:
        return 0.0


def process_pdf_ncb(file_bytes):
    """Process NCB PDF bank statement - uses enhanced extraction"""
    return extract_from_pdf(file_bytes)


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
        'trans. date': 'Date',
        
        'description': 'Description',
        'details': 'Description',
        'transaction': 'Description',
        'merchant': 'Description',
        'narrative': 'Description',
        'particulars': 'Description',
        
        'amount': 'Amount',
        'value': 'Amount',
        'debit': 'Amount',
        'credit': 'Amount',
        
        'type': 'Category',
        'transaction type': 'Category',
        'category': 'Category',
        'trans type': 'Category'
    }
    
    # Rename columns (case-insensitive)
    df.columns = df.columns.str.lower().str.strip()
    
    # Create new column names
    new_columns = {}
    for col in df.columns:
        if col in column_mappings:
            new_columns[col] = column_mappings[col]
    
    df = df.rename(columns=new_columns)
    
    # Ensure required columns exist
    if 'Date' not in df.columns:
        date_candidates = [c for c in df.columns if 'date' in c.lower()]
        if date_candidates:
            df['Date'] = df[date_candidates[0]]
    
    if 'Description' not in df.columns:
        desc_candidates = [c for c in df.columns if any(word in c.lower() for word in ['desc', 'detail', 'particular'])]
        if desc_candidates:
            df['Description'] = df[desc_candidates[0]]
    
    if 'Amount' not in df.columns:
        amount_candidates = [c for c in df.columns if any(word in c.lower() for word in ['amount', 'value', 'debit', 'credit'])]
        if amount_candidates:
            df['Amount'] = df[amount_candidates[0]]
    
    # Add Category if missing
    if 'Category' not in df.columns:
        df['Category'] = 'Debit'
    
    # Convert Date column
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
    
    # Convert Amount to numeric
    if 'Amount' in df.columns:
        df['Amount'] = df['Amount'].astype(str).str.replace('$', '').str.replace(',', '').str.replace('J', '').str.strip()
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Amount'] = df['Amount'].abs()
        df = df[df['Amount'] > 0]
    
    # Clean up description
    if 'Description' in df.columns:
        df['Description'] = df['Description'].astype(str).str.strip()
        df = df[df['Description'].notna()]
        df = df[df['Description'] != 'nan']
    
    return df


def categorize_transactions(df):
    """
    Categorize transactions based on keywords
    This function MUST always add a 'Spending Category' column
    """
    if df.empty:
        return df
    
    # Ensure Description column exists
    if 'Description' not in df.columns:
        df['Spending Category'] = 'Other'
        return df
    
    # Get user preferences or use defaults
    category_keywords = DEFAULT_CATEGORY_MAPPING.copy()
    
    try:
        if 'user' in st.session_state and st.session_state.user:
            prefs = get_user_preferences(st.session_state.user['id'])
            if prefs and prefs.get('category_keywords'):
                user_keywords = json.loads(prefs['category_keywords'])
                # Merge user keywords with defaults (user keywords take priority)
                for category, keywords in user_keywords.items():
                    if keywords:  # Only update if user has keywords for this category
                        category_keywords[category] = keywords
    except Exception as e:
        print(f"Error loading user preferences, using defaults: {e}")
    
    # Initialize spending category column
    df['Spending Category'] = 'Other'
    
    # Categorize each transaction
    for idx, row in df.iterrows():
        description = str(row['Description']).lower()
        
        # Check if it's income/credit first
        if row.get('Category') == 'Credit':
            df.at[idx, 'Spending Category'] = 'Income'
            continue
        
        # Check each category's keywords
        categorized = False
        for category, keywords in category_keywords.items():
            if category == 'Other':  # Skip 'Other' category
                continue
            
            # Check if any keyword matches
            for keyword in keywords:
                if keyword.lower() in description:
                    df.at[idx, 'Spending Category'] = category
                    categorized = True
                    break
            
            if categorized:
                break
        
        # If not categorized, it remains 'Other'
    
    return df
