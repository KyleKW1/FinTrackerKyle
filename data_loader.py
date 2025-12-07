# data_loader.py
"""
Enhanced data loader with better NCB detection and CSV processing
"""

import pandas as pd
from io import BytesIO
import streamlit as st
import pdfplumber
from functools import lru_cache
from database import get_all_user_files
from data_processing import (
    process_csv,
    process_pdf_ncb,
    extract_from_pdf,
    standardize_dataframe_columns,
    categorize_transactions
)


@lru_cache(maxsize=1)
def load_all_user_data(user_id):
    """
    Load and process all user files with improved detection
    """
    files = get_all_user_files(user_id)
    
    if not files:
        return pd.DataFrame()
    
    all_dataframes = []
    
    for file_info in files:
        try:
            file_bytes = BytesIO(file_info['file_data'])
            file_type = file_info['file_type'].lower()
            filename = file_info.get('filename', 'unknown')
            
            print(f"\n📂 Processing: {filename}")
            
            # CSV Processing
            if file_type == 'csv':
                df = process_csv_enhanced(file_bytes, filename)
            
            # PDF Processing with better NCB detection
            elif file_type == 'pdf':
                df = process_pdf_enhanced(file_bytes, filename)
            
            else:
                print(f"⚠️ Unsupported file type: {file_type}")
                continue
            
            # Validate and clean
            if not df.empty:
                df = validate_and_clean_dataframe(df, filename)
                
                if not df.empty:
                    print(f"✅ Loaded {len(df)} transactions from {filename}")
                    all_dataframes.append(df)
                else:
                    print(f"⚠️ No valid transactions after cleaning: {filename}")
            else:
                print(f"⚠️ Empty dataframe: {filename}")
        
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            continue
    
    if not all_dataframes:
        return pd.DataFrame()
    
    # Combine all data
    result = pd.concat(all_dataframes, ignore_index=True)
    
    # Add date-based columns
    if 'Date' in result.columns:
        result['Date'] = pd.to_datetime(result['Date'], errors='coerce')
        result = result.dropna(subset=['Date'])
        result['Year'] = result['Date'].dt.year
        result['Month'] = result['Date'].dt.month
        result['Month-Name'] = result['Date'].dt.month_name()
        result['Month-Year'] = result['Date'].dt.strftime('%B %Y')
        result['YearMonth'] = result['Date'].dt.strftime('%Y-%m')
    
    # Remove duplicates across all files
    result = result.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
    
    print(f"\n✅ FINAL: {len(result)} total transactions loaded")
    
    return result


def process_csv_enhanced(file_bytes, filename):
    """
    Enhanced CSV processing with better column detection
    """
    try:
        file_bytes.seek(0)
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                file_bytes.seek(0)
                df = pd.read_csv(file_bytes, encoding=encoding)
                print(f"   Successfully read CSV with {encoding} encoding")
                break
            except:
                continue
        
        if df is None or df.empty:
            print(f"   ❌ Could not read CSV")
            return pd.DataFrame()
        
        print(f"   Original columns: {list(df.columns)}")
        print(f"   Rows: {len(df)}")
        
        # Clean column names (remove quotes, extra spaces)
        df.columns = df.columns.str.strip().str.strip('"').str.strip("'")
        
        # Standardize columns
        df = standardize_dataframe_columns(df)
        
        # Validate required columns
        if 'Date' not in df.columns or 'Amount' not in df.columns or 'Description' not in df.columns:
            print(f"   ❌ Missing required columns after standardization")
            print(f"   Available: {list(df.columns)}")
            return pd.DataFrame()
        
        # Categorize
        df = categorize_transactions(df)
        
        return df
        
    except Exception as e:
        print(f"   ❌ CSV processing error: {e}")
        return pd.DataFrame()


def process_pdf_enhanced(file_bytes, filename):
    """
    Enhanced PDF processing with better NCB detection
    """
    try:
        file_bytes.seek(0)
        
        # Detect if it's NCB by checking content
        is_ncb = detect_ncb_pdf(file_bytes)
        
        file_bytes.seek(0)
        
        if is_ncb:
            print(f"   ✅ Detected as NCB PDF")
            df = process_pdf_ncb(file_bytes, debug=False)
        else:
            print(f"   ℹ️ Using generic PDF parser")
            df = extract_from_pdf(file_bytes)
        
        return df
        
    except Exception as e:
        print(f"   ❌ PDF processing error: {e}")
        return pd.DataFrame()


def detect_ncb_pdf(file_bytes):
    """
    Robust NCB PDF detection - checks multiple indicators
    """
    try:
        file_bytes.seek(0)
        
        with pdfplumber.open(file_bytes) as pdf:
            if not pdf.pages:
                return False
            
            # Check first page
            first_page_text = pdf.pages[0].extract_text().upper()
            
            # Check for NCB identifiers
            ncb_indicators = [
                'NATIONAL COMMERCIAL BANK',
                'NCB',
                'PRATVILLE P.O.',
                'MANDEVILLE',
                'MANCHESTER',
                'REGULAR SAVINGS',
                'CURRENT ACCOUNT'
            ]
            
            indicator_count = sum(1 for indicator in ncb_indicators if indicator in first_page_text)
            
            # If 3+ indicators found, it's definitely NCB
            if indicator_count >= 3:
                return True
            
            # Also check for NCB transaction pattern
            # NCB uses format: DD/Mon DESCRIPTION AMOUNT BALANCE
            import re
            ncb_pattern = r'\d{2}/[A-Z][a-z]{2}\s+.+?\s+-?[\d,]+\.\d{2}\s+[\d,]+\.\d{2}'
            
            if re.search(ncb_pattern, first_page_text):
                return True
            
            return False
            
    except Exception as e:
        print(f"   Error detecting NCB: {e}")
        return False


def validate_and_clean_dataframe(df, filename):
    """
    Validate and clean dataframe before adding to collection
    """
    if df.empty:
        return df
    
    required_columns = ['Date', 'Description', 'Amount']
    
    # Check required columns exist
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"   ❌ Missing columns: {missing}")
        return pd.DataFrame()
    
    # Convert Date
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Remove invalid dates
    before_date = len(df)
    df = df.dropna(subset=['Date'])
    if len(df) < before_date:
        print(f"   🧹 Removed {before_date - len(df)} rows with invalid dates")
    
    # Remove invalid amounts
    before_amount = len(df)
    df = df[df['Amount'] > 0]
    if len(df) < before_amount:
        print(f"   🧹 Removed {before_amount - len(df)} rows with zero/negative amounts")
    
    # Remove invalid descriptions
    before_desc = len(df)
    df = df[df['Description'].notna()]
    df = df[df['Description'].astype(str).str.strip() != '']
    df = df[df['Description'] != 'nan']
    if len(df) < before_desc:
        print(f"   🧹 Removed {before_desc - len(df)} rows with invalid descriptions")
    
    # Ensure Category exists
    if 'Category' not in df.columns:
        df['Category'] = 'Debit'
    
    # Ensure Spending Category exists
    if 'Spending Category' not in df.columns:
        df = categorize_transactions(df)
    
    return df


def clear_data_cache():
    """Clear the cached data"""
    load_all_user_data.cache_clear()
    print("🔄 Data cache cleared")
