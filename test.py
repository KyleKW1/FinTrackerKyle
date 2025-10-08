import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import re

# ============================================
# DATABASE CONFIGURATION
# ============================================

DB_CONFIG = {
    'host': 'mysql-11beff9b-kamarwatson36-874b.g.aivencloud.com',
    'user': 'avnadmin',  # Change to your MySQL username
    'password': 'AVNS_Dxyg2mu3MEiRoVyasff',  # Change to your MySQL password
    'database': 'defaultdb'
}

# ============================================
# DATABASE FUNCTIONS
# ============================================

def create_connection():
    """Create a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database and create users table if it doesn't exist"""
    try:
        # Connect without database to create it if needed
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        st.error(f"Database initialization error: {e}")
        return False

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(username, email, password):
    """Register a new user"""
    connection = create_connection()
    if not connection:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        password_hash = hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        
        connection.commit()
        cursor.close()
        connection.close()
        return True, "Registration successful!"
    
    except mysql.connector.IntegrityError:
        connection.close()
        return False, "Username or email already exists"
    except Error as e:
        connection.close()
        return False, f"Registration error: {e}"

def authenticate_user(username, password):
    """Authenticate user login"""
    connection = create_connection()
    if not connection:
        return False, None
    
    try:
        cursor = connection.cursor(dictionary=True)
        password_hash = hash_password(password)
        
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password_hash = %s",
            (username, password_hash)
        )
        
        user = cursor.fetchone()
        
        if user:
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user['id'],)
            )
            connection.commit()
        
        cursor.close()
        connection.close()
        
        return user is not None, user
    
    except Error as e:
        st.error(f"Authentication error: {e}")
        connection.close()
        return False, None

# ============================================
# SESSION STATE MANAGEMENT
# ============================================

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'login'
    st.rerun()

# ============================================
# UI PAGES
# ============================================

def login_page():
    """Display login page"""
    st.title("🔐 Finance Hub Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Login", use_container_width=True):
                if username and password:
                    success, user = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
        
        with col_btn2:
            if st.button("Register", use_container_width=True):
                st.session_state.page = 'register'
                st.rerun()
        
        st.markdown("---")
        st.info("💡 **Demo:** Create a new account to get started!")

def register_page():
    """Display registration page"""
    st.title("📝 Register New Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        username = st.text_input("Username", key="reg_username", help="Minimum 3 characters")
        email = st.text_input("Email", key="reg_email", help="Valid email address")
        password = st.text_input("Password", type="password", key="reg_password", help="Minimum 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Create Account", use_container_width=True):
                # Validation
                if not username or not email or not password:
                    st.error("All fields are required")
                elif len(username) < 3:
                    st.error("Username must be at least 3 characters")
                elif not validate_email(email):
                    st.error("Invalid email format")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(username, email, password)
                    if success:
                        st.success(message)
                        st.info("Please login with your new account")
                        st.balloons()
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(message)
        
        with col_btn2:
            if st.button("Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()
        
        st.markdown("---")

def main_app():
    """Display main application - Your Finance Hub"""
    import pandas as pd
    import plotly.express as px
    import calendar
    import smtplib
    from email.message import EmailMessage
    from io import BytesIO
    import tempfile
    import os
    from PIL import Image
    import pdfplumber

    try:
        import pdfkit
        PDFKIT_INSTALLED = True
    except ImportError:
        PDFKIT_INSTALLED = False

    from fpdf import FPDF

    # Sidebar user info at the top
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.markdown(f"📧 {st.session_state.user['email']}")
        if st.session_state.user.get('last_login'):
            last_login = str(st.session_state.user['last_login'])
            st.caption(f"Last login: {last_login[:19]}")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        st.markdown("---")

    # ---------- Helper Functions ----------

    @st.cache_data
    def process_csv(file):
        try:
            df = pd.read_csv(file)
            df.rename(columns={
                'TRANS DATE': 'Date',
                'DETAILS': 'Description',
                'TOTAL AMOUNT': 'Amount',
                'TRANS TYPE': 'Category'
            }, inplace=True)
            df = df[['Date', 'Description', 'Amount', 'Category']]
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df['Category'] = df['Amount'].apply(lambda x: 'Debit' if x < 0 else 'Credit')
            df['Amount'] = df['Amount'].abs()
            return df
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
                    for line in text.split('\n'):
                        if "POS" in line or "TRF" in line or "PURCHASE" in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                date = parts[0]
                                desc = " ".join(parts[1:-2])
                                amt = parts[-2].replace('J$', '').replace(',', '')
                                cat = 'Debit' if '-' in parts[-2] else 'Credit'
                                data.append([date, desc, abs(float(amt)), cat])
            df = pd.DataFrame(data, columns=['Date', 'Description', 'Amount', 'Category'])
            return df
        except Exception as e:
            st.error(f"PDF Error: {e}")
            return pd.DataFrame()

    def classify_expense(description, mapping):
        desc = description.lower()
        for category, keywords in mapping.items():
            for kw in keywords:
                if kw in desc:
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
        processed_data = output.getvalue()
        return processed_data

    def export_to_pdf(text_report):
        if PDFKIT_INSTALLED:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
                f.write(text_report.encode('utf-8'))
                f.flush()
                pdf_file = f.name.replace('.html', '.pdf')
                pdfkit.from_file(f.name, pdf_file)
                with open(pdf_file, 'rb') as pdf_f:
                    pdf_bytes = pdf_f.read()
                os.unlink(f.name)
                os.unlink(pdf_file)
                return pdf_bytes
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            for line in text_report.split('\n'):
                pdf.cell(0, 10, line.encode('latin-1', 'ignore').decode('latin-1'), ln=True)
                
            return pdf.output(dest='S').encode('latin1')

    # ---------- Main App UI ----------
    
    st.title("💼 Welcome to Finance Hub")
    st.markdown("Choose a feature below to get started:")

    option = st.radio(
        "What would you like to do?",
        ["📊 Spending Analysis", "📅 Budget Planner", "🌐 Network Analysis"],
        index=0
    )

    if option == "📊 Spending Analysis":
        st.markdown("### 📊 Spending Analysis")
        
        st.title("Personal Finance Tracker")

        uploaded_files = st.file_uploader(
            "Upload CSV or PDF files",
            type=["csv", "pdf"],
            accept_multiple_files=True
        )

        data = pd.DataFrame()
        if uploaded_files:
            for file in uploaded_files:
                fname = file.name.lower()
                if fname.endswith(".csv"):
                    data = pd.concat([data, process_csv(file)], ignore_index=True)
                elif fname.endswith(".pdf"):
                    data = pd.concat([data, process_pdf(file)], ignore_index=True)

        if data.empty:
            st.info("Upload your bank CSV or PDF statements to get started.")
            st.stop()

        # Convert Date column and create Month-Year and Month-Name columns
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        
        data['Month-Year'] = data['Date'].dt.strftime('%B %Y')
        data['Month-Name'] = data['Date'].dt.strftime('%B')

        # -------- Sidebar: Categories and Budgets --------

        st.sidebar.header("🗂 Customize Categories and Budgets")

        default_mapping = {
            "Food": ["juici", "kfc", "restaurant", "burger", "pizza"],
            "Grocery": ["hi-lo", "supermarket", "wholesale"],
            "Utilities": ["jps", "nwc", "flow", "internet", "light", "water"],
            "Transport": ["uber", "taxi", "gas"],
            "Income": ["remitly", "deposit", "transfer", "payroll"],
            "Miscellaneous": ["atm"],
            "Other": []
        }

        CATEGORY_KEYWORDS = {}

        st.sidebar.markdown("### Edit Categories and Keywords")
        for category, keywords in default_mapping.items():
            with st.sidebar.expander(f"{category} Keywords", expanded=False):
                kw_text = st.text_area(
                    label=f"Keywords for {category} (comma separated)",
                    value=", ".join(keywords),
                    key=f"kw_{category}"
                )
                CATEGORY_KEYWORDS[category] = [kw.strip().lower() for kw in kw_text.split(",") if kw.strip()]

        st.sidebar.markdown("### 💸 Set Monthly Budgets (J$)")

        MONTHLY_BUDGETS = {}

        for category in CATEGORY_KEYWORDS.keys():
            default_val = 0
            if category == "Food":
                default_val = 15000
            elif category == "Grocery":
                default_val = 10000
            elif category == "Utilities":
                default_val = 8000
            elif category == "Transport":
                default_val = 6000
            elif category == "Miscellaneous":
                default_val = 5000
            MONTHLY_BUDGETS[category] = st.sidebar.number_input(
                label=f"Budget for {category}",
                min_value=0,
                value=default_val,
                step=500,
                key=f"budget_{category}"
            )

        st.sidebar.markdown("### 🎯 Set Monthly Savings Goal (J$)")
        default_savings_goal = 5000
        savings_goal_input = st.sidebar.number_input(
            "Savings Goal Amount (J$)", min_value=0, value=default_savings_goal, step=500
        )
        SAVINGS_GOAL = savings_goal_input

        # Email notification settings
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

        # Apply spending categories
        data['Spending Category'] = data['Description'].apply(
            lambda x: classify_expense(x, CATEGORY_KEYWORDS)
        )

        # ---------- Trend Analysis ----------
        
        st.header("📈 Spending Trends")
        
        available_months = sorted(data['Month-Year'].unique(), 
                                key=lambda x: pd.to_datetime(x, format='%B %Y'))
        
        if len(available_months) > 0:
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
            else:
                last_6_months = available_months[-6:] if len(available_months) >= 6 else available_months
                trend_data = data[data['Month-Year'].isin(last_6_months)]
            
            if not trend_data.empty:
                monthly_summary = trend_data.groupby(['Month-Year', 'Category'])['Amount'].sum().unstack(fill_value=0)
                
                if 'Credit' not in monthly_summary.columns:
                    monthly_summary['Credit'] = 0
                if 'Debit' not in monthly_summary.columns:
                    monthly_summary['Debit'] = 0
                
                monthly_summary['Net Flow'] = monthly_summary['Credit'] - monthly_summary['Debit']
                monthly_summary = monthly_summary.reset_index()
                
                monthly_summary['Date_Sort'] = pd.to_datetime(monthly_summary['Month-Year'], format='%B %Y')
                monthly_summary = monthly_summary.sort_values('Date_Sort')
                
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

        # ---------- Monthly Analysis ----------
        
        st.header("📅 Monthly Analysis")
        
        available_months_list = sorted(data['Month-Name'].unique(), 
                                      key=lambda x: list(calendar.month_name).index(x))
        
        selected_month = st.selectbox("Select Month", available_months_list)
        
        month_data = data[data['Month-Name'] == selected_month].copy()
        filtered = month_data
        
        if not month_data.empty:
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
            
            st.subheader(f"📄 Transactions in {selected_month}")
            st.dataframe(filtered[['Date', 'Description', 'Amount', 'Category', 'Spending Category']])

            st.subheader(f"📈 Spending Breakdown for {selected_month}")
            spend = filtered[filtered['Category'] == 'Debit']
            if not spend.empty:
                summary = spend.groupby('Spending Category')['Amount'].sum().reset_index()
                summary['Percentage'] = 100 * summary['Amount'] / summary['Amount'].sum()
                st.dataframe(summary.style.format({"Amount": "J${:,.2f}", "Percentage": "{:.2f}%"}))

                fig = px.pie(
                    summary,
                    names='Spending Category',
                    values='Amount',
                    title=f"{selected_month} Spending Distribution",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader(f"📏 Budget vs. Actual - {selected_month}")
                budget_df = pd.DataFrame.from_dict(MONTHLY_BUDGETS, orient='index', columns=['Budget']).reset_index()
                budget_df.rename(columns={'index': 'Spending Category'}, inplace=True)
                comparison = pd.merge(budget_df, summary, on='Spending Category', how='left')
                comparison['Amount'] = comparison['Amount'].fillna(0)
                comparison['Difference'] = comparison['Budget'] - comparison['Amount']
                comparison['Status'] = comparison.apply(
                    lambda row: "Over Budget" if row['Amount'] > row['Budget'] else "Within Budget", axis=1
                )

                st.dataframe(
                    comparison.style.format({"Budget": "J${:,.0f}", "Amount": "J${:,.0f}", "Difference": "J${:,.0f}"})
                    .apply(lambda s: ['color: red;' if 'Over' in str(v) else '' for v in s], subset=['Status'])
                )

                fig = px.bar(
                    comparison,
                    x='Spending Category',
                    y=['Budget', 'Amount'],
                    barmode='group',
                    title="Budget vs. Actual Spending by Category",
                    labels={"value": "J$", "variable": "Type"},
                    text_auto=True
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader(f"🎯 Savings Goal Check for {selected_month}")

                total_income = filtered[filtered['Category'] == 'Credit']['Amount'].sum()
                total_spending = filtered[filtered['Category'] == 'Debit']['Amount'].sum()
                actual_savings = total_income - total_spending

                st.markdown(f"**Savings Goal:** J${SAVINGS_GOAL:,.2f}")
                st.markdown(f"**Actual Savings:** J${actual_savings:,.2f}")

                if actual_savings >= SAVINGS_GOAL:
                    st.success(f"🎉 Congrats! You've met your savings goal by J${actual_savings - SAVINGS_GOAL:,.2f}!")
                else:
                    st.warning(f"You are J${SAVINGS_GOAL - actual_savings:,.2f} below your savings goal.")

                if enable_email and notify_email and sender_email and sender_password:
                    overspent = comparison[comparison['Amount'] > comparison['Budget']]
                    if not overspent.empty:
                        subject = f"Finance Tracker Alert: Overspending in {selected_month}"
                        body_lines = [f"Dear user,\n\nYou have overspent in the following categories for {selected_month}:\n"]
                        for _, row in overspent.iterrows():
                            body_lines.append(
                                f"- {row['Spending Category']}: Spent J${row['Amount']:.2f} (Budget: J${row['Budget']:.2f})")
                        body_lines.append("\nPlease review your budget.")
                        body = "\n".join(body_lines)
                        
                        if st.button("📧 Send Alert Email"):
                            send_email_alert(
                                notify_email,
                                subject,
                                body,
                                sender_email,
                                sender_password,
                                smtp_server,
                                smtp_port
                            )

                st.subheader("📤 Export Reports")

                report_text = f"Finance Report - {selected_month}\n\nTransactions:\n"
                for idx, row in filtered.iterrows():
                    report_text += f"{row['Date'].date()} | {row['Description']} | J${row['Amount']:,.2f} | {row['Category']} | {row['Spending Category']}\n"

                report_text += "\nSpending Summary:\n"
                for idx, row in summary.iterrows():
                    report_text += f"{row['Spending Category']}: J${row['Amount']:,.2f} ({row['Percentage']:.2f}%)\n"

                report_text += "\nBudget vs Actual:\n"
                for idx, row in comparison.iterrows():
                    report_text += f"{row['Spending Category']}: Budget J${row['Budget']:,.2f}, Actual J${row['Amount']:,.2f}, Status: {row['Status']}\n"

                export_format = st.selectbox("Select export format", options=["Excel", "PDF"])

                if st.button("Download Report"):
                    if export_format == "Excel":
                        excel_bytes = export_to_excel(filtered)
                        st.download_button(
                            label="Download Excel File",
                            data=excel_bytes,
                            file_name=f"Finance_Report_{selected_month}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        pdf_bytes = export_to_pdf(report_text)
                        st.download_button(
                            label="Download PDF File",
                            data=pdf_bytes,
                            file_name=f"Finance_Report_{selected_month}.pdf",
                            mime="application/pdf"
                        )
            else:
                st.info(f"No spending transactions found for {selected_month}")

    elif option == "📅 Budget Planner":
        st.markdown("### 📅 Budget Planner")
        
        st.title("📋 Budget Dashboard")

        @st.cache_data
        def load_budget_excel():
            try:
                return pd.ExcelFile("/mnt/data/Budget Planner (1).xlsx")
            except FileNotFoundError:
                st.error("Budget file not found. Please upload a budget Excel file.")
                return None

        xls = load_budget_excel()
        
        if xls is not None:
            view_option = st.radio("Choose what to view:", ["Budget Summary", "Income Breakdown", "Raw Transactions"],
                                   horizontal=True)

            if view_option == "Budget Summary" and "Budget" in xls.sheet_names:
                st.subheader("📊 Monthly Budget Summary")
                budget_df = xls.parse("Budget", skiprows=1)
                budget_df = budget_df.dropna(subset=["CATEGORIES"]).reset_index(drop=True)
                st.dataframe(budget_df)

                if "YEARLY TOTAL" in budget_df.columns and "CATEGORIES" in budget_df.columns:
                    fig = px.bar(
                        budget_df,
                        x="CATEGORIES",
                        y="YEARLY TOTAL",
                        title="Total Yearly Spending by Category",
                        labels={"YEARLY TOTAL": "J$"},
                        text_auto=True
                    )
                    st.plotly_chart(fig, use_container_width=True)

            elif view_option == "Income Breakdown" and "Income" in xls.sheet_names:
                st.subheader("💰 Income Breakdown by Source")
                income_df = xls.parse("Income")
                income_df.columns = income_df.iloc[0]
                income_df = income_df[1:]
                income_df = income_df.fillna(0)

                try:
                    income_df.iloc[:, 1:] = income_df.iloc[:, 1:].astype(float)
                    income_summary = income_df.sum(numeric_only=True)

                    income_plot_df = pd.DataFrame({
                        'Source': income_summary.index[:-1],
                        'Amount': income_summary.values[:-1]
                    })

                    fig2 = px.pie(
                        income_plot_df,
                        names='Source',
                        values='Amount',
                        title='Income by Source',
                        hole=0.4
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                except Exception as e:
                    st.error(f"Error processing income breakdown: {e}")

            elif view_option == "Raw Transactions" and "Data" in xls.sheet_names:
                st.subheader("📄 Raw Transactions Table")
                data_df = xls.parse("Data")
                st.dataframe(data_df)

    elif option == "🌐 Network Analysis":
        st.markdown("### 🌐 Network Analysis")
        st.info("Network analysis feature coming soon! This will show transaction patterns and relationships.")

# ============================================
# MAIN APPLICATION
# ============================================

def main():
    st.set_page_config(
        page_title="Finance Hub",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize database
    if 'db_initialized' not in st.session_state:
        if init_database():
            st.session_state.db_initialized = True
        else:
            st.error("Failed to initialize database. Please check your MySQL configuration.")
            st.stop()
    
    # Initialize session state
    init_session_state()
    
    # Route to appropriate page
    if not st.session_state.authenticated:
        if st.session_state.page == 'register':
            register_page()
        else:
            login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
