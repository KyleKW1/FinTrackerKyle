# data_loader.py
"""
Enhanced data loader — merges file-uploaded statements AND Gmail-synced transactions.
All pages (Spending Analysis, Budget Planner, Time Machine, etc.) benefit automatically.
"""

import pandas as pd
from io import BytesIO
import streamlit as st
import pdfplumber
from functools import lru_cache
from database import get_all_user_files, get_email_transactions
from data_processing import (
    process_csv,
    process_pdf_ncb,
    extract_from_pdf,
    categorize_transactions,
)


# ── Public cache-clear helper ─────────────────────────────────────────────

def clear_data_cache():
    """Clear the in-memory LRU cache so the next call re-loads from DB."""
    load_all_user_data.cache_clear()
    print("🔄 Data cache cleared")


# ── Main loader ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_all_user_data(user_id):
    """
    Load ALL transactions for a user:
      1. Uploaded CSV / PDF files  (existing logic, unchanged)
      2. Gmail-synced email transactions  (new)
    Returns a single combined DataFrame.
    """
    all_dataframes = []

    # ── 1. File-based transactions ────────────────────────────────────────
    files = get_all_user_files(user_id)
    for file_info in files:
        try:
            file_bytes = BytesIO(file_info["file_data"])
            file_type  = file_info["file_type"].lower()
            filename   = file_info.get("filename", "unknown")
            print(f"\n📂 Processing: {filename}")

            if file_type == "csv":
                df = process_csv_with_fallback(file_bytes, filename)
            elif file_type == "pdf":
                df = process_pdf_enhanced(file_bytes, filename)
            else:
                print(f"⚠️ Unsupported file type: {file_type}")
                continue

            if not df.empty:
                df = validate_and_clean_dataframe(df, filename)
                if not df.empty:
                    df["source"] = "file"
                    print(f"✅ Loaded {len(df)} transactions from {filename}")
                    all_dataframes.append(df)
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            import traceback; traceback.print_exc()

    # ── 2. Email-synced transactions ──────────────────────────────────────
    email_rows = get_email_transactions(user_id)
    if email_rows:
        email_df = _build_email_dataframe(email_rows)
        if not email_df.empty:
            print(f"📧 Loaded {len(email_df)} transactions from Gmail sync")
            all_dataframes.append(email_df)

    if not all_dataframes:
        return pd.DataFrame()

    # ── 3. Combine & enrich ───────────────────────────────────────────────
    result = pd.concat(all_dataframes, ignore_index=True)

    if "Date" in result.columns:
        result["Date"] = pd.to_datetime(result["Date"], errors="coerce")
        result = result.dropna(subset=["Date"])

        result["Year"]       = result["Date"].dt.year.astype(int)
        result["Month"]      = result["Date"].dt.month.astype(int)
        result["Month-Name"] = result["Date"].dt.month_name()
        result["Month-Year"] = result["Date"].dt.strftime("%B %Y")
        result["YearMonth"]  = result["Date"].dt.strftime("%Y-%m")

        print(f"   Date range: {result['Date'].min().date()} → {result['Date'].max().date()}")
        print(f"   Years: {sorted(result['Year'].unique())}")

    # ── 4. Deduplicate across sources ─────────────────────────────────────
    # Email and file uploads may both contain the same transaction.
    # Keep 'file' source over 'email' where there is a clash.
    result = result.sort_values("source", ascending=False)   # 'file' > 'email'
    result = result.drop_duplicates(
        subset=["Date", "Description", "Amount"], keep="first"
    )

    print(f"\n✅ FINAL: {len(result)} total transactions "
          f"(file: {(result['source']=='file').sum()}, "
          f"email: {(result['source']=='email').sum()})")

    return result


# ── Email DataFrame builder ───────────────────────────────────────────────

def _build_email_dataframe(rows: list) -> pd.DataFrame:
    """
    Convert raw DB rows from email_transactions into the standard DataFrame
    schema expected by all Finance Hub pages.
    """
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Rename columns to standard schema
    df = df.rename(columns={"Date": "Date", "Description": "Description",
                             "Amount": "Amount", "Category": "Category"})

    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").abs()
    df = df.dropna(subset=["Date", "Amount"])
    df = df[df["Amount"] > 0]

    if "Category" not in df.columns:
        df["Category"] = "Debit"

    # Normalise Category values
    cat_map = {"deposit": "Credit", "withdrawal": "Debit",
               "credit": "Credit",  "debit": "Debit"}
    df["Category"] = (df["Category"].astype(str).str.lower().str.strip()
                        .map(cat_map).fillna("Debit"))

    if "Description" not in df.columns:
        df["Description"] = "Bank Transaction"
    df["Description"] = df["Description"].fillna("Bank Transaction").astype(str).str.strip()

    df["source"] = "email"

    # Spending categories
    df = categorize_transactions(df)

    return df


# ── File processing helpers (unchanged from original) ─────────────────────

def process_csv_with_fallback(file_bytes, filename):
    encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
    for encoding in encodings:
        try:
            file_bytes.seek(0)
            df = process_csv(file_bytes, encoding=encoding)
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()


def process_pdf_enhanced(file_bytes, filename):
    try:
        file_bytes.seek(0)
        is_ncb = detect_ncb_pdf(file_bytes)
        file_bytes.seek(0)
        if is_ncb:
            return process_pdf_ncb(file_bytes, debug=False)
        return extract_from_pdf(file_bytes)
    except Exception as e:
        print(f"   ❌ PDF processing error: {e}")
        return pd.DataFrame()


def detect_ncb_pdf(file_bytes):
    try:
        file_bytes.seek(0)
        with pdfplumber.open(file_bytes) as pdf:
            if not pdf.pages:
                return False
            text = pdf.pages[0].extract_text().upper()
            indicators = [
                "NATIONAL COMMERCIAL BANK", "NCB JAMAICA",
                "WWW.JNCB.COM", "REGULAR SAVINGS ACCOUNT", "CURRENT ACCOUNT",
            ]
            count = sum(1 for i in indicators if i in text)
            if count >= 2:
                return True
            import re
            if re.search(r"\d{2}/[A-Z][a-z]{2}\s+.+?\s+-?[\d,]+\.\d{2}\s+[\d,]+\.\d{2}", text):
                return True
        return False
    except Exception:
        return False


def validate_and_clean_dataframe(df, filename):
    if df.empty:
        return df

    required = ["Date", "Description", "Amount"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"   ❌ Missing columns: {missing}")
        return pd.DataFrame()

    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df           = df.dropna(subset=["Date"])
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").abs().fillna(0)
    df           = df[df["Amount"] > 0]

    if df.empty:
        return df

    df = df[df["Description"].notna()]
    df = df[df["Description"].astype(str).str.strip().str.len() > 2]

    if "Category" not in df.columns:
        df["Category"] = "Debit"
    if "Spending Category" not in df.columns:
        df = categorize_transactions(df)

    return df
