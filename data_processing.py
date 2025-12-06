# Enhanced PDF processing functions
# Replace the PDF processing functions in data_processing.py with these

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
        
        # Pattern 1: Date Description Amount (most common)
        # Examples: 
        # "01/15/2024 PURCHASE AT KFC 1,500.00"
        # "15-Jan-2024 KFC PURCHASE 1500.00"
        # "2024-01-15 Restaurant 1,500.00"
        
        patterns = [
            # MM/DD/YYYY or DD/MM/YYYY with description and amount
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})',
            # YYYY-MM-DD with description and amount
            r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})',
            # DD-MMM-YYYY (15-Jan-2024)
            r'(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})',
            # MMM DD, YYYY (Jan 15, 2024)
            r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})\s+(.+?)\s+([\d,]+\.\d{2})',
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
        return pd.to_datetime(date_str)
    except:
        return None


def parse_amount(amount_str):
    """Parse amount string"""
    try:
        # Remove currency symbols, commas, and spaces
        cleaned = str(amount_str).replace('$', '').replace(',', '').replace('J', '').replace(' ', '').strip()
        
        # Handle parentheses (negative)
        if '(' in cleaned or ')' in cleaned:
            cleaned = cleaned.replace('(', '').replace(')', '')
            return abs(float(cleaned))
        
        # Handle minus sign
        cleaned = cleaned.replace('-', '')
        
        return abs(float(cleaned))
    except:
        return 0.0


# Keep the process_pdf_ncb function as is, but update it to use the new helper functions
def process_pdf_ncb(file_bytes):
    """Process NCB PDF bank statement"""
    # Use the enhanced extract_from_pdf function
    return extract_from_pdf(file_bytes)
