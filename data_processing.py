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


def detect_ncb_pdf(file_bytes):
    """
    Score-based NCB detection - generalized for all branches
    Works for NCB statements from any branch in Jamaica
    """
    try:
        file_bytes.seek(0)
        with pdfplumber.open(file_bytes) as pdf:
            if not pdf.pages:
                return False
            
            # Extract text from first page
            text = pdf.pages[0].extract_text()
            if not text:
                return False
                
            text = text.upper()
            score = 0
            
            # Primary identifier - CRITICAL (3 points)
            if 'NATIONAL COMMERCIAL BANK' in text:
                score += 3
            
            # Check for NCB-specific account types (1 point)
            account_types = [
                'REGULAR SAVINGS', 'CURRENT ACCOUNT', 'SAVINGS ACCOUNT', 
                'CHEQUING', 'NCB ACCOUNT', 'STUDENT ACCOUNT'
            ]
            if any(acc_type in text for acc_type in account_types):
                score += 1
            
            # Check for NCB date format (DD/Mon pattern, e.g., 15/Jan) (2 points)
            if re.search(r'\d{2}/[A-Z][a-z]{2}\s', text):
                score += 2
            
            # Check for NCB-specific transaction codes (1-2 points)
            ncb_keywords = [
                'ELINK TRF', 'BPYMT', 'ABM TX FEE', 'POS PURCHASE', 
                'ATM WITHDRAWAL', 'BILL PAYMENT', 'BILLPAY', 'E-LINK'
            ]
            keyword_matches = sum(1 for kw in ncb_keywords if kw in text)
            if keyword_matches >= 2:
                score += 2
            elif keyword_matches >= 1:
                score += 1
            
            # Check for Jamaica-specific patterns (1 point)
            jamaica_indicators = ['JAMAICA', 'JMD', 'J$', 'JA ']
            if any(indicator in text for indicator in jamaica_indicators):
                score += 1
            
            # Check for statement-specific headers (1 point)
            if 'STATEMENT' in text and 'ACCOUNT' in text:
                score += 1
            
            # Check for NCB branch patterns - any branch (1 point)
            # Look for typical branch address format
            if re.search(r'[A-Z\s]+,\s*JAMAICA', text):
                score += 1
            
            print(f"   NCB Detection Score: {score}/12")
            
            # Threshold: need at least 4 points to confirm NCB
            # This ensures we need multiple indicators, not just one
            return score >= 4
            
    except Exception as e:
        print(f"   NCB Detection Error: {e}")
        return False


def parse_ncb_transaction_line(line, year):
    """
    Ultra-robust NCB transaction parser
    Handles multiple NCB statement formats
    """
    
    # PATTERN SET 1: Standard format with balance
    # Format: DD/Mon DESCRIPTION AMOUNT BALANCE
    patterns = [
        # Pattern 1a: Standard with clear spacing
        r'^(\d{2}/\w{3})\s+(.*?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$',
        
        # Pattern 1b: With extra whitespace
        r'^(\d{2}/\w{3})\s+(.*?)\s+(-?[\d,]+\.\d{2})\s+[\d,]+\.\d{2}\s*$',
        
        # Pattern 2: Without balance column (some months don't show it)
        r'^(\d{2}/\w{3})\s+(.*?)\s+(-?[\d,]+\.\d{2})\s*$',
        
        # Pattern 3: Looser matching (catches edge cases)
        r'(\d{2}/\w{3})\s+(.+?)\s+(-?[\d,]+\.\d{2})',
        
        # Pattern 4: Very loose - just date, text, and number
        r'(\d{2}/[A-Za-z]{3})\s+(.+?)\s+([-\d,]+\.\d{2})',
    ]
    
    for pattern_idx, pattern in enumerate(patterns):
        match = re.search(pattern, line)
        
        if match:
            try:
                date_str = match.group(1).strip()
                description = match.group(2).strip()
                amount_str = match.group(3).strip().replace(',', '')
                
                # Validation checks
                if not description or len(description) < 2:
                    continue
                
                # Skip if description is just numbers or dates
                if re.match(r'^[\d\s\.\,\-\/]+$', description):
                    continue
                
                # Skip common non-transaction text
                skip_words = ['balance', 'total', 'forward', 'brought', 'opening', 'closing']
                if any(word in description.lower() for word in skip_words):
                    continue
                
                # Parse amount
                amount = float(amount_str)
                
                if amount == 0:
                    continue
                
                # Build full date
                full_date = f"{date_str}/{year}"
                
                # Determine category (NCB uses negative for debits)
                if amount < 0:
                    category = 'Debit'
                    amount = abs(amount)
                else:
                    category = 'Credit'
                
                return {
                    'Date': full_date,
                    'Description': description,
                    'Amount': amount,
                    'Category': category
                }
                
            except (ValueError, IndexError, AttributeError) as e:
                # Try next pattern
                continue
    
    return None

def process_pdf_ncb(file, debug=False):
    """
    IMPROVED NCB PDF processor with better transaction detection
    """
    try:
        transactions = []
        year = "2024"
        
        if isinstance(file, BytesIO):
            pdf_file = file
        else:
            pdf_file = BytesIO(file.read()) if hasattr(file, 'read') else BytesIO(file)
        
        with pdfplumber.open(pdf_file) as pdf:
            # Extract year from first page
            if pdf.pages:
                first_page_text = pdf.pages[0].extract_text()
                
                year_patterns = [
                    r'P\.?O\.?,?\s*\d{2}-\d{2}-(\d{4})',
                    r'[A-Z\s]+,\s*JAMAICA.*?(\d{4})',
                    r'\d{2}/[A-Za-z]{3}/(\d{4})',
                    r'(\d{4})-\d{2}-\d{2}',
                    r'\b(202[0-9])\b'
                ]
                
                for pattern in year_patterns:
                    year_match = re.search(pattern, first_page_text, re.IGNORECASE)
                    if year_match:
                        year = year_match.group(1) if year_match.lastindex else year_match.group(0)
                        break
            
            # Process each page
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Skip exact header/footer matches
                    exact_skip = [
                        'CONTINUED', 'END OF STATEMENT', 'STATEMENT', 'PAGE',
                        'DATE', 'DESCRIPTION', 'WITHDRAWALS', 'DEPOSITS', 'BALANCE'
                    ]
                    
                    if line.upper() in exact_skip:
                        continue
                    
                    # Skip address lines
                    if re.match(r'^(MR|MRS|MS|DR|MISS)\s+[A-Z]', line.upper()):
                        continue
                    if re.match(r'^MA \d{2}-\d{2}', line):
                        continue
                    if line.upper() == 'NATIONAL COMMERCIAL BANK JAMAICA LIMITED':
                        continue
                    if re.match(r'^\d{9,}$', line):
                        continue
                    
                    # Try to parse transaction
                    parsed = parse_ncb_transaction_line(line, year)
                    if parsed and parsed['Amount'] > 0:
                        transactions.append(parsed)
        
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%b/%Y', errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        
        return df
        
    except Exception as e:
        if debug:
            print(f"NCB PDF Error: {e}")
        return pd.DataFrame()



def standardize_dataframe_columns(df):
    """ULTRA-ROBUST column standardization"""
    if df.empty:
        return df
    
    # Clean column names (remove quotes, spaces)
    df.columns = (df.columns.str.strip().str.strip('"').str.strip("'")
                  .str.lower().str.replace(' ', '_'))
    
    # Comprehensive mappings
    column_mappings = {
        'trans_date': 'Date', 'transaction_date': 'Date', 'date': 'Date',
        'details': 'Description', 'description': 'Description', 'particulars': 'Description',
        'amount': 'Amount', 'total_amount': 'Amount', 'debit': 'Amount', 'credit': 'Amount',
        'trans_type': 'Category', 'transaction_type': 'Category', 'type': 'Category'
    }
    
    df = df.rename(columns=column_mappings)
    
    # JMMB: Convert Deposit/Withdrawal to Credit/Debit
    if 'Category' in df.columns:
        category_map = {'deposit': 'Credit', 'withdrawal': 'Debit'}
        df['Category'] = df['Category'].astype(str).str.lower().map(category_map).fillna('Debit')
    
    # Ensure Amount is numeric and positive
    if 'Amount' in df.columns:
        df['Amount'] = (df['Amount'].astype(str)
                       .str.replace('$', '').str.replace('J', '').str.replace(',', '')
                       .str.strip())
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').abs()
    
    # Convert Date
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Add Category if missing
    if 'Category' not in df.columns:
        df['Category'] = 'Debit'
    
    # Clean up
    df = df.dropna(subset=['Date', 'Amount'])
    df = df[df['Amount'] > 0]
    if 'Description' in df.columns:
        df = df[df['Description'].astype(str).str.len() > 2]
    
    return df
    
def categorize_transactions(df):
    """Categorize transactions based on keywords"""
    if df.empty:
        return df
    
    if 'Description' not in df.columns:
        df['Spending Category'] = 'Other'
        return df
    
    category_keywords = DEFAULT_CATEGORY_MAPPING.copy()
    
    try:
        if 'user' in st.session_state and st.session_state.user:
            prefs = get_user_preferences(st.session_state.user['id'])
            if prefs and prefs.get('category_keywords'):
                user_keywords = json.loads(prefs['category_keywords'])
                for category, keywords in user_keywords.items():
                    if keywords:
                        category_keywords[category] = keywords
    except Exception as e:
        print(f"Error loading user preferences: {e}")
    
    df['Spending Category'] = 'Other'
    
    for idx, row in df.iterrows():
        description = str(row['Description']).lower()
        
        if row.get('Category') == 'Credit':
            df.at[idx, 'Spending Category'] = 'Income'
            continue
        
        categorized = False
        for category, keywords in category_keywords.items():
            if category == 'Other':
                continue
            
            for keyword in keywords:
                if keyword.lower() in description:
                    df.at[idx, 'Spending Category'] = category
                    categorized = True
                    break
            
            if categorized:
                break
    
    return df
