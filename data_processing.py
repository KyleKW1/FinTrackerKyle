# data_processing.py
"""
Data processing module - COPIED FROM TEST3.PY WORKING FUNCTIONS
"""

import pandas as pd
import pdfplumber
from io import BytesIO
import re
import streamlit as st
import json

# You'll need to import these from your config/database files
try:
    from config import DEFAULT_CATEGORY_MAPPING
except:
    DEFAULT_CATEGORY_MAPPING = {
        "Food": ["juici", "kfc", "restaurant", "burger"],
        "Grocery": ["hi-lo", "supermarket", "progressive"],
        "Utilities": ["jps", "nwc", "flow", "bill"],
        "Transport": ["uber", "taxi", "gas"],
        "Other": []
    }

try:
    from database import get_user_preferences
except:
    def get_user_preferences(user_id):
        return None


def parse_ncb_transaction_line(line, year):
    """Parse NCB transaction line: DD/Mon DESCRIPTION AMOUNT BALANCE"""
    pattern = r'(\d{2}/\w{3})\s+(.*?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$'
    match = re.search(pattern, line)
    
    if match:
        try:
            date_str = match.group(1)
            description = match.group(2).strip()
            amount_str = match.group(3).replace(',', '')
            
            if not description or description.isspace():
                return None
            
            full_date = f"{date_str}/{year}"
            amount = float(amount_str)
            
            # NCB format: negative = DEBIT, positive = CREDIT
            if amount < 0:
                category = 'Debit'
                amount = abs(amount)
            else:
                category = 'Credit'
            
            if amount == 0 and description == '':
                return None
            
            return {
                'Date': full_date, 
                'Description': description, 
                'Amount': amount, 
                'Category': category
            }
        except Exception as e:
            return None
    return None


def process_pdf_ncb(file, debug=False):
    """Process NCB PDF statement - FROM TEST3.PY"""
    try:
        transactions = []
        year = "2024"
        
        if isinstance(file, BytesIO):
            pdf_file = file
        else:
            pdf_file = BytesIO(file.read()) if hasattr(file, 'read') else BytesIO(file)
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                # Extract year from first page
                if page_num == 1:
                    patterns = [
                        r'P\.O\.,?\s*\d{2}-\d{2}-(\d{4})',
                        r'(\d{4})-\d{2}-\d{2}',
                        r'\b(20\d{2})\b'
                    ]
                    
                    for pattern in patterns:
                        year_match = re.search(pattern, text)
                        if year_match:
                            year = year_match.group(1)
                            break
                
                for line in text.split('\n'):
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Skip header/footer lines
                    skip_keywords = ['CONTINUED', 'END OF STATEMENT', 'JAMAICA', 'NATIONAL COMMERCIAL BANK',
                                   'REGULAR SAVINGS', 'CURRENT ACCOUNT', 'SAVINGS ACCOUNT', 'STATEMENT',
                                   'PAGE', 'MANDEVILLE', 'MANCHESTER', 'JMD', 'USD', 'P.O.',
                                   'BALANCE', 'DATE', 'DESCRIPTION', 'WITHDRAWALS', 'DEPOSITS']
                    
                    if any(keyword in line.upper() for keyword in skip_keywords):
                        continue
                    
                    # Skip customer info and addresses
                    if re.match(r'^(MR|MRS|MS|DR|MISS)\s+[A-Z]', line):
                        continue
                    if re.search(r'^MA \d{2}-\d{2}', line):
                        continue
                    if re.search(r'^\d{9,}$', line):
                        continue
                    if line.isupper() and not any(c.isdigit() for c in line) and len(line.split()) <= 3:
                        continue
                    
                    # Try to parse as transaction
                    parsed = parse_ncb_transaction_line(line, year)
                    if parsed and parsed['Amount'] > 0 and parsed['Description']:
                        transactions.append(parsed)
        
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%b/%Y', errors='coerce')
        df = df.dropna(subset=['Date'])
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        
        return df
        
    except Exception as e:
        if debug:
            st.error(f"NCB PDF Processing Error: {str(e)}")
        return pd.DataFrame()


def process_csv(file_bytes):
    """Process CSV file - FROM TEST3.PY"""
    try:
        df = pd.read_csv(file_bytes)
        
        if df.empty:
            return pd.DataFrame()
        
        return df
        
    except Exception as e:
        st.error(f"CSV processing error: {e}")
        return pd.DataFrame()


def extract_from_pdf(pdf_file):
    """Main PDF extraction function - FROM TEST3.PY"""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            first_page_text = pdf.pages[0].extract_text() if pdf.pages else ""
            
            if any(keyword in first_page_text.upper() for keyword in ['NCB', 'NATIONAL COMMERCIAL BANK', 'JAMAICA']):
                pdf_file.seek(0)
                return process_pdf_ncb(pdf_file)
        
        pdf_file.seek(0)
        
        data = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                for line in lines:
                    parts = line.split()
                    
                    if len(parts) >= 3:
                        try:
                            date_str = parts[0]
                            amount = None
                            trans_type = None
                            
                            for i in range(len(parts)-1, -1, -1):
                                part = parts[i]
                                if part.upper() in ['CR', 'DR', 'CREDIT', 'DEBIT']:
                                    trans_type = part.upper()
                                    continue
                                
                                cleaned = part.replace('J$', '').replace('$', '').replace(',', '').replace('-', '').strip()
                                try:
                                    amount = float(cleaned)
                                    amount_index = i
                                    break
                                except:
                                    continue
                            
                            if amount is not None:
                                description = ' '.join(parts[1:amount_index])
                                
                                if trans_type:
                                    category = 'Credit' if trans_type in ['CR', 'CREDIT'] else 'Debit'
                                else:
                                    category = 'Debit'
                                
                                data.append({
                                    'Date': date_str,
                                    'Description': description,
                                    'Amount': abs(amount),
                                    'Category': category
                                })
                        except:
                            continue
        
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return pd.DataFrame()


def standardize_dataframe_columns(df):
    """Standardize column names - FROM TEST3.PY"""
    df = df.copy()
    
    # Check if Category column already exists with valid values
    has_valid_category = False
    if 'Category' in df.columns:
        unique_cats = df['Category'].unique()
        if any(cat in ['Credit', 'Debit'] for cat in unique_cats):
            has_valid_category = True
            original_category = df['Category'].copy()
    
    column_mappings = {
        'description': 'Description',
        'desc': 'Description',
        'transaction description': 'Description',
        'details': 'Description',
        'narrative': 'Description',
        'particulars': 'Description',
        
        'amount': 'Amount',
        'transaction amount': 'Amount',
        'value': 'Amount',
        'debit': 'Amount',
        'credit': 'Amount',
        
        'date': 'Date',
        'transaction date': 'Date',
        'posting date': 'Date',
        'value date': 'Date',
    }
    
    # Only map 'type' if we don't already have valid Category
    if not has_valid_category:
        column_mappings.update({
            'type': 'Category',
            'transaction type': 'Category',
            'trans type': 'Category',
            'dr/cr': 'Category',
        })
    
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=column_mappings)
    
    # Restore valid Category if it existed
    if has_valid_category:
        df['Category'] = original_category
    
    if 'Description' not in df.columns:
        if len(df.columns) >= 2:
            df['Description'] = df.iloc[:, 1].astype(str)
        else:
            df['Description'] = 'Unknown'
    
    if 'Date' not in df.columns:
        if len(df.columns) >= 1:
            df['Date'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        else:
            df['Date'] = pd.Timestamp.now()
    
    # Handle Amount column
    if 'Amount' not in df.columns:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            df['Amount'] = df[numeric_cols[0]]
        else:
            df['Amount'] = 0.0
    
    # Clean Amount
    def clean_amount(value):
        try:
            if pd.isna(value):
                return 0.0
            
            if isinstance(value, (int, float)):
                return float(value)
            
            value_str = str(value).strip()
            value_str = value_str.replace('J$', '').replace('$', '').replace('JMD', '')
            value_str = value_str.replace(' ', '').replace('\xa0', '')
            value_str = value_str.replace(',', '')
            
            if '(' in value_str and ')' in value_str:
                value_str = '-' + value_str.replace('(', '').replace(')', '')
            
            value_str = value_str.replace('-', '')
            
            return float(value_str) if value_str and value_str not in ['', '-', '+'] else 0.0
            
        except (ValueError, AttributeError):
            return 0.0
    
    df['Amount'] = df['Amount'].apply(clean_amount)
    
    # Handle Category if doesn't exist or not valid
    if 'Category' not in df.columns or not has_valid_category:
        # Check if we have trans_type that wasn't mapped
        if 'trans_type' in df.columns:
            df['Category'] = df['trans_type'].str.lower().str.strip()
            category_map = {
                'deposit': 'Credit',
                'withdrawal': 'Debit',
                'credit': 'Credit',
                'debit': 'Debit'
            }
            df['Category'] = df['Category'].map(category_map).fillna('Debit')
        else:
            df['Category'] = 'Debit'
    
    # Ensure Amount is positive
    df['Amount'] = df['Amount'].abs()
    
    # Remove duplicate 'category' column
    if 'category' in df.columns and 'Category' in df.columns:
        df = df.drop(columns=['category'])
    
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
        pass
    
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
