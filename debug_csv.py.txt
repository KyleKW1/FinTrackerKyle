"""
CSV Diagnostic Script
Run this standalone to debug CSV processing issues
"""

import pandas as pd
from io import StringIO

# Your CSV sample (from the diagnostic output)
csv_content = """
"TRANS DATE","TRANS TYPE","DETAILS","AMOUNT","COMMISSION","GCT","TOTAL AMOUNT"
"2024-12-31","Deposit","Credit Interest","0.66","0","0","0.66"
"2024-12-31","Withdrawal","Withholding Tax","-0.17","0","0","-0.17"
"2024-12-05","Withdrawal","POS Purchase - YORK PHARMACY KINGSTON 10 JM","-816.99","10.43","1.56","-816.99"
"2024-12-02","Withdrawal","POS Purchase - PAPINE TEXACO MONTEGO BAY JM","-1222.01","10.43","1.56","-1222.01"
"2024-11-29","Deposit","Credit Interest","0.54","0","0","0.54"
"""

print("="*70)
print("STEP 1: Load CSV")
print("="*70)

df = pd.read_csv(StringIO(csv_content.strip()))
print(f"✅ Loaded {len(df)} rows")
print(f"📊 Columns: {list(df.columns)}")
print(f"\n📋 First few rows:")
print(df.head())

print("\n" + "="*70)
print("STEP 2: Clean Column Names")
print("="*70)

df.columns = (df.columns.str.strip()
              .str.strip('"').str.strip("'")
              .str.lower()
              .str.replace(' ', '_'))

print(f"✅ Cleaned columns: {list(df.columns)}")

print("\n" + "="*70)
print("STEP 3: Map Column Names")
print("="*70)

column_mappings = {
    'trans_date': 'Date',
    'transaction_date': 'Date',
    'date': 'Date',
    'details': 'Description',
    'description': 'Description',
    'particulars': 'Description',
    'amount': 'Amount',
    'total_amount': 'Amount',
    'debit': 'Amount',
    'credit': 'Amount',
    'trans_type': 'Category',
    'transaction_type': 'Category',
    'type': 'Category'
}

df = df.rename(columns=column_mappings)
print(f"✅ Mapped columns: {list(df.columns)}")
print(f"\n📋 Data after mapping:")
print(df[['Date', 'Category', 'Description', 'Amount']].head())

print("\n" + "="*70)
print("STEP 4: Process Category Column")
print("="*70)

print(f"📊 Unique Category values BEFORE: {df['Category'].unique()}")
print(f"📊 Category value counts BEFORE:")
print(df['Category'].value_counts())

category_map = {
    'deposit': 'Credit',
    'withdrawal': 'Debit',
    'credit': 'Credit',
    'debit': 'Debit'
}

df['Category'] = df['Category'].astype(str).str.lower().str.strip()
print(f"\n📊 After lowercase/strip: {df['Category'].unique()}")

df['Category'] = df['Category'].map(category_map)
print(f"📊 After mapping: {df['Category'].unique()}")
print(f"📊 Any nulls? {df['Category'].isna().sum()}")

df['Category'] = df['Category'].fillna('Debit')
print(f"📊 After fillna: {df['Category'].unique()}")

print("\n" + "="*70)
print("STEP 5: Process Amount Column")
print("="*70)

print(f"📊 Amount column type: {df['Amount'].dtype}")
print(f"📊 Amount sample values:")
print(df['Amount'].head(10))

# Clean amount
df['Amount'] = (df['Amount'].astype(str)
               .str.replace('$', '', regex=False)
               .str.replace('J', '', regex=False)
               .str.replace(',', '', regex=False)
               .str.strip())

print(f"\n📊 After string cleaning:")
print(df['Amount'].head(10))

df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
print(f"\n📊 After to_numeric:")
print(df['Amount'].head(10))
print(f"📊 Any nulls? {df['Amount'].isna().sum()}")

df['Amount'] = df['Amount'].abs()
print(f"\n📊 After abs():")
print(df['Amount'].head(10))

print("\n" + "="*70)
print("STEP 6: Process Date Column")
print("="*70)

print(f"📊 Date sample values:")
print(df['Date'].head(10))

df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
print(f"\n📊 After to_datetime:")
print(df['Date'].head(10))
print(f"📊 Any nulls? {df['Date'].isna().sum()}")

print("\n" + "="*70)
print("STEP 7: Apply Filters")
print("="*70)

print(f"📊 Starting rows: {len(df)}")

# Filter 1: Drop null dates/amounts
before = len(df)
df = df.dropna(subset=['Date', 'Amount'])
print(f"✅ After dropna(Date, Amount): {len(df)} rows (removed {before - len(df)})")

# Filter 2: Amount > 0
before = len(df)
df = df[df['Amount'] > 0]
print(f"✅ After Amount > 0: {len(df)} rows (removed {before - len(df)})")

# Filter 3: Description length > 2
before = len(df)
df = df[df['Description'].notna()]
df = df[df['Description'].astype(str).str.len() > 2]
print(f"✅ After Description check: {len(df)} rows (removed {before - len(df)})")

print("\n" + "="*70)
print("STEP 8: FINAL RESULT")
print("="*70)

print(f"✅ Final row count: {len(df)}")
print(f"✅ Final columns: {list(df.columns)}")

if len(df) > 0:
    print(f"\n📋 Final data sample:")
    print(df[['Date', 'Category', 'Description', 'Amount']].head(10))
    print(f"\n📊 Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"📊 Amount range: ${df['Amount'].min():.2f} to ${df['Amount'].max():.2f}")
    print(f"📊 Category breakdown:")
    print(df['Category'].value_counts())
else:
    print("\n❌ NO ROWS REMAINING!")
    print("\n🔍 Let's check what happened...")
    
    # Reload and check each step
    df_test = pd.read_csv(StringIO(csv_content.strip()))
    df_test.columns = df_test.columns.str.strip().str.strip('"').str.lower().str.replace(' ', '_')
    df_test = df_test.rename(columns=column_mappings)
    
    print(f"\n📊 Original Amount values:")
    print(df_test['Amount'].head(10))
    print(f"📊 Original Amount types: {df_test['Amount'].apply(type).unique()}")
    
    # Check if amounts are being converted properly
    df_test['Amount_str'] = df_test['Amount'].astype(str)
    df_test['Amount_cleaned'] = df_test['Amount_str'].str.replace('$', '').str.replace(',', '').str.strip()
    df_test['Amount_numeric'] = pd.to_numeric(df_test['Amount_cleaned'], errors='coerce')
    df_test['Amount_abs'] = df_test['Amount_numeric'].abs()
    
    print(f"\n📊 Amount conversion steps:")
    print(df_test[['Amount', 'Amount_str', 'Amount_cleaned', 'Amount_numeric', 'Amount_abs']].head(10))
    print(f"\n📊 How many amounts > 0? {(df_test['Amount_abs'] > 0).sum()}")
    print(f"📊 How many amounts are null? {df_test['Amount_abs'].isna().sum()}")
