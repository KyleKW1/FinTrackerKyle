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
from io import BytesIO


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
    Ultra-robust NCB PDF processor
    Extracts transactions even from difficult-to-parse statements
    """
    try:
        transactions = []
        year = None
        
        # Handle different input types
        if isinstance(file, BytesIO):
            pdf_file = file
        else:
            pdf_file = BytesIO(file.read()) if hasattr(file, 'read') else BytesIO(file)
        
        pdf_file.seek(0)
        
        with pdfplumber.open(pdf_file) as pdf:
            if not pdf.pages:
                print("  ❌ PDF has no pages!")
                return pd.DataFrame()
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                
                if not text:
                    print(f"  ⚠️ Page {page_num}: No text extracted")
                    continue
                
                if debug and page_num == 1:
                    print(f"\n  📄 First 20 lines of page 1:")
                    for i, line in enumerate(text.split('\n')[:20], 1):
                        print(f"    {i}: {line}")
                
                # YEAR DETECTION - Try on every page until we find it
                if not year:
                    year_patterns = [
                        # Pattern 1: Look in full dates (most reliable)
                        r'(\d{2}/[A-Za-z]{3}/(\d{4}))',  # 31/Jan/2025
                        
                        # Pattern 2: Statement date
                        r'Statement.*?(\d{4})',
                        r'Period.*?(\d{4})',
                        
                        # Pattern 3: Address format
                        r'P\.O\.,?\s*\d{2}-\d{2}-(\d{4})',
                        
                        # Pattern 4: ISO date
                        r'(\d{4})-\d{2}-\d{2}',
                        
                        # Pattern 5: Any 4-digit year
                        r'\b(202[0-9])\b',
                    ]
                    
                    for pattern in year_patterns:
                        matches = re.findall(pattern, text)
                        if matches:
                            # Handle tuples from groups
                            if isinstance(matches[0], tuple):
                                year = matches[0][-1]  # Get last group
                            else:
                                year = matches[0]
                            
                            # Validate it's a reasonable year
                            if year and len(year) == 4 and year.startswith('20'):
                                print(f"  📅 Detected year: {year} (page {page_num})")
                                break
                    
                    if not year and page_num == 1:
                        # Last resort - use current year
                        year = str(datetime.now().year)
                        print(f"  ⚠️ Could not detect year, using: {year}")
                
                # TRANSACTION EXTRACTION
                lines = text.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    if not line or len(line) < 10:
                        continue
                    
                    # Skip header/footer lines (case insensitive)
                    line_upper = line.upper()
                    skip_keywords = [
                        'CONTINUED', 'END OF STATEMENT', 'STATEMENT',
                        'NATIONAL COMMERCIAL BANK', 'JAMAICA', 'NCB',
                        'REGULAR SAVINGS', 'CURRENT ACCOUNT', 'SAVINGS ACCOUNT',
                        'PAGE', 'MANDEVILLE', 'MANCHESTER', 
                        'JMD', 'USD', 'P.O.', 'P.O BOX',
                        'BALANCE', '---', '===',
                        'DATE', 'DESCRIPTION', 'WITHDRAWALS', 'DEPOSITS',
                        'OPENING', 'CLOSING', 'BROUGHT FORWARD', 'CARRIED FORWARD',
                        'TOTAL', 'INTEREST', 'SERVICE CHARGE'
                    ]
                    
                    if any(keyword in line_upper for keyword in skip_keywords):
                        continue
                    
                    # Skip customer name/address patterns
                    if re.match(r'^(MR|MRS|MS|DR|MISS)\s+[A-Z\s]+$', line_upper):
                        continue
                    if re.match(r'^[A-Z\s]{10,}$', line_upper) and not any(c.isdigit() for c in line):
                        continue
                    if re.search(r'^\d{9,}$', line):  # Account numbers
                        continue
                    if re.search(r'^MA\s*\d{2}-\d{2}', line):  # Address format
                        continue
                    
                    # Try to parse as transaction
                    parsed = parse_ncb_transaction_line(line, year)
                    
                    if parsed:
                        # Extra validation
                        if parsed['Amount'] > 0 and len(parsed['Description']) >= 3:
                            transactions.append(parsed)
                            if debug:
                                print(f"    ✓ Line {line_num}: {parsed['Description'][:40]} = J${parsed['Amount']}")
        
        # Create DataFrame
        if not transactions:
            print(f"  ❌ No valid transactions extracted!")
            if debug:
                print(f"  📊 Tried to parse PDF but found 0 transactions")
            return pd.DataFrame()
        
        print(f"  ✅ Extracted {len(transactions)} raw transactions")
        
        df = pd.DataFrame(transactions)
        
        # Parse dates
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%b/%Y', errors='coerce')
        
        # Check parsing success
        null_dates = df['Date'].isna().sum()
        if null_dates > 0:
            print(f"  ⚠️ {null_dates} transactions had invalid dates")
        
        df = df.dropna(subset=['Date'])
        
        if df.empty:
            print(f"  ❌ All transactions had invalid dates!")
            return pd.DataFrame()
        
        # Remove duplicates
        before_dedup = len(df)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        after_dedup = len(df)
        
        if before_dedup > after_dedup:
            print(f"  🧹 Removed {before_dedup - after_dedup} duplicate transactions")
        
        # Final summary
        print(f"  ✅ Final count: {len(df)} transactions")
        
        if len(df) > 0:
            credit_count = len(df[df['Category'] == 'Credit'])
            debit_count = len(df[df['Category'] == 'Debit'])
            print(f"  📊 {credit_count} Credits | {debit_count} Debits")
            print(f"  📅 Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
        
        return df
        
    except Exception as e:
        print(f"  ❌ NCB PDF Processing Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return pd.DataFrame()

def standardize_dataframe_columns(df):
    """Standardize column names across different formats"""
    if df.empty:
        return df
    
    # Print original columns for debugging
    print(f"Original columns: {list(df.columns)}")
    print(f"First row sample: {df.iloc[0].to_dict() if len(df) > 0 else 'Empty'}")
    
    # Common column name mappings
    column_mappings = {
        'date': 'Date',
        'transaction date': 'Date',
        'posting date': 'Date',
        'trans date': 'Date',
        'trans. date': 'Date',
        'value date': 'Date',
        
        'description': 'Description',
        'details': 'Description',
        'transaction': 'Description',
        'merchant': 'Description',
        'narrative': 'Description',
        'particulars': 'Description',
        'transaction details': 'Description',
        
        'amount': 'Amount',
        'value': 'Amount',
        'debit': 'Amount',
        'credit': 'Amount',
        'transaction amount': 'Amount',
        
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
        for old_name, new_name in column_mappings.items():
            if old_name in col:
                new_columns[col] = new_name
                break
    
    df = df.rename(columns=new_columns)
    
    # Smart column detection - look at actual data
    if 'Description' not in df.columns:
        # Find the column with the most text (likely description)
        text_lengths = {}
        for col in df.columns:
            if col in ['Date', 'Amount', 'Category']:
                continue
            try:
                # Calculate average length of text in column
                avg_len = df[col].astype(str).str.len().mean()
                if avg_len > 5:  # Descriptions are usually longer than 5 chars
                    text_lengths[col] = avg_len
            except:
                continue
        
        if text_lengths:
            # Use column with longest average text as description
            desc_col = max(text_lengths, key=text_lengths.get)
            print(f"Using '{desc_col}' as Description column (avg length: {text_lengths[desc_col]:.1f})")
            df['Description'] = df[desc_col]
    
    # Ensure Date column
    if 'Date' not in df.columns:
        date_candidates = [c for c in df.columns if 'date' in str(c).lower()]
        if date_candidates:
            df['Date'] = df[date_candidates[0]]
        else:
            # Try to find column with date-like values
            for col in df.columns:
                try:
                    test_date = pd.to_datetime(df[col].iloc[0])
                    if 2000 <= test_date.year <= 2100:
                        df['Date'] = df[col]
                        print(f"Using '{col}' as Date column")
                        break
                except:
                    continue
    
    # Ensure Amount column
    if 'Amount' not in df.columns:
        amount_candidates = [c for c in df.columns if any(word in str(c).lower() for word in ['amount', 'value', 'debit', 'credit'])]
        if amount_candidates:
            df['Amount'] = df[amount_candidates[0]]
        else:
            # Find column with numeric values
            for col in df.columns:
                if col in ['Date', 'Description', 'Category']:
                    continue
                try:
                    # Check if column is mostly numeric
                    numeric_count = pd.to_numeric(df[col], errors='coerce').notna().sum()
                    if numeric_count > len(df) * 0.5:  # More than 50% numeric
                        df['Amount'] = df[col]
                        print(f"Using '{col}' as Amount column")
                        break
                except:
                    continue
    
    # Add Category if missing
    if 'Category' not in df.columns:
        df['Category'] = 'Debit'
    
    # Convert Date column
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
    
    # Convert Amount to numeric and clean
    if 'Amount' in df.columns:
        df['Amount'] = df['Amount'].astype(str).str.replace('$', '').str.replace(',', '').str.replace('J', '').str.strip()
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Amount'] = df['Amount'].abs()
        df = df[df['Amount'] > 0]
    
    # Clean up description - CRITICAL FIX
    if 'Description' in df.columns:
        df['Description'] = df['Description'].astype(str).str.strip()
        df = df[df['Description'].notna()]
        df = df[df['Description'] != 'nan']
        # Remove rows where description is just a number or date
        df = df[~df['Description'].str.match(r'^-?\d+\.?\d*$', na=False)]  # Not just numbers
        df = df[df['Description'].str.len() > 3]  # At least 4 characters
    
    # Drop any rows with missing critical data
    df = df.dropna(subset=['Date', 'Description', 'Amount'])
    
    print(f"Final columns: {list(df.columns)}")
    print(f"Rows after cleaning: {len(df)}")
    
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
