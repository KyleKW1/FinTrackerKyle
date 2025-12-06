# utils.py
"""
Utility functions for email, exports, and analytics
"""

import smtplib
from email.message import EmailMessage
import pandas as pd
from io import BytesIO
import streamlit as st
from fpdf import FPDF
from config import EMAIL_CONFIG


# ============================================
# EMAIL FUNCTIONS
# ============================================

def send_email_alert(to_email, subject, body):
    """Send email alerts using configured SMTP"""
    try:
        if not to_email:
            st.error("❌ No recipient email provided")
            return False
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = to_email
        msg.set_content(body)
        
        # Use TLS connection
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        
        st.success("✅ Email alert sent successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Authentication failed. Please check email configuration.")
        return False
    except smtplib.SMTPException as e:
        st.error(f"❌ SMTP error: {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ Failed to send email: {str(e)}")
        return False


# ============================================
# EXPORT FUNCTIONS
# ============================================

def export_to_excel(df):
    """Export dataframe to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')
    return output.getvalue()


def export_to_pdf_simple(text):
    """Export text to simple PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.cell(200, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    return bytes(pdf.output())


# ============================================
# ANALYTICS FUNCTIONS
# ============================================

def calculate_monthly_stats(data, year_month):
    """Calculate monthly statistics"""
    month_data = data[data['YearMonth'] == year_month]
    
    if month_data.empty:
        return {
            'income': 0.0,
            'spending': 0.0,
            'savings': 0.0
        }
    
    # SAFETY CHECK: Ensure Category column exists
    if 'Category' not in month_data.columns:
        # Default behavior if Category is missing
        income = 0.0
        spending = float(month_data['Amount'].sum())
    else:
        income = float(month_data[month_data['Category'] == 'Credit']['Amount'].sum())
        spending = float(month_data[month_data['Category'] == 'Debit']['Amount'].sum())
    
    savings = income - spending
    
    return {
        'income': income,
        'spending': spending,
        'savings': savings
    }


def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100


def get_spending_by_category(data, year_month):
    """Get spending breakdown by category for a month"""
    month_data = data[data['YearMonth'] == year_month]
    
    # SAFETY CHECK: Ensure Category column exists
    if 'Category' in month_data.columns:
        spend_data = month_data[month_data['Category'] == 'Debit']
    else:
        # If no Category column, assume all are spending
        spend_data = month_data.copy()
    
    if spend_data.empty:
        return pd.DataFrame()
    
    # CRITICAL FIX: Check if Spending Category exists
    if 'Spending Category' not in spend_data.columns:
        # Import categorize_transactions and apply it
        from data_processing import categorize_transactions
        spend_data = categorize_transactions(spend_data)
    
    # If still no Spending Category, create a default one
    if 'Spending Category' not in spend_data.columns:
        spend_data['Spending Category'] = 'Uncategorized'
    
    summary = spend_data.groupby('Spending Category')['Amount'].sum().reset_index()
    summary['Percentage'] = 100 * summary['Amount'] / summary['Amount'].sum()
    
    return summary


def compare_budget_vs_actual(budgets, actual_spending):
    """Compare budgets against actual spending"""
    if actual_spending.empty:
        return pd.DataFrame()
    
    budget_df = pd.DataFrame.from_dict(budgets, orient='index', columns=['Budget']).reset_index()
    budget_df.rename(columns={'index': 'Spending Category'}, inplace=True)
    
    comparison = pd.merge(budget_df, actual_spending, on='Spending Category', how='left')
    comparison['Amount'] = comparison['Amount'].fillna(0)
    comparison['Difference'] = comparison['Budget'] - comparison['Amount']
    comparison['Status'] = comparison.apply(
        lambda row: "Over Budget" if row['Amount'] > row['Budget'] else "Within Budget", 
        axis=1
    )
    
    return comparison


def generate_alert_email_body(username, month, overspent_categories):
    """Generate email body for overspending alert"""
    body_lines = [
        f"Dear {username},\n",
        f"You have overspent in the following categories for {month}:\n"
    ]
    
    for _, row in overspent_categories.iterrows():
        body_lines.append(
            f"- {row['Spending Category']}: Spent J${row['Amount']:.2f} (Budget: J${row['Budget']:.2f})"
        )
    
    body_lines.append("\n\nPlease review your budget.\n\nBest regards,\nFinance Hub Team")
    
    return "\n".join(body_lines)
