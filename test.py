import streamlit as st

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
    import pandas as pd
    import plotly.express as px
    import calendar
    import smtplib
    from email.message import EmailMessage
    from io import BytesIO
    import tempfile
    import os
    import datetime
    import streamlit as st
    from PIL import Image
    import pdfplumber

    try:
        import pdfkit
        PDFKIT_INSTALLED = True
    except ImportError:
        PDFKIT_INSTALLED = False

    from fpdf import FPDF

    # ---------- Functions ----------

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
        """
        Enhanced email function with comprehensive authentication troubleshooting
        """
        try:
            # Create message
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = receiver_email

            # Gmail specific handling
            if 'gmail' in smtp_server.lower():
                st.info("🔐 Connecting to Gmail with SSL...")
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.set_debuglevel(0)  # Set to 1 for debugging
                    st.info("🔑 Attempting login...")
                    server.login(sender_email, sender_password)
                    st.info("📤 Sending message...")
                    server.send_message(msg)
                    st.success("✅ Email sent successfully via Gmail!")
            else:
                # Other email providers
                st.info(f"🔐 Connecting to {smtp_server}...")
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.set_debuglevel(0)
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    st.success(f"✅ Email sent successfully via {smtp_server}!")
            
            return True

        except smtplib.SMTPAuthenticationError as e:
            error_code = str(e)
            st.error(f"❌ **Authentication Failed**: {error_code}")
            
            # Specific troubleshooting based on error
            if "535" in error_code:
                st.error("🚫 **Username/Password rejected**")
                with st.expander("🔧 **Gmail Troubleshooting Guide**", expanded=True):
                    st.markdown("""
                    ### For Gmail Users - You MUST use an App Password:
                    
                    #### 🔐 **Step-by-Step Fix:**
                    1. **Enable 2-Factor Authentication** on your Google account first
                    2. Go to: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
                    3. Select "Mail" as the app
                    4. Copy the **16-character password** (no spaces)
                    5. Use this App Password, NOT your regular Gmail password
                    
                    #### ✅ **Checklist:**
                    - [ ] 2-Factor Authentication is ON
                    - [ ] Using App Password (16 characters, no spaces)  
                    - [ ] Email address is correct
                    - [ ] "Less secure app access" is NOT needed (we use App Passwords)
                    
                    #### 🔄 **Alternative Solutions:**
                    - Try generating a new App Password
                    - Make sure you're using the full email address
                    - Check if your account has any security restrictions
                    """)
            
            elif "454" in error_code:
                st.error("🚫 **Too many login attempts** - Wait a few minutes and try again")
            
            return False
            
        except smtplib.SMTPConnectError as e:
            st.error(f"❌ **Connection Failed**: Cannot connect to {smtp_server}:{smtp_port}")
            st.info("🌐 Check your internet connection and SMTP server settings")
            return False
            
        except smtplib.SMTPRecipientsRefused as e:
            st.error(f"❌ **Invalid Recipient**: {receiver_email} was rejected")
            return False
            
        except Exception as e:
            st.error(f"❌ **Unexpected Error**: {str(e)}")
            st.info("🔧 Try using a different email provider or check your settings")
            return False

    def export_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        processed_data = output.getvalue()
        return processed_data

    def export_to_pdf(text_report):
        # Try pdfkit first
        if PDFKIT_INSTALLED:
            try:
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
            except Exception as e:
                st.warning(f"pdfkit failed: {e}. Using fallback PDF generator.")
        
        # Fallback with fpdf (fixed version)
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Split text into lines and add to PDF
            lines = text_report.split('\n')
            for line in lines:
                # Handle long lines by truncating or wrapping
                if len(line) > 80:
                    line = line[:77] + "..."
                pdf.cell(0, 10, line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
                
            return bytes(pdf.output(dest='S'), 'latin-1')
        except Exception as e:
            st.error(f"PDF generation failed: {e}")
            return b"PDF generation failed"

    # ---------- App Start ----------

    st.title("💰 Personal Finance Tracker")

    # Email setup instructions
    with st.expander("📧 **Complete Email Setup Guide**", expanded=False):
        tab1, tab2, tab3 = st.tabs(["📧 Gmail Setup", "🔧 Other Providers", "❓ Troubleshooting"])
        
        with tab1:
            st.markdown("""
            ## 📧 Gmail Setup (Most Common)
            
            ### ⚠️ **CRITICAL: You CANNOT use your regular Gmail password!**
            
            ### 🔐 **Steps to get Gmail App Password:**
            1. **Enable 2-Factor Authentication** on your Google account:
               - Go to [myaccount.google.com/security](https://myaccount.google.com/security)
               - Turn on 2-Step Verification
            
            2. **Generate App Password**:
               - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
               - Select "Mail" from dropdown
               - Click "Generate"
               - Copy the **16-character code** (looks like: `abcd efgh ijkl mnop`)
            
            3. **Use in Finance Tracker**:
               - Email: `youremail@gmail.com`
               - Password: `Your 16-character App Password` (not your regular password!)
               - Provider: Gmail
            
            ### ✅ **Quick Check:**
            - Is 2-Factor Authentication enabled? 
            - Did you copy the 16-character App Password?
            - Are you using the App Password (not your regular password)?
            """)
        
        with tab2:
            st.markdown("""
            ## 🔧 Other Email Providers
            
            ### **Outlook/Hotmail:**
            - SMTP: `smtp-mail.outlook.com`
            - Port: `587`
            - Use your regular Outlook password
            
            ### **Yahoo:**
            - SMTP: `smtp.mail.yahoo.com` 
            - Port: `587`
            - You may need to generate an App Password for Yahoo too
            
            ### **Custom Provider:**
            - Check with your email provider for SMTP settings
            - Common ports: 587 (TLS) or 465 (SSL)
            """)
        
        with tab3:
            st.markdown("""
            ## ❓ Common Issues & Solutions
            
            ### 🚫 **"Username and Password not accepted" (Error 535)**
            - **Gmail**: You're using regular password instead of App Password
            - **Solution**: Generate and use Gmail App Password
            
            ### 🔒 **"Authentication Required"**
            - Enable 2-Factor Authentication first
            - Then generate App Password
            
            ### 🌐 **Connection Timeout**
            - Check internet connection
            - Try different SMTP port (587 vs 465)
            - Check if corporate firewall blocks email ports
            
            ### 📧 **"Invalid Recipient"**
            - Double-check recipient email address
            - Make sure recipient email exists
            
            ### 🔧 **Still Not Working?**
            - Try the "Test Email Settings" button in sidebar
            - Use a different email provider temporarily
            - Contact your IT support if on corporate network
            """)


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
        st.info("📄 Upload your bank CSV or PDF statements to get started.")
        st.stop()

    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    data = data.dropna(subset=['Date'])

    # -------- Sidebar: User-friendly Categories and Budgets --------

    st.sidebar.header("🗂 Customize Categories and Budgets")

    # Default categories and keywords
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

    # Enhanced Email notification settings with validation
    st.sidebar.header("📧 Email Notification Settings")
    enable_email = st.sidebar.checkbox("Enable Email Alerts")
    
    if enable_email:
        st.sidebar.markdown("⚠️ **Important**: Gmail users MUST use App Passwords!")
        
        # Email provider selection first
        email_provider = st.sidebar.selectbox(
            "Email Provider:",
            ["Gmail", "Outlook", "Yahoo", "Custom"]
        )
        
        # Provider-specific instructions
        if email_provider == "Gmail":
            st.sidebar.markdown("""
            📋 **Gmail Setup Required:**
            1. Enable 2-Factor Auth
            2. Generate App Password
            3. Use App Password below
            """)
            smtp_server = "smtp.gmail.com"
            smtp_port = 465  # SSL port for Gmail
            
        elif email_provider == "Outlook":
            smtp_server = "smtp-mail.outlook.com"
            smtp_port = 587
            
        elif email_provider == "Yahoo":
            smtp_server = "smtp.mail.yahoo.com"
            smtp_port = 587
            
        else:  # Custom
            smtp_server = st.sidebar.text_input("SMTP Server:")
            smtp_port = st.sidebar.number_input("SMTP Port:", min_value=1, max_value=65535, value=587)
        
        # Email inputs with validation
        sender_email = st.sidebar.text_input("Your email address:", placeholder="example@gmail.com")
        
        if email_provider == "Gmail":
            sender_password = st.sidebar.text_input("App Password (16 characters):", type="password", placeholder="abcd efgh ijkl mnop")
            if sender_password and len(sender_password.replace(" ", "")) != 16:
                st.sidebar.warning("⚠️ Gmail App Password should be 16 characters!")
        else:
            sender_password = st.sidebar.text_input("Email password:", type="password")
            
        notify_email = st.sidebar.text_input("Send alerts to email:", placeholder="recipient@email.com")
        
        # Test connection button
        if st.sidebar.button("🧪 Test Email Settings"):
            if sender_email and sender_password and notify_email:
                test_sent = send_email_alert(
                    receiver_email=notify_email,
                    subject="Finance Tracker - Test Email",
                    body="This is a test email from your Finance Tracker. If you received this, your email settings are working correctly!",
                    sender_email=sender_email,
                    sender_password=sender_password,
                    smtp_server=smtp_server,
                    smtp_port=smtp_port
                )
            else:
                st.sidebar.error("Please fill in all email fields first!")
    else:
        notify_email = sender_email = sender_password = smtp_server = ""
        smtp_port = 587

    # -------------- Income & Spending Trends for ALL DATA --------------

    st.subheader("📈 Income and Spending Trends (All Data)")

    def get_current_quarter(dt=None):
        if dt is None:
            dt = datetime.datetime.now()
        return (dt.month - 1) // 3 + 1

    def get_current_half_year(dt=None):
        if dt is None:
            dt = datetime.datetime.now()
        return 1 if dt.month <= 6 else 2

    period_type = st.radio(
        "Select Period Type",
        options=["Monthly (Select 2 months)", "Quarterly (Current Quarter)", "Semi-Annually (Current Half-Year)"]
    )

    trend = data.copy()
    trend['Year'] = trend['Date'].dt.year
    trend['Month'] = trend['Date'].dt.month
    trend.set_index('Date', inplace=True)

    if period_type == "Monthly (Select 2 months)":
        trend['Month-Year'] = trend.index.strftime('%B %Y')
        available_month_years = sorted(trend['Month-Year'].unique(),
                                       key=lambda x: datetime.datetime.strptime(x, '%B %Y'))

        if len(available_month_years) == 0:
            st.warning("No data available for monthly analysis.")
        else:
            selected_months = st.multiselect(
                "Select exactly 2 months to compare",
                options=available_month_years,
                default=available_month_years[-2:] if len(available_month_years) >= 2 else available_month_years
            )

            if len(selected_months) != 2:
                st.warning("Please select exactly 2 months.")
            else:
                filtered_trend = trend[trend['Month-Year'].isin(selected_months)]
                
                if filtered_trend.empty:
                    st.warning("No data found for the selected months.")
                else:
                    # Create aggregation with proper handling
                    agg = filtered_trend.groupby(['Month-Year', 'Category'])['Amount'].sum().unstack(fill_value=0)
                    
                    # Ensure required columns exist
                    if 'Credit' not in agg.columns:
                        agg['Credit'] = 0
                    if 'Debit' not in agg.columns:
                        agg['Debit'] = 0
                    
                    agg['Net Flow'] = agg['Credit'] - agg['Debit']
                    agg = agg.reset_index()
                    
                    # Create chart data in long format
                    chart_data = []
                    for _, row in agg.iterrows():
                        chart_data.extend([
                            {'Month-Year': row['Month-Year'], 'Type': 'Credit', 'Amount': row['Credit']},
                            {'Month-Year': row['Month-Year'], 'Type': 'Debit', 'Amount': row['Debit']},
                            {'Month-Year': row['Month-Year'], 'Type': 'Net Flow', 'Amount': row['Net Flow']}
                        ])
                    
                    chart_df = pd.DataFrame(chart_data)
                    
                    fig = px.bar(
                        chart_df,
                        x='Month-Year',
                        y='Amount',
                        color='Type',
                        barmode='group',
                        title="Income, Spending, and Net Flow by Selected Months",
                        labels={'Amount': 'Amount (J$)', 'Month-Year': 'Month'}
                    )
                    fig.update_layout(yaxis_tickprefix="J$")
                    st.plotly_chart(fig, use_container_width=True)

    elif period_type == "Quarterly (Current Quarter)":
        current_year = datetime.datetime.now().year
        current_quarter = get_current_quarter()

        st.markdown(f"**Showing data for Q{current_quarter} of {current_year}**")

        def quarter(month):
            return (month - 1) // 3 + 1

        filtered_trend = trend[(trend['Year'] == current_year) & (trend['Month'].apply(quarter) == current_quarter)]

        agg = filtered_trend.groupby(['Month', 'Category'])['Amount'].sum().unstack(fill_value=0)
        agg['Net Flow'] = agg.get('Credit', 0) - agg.get('Debit', 0)
        agg = agg.reset_index()
        agg['Month Name'] = agg['Month'].apply(lambda m: calendar.month_name[m])

        fig = px.bar(
            agg,
            x='Month Name',
            y=['Credit', 'Debit', 'Net Flow'],
            barmode='group',
            title=f"Income, Spending, and Net Flow for Q{current_quarter} {current_year}",
            labels={'value': 'Amount (J$)', 'Month Name': 'Month'}
        )
        fig.update_layout(yaxis_tickprefix="J$")
        st.plotly_chart(fig, use_container_width=True)

    elif period_type == "Semi-Annually (Current Half-Year)":
        current_year = datetime.datetime.now().year
        current_half = get_current_half_year()

        half_label = "Jan - Jun" if current_half == 1 else "Jul - Dec"
        st.markdown(f"**Showing data for {half_label} {current_year}**")

        if current_half == 1:
            filtered_trend = trend[(trend['Year'] == current_year) & (trend['Month'].between(1, 6))]
        else:
            filtered_trend = trend[(trend['Year'] == current_year) & (trend['Month'].between(7, 12))]

        if filtered_trend.empty:
            st.warning(f"No data found for {half_label} {current_year}")
        else:
            agg = filtered_trend.groupby(['Month', 'Category'])['Amount'].sum().unstack(fill_value=0)
            
            # Ensure required columns exist
            if 'Credit' not in agg.columns:
                agg['Credit'] = 0
            if 'Debit' not in agg.columns:
                agg['Debit'] = 0
                
            agg['Net Flow'] = agg['Credit'] - agg['Debit']
            agg = agg.reset_index()
            agg['Month Name'] = agg['Month'].apply(lambda m: calendar.month_name[m])

            # Create chart data in long format
            chart_data = []
            for _, row in agg.iterrows():
                chart_data.extend([
                    {'Month Name': row['Month Name'], 'Type': 'Credit', 'Amount': row['Credit']},
                    {'Month Name': row['Month Name'], 'Type': 'Debit', 'Amount': row['Debit']},
                    {'Month Name': row['Month Name'], 'Type': 'Net Flow', 'Amount': row['Net Flow']}
                ])
            
            chart_df = pd.DataFrame(chart_data)

            fig = px.bar(
                chart_df,
                x='Month Name',
                y='Amount',
                color='Type',
                barmode='group',
                title=f"Income, Spending, and Net Flow for {half_label} {current_year}",
                labels={'Amount': 'Amount (J$)', 'Month Name': 'Month'}
            )
            fig.update_layout(yaxis_tickprefix="J$")
            st.plotly_chart(fig, use_container_width=True)

    # -------------- Month Selection & Detailed Monthly Analysis --------------

    data['Month'] = data['Date'].dt.strftime('%B')
    available_months = sorted(data['Month'].unique(), key=lambda x: list(calendar.month_name).index(x))

    month = st.selectbox("📅 Select Month to Explore", available_months, key="month_select")
    filtered = data[data['Month'] == month].copy()

    # Optional keyword search
    search_keyword = st.text_input("🔍 Search in Descriptions (optional)")
    if search_keyword:
        filtered = filtered[filtered['Description'].str.lower().str.contains(search_keyword.lower())]

    # Classification
    filtered['Spending Category'] = filtered['Description'].apply(
        lambda d: classify_expense(d, CATEGORY_KEYWORDS)
    )

    # Manual Tagging of Uncategorized
    uncat = filtered[filtered['Spending Category'] == 'Uncategorized']
    if not uncat.empty:
        st.subheader("🧩 Manually Tag Uncategorized Transactions")
        for i, row in uncat.iterrows():
            new_cat = st.selectbox(
                f"{row['Date'].date()} - {row['Description'][:40]}...",
                options=list(CATEGORY_KEYWORDS.keys()) + ["Other"],
                key=f"tag_{i}"
            )
            filtered.at[i, 'Spending Category'] = new_cat

    # Show Transactions
    st.subheader(f"📄 Transactions in {month}")
    st.dataframe(filtered[['Date', 'Description', 'Amount', 'Category', 'Spending Category']])

    # Spending Breakdown
    st.subheader(f"📊 Spending Breakdown for {month}")
    spend = filtered[filtered['Category'] == 'Debit']
    
    if not spend.empty:
        summary = spend.groupby('Spending Category')['Amount'].sum().reset_index()
        summary['Percentage'] = 100 * summary['Amount'] / summary['Amount'].sum()
        st.dataframe(summary.style.format({"Amount": "J${:,.2f}", "Percentage": "{:.2f}%"}))

        fig = px.pie(
            summary,
            names='Spending Category',
            values='Amount',
            title=f"{month} Spending Distribution",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

        # Budget vs Actual with improved data handling
        st.subheader(f"📏 Budget vs. Actual - {month}")
        budget_df = pd.DataFrame.from_dict(MONTHLY_BUDGETS, orient='index', columns=['Budget']).reset_index()
        budget_df.rename(columns={'index': 'Spending Category'}, inplace=True)
        comparison = pd.merge(budget_df, summary, on='Spending Category', how='left')
        comparison['Amount'] = comparison['Amount'].fillna(0)
        comparison['Difference'] = comparison['Budget'] - comparison['Amount']
        comparison['Status'] = comparison.apply(
            lambda row: "⚠️ Over Budget" if row['Amount'] > row['Budget'] else "✅ Within Budget", axis=1
        )

        st.dataframe(
            comparison.style.format({"Budget": "J${:,.0f}", "Amount": "J${:,.0f}", "Difference": "J${:,.0f}"})
            .apply(lambda s: ['color: red;' if '⚠️' in str(v) else 'color: green;' for v in s], subset=['Status'])
        )

        # Create chart data in long format to avoid shape errors
        budget_chart_data = []
        for _, row in comparison.iterrows():
            budget_chart_data.extend([
                {'Spending Category': row['Spending Category'], 'Type': 'Budget', 'Amount': row['Budget']},
                {'Spending Category': row['Spending Category'], 'Type': 'Actual', 'Amount': row['Amount']}
            ])
        
        budget_chart_df = pd.DataFrame(budget_chart_data)

        fig = px.bar(
            budget_chart_df,
            x='Spending Category',
            y='Amount',
            color='Type',
            barmode='group',
            title="Budget vs. Actual Spending by Category",
            labels={"Amount": "J$", "Type": "Type"},
            text='Amount'
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="J$")
        st.plotly_chart(fig, use_container_width=True)

        # Savings Goal Check
        st.subheader(f"🎯 Savings Goal Check for {month}")

        total_income = filtered[filtered['Category'] == 'Credit']['Amount'].sum()
        total_spending = filtered[filtered['Category'] == 'Debit']['Amount'].sum()
        actual_savings = total_income - total_spending

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💰 Total Income", f"J${total_income:,.2f}")
        with col2:
            st.metric("💸 Total Spending", f"J${total_spending:,.2f}")
        with col3:
            st.metric("💰 Actual Savings", f"J${actual_savings:,.2f}")

        st.markdown(f"**🎯 Savings Goal:** J${SAVINGS_GOAL:,.2f}")

        if actual_savings >= SAVINGS_GOAL:
            st.success(f"🎉 Congratulations! You've exceeded your savings goal by J${actual_savings - SAVINGS_GOAL:,.2f}!")
        else:
            st.warning(f"📉 You are J${SAVINGS_GOAL - actual_savings:,.2f} short of your savings goal.")

        # Email alert trigger (enhanced)
        if enable_email and notify_email and sender_email and sender_password:
            overspent = comparison[comparison['Amount'] > comparison['Budget']]
            savings_missed = actual_savings < SAVINGS_GOAL
            
            if not overspent.empty or savings_missed:
                st.subheader("📧 Email Alerts")
                
                # Create alert message
                alert_messages = []
                if not overspent.empty:
                    alert_messages.append("**Overspending Alert:**")
                    for _, row in overspent.iterrows():
                        alert_messages.append(f"• {row['Spending Category']}: Spent J${row['Amount']:.2f} (Budget: J${row['Budget']:.2f})")
                
                if savings_missed:
                    alert_messages.append(f"\n**Savings Goal Alert:**")
                    alert_messages.append(f"• Goal: J${SAVINGS_GOAL:,.2f}, Actual: J${actual_savings:,.2f}")
                    alert_messages.append(f"• Shortfall: J${SAVINGS_GOAL - actual_savings:,.2f}")
                
                preview_body = f"Finance Alert for {month}\n\n" + "\n".join(alert_messages)
                
                st.text_area("Email Preview:", value=preview_body, height=150)
                
                if st.button("📤 Send Alert Email"):
                    with st.spinner("Sending email..."):
                        subject = f"💰 Finance Alert: {month} Budget Review"
                        sent = send_email_alert(
                            receiver_email=notify_email,
                            subject=subject,
                            body=preview_body,
                            sender_email=sender_email,
                            sender_password=sender_password,
                            smtp_server=smtp_server,
                            smtp_port=smtp_port
                        )
                        if sent:
                            st.success("✅ Email sent successfully!")

        # Export Reports
        st.subheader("📤 Export Reports")

        report_text = f"Finance Report - {month}\n{'='*50}\n\n"
        report_text += "TRANSACTIONS:\n" + "-"*20 + "\n"
        for idx, row in filtered.iterrows():
            report_text += f"{row['Date'].date()} | {row['Description']} | J${row['Amount']:,.2f} | {row['Category']} | {row['Spending Category']}\n"

        report_text += f"\nSPENDING SUMMARY:\n" + "-"*20 + "\n"
        for idx, row in summary.iterrows():
            report_text += f"{row['Spending Category']}: J${row['Amount']:,.2f} ({row['Percentage']:.2f}%)\n"

        report_text += f"\nBUDGET vs ACTUAL:\n" + "-"*20 + "\n"
        for idx, row in comparison.iterrows():
            status_text = "OVER BUDGET" if row['Amount'] > row['Budget'] else "Within Budget"
            report_text += f"{row['Spending Category']}: Budget J${row['Budget']:,.2f}, Actual J${row['Amount']:,.2f} ({status_text})\n"

        report_text += f"\nSAVINGS SUMMARY:\n" + "-"*20 + "\n"
        report_text += f"Total Income: J${total_income:,.2f}\n"
        report_text += f"Total Spending: J${total_spending:,.2f}\n"
        report_text += f"Actual Savings: J${actual_savings:,.2f}\n"
        report_text += f"Savings Goal: J${SAVINGS_GOAL:,.2f}\n"
        goal_status = "MET" if actual_savings >= SAVINGS_GOAL else f"MISSED by J${SAVINGS_GOAL - actual_savings:,.2f}"
        report_text += f"Goal Status: {goal_status}\n"

        export_format = st.selectbox("Select export format", options=["Excel", "PDF"])

        if st.button("📥 Download Report"):
            if export_format == "Excel":
                excel_bytes = export_to_excel(filtered)
                st.download_button(
                    label="📊 Download Excel File",
                    data=excel_bytes,
                    file_name=f"Finance_Report_{month}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                pdf_bytes = export_to_pdf(report_text)
                st.download_button(
                    label="📄 Download PDF File",
                    data=pdf_bytes,
                    file_name=f"Finance_Report_{month}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info(f"No spending transactions found for {month}")

elif option == "📅 Budget Planner":
    st.markdown("You selected **Budget Planner**.")
    import pandas as pd
    import plotly.express as px

    st.title("📋 Budget Dashboard")

    # Note about the Excel file
    st.info("💡 **Note:** The Budget Planner requires the Excel file to be accessible. Upload your budget Excel file or update the file path in the code.")

    try:
        # This would need to be updated with the actual file path or file upload
        st.warning("⚠️ Budget Excel file not found. Please upload your budget file or update the file path.")
        
        # Placeholder for budget planner functionality
        st.subheader("📊 Budget Categories")
        
        # Sample budget data for demonstration
        sample_budget = {
            'Category': ['Food', 'Utilities', 'Transport', 'Entertainment', 'Savings'],
            'Budgeted': [15000, 8000, 6000, 4000, 10000],
            'Actual': [12000, 8500, 5500, 3500, 12000],
            'Difference': [3000, -500, 500, 500, -2000]
        }
        
        sample_df = pd.DataFrame(sample_budget)
        st.dataframe(sample_df)
        
        fig = px.bar(
            sample_df,
            x='Category',
            y=['Budgeted', 'Actual'],
            barmode='group',
            title="Budget vs Actual Spending"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading budget data: {e}")

elif option == "🌐 Network Analysis":
    st.markdown("You selected **Network Analysis**.")
    st.info("🚧 Network Analysis feature is coming soon! This will show spending patterns and transaction relationships.")
    
    # Placeholder content
    st.subheader("🔮 Coming Soon Features:")
    st.markdown("""
    - **Transaction Network Visualization**: See how your money flows between categories
    - **Spending Pattern Analysis**: Identify unusual spending behaviors
    - **Merchant Network**: Visualize your most frequent merchants
    - **Seasonal Spending Trends**: Track how your spending changes over time
    """)
