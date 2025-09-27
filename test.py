import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
import smtplib
from email.message import EmailMessage
from io import BytesIO
import tempfile
import os
import datetime
from PIL import Image
import pdfplumber
from fpdf import FPDF

# Page configuration
st.set_page_config(page_title="Finance Hub", layout="wide")

st.title("💼 Welcome to Finance Hub")
st.markdown("Choose a feature below to get started:")

option = st.radio(
    "What would you like to do?",
    ["📊 Spending Analysis", "📅 Budget Planner", "🌐 Network Analysis"],
    index=0
)

if option == "📊 Spending Analysis":
    st.markdown("You selected **Spending Analysis**.")
    
    # ---------- Functions ----------
    
    @st.cache_data
    def process_csv(file):
        try:
            df = pd.read_csv(file)
            # Handle different possible column names
            column_mapping = {
                'TRANS DATE': 'Date',
                'Transaction Date': 'Date',
                'Date': 'Date',
                'DETAILS': 'Description',
                'Details': 'Description',
                'Description': 'Description',
                'TOTAL AMOUNT': 'Amount',
                'Total Amount': 'Amount',
                'Amount': 'Amount',
                'TRANS TYPE': 'Type',
                'Transaction Type': 'Type',
                'Type': 'Type'
            }
            
            # Rename columns based on mapping
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df.rename(columns={old_name: new_name}, inplace=True)
            
            # Ensure we have the required columns
            required_cols = ['Date', 'Description', 'Amount']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
                return pd.DataFrame()
            
            # Process the data
            df = df[['Date', 'Description', 'Amount']]
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df['Category'] = df['Amount'].apply(lambda x: 'Debit' if x < 0 else 'Credit')
            df['Amount'] = df['Amount'].abs()
            
            return df.dropna()
        except Exception as e:
            st.error(f"CSV Error: {e}")
            return pd.DataFrame()

    @st.cache_data
    def process_pdf(file):
        try:
            data = []
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    lines = text.split('\n')
                    for line in lines:
                        # Look for transaction patterns
                        if any(keyword in line.upper() for keyword in ['POS', 'TRF', 'PURCHASE', 'PAYMENT', 'DEPOSIT']):
                            parts = line.split()
                            if len(parts) >= 3:
                                # Try to extract date, description, and amount
                                try:
                                    # Assume first part is date
                                    date_str = parts[0]
                                    # Last part or second to last might be amount
                                    amount_str = parts[-1] if parts[-1].replace(',', '').replace('.', '').replace('-', '').isdigit() else parts[-2]
                                    # Everything in between is description
                                    desc = " ".join(parts[1:-1])
                                    
                                    # Clean amount
                                    amount_str = amount_str.replace('J$', '').replace('$', '').replace(',', '')
                                    amount = abs(float(amount_str))
                                    
                                    # Determine if it's debit or credit
                                    category = 'Debit' if '-' in amount_str or 'PURCHASE' in line.upper() else 'Credit'
                                    
                                    data.append([date_str, desc, amount, category])
                                except:
                                    continue
            
            if data:
                df = pd.DataFrame(data, columns=['Date', 'Description', 'Amount', 'Category'])
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                return df.dropna()
            return pd.DataFrame()
        except Exception as e:
            st.error(f"PDF Error: {e}")
            return pd.DataFrame()

    def classify_expense(description, mapping):
        desc = description.lower()
        for category, keywords in mapping.items():
            for kw in keywords:
                if kw.lower() in desc:
                    return category
        return 'Uncategorized'

    def send_email_alert(receiver_email, subject, body, sender_email, sender_password, smtp_server, smtp_port=587):
        """Send email alerts with proper error handling"""
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = receiver_email

            if 'gmail' in smtp_server.lower():
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    st.success("✅ Email sent successfully!")
            else:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    st.success("✅ Email sent successfully!")
            
            return True

        except smtplib.SMTPAuthenticationError:
            st.error("❌ Authentication Failed - Check your email credentials")
            if 'gmail' in smtp_server.lower():
                st.info("📌 Gmail users must use App Passwords, not regular passwords")
            return False
        except Exception as e:
            st.error(f"❌ Email Error: {str(e)}")
            return False

    def export_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        return output.getvalue()

    def export_to_pdf(text_report):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            lines = text_report.split('\n')
            for line in lines:
                if len(line) > 80:
                    line = line[:77] + "..."
                pdf.cell(0, 10, line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
            
            return bytes(pdf.output(dest='S'), 'latin-1')
        except Exception as e:
            st.error(f"PDF generation error: {e}")
            return b"PDF generation failed"

    # ---------- Main App ----------
    
    st.title("💰 Personal Finance Tracker")
    
    # File Upload
    uploaded_files = st.file_uploader(
        "Upload CSV or PDF bank statements",
        type=["csv", "pdf"],
        accept_multiple_files=True
    )

    data = pd.DataFrame()
    if uploaded_files:
        for file in uploaded_files:
            if file.name.lower().endswith(".csv"):
                df = process_csv(file)
            elif file.name.lower().endswith(".pdf"):
                df = process_pdf(file)
            else:
                continue
            
            if not df.empty:
                data = pd.concat([data, df], ignore_index=True)

    if data.empty:
        st.info("📄 Upload your bank CSV or PDF statements to get started.")
        
        # Show sample data format
        with st.expander("📋 Expected Data Format"):
            st.markdown("""
            Your CSV should contain these columns:
            - **Date** or **TRANS DATE**: Transaction date
            - **Description** or **DETAILS**: Transaction description
            - **Amount** or **TOTAL AMOUNT**: Transaction amount
            
            The system will automatically detect debits (negative) and credits (positive).
            """)
        st.stop()

    # Clean and prepare data
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    data = data.dropna(subset=['Date', 'Amount'])
    data = data.sort_values('Date')

    # ---------- Sidebar Configuration ----------
    
    st.sidebar.header("⚙️ Settings")
    
    # Categories and Keywords
    st.sidebar.subheader("🗂 Expense Categories")
    
    default_categories = {
        "Food": ["restaurant", "food", "eat", "cafe", "pizza", "burger", "kfc", "juici"],
        "Grocery": ["supermarket", "grocery", "hi-lo", "wholesale", "market"],
        "Utilities": ["jps", "nwc", "flow", "internet", "electricity", "water", "phone"],
        "Transport": ["gas", "fuel", "uber", "taxi", "bus", "transport"],
        "Entertainment": ["cinema", "movie", "game", "entertainment", "netflix"],
        "Shopping": ["store", "shop", "mall", "amazon", "online"],
        "Healthcare": ["pharmacy", "doctor", "hospital", "medical", "health"],
        "Income": ["salary", "payment", "deposit", "transfer", "remitly"],
        "Other": []
    }
    
    CATEGORY_KEYWORDS = {}
    for category, keywords in default_categories.items():
        CATEGORY_KEYWORDS[category] = keywords

    # Monthly Budgets
    st.sidebar.subheader("💸 Monthly Budgets (J$)")
    MONTHLY_BUDGETS = {}
    
    budget_defaults = {
        "Food": 15000, "Grocery": 10000, "Utilities": 8000,
        "Transport": 6000, "Entertainment": 3000, "Shopping": 5000,
        "Healthcare": 2000, "Other": 5000
    }
    
    for category in CATEGORY_KEYWORDS.keys():
        if category != "Income":
            MONTHLY_BUDGETS[category] = st.sidebar.number_input(
                f"{category}",
                min_value=0,
                value=budget_defaults.get(category, 5000),
                step=500,
                key=f"budget_{category}"
            )

    # Savings Goal
    st.sidebar.subheader("🎯 Monthly Savings Goal")
    SAVINGS_GOAL = st.sidebar.number_input(
        "Target Amount (J$)",
        min_value=0,
        value=10000,
        step=500
    )

    # Email Settings
    st.sidebar.subheader("📧 Email Alerts")
    enable_email = st.sidebar.checkbox("Enable Email Notifications")
    
    if enable_email:
        email_provider = st.sidebar.selectbox(
            "Provider",
            ["Gmail", "Outlook", "Yahoo", "Custom"]
        )
        
        if email_provider == "Gmail":
            smtp_server = "smtp.gmail.com"
            smtp_port = 465
            st.sidebar.info("⚠️ Use App Password, not regular password")
        elif email_provider == "Outlook":
            smtp_server = "smtp-mail.outlook.com"
            smtp_port = 587
        elif email_provider == "Yahoo":
            smtp_server = "smtp.mail.yahoo.com"
            smtp_port = 587
        else:
            smtp_server = st.sidebar.text_input("SMTP Server")
            smtp_port = st.sidebar.number_input("Port", value=587)
        
        sender_email = st.sidebar.text_input("Your Email")
        sender_password = st.sidebar.text_input("Password", type="password")
        notify_email = st.sidebar.text_input("Send Alerts To")

    # ---------- Data Analysis ----------
    
    # Add month and year columns
    data['Year'] = data['Date'].dt.year
    data['Month'] = data['Date'].dt.month
    data['Month-Year'] = data['Date'].dt.strftime('%B %Y')
    data['Month-Name'] = data['Date'].dt.strftime('%B')
    
    # Classify expenses
    data['Spending Category'] = data['Description'].apply(
        lambda d: classify_expense(d, CATEGORY_KEYWORDS)
    )

    # ---------- Overview Section ----------
    
    st.header("📊 Financial Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_income = data[data['Category'] == 'Credit']['Amount'].sum()
    total_spending = data[data['Category'] == 'Debit']['Amount'].sum()
    net_flow = total_income - total_spending
    num_transactions = len(data)
    
    with col1:
        st.metric("💰 Total Income", f"J${total_income:,.0f}")
    with col2:
        st.metric("💸 Total Spending", f"J${total_spending:,.0f}")
    with col3:
        st.metric("📈 Net Flow", f"J${net_flow:,.0f}")
    with col4:
        st.metric("📝 Transactions", f"{num_transactions:,}")

    # ---------- Trend Analysis ----------
    
    st.header("📈 Spending Trends")
    
    # Get available months
    available_months = sorted(data['Month-Year'].unique(), 
                            key=lambda x: pd.to_datetime(x, format='%B %Y'))
    
    if len(available_months) > 0:
        # Period selection
        period_type = st.radio(
            "Select Analysis Period",
            ["All Time", "Specific Months", "Last 3 Months", "Last 6 Months"]
        )
        
        if period_type == "All Time":
            trend_data = data.copy()
        elif period_type == "Specific Months":
            selected_months = st.multiselect(
                "Select months to analyze",
                options=available_months,
                default=available_months[-2:] if len(available_months) >= 2 else available_months
            )
            trend_data = data[data['Month-Year'].isin(selected_months)]
        elif period_type == "Last 3 Months":
            last_3_months = available_months[-3:] if len(available_months) >= 3 else available_months
            trend_data = data[data['Month-Year'].isin(last_3_months)]
        else:  # Last 6 Months
            last_6_months = available_months[-6:] if len(available_months) >= 6 else available_months
            trend_data = data[data['Month-Year'].isin(last_6_months)]
        
        if not trend_data.empty:
            # Create monthly summary
            monthly_summary = trend_data.groupby(['Month-Year', 'Category'])['Amount'].sum().unstack(fill_value=0)
            
            # Ensure columns exist
            if 'Credit' not in monthly_summary.columns:
                monthly_summary['Credit'] = 0
            if 'Debit' not in monthly_summary.columns:
                monthly_summary['Debit'] = 0
            
            monthly_summary['Net Flow'] = monthly_summary['Credit'] - monthly_summary['Debit']
            monthly_summary = monthly_summary.reset_index()
            
            # Sort by date
            monthly_summary['Date_Sort'] = pd.to_datetime(monthly_summary['Month-Year'], format='%B %Y')
            monthly_summary = monthly_summary.sort_values('Date_Sort')
            
            # Create the chart
            fig = px.bar(
                monthly_summary,
                x='Month-Year',
                y=['Credit', 'Debit'],
                barmode='group',
                title="Income vs Spending by Month",
                labels={'value': 'Amount (J$)', 'variable': 'Type'},
                color_discrete_map={'Credit': 'green', 'Debit': 'red'}
            )
            fig.update_layout(yaxis_tickprefix="J$", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Net flow line chart
            fig_net = px.line(
                monthly_summary,
                x='Month-Year',
                y='Net Flow',
                title="Monthly Net Cash Flow",
                markers=True
            )
            fig_net.update_layout(yaxis_tickprefix="J$", height=350)
            fig_net.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_net, use_container_width=True)

    # ---------- Detailed Monthly Analysis ----------
    
    st.header("📅 Monthly Analysis")
    
    available_months_list = sorted(data['Month-Name'].unique(), 
                                  key=lambda x: list(calendar.month_name).index(x))
    
    selected_month = st.selectbox("Select Month", available_months_list)
    
    # Filter for selected month
    month_data = data[data['Month-Name'] == selected_month].copy()
    
    if not month_data.empty:
        # Month metrics
        col1, col2, col3 = st.columns(3)
        
        month_income = month_data[month_data['Category'] == 'Credit']['Amount'].sum()
        month_spending = month_data[month_data['Category'] == 'Debit']['Amount'].sum()
        month_savings = month_income - month_spending
        
        with col1:
            st.metric(f"Income - {selected_month}", f"J${month_income:,.0f}")
        with col2:
            st.metric(f"Spending - {selected_month}", f"J${month_spending:,.0f}")
        with col3:
            delta_color = "normal" if month_savings >= 0 else "inverse"
            st.metric(f"Savings - {selected_month}", f"J${month_savings:,.0f}",
                     delta=f"Goal: J${SAVINGS_GOAL:,.0f}", delta_color=delta_color)
        
        # Spending breakdown
        st.subheader(f"💸 Spending Breakdown - {selected_month}")
        
        spending_data = month_data[month_data['Category'] == 'Debit']
        
        if not spending_data.empty:
            category_summary = spending_data.groupby('Spending Category')['Amount'].sum().reset_index()
            category_summary = category_summary.sort_values('Amount', ascending=False)
            category_summary['Percentage'] = 100 * category_summary['Amount'] / category_summary['Amount'].sum()
            
            # Pie chart
            fig_pie = px.pie(
                category_summary,
                values='Amount',
                names='Spending Category',
                title=f"Spending Distribution - {selected_month}",
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Budget comparison
            st.subheader("📊 Budget vs Actual")
            
            budget_comparison = []
            for category in MONTHLY_BUDGETS.keys():
                actual = category_summary[category_summary['Spending Category'] == category]['Amount'].sum()
                budget = MONTHLY_BUDGETS[category]
                budget_comparison.append({
                    'Category': category,
                    'Budget': budget,
                    'Actual': actual,
                    'Difference': budget - actual,
                    'Status': '✅' if actual <= budget else '⚠️'
                })
            
            budget_df = pd.DataFrame(budget_comparison)
            
            # Display budget table
            st.dataframe(
                budget_df.style.format({
                    'Budget': 'J${:,.0f}',
                    'Actual': 'J${:,.0f}',
                    'Difference': 'J${:,.0f}'
                }).apply(lambda x: ['background-color: #ffcccc' if '⚠️' in str(v) else '' for v in x], 
                        subset=['Status'])
            )
            
            # Budget chart
            fig_budget = px.bar(
                budget_df,
                x='Category',
                y=['Budget', 'Actual'],
                barmode='group',
                title="Budget vs Actual Spending",
                color_discrete_map={'Budget': 'lightblue', 'Actual': 'orange'}
            )
            fig_budget.update_layout(yaxis_tickprefix="J$")
            st.plotly_chart(fig_budget, use_container_width=True)
            
            # Alerts
            over_budget = budget_df[budget_df['Difference'] < 0]
            if not over_budget.empty or month_savings < SAVINGS_GOAL:
                st.warning("⚠️ Financial Alerts Detected!")
                
                if not over_budget.empty:
                    st.write("**Over Budget Categories:**")
                    for _, row in over_budget.iterrows():
                        st.write(f"- {row['Category']}: Over by J${-row['Difference']:,.0f}")
                
                if month_savings < SAVINGS_GOAL:
                    st.write(f"**Savings Alert:** Short of goal by J${SAVINGS_GOAL - month_savings:,.0f}")
                
                # Email alert option
                if enable_email and notify_email and sender_email and sender_password:
                    if st.button("📧 Send Alert Email"):
                        alert_body = f"Finance Alert for {selected_month}\n\n"
                        
                        if not over_budget.empty:
                            alert_body += "OVER BUDGET:\n"
                            for _, row in over_budget.iterrows():
                                alert_body += f"- {row['Category']}: Over by J${-row['Difference']:,.0f}\n"
                        
                        if month_savings < SAVINGS_GOAL:
                            alert_body += f"\nSAVINGS: Short of goal by J${SAVINGS_GOAL - month_savings:,.0f}"
                        
                        send_email_alert(
                            notify_email,
                            f"Finance Alert - {selected_month}",
                            alert_body,
                            sender_email,
                            sender_password,
                            smtp_server,
                            smtp_port
                        )
        
        # Transaction details
        with st.expander(f"📝 View All Transactions - {selected_month}"):
            st.dataframe(
                month_data[['Date', 'Description', 'Amount', 'Category', 'Spending Category']]
                .sort_values('Date', ascending=False)
                .style.format({'Amount': 'J${:,.2f}'})
            )
        
        # Export options
        st.subheader("📤 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            excel_data = export_to_excel(month_data)
            st.download_button(
                "📊 Download Excel",
                data=excel_data,
                file_name=f"Finance_{selected_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # Create text report
            report = f"Finance Report - {selected_month}\n"
            report += "=" * 50 + "\n\n"
            report += f"Total Income: J${month_income:,.2f}\n"
            report += f"Total Spending: J${month_spending:,.2f}\n"
            report += f"Net Savings: J${month_savings:,.2f}\n"
            report += f"Savings Goal: J${SAVINGS_GOAL:,.2f}\n\n"
            
            if not spending_data.empty:
                report += "SPENDING BY CATEGORY:\n"
                for _, row in category_summary.iterrows():
                    report += f"- {row['Spending Category']}: J${row['Amount']:,.2f} ({row['Percentage']:.1f}%)\n"
            
            pdf_data = export_to_pdf(report)
            st.download_button(
                "📄 Download PDF",
                data=pdf_data,
                file_name=f"Finance_{selected_month}.pdf",
                mime="application/pdf"
            )

elif option == "📅 Budget Planner":
    st.markdown("## 📅 Budget Planner")
    
    st.info("💡 Create and manage your monthly budget plan")
    
    # Budget creation form
    st.subheader("Create Monthly Budget")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Income")
        salary = st.number_input("Monthly Salary", min_value=0, value=50000, step=1000)
        other_income = st.number_input("Other Income", min_value=0, value=0, step=500)
        total_income = salary + other_income
        st.metric("Total Income", f"J${total_income:,.0f}")
    
    with col2:
        st.markdown("### 💸 Expenses")
        rent = st.number_input("Rent/Mortgage", min_value=0, value=15000, step=1000)
        utilities = st.number_input("Utilities", min_value=0, value=8000, step=500)
        food = st.number_input("Food & Groceries", min_value=0, value=12000, step=500)
        transport = st.number_input("Transportation", min_value=0, value=6000, step=500)
        other = st.number_input("Other Expenses", min_value=0, value=5000, step=500)
        
        total_expenses = rent + utilities + food + transport + other
        st.metric("Total Expenses", f"J${total_expenses:,.0f}")
    
    # Summary
    st.subheader("📊 Budget Summary")
    
    remaining = total_income - total_expenses
    savings_rate = (remaining / total_income * 100) if total_income > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Monthly Surplus/Deficit", f"J${remaining:,.0f}")
    with col2:
        st.metric("Savings Rate", f"{savings_rate:.1f}%")
    with col3:
        st.metric("Annual Savings", f"J${remaining * 12:,.0f}")
    
    # Visualization
    budget_data = pd.DataFrame({
        'Category': ['Rent', 'Utilities', 'Food', 'Transport', 'Other', 'Savings'],
        'Amount': [rent, utilities, food, transport, other, max(0, remaining)]
    })
    
    fig = px.pie(
        budget_data,
        values='Amount',
        names='Category',
        title="Budget Allocation",
        hole=0.4
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations
    if remaining < 0:
        st.error("⚠️ Your expenses exceed your income! Consider reducing expenses or increasing income.")
    elif savings_rate < 10:
        st.warning("📉 Your savings rate is below 10%. Try to save at least 10-20% of your income.")
    else:
        st.success(f"✅ Great job! You're saving {savings_rate:.1f}% of your income.")

elif option == "🌐 Network Analysis":
    st.markdown("## 🌐 Network Analysis")
    
    st.info("🚧 This feature is coming soon!")
    
    st.markdown("""
    ### Planned Features:
    
    **🔗 Transaction Network**
    - Visualize money flow between accounts and categories
    - Identify spending patterns and cycles
    
    **📊 Pattern Recognition**
    - Detect unusual spending behaviors
    - Find recurring transactions
    - Identify seasonal trends
    
    **🏪 Merchant Analysis**
    - Track your most frequent merchants
    - Analyze spending by vendor
    - Get insights on shopping habits
    
    **📈 Predictive Analytics**
    - Forecast future spending
    - Budget recommendations based on patterns
    - Early warning for potential overspending
    """)
    
    # Sample visualization placeholder
    st.subheader("Sample Visualization (Coming Soon)")
    
    sample_data = pd.DataFrame({
        'Source': ['Income'] * 5,
        'Target': ['Food', 'Rent', 'Transport', 'Utilities', 'Savings'],
        'Amount': [5000, 15000, 3000, 4000, 8000]
    })
    
    fig = px.bar(
        sample_data,
        x='Target',
        y='Amount',
        title="Sample Money Flow",
        color='Amount',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(yaxis_tickprefix="J$")
    st.plotly_chart(fig, use_container_width=True)
