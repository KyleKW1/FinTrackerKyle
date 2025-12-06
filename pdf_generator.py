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

"""
Add this to your pdf_generator.py file
"""

def create_comprehensive_pdf(data, selected_year, selected_months, analysis_type, user_id):
    """
    Create comprehensive PDF for selected period
    
    Parameters:
    -----------
    data : pd.DataFrame
        All transaction data
    selected_year : int
        Selected year
    selected_months : list
        List of selected month numbers
    analysis_type : str
        Type of analysis (e.g., "Last 3 Months", "All Time")
    user_id : int
        User ID for preferences
    """
    import calendar
    from database import get_user_preferences
    from utils import calculate_monthly_stats, get_spending_by_category, compare_budget_vs_actual
    import json
    
    # Filter data for selected period
    period_data = data[(data['Year'] == selected_year) & (data['Month'].isin(selected_months))]
    
    if period_data.empty:
        raise ValueError("No data available for selected period")
    
    # Get period label
    if analysis_type == "Specific Months":
        month_names = [calendar.month_name[m] for m in sorted(selected_months)]
        period_label = f"{', '.join(month_names)} {selected_year}"
    else:
        period_label = f"{analysis_type} - {selected_year}"
    
    # Initialize PDF
    pdf = FinancePDF(period_label, "User")
    pdf.add_page()
    
    # ==========================================
    # PERIOD OVERVIEW
    # ==========================================
    pdf.section_title('Period Overview', '📅')
    
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f'Analysis Type: {analysis_type}', 0, 1)
    pdf.cell(0, 8, f'Year: {selected_year}', 0, 1)
    pdf.cell(0, 8, f'Months Included: {len(selected_months)}', 0, 1)
    pdf.cell(0, 8, f'Total Transactions: {len(period_data)}', 0, 1)
    pdf.ln(10)
    
    # Calculate total stats
    total_income = 0
    total_spending = 0
    
    for month_num in selected_months:
        year_month = f"{selected_year}-{month_num:02d}"
        stats = calculate_monthly_stats(data, year_month)
        total_income += stats['income']
        total_spending += stats['spending']
    
    total_savings = total_income - total_spending
    
    # ==========================================
    # EXECUTIVE SUMMARY
    # ==========================================
    pdf.section_title('Executive Summary', '📊')
    
    # Metric boxes
    start_x = 15
    pdf.set_xy(start_x, pdf.get_y())
    
    pdf.metric_box('Total Income', f'J${total_income:,.0f}', (16, 185, 129))
    pdf.set_xy(start_x + 65, pdf.get_y() - 25)
    pdf.metric_box('Total Spending', f'J${total_spending:,.0f}', (239, 68, 68))
    pdf.set_xy(start_x + 130, pdf.get_y() - 25)
    pdf.metric_box('Net Savings', f'J${total_savings:,.0f}', (59, 130, 246))
    
    pdf.ln(30)
    
    # Get user preferences
    prefs = get_user_preferences(user_id)
    SAVINGS_GOAL = prefs.get('savings_goal', 5000) if prefs else 5000
    
    # Savings goal status (adjusted for multiple months)
    adjusted_goal = SAVINGS_GOAL * len(selected_months)
    pdf.set_font('Arial', '', 11)
    if total_savings >= adjusted_goal:
        pdf.set_text_color(16, 185, 129)
        status = f'✓ Goal Achieved! Exceeded by J${total_savings - adjusted_goal:,.0f}'
    else:
        pdf.set_text_color(239, 68, 68)
        status = f'✗ Below Goal by J${adjusted_goal - total_savings:,.0f}'
    
    pdf.cell(0, 10, f'Savings Goal ({len(selected_months)} months): J${adjusted_goal:,.0f} | {status}', 0, 1, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    # Create temporary directory for charts
    temp_dir = tempfile.mkdtemp()
    
    try:
        # ==========================================
        # MONTHLY TREND CHART
        # ==========================================
        pdf.section_title('Monthly Trends', '📈')
        
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
        
        months_data = []
        for month_num in sorted(selected_months):
            year_month = f"{selected_year}-{month_num:02d}"
            stats = calculate_monthly_stats(data, year_month)
            months_data.append({
                'Month': calendar.month_abbr[month_num],
                'Income': stats['income'],
                'Spending': stats['spending'],
                'Savings': stats['savings']
            })
        
        df_trends = pd.DataFrame(months_data)
        
        x = range(len(df_trends))
        width = 0.25
        
        ax.bar([i - width for i in x], df_trends['Income'], width, 
               label='Income', color='#10b981', alpha=0.8)
        ax.bar([i for i in x], df_trends['Spending'], width, 
               label='Spending', color='#ef4444', alpha=0.8)
        ax.bar([i + width for i in x], df_trends['Savings'], width, 
               label='Savings', color='#3b82f6', alpha=0.8)
        
        ax.set_xlabel('Month', fontsize=12, weight='bold')
        ax.set_ylabel('Amount (J$)', fontsize=12, weight='bold')
        ax.set_title('Monthly Cash Flow Comparison', fontsize=14, weight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(df_trends['Month'])
        ax.legend(fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'J${x:,.0f}'))
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        trend_chart_path = os.path.join(temp_dir, 'trend_chart.png')
        plt.savefig(trend_chart_path, bbox_inches='tight', dpi=200, facecolor='white')
        plt.close()
        
        pdf.image(trend_chart_path, x=10, w=190)
        pdf.ln(5)
        
        # ==========================================
        # AGGREGATE SPENDING DISTRIBUTION
        # ==========================================
        pdf.add_page()
        pdf.section_title('Spending Distribution', '🥧')
        
        # Aggregate spending across all months
        all_spending = []
        for month_num in selected_months:
            year_month = f"{selected_year}-{month_num:02d}"
            month_summary = get_spending_by_category(data, year_month)
            if not month_summary.empty:
                all_spending.append(month_summary)
        
        if all_spending:
            aggregate_summary = pd.concat(all_spending).groupby('Spending Category')['Amount'].sum().reset_index()
            aggregate_summary['Percentage'] = 100 * aggregate_summary['Amount'] / aggregate_summary['Amount'].sum()
            aggregate_summary = aggregate_summary.sort_values('Amount', ascending=False)
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
            
            colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', 
                     '#43e97b', '#fa709a', '#fee140', '#30cfd0']
            
            wedges, texts, autotexts = ax.pie(
                aggregate_summary['Amount'], 
                labels=aggregate_summary['Spending Category'],
                autopct='%1.1f%%',
                startangle=90,
                colors=colors[:len(aggregate_summary)],
                textprops={'fontsize': 11, 'weight': 'bold'},
                pctdistance=0.85
            )
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_weight('bold')
            
            for text in texts:
                text.set_fontsize(10)
                text.set_weight('bold')
            
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            ax.add_artist(centre_circle)
            
            ax.set_title(f'Total Spending Distribution - {period_label}', 
                        fontsize=14, weight='bold', pad=20)
            
            plt.tight_layout()
            
            pie_chart_path = os.path.join(temp_dir, 'pie_chart.png')
            plt.savefig(pie_chart_path, bbox_inches='tight', dpi=200, facecolor='white')
            plt.close()
            
            pdf.image(pie_chart_path, x=10, w=190)
            pdf.ln(5)
            
            # ==========================================
            # SPENDING BREAKDOWN TABLE
            # ==========================================
            pdf.add_page()
            pdf.section_title('Spending Breakdown', '📋')
            
            pdf.set_font('Arial', 'B', 11)
            pdf.set_fill_color(102, 126, 234)
            pdf.set_text_color(255, 255, 255)
            
            pdf.cell(90, 10, 'Category', 1, 0, 'L', True)
            pdf.cell(50, 10, 'Amount (J$)', 1, 0, 'R', True)
            pdf.cell(40, 10, 'Percentage', 1, 1, 'R', True)
            
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(0, 0, 0)
            
            fill = False
            for idx, row in aggregate_summary.iterrows():
                if fill:
                    pdf.set_fill_color(245, 245, 245)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                pdf.cell(90, 8, str(row['Spending Category']), 1, 0, 'L', True)
                pdf.cell(50, 8, f"J${row['Amount']:,.2f}", 1, 0, 'R', True)
                pdf.cell(40, 8, f"{row['Percentage']:.1f}%", 1, 1, 'R', True)
                
                fill = not fill
            
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(102, 126, 234)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(90, 8, 'TOTAL', 1, 0, 'L', True)
            pdf.cell(50, 8, f"J${aggregate_summary['Amount'].sum():,.2f}", 1, 0, 'R', True)
            pdf.cell(40, 8, '100.0%', 1, 1, 'R', True)
            
            pdf.set_text_color(0, 0, 0)
        
        # ==========================================
        # TOP TRANSACTIONS
        # ==========================================
        pdf.add_page()
        pdf.section_title('Top 20 Transactions', '💳')
        
        top_transactions = period_data.nlargest(20, 'Amount')
        
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(102, 126, 234)
        pdf.set_text_color(255, 255, 255)
        
        pdf.cell(25, 8, 'Date', 1, 0, 'C', True)
        pdf.cell(85, 8, 'Description', 1, 0, 'L', True)
        pdf.cell(35, 8, 'Amount', 1, 0, 'R', True)
        pdf.cell(45, 8, 'Category', 1, 1, 'L', True)
        
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(0, 0, 0)
        
        fill = False
        for idx, row in top_transactions.iterrows():
            if fill:
                pdf.set_fill_color(245, 245, 245)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(25, 7, str(row['Date'].date()), 1, 0, 'C', True)
            desc = str(row['Description'])[:40]
            pdf.cell(85, 7, desc, 1, 0, 'L', True)
            pdf.cell(35, 7, f"J${row['Amount']:,.2f}", 1, 0, 'R', True)
            pdf.cell(45, 7, str(row['Spending Category'])[:20], 1, 1, 'L', True)
            
            fill = not fill
            
            if pdf.get_y() > 270:
                pdf.add_page()
                pdf.set_font('Arial', 'B', 9)
                pdf.set_fill_color(102, 126, 234)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(25, 8, 'Date', 1, 0, 'C', True)
                pdf.cell(85, 8, 'Description', 1, 0, 'L', True)
                pdf.cell(35, 8, 'Amount', 1, 0, 'R', True)
                pdf.cell(45, 8, 'Category', 1, 1, 'L', True)
                pdf.set_font('Arial', '', 8)
                pdf.set_text_color(0, 0, 0)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
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
