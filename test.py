import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
import datetime
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Optional imports with fallback
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    
try:
    from fpdf import FPDF
    FPDF_SUPPORT = True
except ImportError:
    FPDF_SUPPORT = False

try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

# Page configuration
st.set_page_config(
    page_title="Finance Hub Pro",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ===================== UTILITY FUNCTIONS =====================

@st.cache_data
def process_csv(file):
    """Process CSV file with multiple format support"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1']
        df = None
        
        for encoding in encodings:
            try:
                file.seek(0)
                df = pd.read_csv(file, encoding=encoding)
                break
            except:
                continue
                
        if df is None:
            raise ValueError("Could not read CSV file with any encoding")
        
        # Standardize column names (handle various bank formats)
        column_mappings = {
            'TRANS DATE': 'Date',
            'Transaction Date': 'Date',
            'DATE': 'Date',
            'DETAILS': 'Description',
            'Description': 'Description',
            'DESCRIPTION': 'Description',
            'TOTAL AMOUNT': 'Amount',
            'Amount': 'Amount',
            'AMOUNT': 'Amount',
            'TRANS TYPE': 'Type',
            'Transaction Type': 'Type',
            'TYPE': 'Type'
        }
        
        df.rename(columns=column_mappings, inplace=True)
        
        # Ensure required columns exist
        required_cols = ['Date', 'Description', 'Amount']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.warning(f"Missing columns: {missing_cols}. Using default values.")
            for col in missing_cols:
                if col == 'Date':
                    df[col] = pd.Timestamp.now()
                else:
                    df[col] = 'Unknown'
        
        # Process data
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df = df.dropna(subset=['Date', 'Amount'])
        
        # Determine transaction type if not present
        if 'Type' not in df.columns or df['Type'].isna().all():
            df['Type'] = df['Amount'].apply(lambda x: 'Debit' if x < 0 else 'Credit')
        
        df['Amount'] = df['Amount'].abs()
        
        return df
        
    except Exception as e:
        st.error(f"Error processing CSV: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def process_pdf(file):
    """Process PDF bank statements"""
    if not PDF_SUPPORT:
        st.error("PDF support not available. Please install pdfplumber.")
        return pd.DataFrame()
    
    try:
        data = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                    
                # Parse transaction patterns (customizable for different banks)
                lines = text.split('\n')
                for line in lines:
                    # Common transaction indicators
                    if any(indicator in line.upper() for indicator in ['POS', 'TRF', 'PURCHASE', 'WITHDRAWAL', 'DEPOSIT']):
                        parts = line.split()
                        if len(parts) >= 3:
                            # Try to extract date, description, and amount
                            try:
                                date_str = parts[0]
                                amount_str = ''.join(filter(lambda x: x.isdigit() or x in '.-,', parts[-1]))
                                amount_str = amount_str.replace(',', '')
                                amount = float(amount_str)
                                desc = ' '.join(parts[1:-1])
                                
                                # Determine type
                                trans_type = 'Debit' if amount < 0 else 'Credit'
                                
                                data.append({
                                    'Date': date_str,
                                    'Description': desc,
                                    'Amount': abs(amount),
                                    'Type': trans_type
                                })
                            except:
                                continue
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
        
        return df
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return pd.DataFrame()

def classify_expense(description, mapping):
    """Classify expenses based on keywords"""
    desc_lower = description.lower() if isinstance(description, str) else ''
    
    for category, keywords in mapping.items():
        for keyword in keywords:
            if keyword.lower() in desc_lower:
                return category
    
    return 'Other'

def export_to_excel(dataframes_dict):
    """Export multiple dataframes to Excel"""
    if not EXCEL_SUPPORT:
        st.error("Excel export not available. Please install openpyxl.")
        return None
        
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Excel sheet name limit
    
    return output.getvalue()

def create_pdf_report(report_content):
    """Create PDF report"""
    if not FPDF_SUPPORT:
        st.error("PDF export not available. Please install fpdf.")
        return None
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    for line in report_content.split('\n'):
        if len(line) > 80:
            # Handle long lines
            words = line.split(' ')
            current_line = ''
            for word in words:
                if len(current_line + word) < 80:
                    current_line += word + ' '
                else:
                    pdf.cell(0, 10, current_line.strip(), ln=True)
                    current_line = word + ' '
            if current_line:
                pdf.cell(0, 10, current_line.strip(), ln=True)
        else:
            pdf.cell(0, 10, line, ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# ===================== MAIN APPLICATION =====================

def main():
    # Header
    st.markdown('<h1 class="main-header">Finance Hub Pro</h1>', unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("### 🎯 Navigation")
        feature = st.radio(
            "Select Feature",
            ["📊 Spending Analysis", "📅 Budget Planner", "📈 Financial Insights", "⚙️ Settings"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### 📁 Data Upload")
        uploaded_files = st.file_uploader(
            "Upload bank statements",
            type=["csv", "pdf", "xlsx"],
            accept_multiple_files=True,
            help="Support for CSV, PDF, and Excel files"
        )
    
    # Process uploaded files
    all_data = pd.DataFrame()
    if uploaded_files:
        progress_bar = st.progress(0)
        for idx, file in enumerate(uploaded_files):
            progress = (idx + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            
            file_ext = file.name.split('.')[-1].lower()
            
            if file_ext == 'csv':
                df = process_csv(file)
            elif file_ext == 'pdf':
                df = process_pdf(file)
            elif file_ext in ['xlsx', 'xls']:
                try:
                    df = pd.read_excel(file)
                    df = process_csv(BytesIO(df.to_csv(index=False).encode()))
                except:
                    st.error(f"Could not process {file.name}")
                    continue
            else:
                continue
                
            if not df.empty:
                df['Source_File'] = file.name
                all_data = pd.concat([all_data, df], ignore_index=True)
        
        progress_bar.empty()
    
    # Feature pages
    if feature == "📊 Spending Analysis":
        spending_analysis_page(all_data)
    elif feature == "📅 Budget Planner":
        budget_planner_page(all_data)
    elif feature == "📈 Financial Insights":
        financial_insights_page(all_data)
    elif feature == "⚙️ Settings":
        settings_page()

def spending_analysis_page(data):
    """Spending Analysis Feature"""
    st.header("📊 Spending Analysis")
    
    if data.empty:
        st.info("📁 Please upload your bank statements to begin analysis")
        
        # Demo data option
        if st.button("Load Demo Data"):
            data = generate_demo_data()
            st.session_state['demo_data'] = data
    
    if 'demo_data' in st.session_state and data.empty:
        data = st.session_state['demo_data']
    
    if not data.empty:
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=data['Date'].min(),
                min_value=data['Date'].min(),
                max_value=data['Date'].max()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=data['Date'].max(),
                min_value=data['Date'].min(),
                max_value=data['Date'].max()
            )
        
        # Filter data by date range
        mask = (data['Date'].dt.date >= start_date) & (data['Date'].dt.date <= end_date)
        filtered_data = data[mask].copy()
        
        if filtered_data.empty:
            st.warning("No data in selected date range")
            return
        
        # Key metrics
        st.markdown("### 📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        total_income = filtered_data[filtered_data['Type'] == 'Credit']['Amount'].sum()
        total_expense = filtered_data[filtered_data['Type'] == 'Debit']['Amount'].sum()
        net_flow = total_income - total_expense
        num_transactions = len(filtered_data)
        
        with col1:
            st.metric("Total Income", f"${total_income:,.2f}", delta=None)
        with col2:
            st.metric("Total Expenses", f"${total_expense:,.2f}", delta=None)
        with col3:
            delta_color = "normal" if net_flow >= 0 else "inverse"
            st.metric("Net Flow", f"${net_flow:,.2f}", delta=f"${net_flow:,.2f}", delta_color=delta_color)
        with col4:
            st.metric("Transactions", f"{num_transactions:,}", delta=None)
        
        # Categorize expenses
        st.markdown("### 🏷️ Expense Categories")
        
        # Default categories
        if 'categories' not in st.session_state:
            st.session_state['categories'] = {
                "Food & Dining": ["restaurant", "cafe", "food", "dining", "lunch", "dinner", "breakfast"],
                "Groceries": ["grocery", "supermarket", "market", "walmart", "target"],
                "Transport": ["uber", "lyft", "gas", "fuel", "parking", "transit"],
                "Utilities": ["electric", "water", "internet", "phone", "utility"],
                "Entertainment": ["movie", "netflix", "spotify", "game", "entertainment"],
                "Shopping": ["amazon", "shop", "store", "mall"],
                "Healthcare": ["pharmacy", "doctor", "hospital", "medical"],
                "Other": []
            }
        
        # Categorize transactions
        filtered_data['Category'] = filtered_data['Description'].apply(
            lambda x: classify_expense(x, st.session_state['categories'])
        )
        
        # Spending by category
        expense_data = filtered_data[filtered_data['Type'] == 'Debit']
        if not expense_data.empty:
            category_summary = expense_data.groupby('Category')['Amount'].agg(['sum', 'count', 'mean']).reset_index()
            category_summary.columns = ['Category', 'Total', 'Count', 'Average']
            category_summary = category_summary.sort_values('Total', ascending=False)
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    category_summary,
                    values='Total',
                    names='Category',
                    title='Spending Distribution',
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    category_summary.head(10),
                    x='Total',
                    y='Category',
                    orientation='h',
                    title='Top 10 Spending Categories',
                    text='Total'
                )
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            
            # Monthly trend
            st.markdown("### 📅 Monthly Trends")
            
            monthly_data = filtered_data.copy()
            monthly_data['Month'] = monthly_data['Date'].dt.to_period('M')
            monthly_summary = monthly_data.groupby(['Month', 'Type'])['Amount'].sum().reset_index()
            monthly_summary['Month'] = monthly_data['Month'].astype(str)
            
            fig = px.line(
                monthly_summary,
                x='Month',
                y='Amount',
                color='Type',
                title='Income vs Expenses Over Time',
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Transaction details
            st.markdown("### 📋 Transaction Details")
            
            # Search and filter
            search_term = st.text_input("Search transactions", placeholder="Enter keywords...")
            
            display_data = filtered_data.copy()
            if search_term:
                mask = display_data['Description'].str.contains(search_term, case=False, na=False)
                display_data = display_data[mask]
            
            # Sort options
            col1, col2 = st.columns([3, 1])
            with col1:
                sort_by = st.selectbox("Sort by", ['Date', 'Amount', 'Description', 'Category'])
            with col2:
                sort_order = st.radio("Order", ['Descending', 'Ascending'])
            
            ascending = sort_order == 'Ascending'
            display_data = display_data.sort_values(sort_by, ascending=ascending)
            
            # Display transactions
            st.dataframe(
                display_data[['Date', 'Description', 'Amount', 'Type', 'Category']].style.format({
                    'Date': lambda x: x.strftime('%Y-%m-%d'),
                    'Amount': '${:,.2f}'
                }),
                use_container_width=True
            )
            
            # Export options
            st.markdown("### 💾 Export Data")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Export to Excel"):
                    excel_data = export_to_excel({
                        'Transactions': display_data,
                        'Category_Summary': category_summary,
                        'Monthly_Summary': monthly_summary
                    })
                    if excel_data:
                        st.download_button(
                            label="Download Excel File",
                            data=excel_data,
                            file_name=f"financial_report_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            
            with col2:
                if st.button("📄 Export to CSV"):
                    csv = display_data.to_csv(index=False)
                    st.download_button(
                        label="Download CSV File",
                        data=csv,
                        file_name=f"transactions_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("📑 Generate PDF Report"):
                    report = generate_text_report(display_data, category_summary)
                    pdf_data = create_pdf_report(report)
                    if pdf_data:
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_data,
                            file_name=f"report_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )

def budget_planner_page(data):
    """Budget Planning Feature"""
    st.header("📅 Budget Planner")
    
    # Budget setup
    st.markdown("### 💰 Set Your Budget")
    
    if 'budgets' not in st.session_state:
        st.session_state['budgets'] = {}
    
    # Get categories from session state or use defaults
    categories = st.session_state.get('categories', {
        "Food & Dining": [],
        "Groceries": [],
        "Transport": [],
        "Utilities": [],
        "Entertainment": [],
        "Shopping": [],
        "Healthcare": [],
        "Other": []
    })
    
    # Budget input form
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Monthly Budgets")
        for category in categories.keys():
            budget_key = f"budget_{category}"
            default_value = st.session_state['budgets'].get(category, 0)
            st.session_state['budgets'][category] = st.number_input(
                f"{category}",
                min_value=0.0,
                value=float(default_value),
                step=50.0,
                key=budget_key
            )
    
    with col2:
        st.markdown("#### Budget vs Actual")
        if not data.empty:
            # Calculate actual spending for current month
            current_month = datetime.datetime.now().month
            current_year = datetime.datetime.now().year
            
            month_data = data[
                (data['Date'].dt.month == current_month) &
                (data['Date'].dt.year == current_year) &
                (data['Type'] == 'Debit')
            ].copy()
            
            if not month_data.empty:
                month_data['Category'] = month_data['Description'].apply(
                    lambda x: classify_expense(x, categories)
                )
                
                actual_spending = month_data.groupby('Category')['Amount'].sum().to_dict()
                
                # Create comparison dataframe
                comparison_data = []
                for category, budget in st.session_state['budgets'].items():
                    actual = actual_spending.get(category, 0)
                    remaining = budget - actual
                    percentage = (actual / budget * 100) if budget > 0 else 0
                    
                    comparison_data.append({
                        'Category': category,
                        'Budget': budget,
                        'Actual': actual,
                        'Remaining': remaining,
                        'Usage %': percentage
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                # Display metrics
                for _, row in comparison_df.iterrows():
                    color = "🟢" if row['Remaining'] >= 0 else "🔴"
                    st.write(f"{color} **{row['Category']}**: ${row['Actual']:.2f} / ${row['Budget']:.2f} ({row['Usage %']:.1f}%)")
            else:
                st.info("No spending data for current month")
        else:
            st.info("Upload data to see budget vs actual comparison")
    
    # Budget visualization
    if st.session_state['budgets'] and any(v > 0 for v in st.session_state['budgets'].values()):
        st.markdown("### 📊 Budget Overview")
        
        budget_df = pd.DataFrame([
            {'Category': k, 'Budget': v}
            for k, v in st.session_state['budgets'].items()
            if v > 0
        ])
        
        fig = px.bar(
            budget_df,
            x='Category',
            y='Budget',
            title='Monthly Budget Allocation',
            text='Budget'
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        # Savings goal
        st.markdown("### 🎯 Savings Goal")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            monthly_income = st.number_input(
                "Expected Monthly Income",
                min_value=0.0,
                value=0.0,
                step=100.0
            )
        
        with col2:
            total_budget = sum(st.session_state['budgets'].values())
            expected_savings = monthly_income - total_budget
            st.metric(
                "Expected Savings",
                f"${expected_savings:,.2f}",
                delta=f"{(expected_savings/monthly_income*100) if monthly_income > 0 else 0:.1f}% of income"
            )
        
        with col3:
            savings_goal = st.number_input(
                "Savings Goal",
                min_value=0.0,
                value=max(0.0, expected_savings),
                step=50.0
            )
            
            if savings_goal > expected_savings:
                st.warning(f"⚠️ Need to reduce spending by ${savings_goal - expected_savings:,.2f} to meet goal")

def financial_insights_page(data):
    """Financial Insights and Analytics"""
    st.header("📈 Financial Insights")
    
    if data.empty:
        st.info("📁 Upload data to see financial insights")
        return
    
    # Prepare data
    data['Month'] = data['Date'].dt.to_period('M')
    data['DayOfWeek'] = data['Date'].dt.day_name()
    data['Hour'] = data['Date'].dt.hour if 'Time' in data.columns else 12  # Default to noon if no time
    
    # Insights tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Spending Patterns", "📊 Trends", "🎯 Anomalies", "💡 Recommendations"])
    
    with tab1:
        st.markdown("### Spending Patterns Analysis")
        
        # Day of week analysis
        col1, col2 = st.columns(2)
        
        with col1:
            dow_spending = data[data['Type'] == 'Debit'].groupby('DayOfWeek')['Amount'].agg(['sum', 'mean', 'count']).reset_index()
            
            # Order days properly
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_spending['DayOfWeek'] = pd.Categorical(dow_spending['DayOfWeek'], categories=day_order, ordered=True)
            dow_spending = dow_spending.sort_values('DayOfWeek')
            
            fig = px.bar(
                dow_spending,
                x='DayOfWeek',
                y='sum',
                title='Spending by Day of Week',
                labels={'sum': 'Total Spending ($)', 'DayOfWeek': 'Day'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top merchants/descriptions
            top_merchants = data[data['Type'] == 'Debit'].groupby('Description')['Amount'].sum().nlargest(10).reset_index()
            
            fig = px.bar(
                top_merchants,
                y='Description',
                x='Amount',
                orientation='h',
                title='Top 10 Merchants/Vendors',
                labels={'Amount': 'Total Spent ($)'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Spending velocity
        st.markdown("### 💨 Spending Velocity")
        
        daily_spending = data[data['Type'] == 'Debit'].groupby(data['Date'].dt.date)['Amount'].sum().reset_index()
        daily_spending.columns = ['Date', 'Amount']
        
        # Calculate moving average
        daily_spending['MA7'] = daily_spending['Amount'].rolling(window=7, min_periods=1).mean()
        daily_spending['MA30'] = daily_spending['Amount'].rolling(window=30, min_periods=1).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_spending['Date'],
            y=daily_spending['Amount'],
            mode='lines',
            name='Daily Spending',
            line=dict(color='lightgray', width=1)
        ))
        fig.add_trace(go.Scatter(
            x=daily_spending['Date'],
            y=daily_spending['MA7'],
            mode='lines',
            name='7-Day Average',
            line=dict(color='blue', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=daily_spending['Date'],
            y=daily_spending['MA30'],
            mode='lines',
            name='30-Day Average',
            line=dict(color='red', width=2)
        ))
        
        fig.update_layout(title='Spending Velocity Over Time', xaxis_title='Date', yaxis_title='Amount ($)')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("### 📈 Financial Trends")
        
        # Monthly comparison
        monthly_summary = data.groupby(['Month', 'Type'])['Amount'].sum().reset_index()
        monthly_summary['Month'] = monthly_summary['Month'].astype(str)
        
        # Pivot for better visualization
        monthly_pivot = monthly_summary.pivot(index='Month', columns='Type', values='Amount').fillna(0)
        monthly_pivot['Net'] = monthly_pivot.get('Credit', 0) - monthly_pivot.get('Debit', 0)
        monthly_pivot = monthly_pivot.reset_index()
        
        fig = go.Figure()
        
        if 'Credit' in monthly_pivot.columns:
            fig.add_trace(go.Bar(name='Income', x=monthly_pivot['Month'], y=monthly_pivot['Credit'], marker_color='green'))
        if 'Debit' in monthly_pivot.columns:
            fig.add_trace(go.Bar(name='Expenses', x=monthly_pivot['Month'], y=monthly_pivot['Debit'], marker_color='red'))
        
        fig.add_trace(go.Scatter(
            name='Net Flow',
            x=monthly_pivot['Month'],
            y=monthly_pivot['Net'],
            mode='lines+markers',
            marker_color='blue',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Monthly Financial Flow',
            xaxis_title='Month',
            yaxis_title='Amount ($)',
            yaxis2=dict(title='Net Flow ($)', overlaying='y', side='right'),
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Year-over-year comparison if multiple years
        if data['Date'].dt.year.nunique() > 1:
            st.markdown("### 📅 Year-over-Year Comparison")
            
            yearly_data = data.groupby([data['Date'].dt.year, 'Type'])['Amount'].sum().reset_index()
            yearly_data.columns = ['Year', 'Type', 'Amount']
            
            fig = px.bar(
                yearly_data,
                x='Year',
                y='Amount',
                color='Type',
                barmode='group',
                title='Yearly Income vs Expenses'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### 🎯 Anomaly Detection")
        
        # Detect unusual transactions
        expense_data = data[data['Type'] == 'Debit']['Amount']
        
        if not expense_data.empty:
            mean_expense = expense_data.mean()
            std_expense = expense_data.std()
            
            # Define anomalies as transactions > 2 standard deviations from mean
            threshold = mean_expense + (2 * std_expense)
            
            anomalies = data[(data['Type'] == 'Debit') & (data['Amount'] > threshold)].copy()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Transaction", f"${mean_expense:.2f}")
            with col2:
                st.metric("Anomaly Threshold", f"${threshold:.2f}")
            with col3:
                st.metric("Anomalies Found", len(anomalies))
            
            if not anomalies.empty:
                st.markdown("#### 🚨 Unusual Transactions")
                st.dataframe(
                    anomalies[['Date', 'Description', 'Amount']].style.format({
                        'Date': lambda x: x.strftime('%Y-%m-%d'),
                        'Amount': '${:,.2f}'
                    }),
                    use_container_width=True
                )
                
                # Anomaly timeline
                fig = px.scatter(
                    data[data['Type'] == 'Debit'],
                    x='Date',
                    y='Amount',
                    color=data[data['Type'] == 'Debit']['Amount'].apply(
                        lambda x: 'Anomaly' if x > threshold else 'Normal'
                    ),
                    title='Transaction Anomalies Over Time',
                    color_discrete_map={'Anomaly': 'red', 'Normal': 'blue'}
                )
                fig.add_hline(y=threshold, line_dash="dash", line_color="orange", annotation_text="Anomaly Threshold")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No unusual transactions detected")
    
    with tab4:
        st.markdown("### 💡 Smart Recommendations")
        
        # Calculate insights
        total_income = data[data['Type'] == 'Credit']['Amount'].sum()
        total_expenses = data[data['Type'] == 'Debit']['Amount'].sum()
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
        
        # Categorize expenses for recommendations
        if 'categories' in st.session_state:
            expense_data = data[data['Type'] == 'Debit'].copy()
            expense_data['Category'] = expense_data['Description'].apply(
                lambda x: classify_expense(x, st.session_state['categories'])
            )
            category_spending = expense_data.groupby('Category')['Amount'].sum().sort_values(ascending=False)
            
            # Generate recommendations
            recommendations = []
            
            # Savings rate recommendation
            if savings_rate < 10:
                recommendations.append({
                    'Priority': 'High',
                    'Area': 'Savings',
                    'Recommendation': f'Your savings rate is {savings_rate:.1f}%. Aim for at least 20% by reducing discretionary spending.'
                })
            elif savings_rate < 20:
                recommendations.append({
                    'Priority': 'Medium',
                    'Area': 'Savings',
                    'Recommendation': f'Good job! Your savings rate is {savings_rate:.1f}%. Try to reach 20% for better financial security.'
                })
            else:
                recommendations.append({
                    'Priority': 'Low',
                    'Area': 'Savings',
                    'Recommendation': f'Excellent! Your savings rate is {savings_rate:.1f}%. Consider investing surplus funds.'
                })
            
            # Category-specific recommendations
            if not category_spending.empty:
                top_category = category_spending.index[0]
                top_amount = category_spending.iloc[0]
                percentage = (top_amount / total_expenses * 100) if total_expenses > 0 else 0
                
                if percentage > 30:
                    recommendations.append({
                        'Priority': 'High',
                        'Area': top_category,
                        'Recommendation': f'{top_category} accounts for {percentage:.1f}% of spending. Consider setting a stricter budget.'
                    })
                
                # Check for subscription-like patterns
                recurring = detect_recurring_transactions(data)
                if recurring:
                    total_recurring = sum(t['amount'] for t in recurring)
                    recommendations.append({
                        'Priority': 'Medium',
                        'Area': 'Subscriptions',
                        'Recommendation': f'Found {len(recurring)} recurring charges totaling ${total_recurring:.2f}/month. Review and cancel unused services.'
                    })
            
            # Display recommendations
            for rec in recommendations:
                priority_color = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
                st.markdown(f"{priority_color[rec['Priority']]} **{rec['Area']}**: {rec['Recommendation']}")
            
            # Opportunity analysis
            st.markdown("### 💰 Savings Opportunities")
            
            if not category_spending.empty:
                # Calculate potential savings (10% reduction in top 3 categories)
                top_3_categories = category_spending.head(3)
                potential_savings = top_3_categories.sum() * 0.1
                
                st.info(f"💡 Reducing spending in your top 3 categories by 10% could save you **${potential_savings:.2f}** per month")
                
                # Show breakdown
                savings_breakdown = pd.DataFrame({
                    'Category': top_3_categories.index,
                    'Current Spending': top_3_categories.values,
                    'Potential Savings (10%)': top_3_categories.values * 0.1
                })
                
                st.dataframe(
                    savings_breakdown.style.format({
                        'Current Spending': '${:,.2f}',
                        'Potential Savings (10%)': '${:,.2f}'
                    }),
                    use_container_width=True
                )

def settings_page():
    """Settings and Configuration Page"""
    st.header("⚙️ Settings")
    
    # Category Management
    st.markdown("### 🏷️ Category Management")
    
    if 'categories' not in st.session_state:
        st.session_state['categories'] = {
            "Food & Dining": ["restaurant", "cafe", "food", "dining"],
            "Groceries": ["grocery", "supermarket", "market"],
            "Transport": ["uber", "lyft", "gas", "fuel"],
            "Utilities": ["electric", "water", "internet", "phone"],
            "Entertainment": ["movie", "netflix", "spotify", "game"],
            "Shopping": ["amazon", "shop", "store", "mall"],
            "Healthcare": ["pharmacy", "doctor", "hospital"],
            "Other": []
        }
    
    # Add new category
    with st.expander("➕ Add New Category"):
        new_category = st.text_input("Category Name")
        new_keywords = st.text_area("Keywords (comma-separated)")
        
        if st.button("Add Category"):
            if new_category and new_category not in st.session_state['categories']:
                keywords = [k.strip().lower() for k in new_keywords.split(',') if k.strip()]
                st.session_state['categories'][new_category] = keywords
                st.success(f"✅ Added category: {new_category}")
                st.rerun()
    
    # Edit existing categories
    st.markdown("#### Edit Categories")
    
    for category, keywords in st.session_state['categories'].items():
        with st.expander(f"📝 {category}"):
            # Edit keywords
            updated_keywords = st.text_area(
                "Keywords",
                value=', '.join(keywords),
                key=f"edit_{category}"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Update", key=f"update_{category}"):
                    st.session_state['categories'][category] = [
                        k.strip().lower() for k in updated_keywords.split(',') if k.strip()
                    ]
                    st.success(f"✅ Updated {category}")
                    st.rerun()
            
            with col2:
                if category != "Other":  # Don't allow deleting "Other" category
                    if st.button(f"Delete", key=f"delete_{category}"):
                        del st.session_state['categories'][category]
                        st.success(f"✅ Deleted {category}")
                        st.rerun()
    
    # Data Management
    st.markdown("### 📊 Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear All Data"):
            if 'data' in st.session_state:
                del st.session_state['data']
            if 'demo_data' in st.session_state:
                del st.session_state['demo_data']
            st.success("✅ All data cleared")
    
    with col2:
        if st.button("🔄 Reset Categories to Default"):
            st.session_state['categories'] = {
                "Food & Dining": ["restaurant", "cafe", "food", "dining"],
                "Groceries": ["grocery", "supermarket", "market"],
                "Transport": ["uber", "lyft", "gas", "fuel"],
                "Utilities": ["electric", "water", "internet", "phone"],
                "Entertainment": ["movie", "netflix", "spotify", "game"],
                "Shopping": ["amazon", "shop", "store", "mall"],
                "Healthcare": ["pharmacy", "doctor", "hospital"],
                "Other": []
            }
            st.success("✅ Categories reset to default")
            st.rerun()
    
    # Export/Import Settings
    st.markdown("### 💾 Export/Import Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Settings"):
            settings = {
                'categories': st.session_state.get('categories', {}),
                'budgets': st.session_state.get('budgets', {})
            }
            settings_json = pd.Series(settings).to_json()
            st.download_button(
                label="Download Settings",
                data=settings_json,
                file_name="finance_hub_settings.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_settings = st.file_uploader("Upload Settings", type=['json'])
        if uploaded_settings:
            try:
                settings = pd.read_json(uploaded_settings, typ='series').to_dict()
                st.session_state['categories'] = settings.get('categories', {})
                st.session_state['budgets'] = settings.get('budgets', {})
                st.success("✅ Settings imported successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing settings: {str(e)}")

def generate_demo_data():
    """Generate demo transaction data for testing"""
    import random
    from datetime import timedelta
    
    # Demo merchants and categories
    merchants = {
        'Food & Dining': ['Starbucks', 'McDonalds', 'Pizza Hut', 'Subway', 'Chipotle'],
        'Groceries': ['Walmart', 'Target', 'Whole Foods', 'Kroger'],
        'Transport': ['Uber', 'Lyft', 'Shell Gas', 'BP Gas'],
        'Utilities': ['Electric Company', 'Water Utility', 'Internet Provider'],
        'Entertainment': ['Netflix', 'Spotify', 'AMC Theaters', 'Steam Games'],
        'Shopping': ['Amazon', 'Best Buy', 'Nike Store', 'Apple Store']
    }
    
    # Generate transactions
    transactions = []
    start_date = datetime.datetime.now() - timedelta(days=180)
    
    for i in range(500):
        date = start_date + timedelta(days=random.randint(0, 180))
        
        # Mix of income and expenses
        if random.random() < 0.1:  # 10% income transactions
            transactions.append({
                'Date': date,
                'Description': random.choice(['Salary', 'Freelance Payment', 'Refund', 'Cashback']),
                'Amount': random.uniform(1000, 5000),
                'Type': 'Credit'
            })
        else:  # 90% expense transactions
            category = random.choice(list(merchants.keys()))
            merchant = random.choice(merchants[category])
            
            # Variable amounts based on category
            amount_ranges = {
                'Food & Dining': (10, 50),
                'Groceries': (50, 200),
                'Transport': (10, 60),
                'Utilities': (50, 150),
                'Entertainment': (10, 100),
                'Shopping': (20, 500)
            }
            
            min_amt, max_amt = amount_ranges[category]
            
            transactions.append({
                'Date': date,
                'Description': merchant,
                'Amount': random.uniform(min_amt, max_amt),
                'Type': 'Debit'
            })
    
    return pd.DataFrame(transactions)

def detect_recurring_transactions(data):
    """Detect recurring/subscription transactions"""
    recurring = []
    
    # Group by description and look for regular patterns
    for desc, group in data.groupby('Description'):
        if len(group) >= 3:  # At least 3 occurrences
            # Check if transactions occur roughly monthly
            dates = group['Date'].sort_values()
            intervals = [(dates.iloc[i+1] - dates.iloc[i]).days for i in range(len(dates)-1)]
            
            # If most intervals are between 25-35 days, likely monthly
            monthly_intervals = [i for i in intervals if 25 <= i <= 35]
            if len(monthly_intervals) >= len(intervals) * 0.7:  # 70% are monthly
                avg_amount = group['Amount'].mean()
                recurring.append({
                    'description': desc,
                    'frequency': 'Monthly',
                    'amount': avg_amount,
                    'occurrences': len(group)
                })
    
    return recurring

def generate_text_report(data, category_summary):
    """Generate text report for PDF export"""
    report = []
    report.append("FINANCIAL REPORT")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")
    
    # Summary statistics
    total_income = data[data['Type'] == 'Credit']['Amount'].sum()
    total_expenses = data[data['Type'] == 'Debit']['Amount'].sum()
    net_flow = total_income - total_expenses
    
    report.append("SUMMARY")
    report.append("-" * 30)
    report.append(f"Total Income: ${total_income:,.2f}")
    report.append(f"Total Expenses: ${total_expenses:,.2f}")
    report.append(f"Net Flow: ${net_flow:,.2f}")
    report.append(f"Number of Transactions: {len(data)}")
    report.append("")
    
    # Category breakdown
    if not category_summary.empty:
        report.append("SPENDING BY CATEGORY")
        report.append("-" * 30)
        for _, row in category_summary.iterrows():
            report.append(f"{row['Category']}: ${row['Total']:,.2f}")
    report.append("")
    
    # Recent transactions
    report.append("RECENT TRANSACTIONS (Last 10)")
    report.append("-" * 30)
    recent = data.nlargest(10, 'Date')
    for _, row in recent.iterrows():
        report.append(f"{row['Date'].strftime('%Y-%m-%d')} | {row['Description'][:30]} | ${row['Amount']:,.2f}")
    
    return "\n".join(report)

