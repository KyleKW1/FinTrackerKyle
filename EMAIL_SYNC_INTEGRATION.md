# EMAIL_SYNC_INTEGRATION.md

## Gmail Banking Sync — Integration Guide

Four steps to wire this into your existing Finance Hub.

---

### Step 1 — Run the SQL on your Aiven database

Connect to your MySQL database and run `setup_email_tables.sql`. You can do this once via any MySQL client (TablePlus, DBeaver, the Aiven console, or `mysql` CLI).

```bash
mysql -h mysql-11beff9b-kamarwatson36-874b.g.aivencloud.com \
      -P 11510 -u avnadmin -p defaultdb < setup_email_tables.sql
```

Or paste the SQL directly into the Aiven web console query editor.

---

### Step 2 — Add `email_scanner.py` to your project root

Copy `email_scanner.py` into the same folder as `app.py`. No changes needed.

---

### Step 3 — Patch `database.py`

Open `database.py` and paste the contents of `database_email_additions.py` **at the bottom**, before `if __name__ == "__main__":` (if that block exists).

The new functions added are:
- `save_email_sync_settings()`
- `get_email_sync_settings()`
- `update_email_last_sync()`
- `save_email_transactions()`
- `get_email_transactions()`
- `delete_all_email_transactions()`

---

### Step 4 — Replace `data_loader.py`

Replace your entire `data_loader.py` with the new one provided. Key change: `load_all_user_data()` now also calls `get_email_transactions()` and merges those rows into the same DataFrame. Because **every page** in Finance Hub calls `load_all_user_data()`, email transactions automatically appear in:

- Spending Analysis (charts, pie, category breakdown)
- Budget vs Actual
- Financial Time Machine (projections use the richer dataset)
- Network Analysis (merchant heatmaps, timelines)
- Subscription Tracker (recurring detection)
- Possible Savings (round-up calculations)

No other page code needs changing.

---

### Step 5 — Add Gmail Sync to `spending_analysis.py`

At the **top** of `spending_analysis.py`, add these imports:

```python
from email_scanner import sync_gmail_transactions
from database import (save_email_sync_settings, get_email_sync_settings,
                      delete_all_email_transactions)
```

Copy the `render_gmail_sync_section()` function from `gmail_sync_section.py` into `spending_analysis.py`.

Then inside `spending_analysis_page()`, find the section that shows "Uploaded Files" and add one line after it:

```python
# ── category editor ──────────────────────────
st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
render_category_editor()

# ── Gmail sync  ←── ADD THIS LINE
render_gmail_sync_section()

# ── visualisations ───────────────────────────
```

---

### Step 6 — Update `requirements.txt`

No new packages needed — `imaplib` and `email` are Python standard library modules.

---

### How it works end-to-end

```
User clicks "Sync now"
  → email_scanner.py connects via Gmail IMAP
  → Searches for emails with banking keywords (last N days)
  → For each email: extracts amount, merchant, date, debit/credit
  → Saves new rows to email_transactions table (duplicates ignored)
  → Clears data cache

Next page load
  → load_all_user_data() fetches file transactions + email transactions
  → Combines and deduplicates (file wins over email for same tx)
  → All pages show the merged data automatically
```

---

### Tips for your friend

- His bank must send **email alerts** for each transaction. Most Jamaican banks do this — he just needs to enable it in his online banking settings (usually under "Notifications" or "Alerts").
- He should use his **personal Gmail** that receives the bank alerts, not the app's sender email.
- Gmail App Passwords require 2-Step Verification to be turned on first.
- The sync is **one-directional** — it only reads emails, never sends or deletes anything.
- Transactions already in uploaded PDF/CSV files won't be double-counted (deduplication by date + description + amount).
