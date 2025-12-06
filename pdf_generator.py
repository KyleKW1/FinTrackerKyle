"""
pdf_generator.py - COMPLETE FILE
Professional PDF Report Generation for Finance Hub
"""

from fpdf import FPDF
from datetime import datetime
import tempfile
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import shutil
import calendar


class FinancePDF(FPDF):
    """Custom PDF class with professional styling"""
    
    def __init__(self, report_month, username):
        super().__init__()
        self.report_month = report_month
        self.username = username
        
    def header(self):
        # Gradient-style header background
        self.set_fill_color(102, 126, 234)  # Purple-blue
        self.rect(0, 0, 210, 40, 'F')
        
        # Title
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 24)
        self.set_y(12)
        self.cell(0, 10, 'Finance Hub Report', 0, 1, 'C')
        
        # Subtitle
        self.set_font('Arial', '', 12)
        self.cell(0, 8, f'{self.report_month}', 0, 1, 'C')
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')
    
    def section_title(self, title, icon=''):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(102, 126, 234)
        self.cell(0, 10, f'{icon} {title}', 0, 1, 'L')
        self.set_text_color(0, 0, 0)
        self.ln(2)
    
    def metric_box(self, label, value, color_rgb):
        """Create a colored metric box"""
        # Box background
        self.set_fill_color(*color_rgb)
        self.rect(self.get_x(), self.get_y(), 60, 25, 'F')
        
        # Label
        self.set_font('Arial', '', 9)
        self.set_text_color(255, 255, 255)
        self.cell(60, 8, label, 0, 1, 'C')
        
        # Value
        self.set_font('Arial', 'B', 14)
        self.cell(60, 12, value, 0, 1, 'C')
        
        # Reset
        self.set_text_color(0, 0, 0)


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
        status = f'Goal Achieved! Exceeded by J${total_savings - adjusted_goal:,.0f}'
    else:
        pdf.set_text_color(239, 68, 68)
        status = f'Below Goal by J${adjusted_goal - total_savings:,.0f}'
    
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


# Keep the old function for backward compatibility
def create_pdf_with_charts(month_data, selected_month, summary, comparison, 
                          month_income, month_spending, month_savings, SAVINGS_GOAL):
    """Legacy function - redirects to comprehensive PDF"""
    # This is kept for any old code that might call it
    # Extract year and month from the data
    if not month_data.empty and 'Year' in month_data.columns and 'Month' in month_data.columns:
        selected_year = month_data['Year'].iloc[0]
        selected_months = [month_data['Month'].iloc[0]]
        
        # Reconstruct the full data (we only have month_data)
        # For now, just use the month_data as the full dataset
        return create_comprehensive_pdf(
            data=month_data,
            selected_year=selected_year,
            selected_months=selected_months,
            analysis_type=selected_month,
            user_id=1  # Default user
        )
    else:
        raise ValueError("Invalid month data provided")
