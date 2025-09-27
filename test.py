import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
import smtplib
import datetime
import os
import tempfile
from email.message import EmailMessage
from io import BytesIO
from PIL import Image
import pdfplumber
from fpdf import FPDF

# Attempt to import pdfkit but don't fail if it's not there
try:
    import pdfkit
    PDFKIT_INSTALLED = True
except ImportError:
    PDFKIT_INSTALLED = False

# --- Page Config (MUST be the first Streamlit command) ---
st.set_page_config(page_title="Finance Hub", layout="wide")


# --- Main App Interface ---
st.title("💼 Welcome to Finance Hub")
st.markdown("Choose a feature below to get started:")

option = st.radio(
    "What would you like to do?",
    ["📊 Spending Analysis", "📅 Budget Planner", "🌐 Network Analysis"],
    index=0
)

# --- SPENDING ANALYSIS FEATURE ---
if option == "📊 Spending Analysis":

    # ---------- Functions for Spending Analysis ----------
    @st.cache_data
    def process_csv(file):
        try:
            df = pd.read_csv(file)
            # Standardize column names
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
            st.error(f"Error processing CSV file: {e}")
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
                        # This logic is specific to a PDF format and may need adjustment
                        if "POS" in line or "TRF" in line or "PURCHASE" in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                date = parts[0]
                                desc = " ".join(parts[1:-2])
                                amt_str = parts[-2].replace('J$', '').replace(',', '')
                                cat = 'Debit' if '-' in amt_str else 'Credit'
                                data.append([date, desc, abs(float(amt_str)), cat])
            df = pd.DataFrame(data, columns=['Date', 'Description', 'Amount', 'Category'])
            return df
        except Exception as e:
            st.error(f"Error processing PDF file: {e}")
            return pd.DataFrame()

    def classify_expense(description, mapping):
        desc = description.lower()
        for category, keywords in mapping.items():
            for kw in keywords:
                if kw in desc:
                    return category
        return 'Uncategorized'

    def send_email_alert(receiver_email, subject, body, sender_email, sender_password, smtp_server, smtp_port=587):
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = receiver_email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            return True
        except Exception as e:
            st.error(f"Failed to send email: {e}")
            return False

    def export_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        # No writer.save() needed, the 'with' statement handles it.
        processed_data = output.getvalue()
        return processed_data

    def export_to_pdf(report_text):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        # Process one line at a time to create the PDF
        for line in report_text.split('\n'):
            # Encode each line to avoid errors with special characters
            cleaned_line = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, cleaned_line)
        return pdf.output(dest='S').encode('latin-1')

    # ---------- App Logic for Spending Analysis ----------
    st.header("Personal Finance Tracker")

    uploaded_files = st.file_uploader(
        "Upload your transaction files (CSV or PDF)",
        type=["csv", "pdf"],
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("Upload your bank statements to get started.")
        st.stop()

    data_frames = []
    for file in uploaded_files:
        if file.name.lower().endswith(".csv"):
            data_frames.append(process_csv(file))
        elif file.name.lower().endswith(".pdf"):
            data_frames.append(process_pdf(file))

    data = pd.concat(data_frames, ignore_index=True)

    if data.empty:
        st.warning("Could not extract any transaction data from the uploaded files.")
        st.stop()

    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    data.dropna(subset=['Date'], inplace=True)

    # --- Sidebar for Settings ---
    st.sidebar.header("🗂️ Customize & Configure")
    
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
        with st.sidebar.expander(f"{category} Keywords"):
            kw_text = st.text_area(f"Keywords for {category}", ", ".join(keywords), key=f"kw_{category}")
            CATEGORY_KEYWORDS[category] = [kw.strip().lower() for kw in kw_text.split(",") if kw.strip()]

    st.sidebar.markdown("### 💸 Set Monthly Budgets (J$)")
    MONTHLY_BUDGETS = {
        cat: st.sidebar.number_input(f"Budget for {cat}", min_value=0, value=10000, step=500, key=f"budget_{cat}")
        for cat in CATEGORY_KEYWORDS if cat != "Income"
    }
    
    st.sidebar.markdown("### 🎯 Set Monthly Savings Goal (J$)")
    SAVINGS_GOAL = st.sidebar.number_input("Savings Goal Amount (J$)", min_value=0, value=5000, step=500)

    # --- Main Page Content ---
    data['Month'] = data['Date'].dt.strftime('%B')
    available_months = sorted(data['Month'].unique(), key=lambda m: list(calendar.month_name).index(m))
    
    month = st.selectbox("📅 Select Month to Explore", available_months)
    filtered = data[data['Month'] == month].copy()

    # Classification and manual tagging
    filtered['Spending Category'] = filtered['Description'].apply(lambda d: classify_expense(d, CATEGORY_KEYWORDS))
    
    uncategorized_transactions = filtered[filtered['Spending Category'] == 'Uncategorized']
    if not uncategorized_transactions.empty:
        st.subheader("🧩 Manually Tag Uncategorized Transactions")
        for i, row in uncategorized_transactions.iterrows():
            new_cat = st.selectbox(
                f"{row['Date'].date()} - {row['Description'][:40]}...",
                options=list(CATEGORY_KEYWORDS.keys()) + ["Other"],
                key=f"tag_{i}"
            )
            filtered.at[i, 'Spending Category'] = new_cat

    # Display charts and data for the selected month
    st.subheader(f"📈 Analysis for {month}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Spending Breakdown")
        spend_df = filtered[filtered['Category'] == 'Debit']
        summary = spend_df.groupby('Spending Category')['Amount'].sum().reset_index()
        fig_pie = px.pie(summary, names='Spending Category', values='Amount', title=f"Spending Distribution", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("#### Budget vs. Actual")
        budget_df = pd.DataFrame(MONTHLY_BUDGETS.items(), columns=['Spending Category', 'Budget'])
        comparison = pd.merge(budget_df, summary, on='Spending Category', how='left').fillna(0)
        comparison['Difference'] = comparison['Budget'] - comparison['Amount']
        fig_bar = px.bar(comparison, x='Spending Category', y=['Budget', 'Amount'], barmode='group', title="Budget vs. Actual Spending")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📄 Transactions")
    st.dataframe(filtered[['Date', 'Description', 'Amount', 'Category', 'Spending Category']])

    # --- Export Section ---
    st.subheader("📤 Export Report")
    report_text = f"Finance Report for {month}\n\n--- Transactions ---\n" + filtered.to_string(index=False)
    
    export_format = st.radio("Select export format", ["Excel", "PDF"], horizontal=True)

    if export_format == "Excel":
        excel_bytes = export_to_excel(filtered)
        st.download_button(
            label="📥 Download Excel Report",
            data=excel_bytes,
            file_name=f"Finance_Report_{month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        pdf_bytes = export_to_pdf(report_text)
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"Finance_Report_{month}.pdf",
            mime="application/pdf"
        )

# --- BUDGET PLANNER FEATURE ---
elif option == "📅 Budget Planner":
    st.header("📋 Budget Planner Dashboard")

    # Use a file uploader instead of a hardcoded path
    uploaded_budget_file = st.file_uploader(
        "Upload your Budget Planner Excel file", type=["xlsx"]
    )

    if uploaded_budget_file:
        xls = pd.ExcelFile(uploaded_budget_file)
        
        view_option = st.radio(
            "Choose a view:",
            ["Budget Summary", "Income Breakdown", "Raw Transactions"],
            horizontal=True
        )

        if view_option == "Budget Summary" and "Budget" in xls.sheet_names:
            st.subheader("📊 Monthly Budget Summary")
            budget_df = xls.parse("Budget", skiprows=1)
            budget_df.dropna(subset=["CATEGORIES"], inplace=True)
            st.dataframe(budget_df)
            if "YEARLY TOTAL" in budget_df.columns:
                fig = px.bar(budget_df, x="CATEGORIES", y="YEARLY TOTAL", title="Total Yearly Budget by Category")
                st.plotly_chart(fig, use_container_width=True)

        elif view_option == "Income Breakdown" and "Income" in xls.sheet_names:
            st.subheader("💰 Income Breakdown by Source")
            income_df = xls.parse("Income", header=1)
            income_df.dropna(how='all', inplace=True)
            st.dataframe(income_df)

        elif view_option == "Raw Transactions" and "Data" in xls.sheet_names:
            st.subheader("📄 Raw Transactions Table")
            data_df = xls.parse("Data")
            st.dataframe(data_df)
    else:
        st.info("Please upload an Excel file to begin planning your budget.")

# --- NETWORK ANALYSIS FEATURE (Placeholder) ---
elif option == "🌐 Network Analysis":
    st.header("🌐 Network Analysis")
    st.info("This feature is under construction. Check back later!")
