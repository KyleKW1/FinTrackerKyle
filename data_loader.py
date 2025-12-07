# data_loader.py - FIXED VERSION
"""
Data loading module - loads and combines user files
Optimized for performance with caching
"""

import pandas as pd
from io import BytesIO
import streamlit as st
from database import get_all_user_files
from data_processing import (
    process_csv, 
    process_pdf_ncb, 
    extract_from_pdf,
    standardize_dataframe_columns,
    categorize_transactions
)
import pdfplumber


@st.cache_data(ttl=300, show_spinner=False)
def load_all_user_data(user_id):
    """
    Load all user data with caching
    Cache is cleared every 5 minutes or when explicitly cleared
    """
    files = get_all_user_files(user_id)
    
    if not files:
        return pd.DataFrame()
    
    all_data = []
    processing_log = []  # Track what happens to each file
    
    for file_info in files:
        try:
            file_bytes = BytesIO(file_info['file_data'])
            filename = file_info.get('filename', '')
            file_type = file_info['file_type'].lower()
            
            processing_log.append(f"Processing: {filename}")
            
            # Process based on file type
            if file_type == 'pdf':
                df = process_pdf_file(file_bytes, filename)
            elif file_type == 'csv':
                df = process_csv(file_bytes)
            else:
                processing_log.append(f"  ❌ Skipped (unknown type): {filename}")
                continue
            
            # Validate and clean
            if not df.empty:
                processing_log.append(f"  ✅ Initial rows: {len(df)}")
                
                df = standardize_dataframe_columns(df)
                processing_log.append(f"  ✅ After standardize: {len(df)}")
                
                # CRITICAL FIX: Ensure categorization happens here
                if 'Spending Category' not in df.columns:
                    df = categorize_transactions(df)
                
                df = clean_dataframe(df)
                processing_log.append(f"  ✅ After clean: {len(df)}")
                
                if not df.empty:
                    # Check for dates
                    if 'Date' in df.columns:
                        date_range = f"{df['Date'].min()} to {df['Date'].max()}"
                        processing_log.append(f"  📅 Date range: {date_range}")
                    
                    all_data.append(df)
                    processing_log.append(f"  ✅ Added to dataset")
                else:
                    processing_log.append(f"  ❌ Empty after cleaning: {filename}")
            else:
                processing_log.append(f"  ❌ No data extracted: {filename}")
                    
        except Exception as e:
            processing_log.append(f"  ❌ ERROR: {filename} - {str(e)}")
            print(f"Error processing file {filename}: {e}")
            continue
    
    # Print processing log for debugging
    print("\n=== FILE PROCESSING LOG ===")
    for log_entry in processing_log:
        print(log_entry)
    print("===========================\n")
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine all data
    result = pd.concat(all_data, ignore_index=True)
    print(f"Total combined rows: {len(result)}")
    
    # Add date-based columns BEFORE any filtering
    if 'Date' in result.columns:
        result['Date'] = pd.to_datetime(result['Date'], errors='coerce')
        
        # Count how many dates failed to parse
        null_dates = result['Date'].isna().sum()
        if null_dates > 0:
            print(f"⚠️ WARNING: {null_dates} rows have invalid dates and will be removed")
        
        result = result.dropna(subset=['Date'])
        print(f"After removing invalid dates: {len(result)} rows")
        
        # Add time-based columns
        result['Month-Name'] = result['Date'].dt.month_name()
        result['Month-Year'] = result['Date'].dt.strftime('%B %Y')
        result['YearMonth'] = result['Date'].dt.strftime('%Y-%m')
        result['Year'] = result['Date'].dt.year
        result['Month'] = result['Date'].dt.month
        
        # Show what months we have
        unique_months = sorted(result['YearMonth'].unique())
        print(f"📅 Months in dataset: {unique_months}")
        
        # Show transaction count per month
        month_counts = result.groupby('YearMonth').size()
        print("\n📊 Transactions per month:")
        for month, count in month_counts.items():
            print(f"  {month}: {count} transactions")
    
    # Remove duplicate columns
    result = result.loc[:, ~result.columns.duplicated()]
    
    # CRITICAL FIX: Final check for Spending Category
    if 'Spending Category' not in result.columns:
        result = categorize_transactions(result)
    
    # Final cleanup - BE CAREFUL NOT TO REMOVE TOO MUCH
    if 'Amount' in result.columns:
        zero_amount = (result['Amount'] == 0).sum()
        if zero_amount > 0:
            print(f"⚠️ Removing {zero_amount} rows with zero amount")
        result = result[result['Amount'] > 0]
    
    if 'Description' in result.columns:
        empty_desc = result['Description'].isna().sum()
        if empty_desc > 0:
            print(f"⚠️ Removing {empty_desc} rows with empty description")
        result = result[result['Description'].notna()]
    
    print(f"\n✅ FINAL DATASET: {len(result)} rows across {len(result['YearMonth'].unique())} months")
    
    return result


def process_pdf_file(file_bytes, filename):
    """Process PDF file - detects type and routes to correct processor"""
    # Check if it's NCB by filename
    if 'ncb' in filename.lower():
        return process_pdf_ncb(file_bytes)
    
    # Check by content
    try:
        file_bytes.seek(0)
        with pdfplumber.open(file_bytes) as pdf:
            first_page_text = pdf.pages[0].extract_text().lower()
            if 'ncb' in first_page_text or 'national commercial bank' in first_page_text:
                file_bytes.seek(0)
                return process_pdf_ncb(file_bytes)
        
        file_bytes.seek(0)
        return extract_from_pdf(file_bytes)
    except:
        file_bytes.seek(0)
        return extract_from_pdf(file_bytes)


def clean_dataframe(df):
    """Clean invalid rows from dataframe - BE CONSERVATIVE"""
    if df.empty:
        return df
    
    initial_count = len(df)
    
    # Remove rows with invalid amounts (but keep zero for now, remove later)
    if 'Amount' in df.columns:
        # Convert to numeric first
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df = df[df['Amount'].notna()]
    
    # Remove rows with completely empty descriptions
    if 'Description' in df.columns:
        df = df[df['Description'].notna()]
        df = df[~df['Description'].isin(['nan', 'NaN', 'None'])]
        df = df[df['Description'].astype(str).str.strip() != '']
    
    removed_count = initial_count - len(df)
    if removed_count > 0:
        print(f"  Cleaned: removed {removed_count} invalid rows")
    
    return df


def clear_data_cache():
    """Clear the data cache - call this after file operations"""
    load_all_user_data.clear()
