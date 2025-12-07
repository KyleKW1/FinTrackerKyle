# data_loader.py
"""
Enhanced data loader with better debugging
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
                df = process_csv_with_fallback(file_bytes, filename)
            
            # PDF Processing
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
            import traceback
            traceback.print_exc()
            continue
    
    if not all_dataframes:
        return pd.DataFrame()
    
    # Combine all data
    result = pd.concat(all_dataframes, ignore_index=True)
    
    # Add date-based columns
    if 'Date' in result.columns:
        # CRITICAL: Ensure Date is datetime before extracting year
        result['Date'] = pd.to_datetime(result['Date'], errors='coerce')
        result = result.dropna(subset=['Date'])
        
        # Debug: Check what dates we actually have
        print(f"   [date columns] Date range BEFORE year extraction: {result['Date'].min()} to {result['Date'].max()}")
        
        # Force Year to be integer type from the Date column
        result['Year'] = result['Date'].dt.year.astype(int)
        result['Month'] = result['Date'].dt.month.astype(int)
        result['Month-Name'] = result['Date'].dt.month_name()
        result['Month-Year'] = result['Date'].dt.strftime('%B %Y')
        result['YearMonth'] = result['Date'].dt.strftime('%Y-%m')
        
        print(f"   [date columns] Years extracted: {sorted(result['Year'].unique())}")
        print(f"   [date columns] Sample Year values: {result['Year'].head(10).tolist()}")
        print(f"   [date columns] Sample Date values: {result['Date'].head(10).tolist()}")
        
        # Verify the year matches the date
        sample_check = result[['Date', 'Year']].head(5)
        print(f"   [date columns] Date vs Year check:")
        for idx, row in sample_check.iterrows():
            print(f"      Date: {row['Date']} -> Year: {row['Year']}")
    
    # Remove duplicates across all files
    result = result.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
    
    print(f"\n✅ FINAL: {len(result)} total transactions loaded")
    
    return result


def process_csv_with_fallback(file_bytes, filename):
    """
    Process CSV with multiple encoding attempts
    """
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            print(f"   Trying encoding: {encoding}")
            file_bytes.seek(0)
            df = process_csv(file_bytes, encoding=encoding)
            
            if not df.empty:
                print(f"   ✅ Successfully processed with {encoding}")
                return df
        except Exception as e:
            print(f"   ❌ Failed with {encoding}: {e}")
            continue
    
    print(f"   ❌ All encodings failed")
    return pd.DataFrame()


def process_pdf_enhanced(file_bytes, filename):
    """
    Enhanced PDF processing with better NCB detection
    """
    try:
        file_bytes.seek(0)
        
        # Detect if it's NCB
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
    Robust NCB PDF detection - uses bank-specific identifiers only
    """
    try:
        file_bytes.seek(0)
        
        with pdfplumber.open(file_bytes) as pdf:
            if not pdf.pages:
                return False
            
            first_page_text = pdf.pages[0].extract_text().upper()
            
            # Check for NCB-specific identifiers (not customer locations)
            ncb_indicators = [
                'NATIONAL COMMERCIAL BANK',
                'NCB JAMAICA',
                'WWW.JNCB.COM',
                'REGULAR SAVINGS ACCOUNT',
                'CURRENT ACCOUNT'
            ]
            
            # Need at least 2 indicators
            indicator_count = sum(1 for indicator in ncb_indicators if indicator in first_page_text)
            
            if indicator_count >= 2:
                print(f"   NCB detected: {indicator_count} indicators found")
                return True
            
            # Check for NCB-specific transaction pattern
            # NCB uses: DD/Mon DESCRIPTION AMOUNT BALANCE (all on same line)
            import re
            ncb_pattern = r'\d{2}/[A-Z][a-z]{2}\s+.+?\s+-?[\d,]+\.\d{2}\s+[\d,]+\.\d{2}'
            
            if re.search(ncb_pattern, first_page_text):
                print(f"   NCB detected: transaction pattern match")
                return True
            
            print(f"   Not detected as NCB")
            return False
            
    except Exception as e:
        print(f"   Error detecting NCB: {e}")
        return False


def validate_and_clean_dataframe(df, filename):
    """
    Validate and clean dataframe with detailed logging
    """
    if df.empty:
        return df
    
    print(f"   [validate] Starting with {len(df)} rows")
    print(f"   [validate] Columns: {list(df.columns)}")
    
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
    
    # CRITICAL: Check amounts BEFORE filtering
    print(f"   [validate] Amount column type: {df['Amount'].dtype}")
    print(f"   [validate] Amount sample: {df['Amount'].head().tolist()}")
    print(f"   [validate] Amount stats: min={df['Amount'].min()}, max={df['Amount'].max()}")
    print(f"   [validate] Rows with Amount > 0: {(df['Amount'] > 0).sum()}")
    
    # Remove invalid amounts (zero or negative)
    before_amount = len(df)
    df = df[df['Amount'] > 0]
    if len(df) < before_amount:
        print(f"   🧹 Removed {before_amount - len(df)} rows with zero/negative amounts")
    
    if df.empty:
        print(f"   ❌ No rows remaining after amount filter!")
        return df
    
    # Remove invalid descriptions
    before_desc = len(df)
    df = df[df['Description'].notna()]
    df = df[df['Description'].astype(str).str.strip() != '']
    df = df[df['Description'].astype(str) != 'nan']
    df = df[df['Description'].astype(str).str.len() > 2]
    if len(df) < before_desc:
        print(f"   🧹 Removed {before_desc - len(df)} rows with invalid descriptions")
    
    # Ensure Category exists
    if 'Category' not in df.columns:
        print(f"   ⚠️ No Category column - adding default")
        df['Category'] = 'Debit'
    
    # Ensure Spending Category exists
    if 'Spending Category' not in df.columns:
        print(f"   ⚠️ No Spending Category - categorizing")
        df = categorize_transactions(df)
    
    print(f"   [validate] Final: {len(df)} rows")
    
    return df


def clear_data_cache():
    """Clear the cached data"""
    load_all_user_data.cache_clear()
    print("🔄 Data cache cleared")
