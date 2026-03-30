# styles.py
"""
Global UI styling — Finance Hub
Dark-luxury editorial aesthetic: deep navy, amber/coral accents, serif display type
"""
import streamlit as st


def apply_custom_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap');

    /* ── tokens ─────────────────────────────── */
    :root {
      --bg:        #07080f;
      --surface:   #0e1018;
      --card:      #13151f;
      --border:    rgba(255,255,255,0.07);
      --border-hi: rgba(255,255,255,0.14);
      --text:      #e8eaf0;
      --muted:     #7b7f94;
      --amber:     #f5a623;
      --coral:     #f04e5e;
      --sky:       #3d9df6;
      --mint:      #1fcf8a;
      --violet:    #7c6bf6;
      --gold-grad: linear-gradient(135deg,#f5a623 0%,#f07a23 100%);
      --red-grad:  linear-gradient(135deg,#f04e5e 0%,#c2273b 100%);
      --blue-grad: linear-gradient(135deg,#3d9df6 0%,#1c6fd1 100%);
      --green-grad:linear-gradient(135deg,#1fcf8a 0%,#0fa86e 100%);
      --page-grad: linear-gradient(160deg,#07080f 0%,#0c0f1c 40%,#07080f 100%);
    }

    /* ── page base ───────────────────────────── */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main {
      background: var(--page-grad) !important;
      font-family: 'Outfit', sans-serif !important;
      color: var(--text) !important;
    }

    /* background noise texture overlay */
    .stApp::before {
      content:'';
      position:fixed; inset:0; z-index:0; pointer-events:none;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
      background-size: 200px 200px;
    }

    /* ── hide streamlit chrome ───────────────── */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stSidebarNav"] { visibility: hidden !important; display: none !important; }

    /* ── scrollbar ───────────────────────────── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--surface); }
    ::-webkit-scrollbar-thumb { background: #2a2d3e; border-radius: 99px; }

    /* ── sidebar ─────────────────────────────── */
    section[data-testid="stSidebar"] {
      background: var(--surface) !important;
      border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] * { color: var(--text) !important; }
    section[data-testid="stSidebar"] .stButton > button {
      background: rgba(255,255,255,0.04) !important;
      border: 1px solid var(--border) !important;
      color: var(--text) !important;
      text-align: left !important;
      justify-content: flex-start !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
      background: rgba(255,255,255,0.09) !important;
      border-color: var(--border-hi) !important;
    }

    /* ── buttons ─────────────────────────────── */
    .stButton > button {
      font-family: 'Outfit', sans-serif !important;
      font-weight: 600 !important;
      font-size: 0.875rem !important;
      letter-spacing: 0.01em !important;
      border-radius: 10px !important;
      padding: 0.6rem 1.25rem !important;
      border: 1px solid var(--border-hi) !important;
      background: rgba(255,255,255,0.05) !important;
      color: var(--text) !important;
      transition: all 0.2s ease !important;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    .stButton > button:hover {
      background: rgba(255,255,255,0.10) !important;
      border-color: rgba(255,255,255,0.22) !important;
      transform: translateY(-1px) !important;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4) !important;
    }
    .stButton > button[kind="primary"] {
      background: var(--amber) !important;
      border-color: var(--amber) !important;
      color: #07080f !important;
      box-shadow: 0 4px 18px rgba(245,166,35,0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
      background: #f7b84a !important;
      border-color: #f7b84a !important;
      box-shadow: 0 6px 24px rgba(245,166,35,0.50) !important;
    }

    /* ── inputs ──────────────────────────────── */
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stMultiselect label,
    .stTextArea label,
    .stRadio label {
      font-family: 'Outfit', sans-serif !important;
      font-size: 0.72rem !important;
      font-weight: 600 !important;
      color: var(--muted) !important;
      text-transform: uppercase !important;
      letter-spacing: 0.07em !important;
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
      background: var(--card) !important;
      border: 1.5px solid var(--border) !important;
      border-radius: 10px !important;
      color: var(--text) !important;
      font-family: 'Outfit', sans-serif !important;
      font-size: 0.93rem !important;
      transition: border-color 0.2s !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
      border-color: var(--amber) !important;
      box-shadow: 0 0 0 3px rgba(245,166,35,0.15) !important;
    }
    .stSelectbox > div > div,
    .stMultiselect > div > div {
      background: var(--card) !important;
      border: 1.5px solid var(--border) !important;
      border-radius: 10px !important;
      color: var(--text) !important;
    }

    /* ── alerts ──────────────────────────────── */
    .stAlert {
      background: rgba(255,255,255,0.03) !important;
      border: 1px solid var(--border) !important;
      border-radius: 10px !important;
      font-family: 'Outfit', sans-serif !important;
    }
    [data-baseweb="notification"] { border-radius: 10px !important; }

    /* ── tabs ────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
      background: var(--card) !important;
      border-radius: 12px !important;
      padding: 4px !important;
      gap: 2px !important;
      border: 1px solid var(--border) !important;
    }
    .stTabs [data-baseweb="tab"] {
      font-family: 'Outfit', sans-serif !important;
      font-weight: 500 !important;
      font-size: 0.875rem !important;
      color: var(--muted) !important;
      border-radius: 8px !important;
      padding: 0.5rem 1.25rem !important;
    }
    .stTabs [aria-selected="true"] {
      background: var(--amber) !important;
      color: #07080f !important;
      font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
      padding-top: 1.5rem !important;
    }

    /* ── expander ────────────────────────────── */
    .streamlit-expanderHeader {
      background: var(--card) !important;
      border: 1px solid var(--border) !important;
      border-radius: 10px !important;
      font-family: 'Outfit', sans-serif !important;
      font-weight: 600 !important;
      color: var(--text) !important;
    }
    .streamlit-expanderContent {
      background: rgba(255,255,255,0.015) !important;
      border: 1px solid var(--border) !important;
      border-top: none !important;
      border-radius: 0 0 10px 10px !important;
    }

    /* ── dataframe ───────────────────────────── */
    .stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
    .stDataFrame [data-testid="stDataFrameResizable"] {
      border: 1px solid var(--border) !important;
      border-radius: 12px !important;
    }

    /* ── metrics ─────────────────────────────── */
    [data-testid="stMetric"] {
      background: var(--card) !important;
      border: 1px solid var(--border) !important;
      border-radius: 12px !important;
      padding: 1rem 1.25rem !important;
    }
    [data-testid="stMetricLabel"] {
      font-family: 'Outfit', sans-serif !important;
      font-size: 0.72rem !important;
      font-weight: 600 !important;
      color: var(--muted) !important;
      text-transform: uppercase !important;
      letter-spacing: 0.07em !important;
    }
    [data-testid="stMetricValue"] {
      font-family: 'Outfit', sans-serif !important;
      font-weight: 700 !important;
      color: var(--text) !important;
    }

    /* ── spinner ─────────────────────────────── */
    .stSpinner > div > div {
      border-top-color: var(--amber) !important;
    }

    /* ── progress ────────────────────────────── */
    .stProgress > div > div > div {
      background: var(--amber) !important;
    }

    /* ── file uploader ───────────────────────── */
    [data-testid="stFileUploadDropzone"] {
      background: var(--card) !important;
      border: 2px dashed var(--border-hi) !important;
      border-radius: 14px !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
      border-color: var(--amber) !important;
      background: rgba(245,166,35,0.04) !important;
    }

    /* ── shared page card ────────────────────── */
    .page-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 2rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    }

    /* ── page header row ─────────────────────── */
    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 0.25rem;
    }
    .page-header h2 {
      font-family: 'Playfair Display', serif;
      font-size: 1.85rem;
      font-weight: 600;
      color: var(--text);
      margin: 0;
      letter-spacing: -0.02em;
    }
    .page-subhead {
      font-family: 'Outfit', sans-serif;
      font-size: 0.88rem;
      color: var(--muted);
      margin-bottom: 1.5rem;
      margin-top: 0.2rem;
    }

    /* ── stat card ───────────────────────────── */
    .stat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.5rem;
      position: relative;
      overflow: hidden;
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .stat-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: var(--accent-grad, var(--gold-grad));
    }
    .stat-card:hover {
      transform: translateY(-3px);
      box-shadow: 0 12px 32px rgba(0,0,0,0.4);
    }
    .stat-card .sc-label {
      font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 0.6rem;
    }
    .stat-card .sc-value {
      font-family: 'Outfit', sans-serif;
      font-size: 1.95rem; font-weight: 700; color: var(--text);
      margin-bottom: 0.35rem; line-height: 1;
    }
    .stat-card .sc-delta {
      font-size: 0.78rem; color: var(--muted);
    }
    .stat-card .sc-delta.up   { color: var(--mint); }
    .stat-card .sc-delta.down { color: var(--coral); }

    /* ── feature card ────────────────────────── */
    .feat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 1.75rem;
      margin-bottom: 0.25rem;
      cursor: pointer;
      transition: border-color 0.25s, box-shadow 0.25s, transform 0.25s;
      position: relative; overflow: hidden;
    }
    .feat-card::after {
      content: '';
      position: absolute; inset: 0;
      background: radial-gradient(circle at 70% 50%, rgba(245,166,35,0.07) 0%, transparent 70%);
      opacity: 0; transition: opacity 0.3s;
    }
    .feat-card:hover { border-color: var(--border-hi); transform: translateY(-4px);
                       box-shadow: 0 16px 40px rgba(0,0,0,0.45); }
    .feat-card:hover::after { opacity: 1; }
    .feat-card .fc-icon { font-size: 2.4rem; margin-bottom: 0.9rem; }
    .feat-card .fc-title {
      font-family: 'Playfair Display', serif;
      font-size: 1.2rem; font-weight: 600; color: var(--text); margin-bottom: 0.5rem;
    }
    .feat-card .fc-desc { font-size: 0.86rem; color: var(--muted); line-height: 1.6; }
    .feat-card.featured { border-color: rgba(245,166,35,0.30);
                           box-shadow: 0 4px 24px rgba(245,166,35,0.12); }

    /* ── insight pill ────────────────────────── */
    .insight-pill {
      background: rgba(255,255,255,0.04);
      border: 1px solid var(--border);
      border-radius: 12px; padding: 1.1rem 1.25rem; text-align: center;
    }
    .insight-pill .ip-label {
      font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 0.4rem;
    }
    .insight-pill .ip-value {
      font-family: 'Outfit', sans-serif;
      font-size: 1.5rem; font-weight: 700; color: var(--text);
    }

    /* ── section divider ─────────────────────── */
    .section-divider {
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--border-hi), transparent);
      margin: 1.75rem 0;
    }

    /* ── badge ───────────────────────────────── */
    .badge {
      display: inline-block; padding: 0.2rem 0.7rem;
      border-radius: 99px; font-size: 0.7rem; font-weight: 700;
      letter-spacing: 0.05em; text-transform: uppercase;
    }
    .badge-green  { background: rgba(31,207,138,0.15); color: #1fcf8a; }
    .badge-red    { background: rgba(240,78,94,0.15);  color: #f04e5e; }
    .badge-amber  { background: rgba(245,166,35,0.15); color: #f5a623; }
    .badge-blue   { background: rgba(61,157,246,0.15); color: #3d9df6; }

    /* ── category detail card ────────────────── */
    .cat-card {
      border-radius: 10px; padding: 0.85rem 1rem;
      margin-bottom: 0.5rem; border-left: 3px solid;
      transition: opacity 0.2s;
    }
    .cat-card:hover { opacity: 0.85; }

    /* ── file card ───────────────────────────── */
    .file-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px; padding: 1rem;
      text-align: center; transition: border-color 0.2s, transform 0.2s;
    }
    .file-card:hover { border-color: var(--amber); transform: translateY(-2px); }
    </style>
    """, unsafe_allow_html=True)
