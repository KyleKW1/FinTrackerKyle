# email_scanner.py
"""
Finance Hub — Universal Banking Email Scanner
=============================================
Supports Gmail, Yahoo, Outlook, Hotmail, iCloud and any IMAP provider.
Multiple accounts per user are supported.

Key improvements over v1:
  - Multi-provider IMAP routing (Gmail, Yahoo, Outlook, iCloud, custom)
  - Multiple email accounts per user (reads from email_accounts table)
  - Vastly improved merchant extraction (NCB / JMMB / Scotia alert formats)
  - Cleaner amount extraction with J$ / JMD / USD awareness
  - Debit/credit classification tuned for Jamaican bank alert wording
  - Budget-match hint attached to every parsed transaction
  - Subscription-likelihood score so the tracker has richer data
"""

import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime, timedelta
from typing import Optional

# ── Provider IMAP routing ─────────────────────────────────────────────────
IMAP_SERVERS: dict[str, tuple[str, int]] = {
    # Google
    "gmail.com":          ("imap.gmail.com",            993),
    "googlemail.com":     ("imap.gmail.com",            993),
    # Yahoo / Verizon Media
    "yahoo.com":          ("imap.mail.yahoo.com",       993),
    "yahoo.co.uk":        ("imap.mail.yahoo.com",       993),
    "yahoo.com.jm":       ("imap.mail.yahoo.com",       993),
    "ymail.com":          ("imap.mail.yahoo.com",       993),
    "rocketmail.com":     ("imap.mail.yahoo.com",       993),
    # Microsoft
    "outlook.com":        ("outlook.office365.com",     993),
    "hotmail.com":        ("outlook.office365.com",     993),
    "live.com":           ("outlook.office365.com",     993),
    "msn.com":            ("outlook.office365.com",     993),
    # Apple
    "icloud.com":         ("imap.mail.me.com",          993),
    "me.com":             ("imap.mail.me.com",          993),
    "mac.com":            ("imap.mail.me.com",          993),
    # Jamaican / Caribbean ISPs
    "cwjamaica.com":      ("mail.cwjamaica.com",        993),
    "flowjamaica.com":    ("mail.flowjamaica.com",      993),
}

def _imap_server_for(email_address: str) -> tuple[str, int]:
    """Return (host, port) for the given email address domain."""
    domain = email_address.split("@")[-1].lower().strip()
    return IMAP_SERVERS.get(domain, ("imap.gmail.com", 993))  # safe fallback


# ── Bank signal patterns ──────────────────────────────────────────────────
# Senders / subjects that indicate a bank transaction alert
BANK_SENDER_SIGNALS = [
    "ncb", "jmmb", "scotiabank", "sagicor", "cibc", "firstglobal",
    "jnbank", "vmbs", "rbtt", "bns", "nationwidejm", "carib",
    "noreply@jncb", "alerts@", "notify@", "notification@",
    "transactions@", "donotreply@",
]
BANK_SUBJECT_SIGNALS = [
    "transaction alert", "account alert", "debit alert", "credit alert",
    "transaction notification", "account activity", "account debit",
    "account credit", "bank alert", "banking alert", "your account",
    "was debited", "was credited", "withdrawal alert", "deposit alert",
    "payment alert", "transfer alert", "purchase alert",
    # NCB-specific
    "ncb alert", "your ncb", "ncb transaction",
    # JMMB-specific
    "jmmb alert", "your jmmb",
    # Scotia
    "scotiabank alert", "scotia alert",
]

# ── Amount patterns (ordered: most-specific first) ────────────────────────
# Group 1 always = numeric amount string (with commas, optional decimals)
AMOUNT_PATTERNS = [
    # J$ / JMD explicit
    r"J\$\s*([\d,]+\.?\d*)",
    r"JMD\s*([\d,]+\.?\d*)",
    # "amount of J$" or "amount: 1,500.00"
    r"amount\s+of\s+(?:J\$|JMD|\$)?\s*([\d,]+\.?\d*)",
    r"amount[:\s]+(?:J\$|JMD|\$)?\s*([\d,]+\.?\d*)",
    # "debited/credited ... 1,500.00"
    r"(?:debited|credited|deducted|withdrawn)\s+(?:J\$|JMD|\$)?\s*([\d,]+\.?\d*)",
    # trailing JMD / J$
    r"([\d,]+\.\d{2})\s*(?:JMD|J\$)",
    # generic $ amount (fallback)
    r"\$\s*([\d,]+\.?\d{2})",
    # bare number with 2 decimal places — very last resort
    r"\b([\d,]{3,}\.[\d]{2})\b",
]

# ── Merchant patterns (ordered: most-specific first) ──────────────────────
MERCHANT_PATTERNS = [
    # "at MERCHANT NAME on" — most common in NCB alerts
    r"\bat\s+([A-Z0-9][A-Z0-9\s&\-\'\./]{2,50}?)(?:\s+on\b|\s+dated\b|\s+for\b|\s*[,\.\n\r])",
    # "merchant: NAME"
    r"merchant[:\s]+([^\n\r,\.]{3,60})",
    # "POS purchase at NAME" or "purchase at NAME"
    r"(?:pos\s+purchase|purchase)\s+(?:at\s+)?([^\n\r,\.]{3,60})",
    # "payment to NAME"
    r"payment\s+to\s+([^\n\r,\.]{3,60})",
    # "transfer to NAME"
    r"(?:transfer\s+to|sent\s+to)\s+([^\n\r,\.]{3,60})",
    # "description: NAME"
    r"description[:\s]+([^\n\r,\.]{3,80})",
    # "reference: NAME"
    r"reference[:\s]+([^\n\r,\.]{3,60})",
    # NCB: "Your account ... was debited for MERCHANT"
    r"debited\s+(?:for|at)\s+([A-Z0-9][A-Z0-9\s&\-\'\./]{2,50}?)(?:\s+on\b|\s+[,\.\n\r]|$)",
]

# Words that indicate a debit / withdrawal
DEBIT_WORDS = {
    "debit", "debited", "withdrawal", "withdraw", "withdrawn",
    "purchase", "payment", "charged", "spent", "dr", "pos",
    "deducted", "deduction", "paid",
}
# Words that indicate a credit / deposit
CREDIT_WORDS = {
    "credit", "credited", "deposit", "deposited", "received",
    "transfer in", "salary", "refund", "cr", "incoming",
    "remittance", "remitly", "western union",
}

# ── Spending-category keyword map (mirrors config.py DEFAULT_CATEGORY_MAPPING)
# Used to attach a budget-match hint to each parsed transaction.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Food":                   ["juici", "kfc", "restaurant", "burger", "pizza",
                               "subway", "mcdonald", "starbucks", "cafe", "bakery",
                               "jerk", "eatery", "diner", "food court"],
    "Grocery":                ["hi-lo", "supermarket", "wholesale", "grocery",
                               "market", "walmart", "costco", "shoppers fair",
                               "progressive", "megamart", "pricesmart"],
    "Utilities":              ["jps", "nwc", "flow", "internet", "light", "water",
                               "electric", "cable", "wifi", "bill payment",
                               "digicel", "lime", "c&w"],
    "Transport":              ["uber", "ubr", "taxi", "gas", "shell", "parking",
                               "lyft", "bus", "knutsford", "petcom", "total",
                               "esso", "texaco", "gogas"],
    "Retail & Entertainment": ["amazon", "paypal", "apple", "google play",
                               "netflix", "spotify", "disney", "hulu",
                               "macy", "duty free", "online purchase"],
    "Home Improvement":       ["lumber depot", "hardware", "home depot",
                               "paint", "ace hardware"],
    "Miscellaneous":          ["atm", "abm", "fee", "charge", "gct", "tax",
                               "insurance", "premium"],
}

# ── Subscription keywords — recurring-charge detection ───────────────────
SUBSCRIPTION_KEYWORDS = [
    "netflix", "spotify", "disney", "hulu", "apple", "google",
    "amazon prime", "youtube premium", "microsoft", "adobe",
    "dropbox", "icloud", "linkedin", "zoom", "slack", "github",
    "canva", "notion", "chatgpt", "openai", "vpn", "norton",
    "duolingo", "bumble", "tinder", "digicel", "flow",
    "monthly", "subscription", "recurring", "auto-renew",
]


# ═════════════════════════════════════════════════════════════════════════════
# CONNECTION
# ═════════════════════════════════════════════════════════════════════════════

def connect_email(email_address: str, app_password: str):
    """
    Open an authenticated IMAP connection for any supported provider.
    Returns an imaplib.IMAP4_SSL object, or None on failure.
    """
    host, port = _imap_server_for(email_address)
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(email_address.strip(), app_password.strip())
        return mail
    except imaplib.IMAP4.error:
        return None
    except Exception:
        return None


# Keep legacy name for backwards compatibility
connect_gmail = connect_email


# ═════════════════════════════════════════════════════════════════════════════
# EMAIL FETCHING
# ═════════════════════════════════════════════════════════════════════════════

def _imap_search(mail, criteria: str) -> list:
    """Safe IMAP SEARCH — returns list of byte message IDs."""
    try:
        status, data = mail.search(None, criteria)
        if status == "OK" and data[0]:
            return data[0].split()
    except Exception:
        pass
    return []


def fetch_banking_email_ids(mail, days: int = 90) -> list:
    """
    Return a de-duplicated list of IMAP message IDs that look like
    bank transaction alerts, searching by sender domain and subject keywords.
    """
    mail.select("INBOX")
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

    seen: set = set()

    # Subject-based searches
    subject_terms = [
        "transaction", "debit", "credit", "alert",
        "account activity", "bank", "withdrawal", "deposit",
        "payment", "purchase",
    ]
    for term in subject_terms:
        for mid in _imap_search(mail, f'(SINCE "{since}" SUBJECT "{term}")'):
            seen.add(mid)

    # Sender-based searches (common Jamaican / Caribbean banks)
    sender_terms = [
        "ncb", "jmmb", "scotiabank", "sagicor",
        "cibc", "jnbank", "firstglobal", "vmbs",
        "alerts", "notify", "noreply",
    ]
    for term in sender_terms:
        for mid in _imap_search(mail, f'(SINCE "{since}" FROM "{term}")'):
            seen.add(mid)

    return list(seen)


# ═════════════════════════════════════════════════════════════════════════════
# EMAIL BODY / HEADER HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _decode_header_value(value: str) -> str:
    """Decode RFC 2047-encoded email header into a plain string."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _get_body(msg) -> str:
    """
    Extract the best plain-text representation of an email message.
    Prefers text/plain; falls back to HTML with tags stripped.
    """
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if ctype == "text/plain":
                    body += text + "\n"
                elif ctype == "text/html" and not body:
                    # Strip HTML tags for fallback
                    body += re.sub(r"<[^>]+>", " ", text) + "\n"
            except Exception:
                continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())

    # Collapse excessive whitespace
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = re.sub(r" {2,}", " ", body)
    return body.strip()


# ═════════════════════════════════════════════════════════════════════════════
# TRANSACTION EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════

def _is_banking_email(subject: str, sender: str, body: str) -> bool:
    """Return True if the email appears to be a bank transaction alert."""
    combined = f"{subject} {sender} {body[:600]}".lower()
    for sig in BANK_SENDER_SIGNALS:
        if sig in combined:
            return True
    for sig in BANK_SUBJECT_SIGNALS:
        if sig in combined:
            return True
    return False


def _extract_amount(text: str) -> Optional[float]:
    """
    Find the transaction amount in the email text.
    Returns a positive float or None.
    """
    for pattern in AMOUNT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                # Sanity range: J$1 – J$10,000,000
                if 1.0 <= val <= 10_000_000.0:
                    return val
            except ValueError:
                continue
    return None


def _extract_category(text: str) -> str:
    """
    Determine whether this is a Debit or Credit transaction.
    Checks for debit/credit keywords; defaults to Debit.
    """
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))

    credit_hits = words & CREDIT_WORDS
    debit_hits  = words & DEBIT_WORDS

    if credit_hits and not debit_hits:
        return "Credit"
    if debit_hits:
        return "Debit"

    # Phrase-level check (handles "transfer in", "was credited", etc.)
    for phrase in ["transfer in", "was credited", "deposit received",
                   "salary received", "remittance received"]:
        if phrase in lower:
            return "Credit"

    return "Debit"


def _extract_merchant(subject: str, body: str) -> str:
    """
    Try to extract a clean merchant / payee name from the email.
    Falls back to a cleaned version of the subject line.
    """
    full_text = f"{subject}\n{body}"

    for pattern in MERCHANT_PATTERNS:
        m = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
        if m:
            raw = m.group(1).strip().rstrip(".,;:- ")
            # Drop very short or generic matches
            if 3 < len(raw) < 120 and raw.lower() not in {
                "your", "the", "account", "bank", "card", "you"
            }:
                # Title-case if all-caps
                if raw.isupper():
                    raw = raw.title()
                return raw

    # Fallback: strip boilerplate words from the subject
    clean = re.sub(
        r"\b(transaction|alert|notification|bank|account|your|has\s+been|"
        r"debited|credited|debit|credit|ncb|jmmb|scotiabank|sagicor)\b",
        "",
        subject,
        flags=re.IGNORECASE,
    ).strip(" -:,.")
    if clean:
        if clean.isupper():
            clean = clean.title()
        return clean[:100]

    return "Bank Transaction"


def _guess_spending_category(merchant: str) -> str:
    """
    Return the best-matching spending category for a merchant name.
    Used to attach a budget-match hint to email-parsed transactions.
    """
    merchant_lower = merchant.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in merchant_lower:
                return category
    return "Other"


def _subscription_likelihood(merchant: str, description: str) -> bool:
    """
    Return True if the merchant/description looks like a subscription charge.
    This flag is stored so the Subscription Tracker can surface it.
    """
    combined = f"{merchant} {description}".lower()
    for kw in SUBSCRIPTION_KEYWORDS:
        if kw in combined:
            return True
    return False


def _parse_date(date_str: str):
    """
    Try multiple date formats common in email headers; fall back to today.
    Returns a datetime.date object.
    """
    # Strip timezone name after offset if present (e.g. "GMT", "EST")
    date_str = re.sub(r"\s+\([A-Z]{2,5}\)\s*$", "", date_str.strip())

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:35], fmt).date()
        except (ValueError, TypeError):
            continue

    # Last resort: try just YYYY-MM-DD prefix
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime.today().date()


def extract_transaction_from_email(
    subject: str,
    sender: str,
    body: str,
    date_str: str,
) -> Optional[dict]:
    """
    Parse a single email into a transaction dict.
    Returns None if the email does not look like a bank alert
    or if no amount can be found.

    Returned dict keys:
        date, description, amount, category,
        spending_category, is_subscription,
        subject, sender
    """
    if not _is_banking_email(subject, sender, body):
        return None

    full_text = f"{subject}\n{body}"
    amount = _extract_amount(full_text)
    if not amount:
        return None

    category    = _extract_category(full_text)
    merchant    = _extract_merchant(subject, body)
    spend_cat   = _guess_spending_category(merchant) if category == "Debit" else "Income"
    is_sub      = _subscription_likelihood(merchant, subject)

    return {
        "date":               _parse_date(date_str),
        "description":        merchant,
        "amount":             amount,
        "category":           category,           # "Debit" or "Credit"
        "spending_category":  spend_cat,           # matches budget categories
        "is_subscription":    is_sub,              # True → subscription tracker hint
        "subject":            subject[:200],
        "sender":             sender[:200],
    }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN SYNC — SINGLE ACCOUNT
# ═════════════════════════════════════════════════════════════════════════════

def sync_email_account(
    user_id: int,
    email_address: str,
    app_password: str,
    days: int = 90,
) -> tuple[int, Optional[str]]:
    """
    Connect to one email account, scan for bank alerts, save new transactions.

    Returns:
        (n_added, error_message_or_None)
    """
    from database import save_email_transactions, update_email_last_sync

    mail = connect_email(email_address, app_password)
    if mail is None:
        provider = email_address.split("@")[-1]
        return 0, (
            f"Could not connect to {provider}. "
            "Make sure you are using an App Password (not your regular password) "
            "and that IMAP access is enabled in your mail settings."
        )

    email_ids = fetch_banking_email_ids(mail, days)
    if not email_ids:
        mail.logout()
        update_email_last_sync(user_id)
        return 0, None

    parsed: list[dict] = []
    # Cap at 100 emails per sync to avoid Streamlit timeouts
    for eid in email_ids[:100]:
        try:
            status, data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_header_value(msg.get("Subject", ""))
            sender  = _decode_header_value(msg.get("From", ""))
            date_s  = str(msg.get("Date", ""))
            body    = _get_body(msg)

            tx = extract_transaction_from_email(subject, sender, body, date_s)
            if tx:
                parsed.append(tx)
        except Exception:
            continue

    mail.logout()

    if not parsed:
        update_email_last_sync(user_id)
        return 0, None

    added = save_email_transactions(user_id, parsed)
    update_email_last_sync(user_id)
    return added, None


# ═════════════════════════════════════════════════════════════════════════════
# MAIN SYNC — ALL ACCOUNTS FOR A USER
# ═════════════════════════════════════════════════════════════════════════════

def sync_all_accounts(user_id: int, days: int = 90) -> tuple[int, list[str]]:
    """
    Sync every email account saved for this user.
    Reads from email_accounts table (multi-account schema).

    Returns:
        (total_added, list_of_error_strings)
    """
    try:
        from database import get_all_email_accounts
        accounts = get_all_email_accounts(user_id)
    except ImportError:
        # Fall back to single-account schema if new DB functions not yet deployed
        try:
            from database import get_email_sync_settings
            cfg = get_email_sync_settings(user_id)
            if not cfg:
                return 0, ["No email accounts configured."]
            accounts = [{
                "email_address": cfg["gmail_address"],
                "app_password":  cfg["app_password"],
                "sync_days":     cfg.get("sync_days", days),
            }]
        except Exception as e:
            return 0, [str(e)]

    if not accounts:
        return 0, ["No email accounts configured."]

    total_added = 0
    errors: list[str] = []

    for acct in accounts:
        addr = acct.get("email_address") or acct.get("gmail_address", "")
        pwd  = acct.get("app_password", "")
        d    = acct.get("sync_days", days)
        if not addr or not pwd:
            continue
        n, err = sync_email_account(user_id, addr, pwd, d)
        total_added += n
        if err:
            errors.append(f"{addr}: {err}")

    return total_added, errors


# ── Legacy alias expected by existing code ────────────────────────────────
def sync_gmail_transactions(
    user_id: int,
    gmail_address: str,
    app_password: str,
    days: int = 90,
) -> tuple[int, Optional[str]]:
    """
    Backwards-compatible wrapper around sync_email_account.
    Existing calls in gmail_sync_section.py and subscription_tracker.py
    will continue to work without any changes.
    """
    return sync_email_account(user_id, gmail_address, app_password, days)
