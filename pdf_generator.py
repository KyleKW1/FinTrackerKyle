"""
pdf_generator.py
PDF Report Generation Module for Finance Hub
"""

from fpdf import FPDF
from datetime import datetime
import tempfile
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import shutil


def create_pdf_with_charts(month_data, selected_month, summary, comparison, 
                          month_income, month_spending, month_savings, SAVINGS_GOAL):
    """
    Create a comprehensive PDF report with charts using matplotlib
    
    Parameters:
    -----------
    month_data : pd.DataFrame
        Transaction data for the selected month
    selected_month : str
        Name of the selected month
    summary : pd.DataFrame
        Spending summary by category
    comparison : pd.DataFrame
        Budget vs actual comparison
    month_income : float
        Total income for the month
    month_spending : float
        Total spending for the month
    month_savings : float
        Net savings for the month
    SAVINGS_GOAL : float
        Target savings goal
    
    Returns:
    --------
    bytes
        PDF file as bytes
    """
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, f'Finance Report - {selected_month}', 0, 1, 'C')
            self.set_font('Arial', '', 10)
            self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
            self.ln(5)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    pdf = PDF()
    pdf.add_page()
    
    # ==========================================
    # SUMMARY SECTION
    # ==========================================
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Monthly Summary', 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.ln(2)
    
    pdf.cell(60, 10, 'Total Income:', 0, 0)
    pdf.cell(0, 10, f'J${month_income:,.2f}', 0, 1)
    
    pdf.cell(60, 10, 'Total Spending:', 0, 0)
    pdf.cell(0, 10, f'J${month_spending:,.2f}', 0, 1)
    
    pdf.cell(60, 10, 'Net Savings:', 0, 0)
    pdf.cell(0, 10, f'J${month_savings:,.2f}', 0, 1)
    
    pdf.cell(60, 10, 'Savings Goal:', 0, 0)
    pdf.cell(0, 10, f'J${SAVINGS_GOAL:,.2f}', 0, 1)
    
    if month_savings >= SAVINGS_GOAL:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 10, f'Goal achieved! Exceeded by J${month_savings - SAVINGS_GOAL:,.2f}', 0, 1)
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, f'Below goal by J${SAVINGS_GOAL - month_savings:,.2f}', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    # Create temporary directory for charts
    temp_dir = tempfile.mkdtemp()
    
    try:
        # ==========================================
        # CHART 1: SPENDING DISTRIBUTION PIE CHART
        # ==========================================
        if not summary.empty:
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Spending Distribution by Category', 0, 1)
            pdf.ln(2)
            
            fig, ax = plt.subplots(figsize=(8, 6))
            colors = plt.cm.Set3(range(len(summary)))
            wedges, texts, autotexts = ax.pie(
                summary['Amount'], 
                labels=summary['Spending Category'],
                autopct='%1.1f%%',
                startangle=90,
                colors=colors
            )
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')
            ax.set_title(f'{selected_month} Spending Distribution')
            
            pie_chart_path = os.path.join(temp_dir, 'pie_chart.png')
            plt.savefig(pie_chart_path, bbox_inches='tight', dpi=150)
            plt.close()
            
            pdf.image(pie_chart_path, x=10, w=190)
            pdf.ln(5)
        
        # ==========================================
        # CHART 2: BUDGET VS ACTUAL BAR CHART
        # ==========================================
        if comparison is not None and not comparison.empty:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Budget vs. Actual Spending', 0, 1)
            pdf.ln(2)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            x = range(len(comparison))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], comparison['Budget'], 
                   width, label='Budget', color='#3b82f6')
            ax.bar([i + width/2 for i in x], comparison['Amount'], 
                   width, label='Actual', color='#ef4444')
            
            ax.set_xlabel('Category')
            ax.set_ylabel('Amount (J$)')
            ax.set_title('Budget vs. Actual Spending by Category')
            ax.set_xticks(x)
            ax.set_xticklabels(comparison['Spending Category'], rotation=45, ha='right')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            # Format y-axis as currency
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'J${x:,.0f}'))
            
            bar_chart_path = os.path.join(temp_dir, 'bar_chart.png')
            plt.savefig(bar_chart_path, bbox_inches='tight', dpi=150)
            plt.close()
            
            pdf.image(bar_chart_path, x=10, w=190)
            pdf.ln(5)
        
        # ==========================================
        # SPENDING SUMMARY TABLE
        # ==========================================
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Spending Breakdown', 0, 1)
        pdf.ln(2)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(80, 10, 'Category', 1)
        pdf.cell(50, 10, 'Amount (J$)', 1)
        pdf.cell(50, 10, 'Percentage', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 10)
        for idx, row in summary.iterrows():
            pdf.cell(80, 10, str(row['Spending Category']), 1)
            pdf.cell(50, 10, f"J${row['Amount']:,.2f}", 1)
            pdf.cell(50, 10, f"{row['Percentage']:.2f}%", 1)
            pdf.ln()
        
        # ==========================================
        # BUDGET COMPARISON TABLE
        # ==========================================
        if comparison is not None and not comparison.empty:
            pdf.ln(10)
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Budget Comparison', 0, 1)
            pdf.ln(2)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(60, 10, 'Category', 1)
            pdf.cell(40, 10, 'Budget', 1)
            pdf.cell(40, 10, 'Actual', 1)
            pdf.cell(40, 10, 'Difference', 1)
            pdf.ln()
            
            pdf.set_font('Arial', '', 10)
            for idx, row in comparison.iterrows():
                pdf.cell(60, 10, str(row['Spending Category']), 1)
                pdf.cell(40, 10, f"J${row['Budget']:,.0f}", 1)
                pdf.cell(40, 10, f"J${row['Amount']:,.0f}", 1)
                
                # Color code the difference
                if row['Amount'] > row['Budget']:
                    pdf.set_text_color(255, 0, 0)
                else:
                    pdf.set_text_color(0, 128, 0)
                
                pdf.cell(40, 10, f"J${row['Difference']:,.0f}", 1)
                pdf.set_text_color(0, 0, 0)
                pdf.ln()
        
        # ==========================================
        # TRANSACTION DETAILS
        # ==========================================
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Recent Transactions', 0, 1)
        pdf.ln(2)
        
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(30, 8, 'Date', 1)
        pdf.cell(80, 8, 'Description', 1)
        pdf.cell(35, 8, 'Amount', 1)
        pdf.cell(35, 8, 'Category', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)
        for idx, row in month_data.head(20).iterrows():
            pdf.cell(30, 8, str(row['Date'].date()), 1)
            
            # Truncate long descriptions
            desc = str(row['Description'])[:35]
            pdf.cell(80, 8, desc, 1)
            
            pdf.cell(35, 8, f"J${row['Amount']:,.2f}", 1)
            pdf.cell(35, 8, str(row['Spending Category'])[:12], 1)
            pdf.ln()
            
            # Check if we need a new page
            if pdf.get_y() > 270:
                pdf.add_page()
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(30, 8, 'Date', 1)
                pdf.cell(80, 8, 'Description', 1)
                pdf.cell(35, 8, 'Amount', 1)
                pdf.cell(35, 8, 'Category', 1)
                pdf.ln()
                pdf.set_font('Arial', '', 8)
        
    finally:
        # Clean up temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Handle different FPDF versions
    output = pdf.output(dest='S')
    if isinstance(output, bytes):
        return output
    elif isinstance(output, bytearray):
        return bytes(output)
    elif isinstance(output, str):
        return output.encode('latin-1')
    else:
        return bytes(output)


def create_simple_pdf(text_content, title="Finance Report"):
    """
    Create a simple text-based PDF report
    
    Parameters:
    -----------
    text_content : str
        Text content to include in PDF
    title : str
        Report title
    
    Returns:
    --------
    bytes
        PDF file as bytes
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    for line in text_content.split('\n'):
        # Handle special characters
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 10, txt=safe_line, ln=True)
    
    # Handle different FPDF versions
    output = pdf.output()
    if isinstance(output, bytes):
        return output
    elif isinstance(output, bytearray):
        return bytes(output)
    elif isinstance(output, str):
        return output.encode('latin-1')
    else:
        return bytes(output)
