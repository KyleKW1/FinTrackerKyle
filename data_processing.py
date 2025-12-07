# data_processing.py
"""
Data processing module - Fixed version with better CSV handling
"""

import pandas as pd
import pdfplumber
from io import BytesIO
import re
import streamlit as st
import json

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
    """Process NCB PDF statement"""
    try:
        transactions = []
        year = None
        
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
                if page_num == 1 and year is None:
                    full_date_pattern = r'\d{2}/[A-Z][a-z]{2}/(\d{4})'
                    full_date_matches = re.findall(full_date_pattern, text)
                    if full_date_matches:
                        year = full_date_matches[0]
                        print(f"   [NCB] Year from transaction date: {year}")
                    else:
                        patterns = [
                            r'P\.O\.,?\s*\d{2}-\d{2}-(\d{4})',
                            r'(\d{4})-\d{2}-\d{2}',
                            r'Statement.*?(\d{4})',
                            r'\b(202[0-9])\b'
                        ]
                        
                        for pattern in patterns:
                            year_match = re.search(pattern, text)
                            if year_match:
                                year = year_match.group(1)
                                print(f"   [NCB] Year from pattern: {year}")
                                break
                    
                    if not year:
                        from datetime import datetime
                        year = str(datetime.now().year - 1)
                        print(f"   [NCB] No year found, defaulting to: {year}")
                
                for line in text.split('\n'):
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    skip_keywords = ['CONTINUED', 'END OF STATEMENT', 'JAMAICA', 'NATIONAL COMMERCIAL BANK',
                                   'REGULAR SAVINGS', 'CURRENT ACCOUNT', 'SAVINGS ACCOUNT', 'STATEMENT',
                                   'PAGE', 'MANDEVILLE', 'MANCHESTER', 'JMD', 'USD', 'P.O.',
                                   'BALANCE', 'DATE', 'DESCRIPTION', 'WITHDRAWALS', 'DEPOSITS']
                    
                    if any(keyword in line.upper() for keyword in skip_keywords):
                        continue
                    
                    if re.match(r'^(MR|MRS|MS|DR|MISS)\s+[A-Z]', line):
                        continue
                    if re.search(r'^MA \d{2}-\d{2}', line):
                        continue
                    if re.search(r'^\d{9,}$', line):
                        continue
                    if line.isupper() and not any(c.isdigit() for c in line) and len(line.split()) <= 3:
                        continue
                    
                    parsed = parse_ncb_transaction_line(line, year)
                    if parsed and parsed['Amount'] > 0 and parsed['Description']:
                        transactions.append(parsed)
        
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%b/%Y', errors='coerce')
        df = df.dropna(subset=['Date'])
        
        if not df.empty:
            print(f"   [NCB] Parsed {len(df)} transactions")
            print(f"   [NCB] Date range: {df['Date'].min()} to {df['Date'].max()}")
        
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        
        return df
        
    except Exception as e:
        if debug:
            st.error(f"NCB PDF Processing Error: {str(e)}")
        return pd.DataFrame()


def process_csv(file_bytes, encoding='utf-8'):
    """Process CSV file with proper column mapping"""
    try:
        file_bytes.seek(0)
        df = pd.read_csv(file_bytes, encoding=encoding)
        
        if df.empty:
            print("   CSV is empty")
            return pd.DataFrame()
        
        print(f"   Read {len(df)} rows")
        print(f"   Original columns: {list(df.columns)}")
        
        df.columns = (df.columns.str.strip()
                     .str.strip('"').str.strip("'")
                     .str.lower()
                     .str.replace(' ', '_'))
        
        print(f"   Cleaned columns: {list(df.columns)}")
        
        df = standardize_dataframe_columns(df)
        
        required = ['Date', 'Description', 'Amount']
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"   ERROR: Missing columns: {missing}")
            return pd.DataFrame()
        
        print(f"   After standardization: {list(df.columns)}")
        
        df = categorize_transactions(df)
        
        print(f"   Final: {len(df)} transactions")
        
        return df
        
    except Exception as e:
        print(f"   CSV error: {e}")
        return pd.DataFrame()


def extract_from_pdf(pdf_file):
    """Main PDF extraction function"""
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
    """Standardize column names"""
    df = df.copy()
    
    print(f"   [standardize] Input columns: {list(df.columns)}")
    
    has_valid_category = False
    if 'Category' in df.columns:
        unique_cats = df['Category'].dropna().unique()
        print(f"   [standardize] Found Category: {unique_cats}")
        if any(str(cat).lower() in ['credit', 'debit'] for cat in unique_cats):
            has_valid_category = True
            original_category = df['Category'].copy()
    
    column_mappings = {
        'description': 'Description',
        'desc': 'Description',
        'transaction_description': 'Description',
        'details': 'Description',
        'narrative': 'Description',
        'particulars': 'Description',
        
        'total_amount': 'Amount',
        'amount': 'Amount',
        'transaction_amount': 'Amount',
        'value': 'Amount',
        
        'date': 'Date',
        'trans_date': 'Date',
        'transaction_date': 'Date',
        'posting_date': 'Date',
        'value_date': 'Date',
    }
    
    if not has_valid_category:
        column_mappings['trans_type'] = 'Category'
        column_mappings['transaction_type'] = 'Category'
        column_mappings['type'] = 'Category'
    
    df = df.rename(columns=column_mappings)
    
    print(f"   [standardize] After rename: {list(df.columns)}")
    
    df = df.loc[:, ~df.columns.duplicated()]
    
    columns_to_drop = ['commission', 'gct', 'total_amount']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
    
    print(f"   [standardize] After cleanup: {list(df.columns)}")
    
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
    
    if 'Amount' not in df.columns:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            df['Amount'] = df[numeric_cols[0]]
        else:
            df['Amount'] = 0.0
    
    def clean_amount(value):
        try:
            if pd.isna(value):
                return 0.0
            
            if isinstance(value, (int, float)):
                return abs(float(value))
            
            value_str = str(value).strip()
            value_str = value_str.replace('J$', '').replace('$', '').replace('JMD', '')
            value_str = value_str.replace(' ', '').replace('\xa0', '')
            value_str = value_str.replace(',', '')
            
            if '(' in value_str and ')' in value_str:
                value_str = value_str.replace('(', '').replace(')', '')
            
            value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
            
            if not value_str or value_str in ['', '-', '+', '.']:
                return 0.0
            
            return abs(float(value_str))
            
        except (ValueError, AttributeError):
            return 0.0
    
    df['Amount'] = df['Amount'].apply(clean_amount)
    
    print(f"   [standardize] Amount stats: min={df['Amount'].min()}, max={df['Amount'].max()}, count>0={(df['Amount'] > 0).sum()}")
    
    if 'Category' not in df.columns:
        print(f"   [standardize] No Category - checking trans_type")
        if 'trans_type' in df.columns:
            df['Category'] = df['trans_type'].astype(str).str.lower().str.strip()
            category_map = {
                'deposit': 'Credit',
                'withdrawal': 'Debit',
                'credit': 'Credit',
                'debit': 'Debit'
            }
            df['Category'] = df['Category'].map(category_map).fillna('Debit')
            print(f"   [standardize] Mapped trans_type: {df['Category'].unique()}")
        else:
            df['Category'] = 'Debit'
    else:
        print(f"   [standardize] Category exists: {df['Category'].unique()}")
        df['Category'] = df['Category'].astype(str).str.lower().str.strip()
        category_map = {
            'deposit': 'Credit',
            'withdrawal': 'Debit',
            'credit': 'Credit',
            'debit': 'Debit',
            'cr': 'Credit',
            'dr': 'Debit'
        }
        df['Category'] = df['Category'].map(category_map).fillna(df['Category'])
        df['Category'] = df['Category'].apply(lambda x: x if x in ['Credit', 'Debit'] else 'Debit')
        print(f"   [standardize] Normalized Category: {df['Category'].unique()}")
    
    df['Description'] = df['Description'].fillna('Unknown')
    df['Description'] = df['Description'].astype(str).str.strip()
    
    if 'category' in df.columns and 'Category' in df.columns:
        df = df.drop(columns=['category'])
    
    print(f"   [standardize] Final columns: {list(df.columns)}")
    
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
