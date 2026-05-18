# gmail_sync_section.py  (updated — multi-account, multi-provider)
"""
Drop-in replacement for the original gmail_sync_section.py.

Changes vs v1:
  - Supports Gmail, Yahoo, Outlook, iCloud, and any IMAP provider
  - Users can add / remove multiple email accounts
  - Each account shows its own last-sync time and a per-account Sync button
  - "Sync All" button syncs every connected account in one click
  - Subscription-likelihood badge shown in the source breakdown
  - Falls back gracefully to the legacy single-account schema if the new
    email_accounts table hasn't been created yet
"""

import streamlit as st
from data_loader import clear_data_cache

# Provider display names for the UI hint
_PROVIDER_HINTS = {
    "gmail.com":    ("Gmail",   "Go to Google Account → Security → App passwords"),
    "yahoo.com":    ("Yahoo",   "Go to Yahoo Account Security → Generate app password"),
    "ymail.com":    ("Yahoo",   "Go to Yahoo Account Security → Generate app password"),
    "outlook.com":  ("Outlook", "Go to Microsoft Account → Security → App passwords"),
    "hotmail.com":  ("Outlook", "Go to Microsoft Account → Security → App passwords"),
    "live.com":     ("Outlook", "Go to Microsoft Account → Security → App passwords"),
    "icloud.com":   ("iCloud",  "Go to appleid.apple.com → Sign-In and Security → App-Specific Passwords"),
    "me.com":       ("iCloud",  "Go to appleid.apple.com → Sign-In and Security → App-Specific Passwords"),
}

def _provider_hint(email_address: str) -> str:
    domain = email_address.split("@")[-1].lower() if "@" in email_address else ""
    name, hint = _PROVIDER_HINTS.get(domain, ("your email provider", "Check your provider's help pages for App Password / IMAP setup"))
    return f"<strong>{name} App Password:</strong> {hint}"


def _load_accounts(user_id: int) -> list:
    """
    Load connected accounts.  Tries the new multi-account table first,
    then falls back to the legacy single-account settings row.
    """
    try:
        from database import get_all_email_accounts
        accounts = get_all_email_accounts(user_id)
        if accounts:
            return accounts
    except Exception:
        pass

    # Legacy fallback
    try:
        from database import get_email_sync_settings
        cfg = get_email_sync_settings(user_id)
        if cfg:
            return [{
                "email_address": cfg["gmail_address"],
                "app_password":  cfg["app_password"],
                "sync_days":     cfg.get("sync_days", 90),
                "last_sync":     cfg.get("last_sync"),
            }]
    except Exception:
        pass

    return []


def render_gmail_sync_section():
    """
    Multi-account email banking sync panel.
    Call this inside spending_analysis_page() just like the original.
    """
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    st.markdown("""
        <div style="margin:1.75rem 0 1rem;">
            <h3 style="font-family:'Playfair Display',serif;font-size:1.2rem;
                       font-weight:600;color:#e8eaf0;margin:0 0 .2rem;">
                📧 Email Banking Sync
            </h3>
            <p style="font-size:.82rem;color:#7b7f94;margin:0;">
                Connect Gmail, Yahoo, Outlook, iCloud — any account that receives
                bank alert emails. Transactions appear across every Finance Hub page.
            </p>
        </div>
    """, unsafe_allow_html=True)

    user_id  = st.session_state.user["id"]
    accounts = _load_accounts(user_id)

    # ── Connected accounts ─────────────────────────────────────────────
    if accounts:
        st.markdown(f"""
            <div style="font-size:.75rem;font-weight:600;letter-spacing:.07em;
                        text-transform:uppercase;color:#7b7f94;margin-bottom:.6rem;">
                {len(accounts)} connected account{'s' if len(accounts) > 1 else ''}
            </div>""", unsafe_allow_html=True)

        for acct in accounts:
            addr      = acct.get("email_address") or acct.get("gmail_address", "")
            last_sync = acct.get("last_sync")
            last_str  = last_sync.strftime("%d %b %Y %I:%M %p") if last_sync else "Never"

            c_info, c_btn, c_del = st.columns([4, 1.5, 1])

            with c_info:
                st.markdown(f"""
                    <div style="background:rgba(31,207,138,.06);border:1px solid rgba(31,207,138,.18);
                                border-radius:10px;padding:.6rem 1rem;margin-bottom:.4rem;">
                        <span style="color:#1fcf8a;font-weight:600;font-size:.88rem;">✓ {addr}</span>
                        <span style="color:#7b7f94;font-size:.75rem;margin-left:.75rem;">
                            Last sync: {last_str}</span>
                    </div>""", unsafe_allow_html=True)

            with c_btn:
                if st.button("🔄 Sync", key=f"sync_{addr}", use_container_width=True,
                             type="primary"):
                    pwd = acct.get("app_password", "")
                    days = acct.get("sync_days", 90)
                    with st.spinner(f"Scanning {addr}…"):
                        from email_scanner import sync_email_account
                        n, err = sync_email_account(user_id, addr, pwd, days)
                    if err:
                        st.error(f"❌ {err}")
                    else:
                        clear_data_cache()
                        st.success(f"✅ {n} new transaction(s)!" if n
                                   else "Up to date — no new transactions.")
                        st.rerun()

            with c_del:
                if st.button("🗑", key=f"del_{addr}", use_container_width=True):
                    try:
                        from database import remove_email_account
                        remove_email_account(user_id, addr)
                        clear_data_cache()
                        st.rerun()
                    except Exception:
                        # Legacy: can't remove single-account row, just warn
                        st.warning("Remove the account in your email sync settings.")

        # Sync All button (only meaningful with multiple accounts)
        if len(accounts) > 1:
            if st.button("🔄 Sync All Accounts", use_container_width=True, type="primary"):
                with st.spinner("Syncing all accounts…"):
                    from email_scanner import sync_all_accounts
                    total, errors = sync_all_accounts(user_id)
                clear_data_cache()
                if errors:
                    for e in errors:
                        st.error(f"❌ {e}")
                st.success(f"✅ {total} new transaction(s) across all accounts." if total
                           else "All accounts up to date.")
                st.rerun()

    else:
        st.info("No email accounts connected yet. Add one below.")

    # ── Add new account ────────────────────────────────────────────────
    with st.expander("➕ Add email account", expanded=not bool(accounts)):

        new_addr = st.text_input(
            "Email address",
            placeholder="yourname@gmail.com  /  yourname@yahoo.com  /  etc.",
            key="new_email_addr",
        )

        # Dynamic provider hint
        if new_addr and "@" in new_addr:
            st.markdown(f"""
                <div style="background:rgba(61,157,246,.08);border:1px solid rgba(61,157,246,.2);
                            border-radius:8px;padding:.65rem 1rem;margin-bottom:.75rem;
                            font-size:.82rem;color:#3d9df6;">
                    {_provider_hint(new_addr)}
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="background:rgba(61,157,246,.06);border:1px solid rgba(61,157,246,.15);
                            border-radius:8px;padding:.65rem 1rem;margin-bottom:.75rem;
                            font-size:.82rem;color:#3d9df6;">
                    Supports <strong>Gmail, Yahoo, Outlook, Hotmail, iCloud</strong>
                    and most IMAP providers. Enter your address above to see
                    provider-specific setup instructions.
                </div>""", unsafe_allow_html=True)

        new_pwd = st.text_input(
            "App Password",
            type="password",
            placeholder="16-character app password (NOT your regular password)",
            key="new_email_pwd",
        )

        new_days = st.slider(
            "Scan emails from the last N days",
            min_value=7, max_value=365, value=90, step=7,
            key="new_email_days",
        )

        if st.button("🔗 Connect account", type="primary", use_container_width=True,
                     key="connect_email_btn"):
            if not new_addr or "@" not in new_addr:
                st.error("Enter a valid email address.")
            elif len(new_pwd.replace(" ", "")) < 16:
                st.error("App password should be 16 characters (no spaces).")
            else:
                # Test the connection before saving
                with st.spinner("Testing connection…"):
                    from email_scanner import connect_email
                    test = connect_email(new_addr, new_pwd)

                if test is None:
                    st.error(
                        "❌ Could not connect. Double-check your app password "
                        "and make sure IMAP is enabled in your email settings."
                    )
                else:
                    test.logout()
                    # Save to new multi-account table (with legacy fallback)
                    saved = False
                    try:
                        from database import add_email_account
                        saved = add_email_account(user_id, new_addr, new_pwd, new_days)
                    except Exception:
                        pass

                    if not saved:
                        # Legacy fallback: write to email_sync_settings
                        try:
                            from database import save_email_sync_settings
                            saved = save_email_sync_settings(
                                user_id, new_addr, new_pwd, new_days
                            )
                        except Exception:
                            pass

                    if saved:
                        st.success(f"✅ {new_addr} connected successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save account — check database connection.")

    # ── Source breakdown pill ──────────────────────────────────────────
    try:
        from data_loader import load_all_user_data
        data = load_all_user_data(user_id)
        if not data.empty and "source" in data.columns:
            n_email = int((data["source"] == "email").sum())
            n_file  = int((data["source"] == "file").sum())

            if n_email > 0 or n_file > 0:
                # Count likely subscriptions from email data
                n_sub = 0
                if "is_subscription" in data.columns:
                    n_sub = int(
                        ((data["source"] == "email") & (data["is_subscription"] == 1)).sum()
                    )

                sub_tag = (
                    f'&nbsp;·&nbsp;<span style="color:#7c6bf6;font-weight:600;">'
                    f'{n_sub} likely subscription charge{"s" if n_sub != 1 else ""}</span>'
                ) if n_sub > 0 else ""

                st.markdown(f"""
                    <div style="font-size:.78rem;color:#7b7f94;margin-top:.6rem;">
                        📊 Current data:
                        <span style="color:#1fcf8a;font-weight:600;">{n_email} from email</span>
                        &nbsp;+&nbsp;
                        <span style="color:#f5a623;font-weight:600;">{n_file} from files</span>
                        &nbsp;=&nbsp;
                        <span style="color:#e8eaf0;font-weight:600;">{n_email + n_file} total</span>
                        {sub_tag}
                    </div>""", unsafe_allow_html=True)
    except Exception:
        pass
