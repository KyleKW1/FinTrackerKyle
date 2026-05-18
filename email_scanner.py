# email_scanner.py
"""
Gmail Banking Email Scanner — Finance Hub
Connects via IMAP, finds bank alert emails, extracts transactions automatically.
Supports NCB, JMMB, Scotia, Sagicor, CIBC, First Global and any bank
that sends transaction alerts to Gmail.
"""

import imaplib
import email
from email import policy
from email.header import decode_header
import re
from datetime import datetime, timedelta
import streamlit as st


# ── Recognised bank sender domains / subjects ─────────────────────────────
BANK_SIGNALS = [
    # Senders
    "ncb", "jmmb", "scotiabank", "sagicor", "cibc", "firstglobal",
    "jnbank", "vmbs", "rbtt", "bns",
    # Subject keywords
    "transaction alert", "account alert", "debit alert", "credit alert",
    "transaction notification", "account activity", "account debit",
    "account credit", "bank alert", "banking alert",
    "your account", "was debited", "was credited",
]

# ── Amount extraction patterns (J$ first, then generic) ──────────────────
AMOUNT_PATTERNS = [
    r"J\$\s*([0-9,]+\.?\d*)",
    r"JMD\s*([0-9,]+\.?\d*)",
    r"\$\s*([0-9,]+\.?\d{2})",
    r"amount[:\s]+(?:J\$|JMD|\$)?\s*([0-9,]+\.?\d*)",
    r"([0-9,]+\.\d{2})\s*(?:JMD|J\$)",
    r"(?:debit|credit|transfer)[ed\s]+(?:of\s+)?(?:J\$|JMD|\$)?\s*([0-9,]+\.?\d*)",
]

# ── Merchant / description patterns ──────────────────────────────────────
MERCHANT_PATTERNS = [
    r"at\s+([A-Z0-9][A-Z0-9\s&\-\'\.\/]+?)(?:\s+on\s|\s+dated|\s+for|\s*[,\.\n])",
    r"merchant[:\s]+([^\n\r,\.]{3,60})",
    r"(?:pos purchase|purchase)\s+(?:at\s+)?([^\n\r,\.]{3,60})",
    r"payment\s+to\s+([^\n\r,\.]{3,60})",
    r"(?:transfer to|sent to)\s+([^\n\r,\.]{3,60})",
    r"description[:\s]+([^\n\r,\.]{3,80})",
    r"reference[:\s]+([^\n\r,\.]{3,60})",
]

DEBIT_WORDS  = {"debit", "debited", "withdrawal", "withdraw", "purchase",
                "payment", "charged", "spent", "dr", "pos"}
CREDIT_WORDS = {"credit", "credited", "deposit", "deposited", "received",
                "transfer in", "salary", "refund", "cr", "incoming"}


# ── IMAP connection ───────────────────────────────────────────────────────

def connect_gmail(email_address: str, app_password: str):
    """Open an IMAP connection to Gmail. Returns mail object or None."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_address, app_password)
        return mail
    except imaplib.IMAP4.error as e:
        return None
    except Exception:
        return None


# ── Email fetching ────────────────────────────────────────────────────────

def _imap_search(mail, criteria: str):
    """Safe IMAP search returning a list of byte IDs."""
    try:
        status, data = mail.search(None, criteria)
        if status == "OK" and data[0]:
            return data[0].split()
    except Exception:
        pass
    return []


def fetch_banking_email_ids(mail, days: int = 90) -> list:
    """Return a de-duplicated list of IMAP message IDs that are likely bank alerts."""
    mail.select("INBOX")
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    searches = [
        f'(SINCE "{since}" SUBJECT "transaction")',
        f'(SINCE "{since}" SUBJECT "debit")',
        f'(SINCE "{since}" SUBJECT "credit")',
        f'(SINCE "{since}" SUBJECT "alert")',
        f'(SINCE "{since}" SUBJECT "account activity")',
        f'(SINCE "{since}" SUBJECT "bank")',
        f'(SINCE "{since}" FROM "ncb")',
        f'(SINCE "{since}" FROM "jmmb")',
        f'(SINCE "{since}" FROM "scotiabank")',
        f'(SINCE "{since}" FROM "sagicor")',
        f'(SINCE "{since}" FROM "cibc")',
        f'(SINCE "{since}" FROM "jnbank")',
        f'(SINCE "{since}" FROM "firstglobal")',
    ]
    seen = set()
    for q in searches:
        for mid in _imap_search(mail, q):
            seen.add(mid)
    return list(seen)


# ── Email body extraction ─────────────────────────────────────────────────

def _get_body(msg) -> str:
    """Extract plain text from an email.message.Message object."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                if ctype == "text/plain":
                    body += text + "\n"
                elif ctype == "text/html" and not body:
                    body += re.sub(r"<[^>]+>", " ", text) + "\n"
            except Exception:
                continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body


def _decode_header_value(value: str) -> str:
    """Decode encoded email headers."""
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


# ── Transaction extraction from a single email ────────────────────────────

def _is_banking_email(subject: str, sender: str, body: str) -> bool:
    text = f"{subject} {sender} {body[:500]}".lower()
    return any(sig in text for sig in BANK_SIGNALS)


def _extract_amount(text: str):
    for pattern in AMOUNT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                if 1 <= val <= 10_000_000:     # sanity range
                    return val
            except ValueError:
                continue
    return None


def _extract_category(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    if words & CREDIT_WORDS:
        return "Credit"
    return "Debit"


def _extract_description(subject: str, body: str) -> str:
    text = f"{subject}\n{body}"
    for pattern in MERCHANT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            desc = m.group(1).strip().rstrip(".,;")
            if 3 < len(desc) < 120:
                return desc
    # Fall back to subject (strip generic words)
    clean = re.sub(
        r"\b(transaction|alert|notification|bank|account|your|has been|"
        r"debited|credited|debit|credit)\b", "", subject, flags=re.IGNORECASE
    ).strip(" -:,.")
    return clean[:100] if clean else "Bank Transaction"


def _parse_date(date_str: str):
    """Try several date formats; fall back to today."""
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(date_str.strip()[:30], fmt).date()
        except Exception:
            continue
    # Try just first 10 chars as YYYY-MM-DD
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime.today().date()


def extract_transaction_from_email(subject: str, sender: str,
                                   body: str, date_str: str) -> dict | None:
    """
    Try to extract a single transaction dict from an email.
    Returns None if it doesn't look like a bank transaction email.
    """
    if not _is_banking_email(subject, sender, body):
        return None

    full = f"{subject}\n{body}"
    amount = _extract_amount(full)
    if not amount:
        return None

    return {
        "date":        _parse_date(date_str),
        "description": _extract_description(subject, body),
        "amount":      amount,
        "category":    _extract_category(full),
        "subject":     subject[:200],
        "sender":      sender[:200],
    }


# ── Main sync function ────────────────────────────────────────────────────

def sync_gmail_transactions(user_id: int, gmail_address: str,
                            app_password: str, days: int = 90):
    """
    Connect to Gmail, fetch bank alert emails, parse transactions,
    save new ones to the database.

    Returns (n_added: int, error_msg: str | None)
    """
    from database import save_email_transactions, update_email_last_sync

    mail = connect_gmail(gmail_address, app_password)
    if mail is None:
        return 0, (
            "Could not connect to Gmail. "
            "Make sure you're using a Gmail App Password "
            "(not your regular password) and that IMAP is enabled in Gmail settings."
        )

    email_ids = fetch_banking_email_ids(mail, days)
    if not email_ids:
        mail.logout()
        update_email_last_sync(user_id)
        return 0, None

    parsed = []
    for eid in email_ids[:75]:   # cap at 75 to avoid timeouts
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
