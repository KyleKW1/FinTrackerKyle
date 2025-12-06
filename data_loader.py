# data_loader.py
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
    standardize_dataframe_columns
)
import pdfplumber


@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes, hide spinner
def load_all_user_data(user_id):
    """
    Load all user data with caching
    Cache is cleared every 5 minutes or when explicitly cleared
    """
    files = get_all_user_files(user_id)
    
    if not files:
        return pd.DataFrame()
    
    all_data = []
    
    for file_info in files:
        try:
            file_bytes = BytesIO(file_info['file_data'])
            filename = file_info.get('filename', '')
            file_type = file_info['file_type'].lower()
            
            # Process based on file type
            if file_type == 'pdf':
                df = process_pdf_file(file_bytes, filename)
            elif file_type == 'csv':
                df = process_csv(file_bytes)
            else:
                continue
            
            # Validate and clean
            if not df.empty:
                df = standardize_dataframe_columns(df)
                df = clean_dataframe(df)
                
                if not df.empty:
                    all_data.append(df)
                    
        except Exception as e:
            # Silently log errors, don't show to user unless needed
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine all data
    result = pd.concat(all_data, ignore_index=True)
    
    # Add date-based columns
    if 'Date' in result.columns:
        result['Date'] = pd.to_datetime(result['Date'], errors='coerce')
        result = result.dropna(subset=['Date'])
        result['Month-Name'] = result['Date'].dt.month_name()
        result['Month-Year'] = result['Date'].dt.strftime('%B %Y')
        result['YearMonth'] = result['Date'].dt.strftime('%Y-%m')
    
    # Remove duplicate columns
    result = result.loc[:, ~result.columns.duplicated()]
    
    # Final cleanup
    if 'Amount' in result.columns:
        result = result[result['Amount'] > 0]
    if 'Description' in result.columns:
        result = result[result['Description'].notna()]
    
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
    """Clean invalid rows from dataframe"""
    if df.empty:
        return df
    
    initial_count = len(df)
    
    # Remove rows with invalid data
    if 'Amount' in df.columns:
        df = df[df['Amount'] > 0]
    
    if 'Description' in df.columns:
        df = df[df['Description'].notna()]
        df = df[~df['Description'].isin(['nan', 'NaN', 'None'])]
        df = df[df['Description'].astype(str).str.strip() != '']
    
    # Silently clean without showing message
    return df


def clear_data_cache():
    """Clear the data cache - call this after file operations"""
    load_all_user_data.clear()
