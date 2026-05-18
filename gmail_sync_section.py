# gmail_sync_section.py
"""
PASTE THIS FUNCTION into pages/spending_analysis.py,
then call render_gmail_sync_section() inside spending_analysis_page()
right after the file-upload section (after the "your files" divider).

Also add these two imports at the top of spending_analysis.py:
    from email_scanner import sync_gmail_transactions
    from database import (save_email_sync_settings, get_email_sync_settings,
                          delete_all_email_transactions)
"""

import streamlit as st
from data_loader import clear_data_cache


def render_gmail_sync_section():
    """
    Gmail banking email sync — lets users connect their Gmail so bank alert
    emails are automatically pulled in and available across the whole platform.
    """
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # Section heading
    st.markdown("""
        <div style="margin:1.75rem 0 1rem;">
            <h3 style="font-family:'Playfair Display',serif;font-size:1.2rem;
                       font-weight:600;color:#e8eaf0;margin:0 0 .2rem;">
                📧 Gmail Banking Sync
            </h3>
            <p style="font-size:.82rem;color:#7b7f94;margin:0;">
                Connect your Gmail once — bank alert emails are scanned automatically
                and transactions appear across every Finance Hub page.
            </p>
        </div>
    """, unsafe_allow_html=True)

    user_id = st.session_state.user["id"]

    # Load existing config
    from database import (save_email_sync_settings, get_email_sync_settings,
                          delete_all_email_transactions)
    from email_scanner import sync_gmail_transactions

    cfg = get_email_sync_settings(user_id)

    # ── Status banner ──────────────────────────────────────────────────
    if cfg:
        last_sync = cfg.get("last_sync")
        last_sync_str = (last_sync.strftime("%d %b %Y at %I:%M %p")
                         if last_sync else "Never")
        st.markdown(f"""
            <div style="background:rgba(31,207,138,.07);border:1px solid rgba(31,207,138,.2);
                        border-radius:10px;padding:.7rem 1.1rem;margin-bottom:1rem;
                        display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:.85rem;color:#1fcf8a;font-weight:600;">
                    ✓ Gmail connected: {cfg['gmail_address']}
                </span>
                <span style="font-size:.78rem;color:#7b7f94;">
                    Last sync: {last_sync_str}
                </span>
            </div>""", unsafe_allow_html=True)

    # ── Main expander ──────────────────────────────────────────────────
    label = "⚙️ Gmail Settings" if cfg else "🔗 Connect Gmail"
    with st.expander(label, expanded=not bool(cfg)):

        # How-to tip
        st.markdown("""
            <div style="background:rgba(61,157,246,.08);border:1px solid rgba(61,157,246,.2);
                        border-radius:8px;padding:.75rem 1rem;margin-bottom:1rem;
                        font-size:.82rem;color:#3d9df6;">
                <strong>How to get a Gmail App Password:</strong><br>
                1. Go to your Google Account → Security → 2-Step Verification (enable it)<br>
                2. Then go to Security → App passwords → Generate one for "Mail"<br>
                3. Paste that 16-character password below — NOT your regular Gmail password
            </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            gmail_address = st.text_input(
                "Gmail address",
                value=cfg["gmail_address"] if cfg else "",
                placeholder="yourname@gmail.com",
                key="gmail_address_input",
            )
        with col2:
            app_password = st.text_input(
                "Gmail App Password",
                type="password",
                value=cfg["app_password"] if cfg else "",
                placeholder="xxxx xxxx xxxx xxxx",
                key="gmail_app_password_input",
            )

        sync_days = st.slider(
            "Scan emails from the last N days",
            min_value=7, max_value=365, value=cfg["sync_days"] if cfg else 90,
            step=7, key="gmail_sync_days",
        )

        col_save, col_sync, col_clear = st.columns(3)

        # ── Save credentials ───────────────────────────────────────────
        with col_save:
            if st.button("💾 Save credentials", use_container_width=True):
                if not gmail_address or "@" not in gmail_address:
                    st.error("Enter a valid Gmail address.")
                elif len(app_password.replace(" ", "")) < 16:
                    st.error("App password should be 16 characters.")
                else:
                    ok = save_email_sync_settings(
                        user_id, gmail_address.strip(),
                        app_password.strip(), sync_days
                    )
                    if ok:
                        st.success("✅ Credentials saved!")
                        st.rerun()
                    else:
                        st.error("Failed to save — check DB connection.")

        # ── Sync now ───────────────────────────────────────────────────
        with col_sync:
            if st.button("🔄 Sync now", use_container_width=True, type="primary",
                         disabled=not bool(cfg)):
                addr = gmail_address or (cfg["gmail_address"] if cfg else "")
                pwd  = app_password  or (cfg["app_password"]  if cfg else "")
                days = sync_days

                if not addr or not pwd:
                    st.error("Save your Gmail credentials first.")
                else:
                    with st.spinner("Scanning Gmail for bank alerts…"):
                        n_added, err = sync_gmail_transactions(
                            user_id, addr, pwd, days
                        )
                    if err:
                        st.error(f"❌ {err}")
                    else:
                        clear_data_cache()
                        if n_added:
                            st.success(
                                f"✅ {n_added} new transaction(s) imported from Gmail!"
                            )
                        else:
                            st.info(
                                "Scan complete — no new bank transactions found. "
                                "Make sure your bank sends alerts to this Gmail."
                            )
                        st.rerun()

        # ── Clear email transactions ───────────────────────────────────
        with col_clear:
            if st.button("🗑 Clear email data", use_container_width=True,
                         disabled=not bool(cfg)):
                if delete_all_email_transactions(user_id):
                    clear_data_cache()
                    st.success("Email transactions cleared.")
                    st.rerun()

    # ── Source breakdown pill ──────────────────────────────────────────
    # Shows how many transactions came from email vs file uploads
    try:
        from data_loader import load_all_user_data
        data = load_all_user_data(user_id)
        if not data.empty and "source" in data.columns:
            n_email = int((data["source"] == "email").sum())
            n_file  = int((data["source"] == "file").sum())
            if n_email > 0:
                st.markdown(f"""
                    <div style="font-size:.78rem;color:#7b7f94;margin-top:.5rem;">
                        📊 Current data:
                        <span style="color:#1fcf8a;font-weight:600;">{n_email} from Gmail</span>
                        &nbsp;+&nbsp;
                        <span style="color:#f5a623;font-weight:600;">{n_file} from files</span>
                        &nbsp;=&nbsp;
                        <span style="color:#e8eaf0;font-weight:600;">{n_email+n_file} total</span>
                    </div>""", unsafe_allow_html=True)
    except Exception:
        pass
