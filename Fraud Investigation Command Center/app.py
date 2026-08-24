import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import re
import io
import traceback
import time
import numpy as np
from databricks import sql
from databricks.sdk import WorkspaceClient

# Setup Page - sidebar expanded by default
st.set_page_config(page_title="Insurance Fraud Investigation Analytics", layout="wide", initial_sidebar_state="expanded")

# --- Premium UI Styling ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

/* ============================================
   GLOBAL RESET & TYPOGRAPHY
   ============================================ */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ============================================
   DARK THEME BACKGROUND
   ============================================ */
[data-testid="stAppViewContainer"] {
    background: #0a0e1a !important;
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 50%, rgba(0, 194, 168, 0.06) 0%, transparent 50%) !important;
    color: #e2e8f0 !important;
}
[data-testid="stHeader"] {
    background: rgba(10, 14, 26, 0.8) !important;
    backdrop-filter: blur(20px) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
}
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px !important;
}

/* ============================================
   SIDEBAR STYLING
   ============================================ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #070b14 0%, #0d1220 50%, #0a0e1a 100%) !important;
    border-right: 1px solid rgba(99, 102, 241, 0.1) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #cbd5e1 !important;
    font-size: 0.9rem !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4 {
    color: #f1f5f9 !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(99, 102, 241, 0.15) !important;
    margin: 12px 0 !important;
}

/* Sidebar radio buttons as nav items */
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
}
[data-testid="stSidebar"] .stRadio > div > label {
    background: transparent !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    margin: 1px 0 !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
    border: 1px solid transparent !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(99, 102, 241, 0.08) !important;
    border-color: rgba(99, 102, 241, 0.15) !important;
}
[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(0, 194, 168, 0.1)) !important;
    border-color: rgba(99, 102, 241, 0.3) !important;
    box-shadow: 0 2px 8px -2px rgba(99, 102, 241, 0.3) !important;
}
[data-testid="stSidebar"] .stRadio > div > label p {
    color: #94a3b8 !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) p {
    color: #e2e8f0 !important;
    font-weight: 600 !important;
}
/* Hide radio circles */
[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none !important;
}

/* Sidebar branding */
.sidebar-brand {
    text-align: center;
    padding: 16px 8px 8px 8px;
}
.sidebar-brand-title {
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #818cf8, #00C2A8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 2px;
}
.sidebar-brand-sub {
    font-size: 0.72rem;
    color: #64748b;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
}
.sidebar-section-label {
    font-size: 0.68rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    padding: 12px 16px 4px 16px;
}

/* ============================================
   TYPOGRAPHY HIERARCHY - BRIGHTENED
   ============================================ */
h1, h2, h3, h4, h5, h6 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMarkdownContainer"] p {
    color: #cbd5e1 !important;
    line-height: 1.7 !important;
    font-size: 0.95rem !important;
}
[data-testid="stMarkdownContainer"] h3 {
    font-size: 1.15rem !important;
    color: #e2e8f0 !important;
    font-weight: 600 !important;
    margin-top: 0.5rem !important;
}
[data-testid="stMarkdownContainer"] strong {
    color: #f1f5f9 !important;
}
[data-testid="stMarkdownContainer"] li {
    color: #cbd5e1 !important;
    font-size: 0.93rem !important;
}
[data-testid="stMarkdownContainer"] code {
    color: #a5b4fc !important;
    background: rgba(99, 102, 241, 0.1) !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
}

/* ============================================
   ANIMATED GRADIENT TITLE
   ============================================ */
.gradient-title {
    background: linear-gradient(135deg, #818cf8, #6366f1, #a78bfa, #00C2A8, #34d399);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.2rem !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.1 !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
    animation: gradientShift 8s ease infinite;
}
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.subtitle-text {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    margin-top: 4px !important;
}

/* ============================================
   METRIC CARDS - GLASSMORPHISM
   ============================================ */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.6)) !important;
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
    border-radius: 16px !important;
    padding: 24px 20px !important;
    backdrop-filter: blur(12px) !important;
    box-shadow:
        0 4px 24px -4px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: visible !important;
}
[data-testid="stMetric"]::before {
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 3px !important;
    background: linear-gradient(90deg, #6366f1, #00C2A8) !important;
    border-radius: 16px 16px 0 0 !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-4px) !important;
    border-color: rgba(99, 102, 241, 0.4) !important;
    box-shadow:
        0 12px 40px -8px rgba(99, 102, 241, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
}
[data-testid="stMetricValue"] > div {
    color: #ffffff !important;
    font-weight: 800 !important;
    font-size: 1.35rem !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricLabel"] > div {
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    white-space: normal !important;
}
[data-testid="stMetricDelta"] > div {
    font-weight: 600 !important;
}

/* ============================================
   CARD CONTAINERS
   ============================================ */
.glass-card {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.7), rgba(30, 41, 59, 0.4)) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 28px !important;
    margin-bottom: 20px !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 4px 24px -4px rgba(0, 0, 0, 0.2) !important;
}
.glass-card h4 {
    color: #f1f5f9 !important;
}
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.section-header-icon {
    font-size: 1.4rem;
}
.section-header-text {
    font-size: 1.15rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.01em;
}

/* ============================================
   DATAFRAME STYLING
   ============================================ */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}
[data-testid="stDataFrame"] > div {
    border-radius: 12px !important;
}

/* ============================================
   BUTTONS
   ============================================ */
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.01em !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 2px 8px -2px rgba(99, 102, 241, 0.4) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #4338ca, #4f46e5) !important;
    box-shadow: 0 6px 20px -4px rgba(99, 102, 241, 0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
}
.stLinkButton > a {
    background: rgba(99, 102, 241, 0.1) !important;
    color: #a5b4fc !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
}
.stLinkButton > a:hover {
    background: rgba(99, 102, 241, 0.2) !important;
    border-color: rgba(99, 102, 241, 0.5) !important;
}

/* ============================================
   SELECT BOXES & INPUTS
   ============================================ */
[data-testid="stSelectbox"] > div > div {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] label p {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}
.stTextArea textarea, .stChatInput textarea {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
}
.stTextArea textarea:focus, .stChatInput textarea:focus {
    border-color: rgba(99, 102, 241, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}
.stTextArea label p {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}

/* ============================================
   INFO/WARNING/SUCCESS BOXES
   ============================================ */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: none !important;
    backdrop-filter: blur(8px) !important;
    font-size: 0.9rem !important;
}

/* ============================================
   DIVIDERS
   ============================================ */
hr {
    border-color: rgba(255, 255, 255, 0.08) !important;
    margin: 1.5rem 0 !important;
}

/* ============================================
   CUSTOM SCROLLBAR
   ============================================ */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.5);
}
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.5);
}

/* ============================================
   EXPANDER
   ============================================ */
[data-testid="stExpander"] {
    background: rgba(15, 23, 42, 0.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary p {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}

/* ============================================
   SPINNER
   ============================================ */
.stSpinner > div {
    border-top-color: #6366f1 !important;
}

/* ============================================
   FOOTER
   ============================================ */
.footer-bar {
    text-align: center;
    padding: 20px 0 10px 0;
    color: #64748b;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    font-weight: 500;
}
.footer-bar span {
    color: #818cf8;
    font-weight: 600;
}

/* ============================================
   CAPTION TEXT
   ============================================ */
[data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
}

/* ============================================
   CHAT MESSAGE STYLING
   ============================================ */
.chat-user-msg {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.08));
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 12px;
    color: #f1f5f9;
    font-size: 0.93rem;
}
.chat-agent-msg {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.7), rgba(30, 41, 59, 0.4));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 16px;
    color: #e2e8f0;
    font-size: 0.93rem;
    line-height: 1.7;
}
.chat-agent-msg strong {
    color: #f1f5f9;
}

/* ============================================
   TABS (for GenAI sub-nav)
   ============================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    background: rgba(15, 23, 42, 0.5) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    flex-wrap: wrap !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 8px 14px !important;
    transition: all 0.3s ease !important;
}
.stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] div {
    color: #94a3b8 !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(99, 102, 241, 0.08) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.9), rgba(0, 194, 168, 0.8)) !important;
    box-shadow: 0 4px 16px -4px rgba(99, 102, 241, 0.4) !important;
}
.stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] div {
    color: #ffffff !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# DATABRICKS CLIENTS
# ============================================
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
WAREHOUSE_ID = os.environ.get("DATABRICKS_SQL_WAREHOUSE_ID")

w = WorkspaceClient()

@st.cache_data(ttl=600)
def load_data():
    """Fetches the core investigation data from Databricks Unity Catalog"""
    try:
        if not WAREHOUSE_ID:
            st.warning("Running without explicit SQL Warehouse ID. Ensure compute is attached.")
            return pd.DataFrame()
            
        w = WorkspaceClient()
        response = w.statement_execution.execute_statement(
            statement="SELECT * FROM uae_insurance.uae_silver.fact_fraud_investigation LIMIT 50000",
            warehouse_id=WAREHOUSE_ID,
            wait_timeout="40s"
        )
        
        if response.status.state.value in ('FAILED', 'CANCELED', 'CLOSED'):
            st.error(f"Execution Failed: {response.status}")
            return pd.DataFrame()
            
        data = response.result.data_array or []
        columns = [col.name for col in response.manifest.schema.columns]
        df = pd.DataFrame(data, columns=columns)
        
        if not df.empty and 'FRAUD_SCORE' in df.columns:
            df['FRAUD_SCORE'] = pd.to_numeric(df['FRAUD_SCORE'], errors='coerce')
            df['RECOVERY_AMOUNT'] = pd.to_numeric(df['RECOVERY_AMOUNT'], errors='coerce')
            df['FRAUD_AMOUNT_DETECTED'] = pd.to_numeric(df['FRAUD_AMOUNT_DETECTED'], errors='coerce')
            df['INVESTIGATION_COST'] = pd.to_numeric(df['INVESTIGATION_COST'], errors='coerce')
            df['INVESTIGATION_DAYS'] = pd.to_numeric(df['INVESTIGATION_DAYS'], errors='coerce')
            
        return df
        
    except Exception as e:
        st.error(f"Failed to fetch via SDK: {e}")
        return pd.DataFrame(columns=['INVESTIGATION_ID', 'INVESTIGATION_STATUS', 'FRAUD_SCORE', 'RECOVERY_AMOUNT', 'FRAUD_AMOUNT_DETECTED', 'FINDINGS', 'INVESTIGATION_COST', 'INVESTIGATION_DAYS', 'MONTHYEAR', 'MONTHYEAR_SORT', 'INVESTIGATOR_ID'])

def execute_sql(query, max_wait=300):
    """Execute Databricks SQL with polling for long-running AI queries (up to max_wait seconds)."""
    w = WorkspaceClient()
    response = w.statement_execution.execute_statement(
        statement=query,
        warehouse_id=WAREHOUSE_ID,
        wait_timeout="50s"
    )
    # Check immediate failure
    if response.status.state.value in ('FAILED', 'CANCELED', 'CLOSED'):
        error_msg = ""
        if hasattr(response.status, 'error') and response.status.error:
            error_msg = str(response.status.error.message) if hasattr(response.status.error, 'message') else str(response.status.error)
        raise RuntimeError(f"SQL execution failed ({response.status.state.value}): {error_msg}")
    
    # Poll if query is still running (PENDING/RUNNING) - needed for ai_query calls
    statement_id = response.statement_id
    elapsed = 0
    poll_interval = 3
    while response.status.state.value in ('PENDING', 'RUNNING') and elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        response = w.statement_execution.get_statement(statement_id=statement_id)
        if response.status.state.value in ('FAILED', 'CANCELED', 'CLOSED'):
            error_msg = ""
            if hasattr(response.status, 'error') and response.status.error:
                error_msg = str(response.status.error.message) if hasattr(response.status.error, 'message') else str(response.status.error)
            raise RuntimeError(f"SQL execution failed ({response.status.state.value}): {error_msg}")
    
    if response.status.state.value in ('PENDING', 'RUNNING'):
        raise RuntimeError(f"Query timed out after {max_wait}s. Try reducing the number of rows.")
    
    if response.result is None or response.result.data_array is None:
        return pd.DataFrame()
    
    data = response.result.data_array or []
    schema_cols = response.manifest.schema.columns
    columns = [col.name for col in schema_cols]
    result_df = pd.DataFrame(data, columns=columns)
    
    # Auto-convert types based on manifest schema
    for col_info in schema_cols:
        cname = col_info.name
        ctype = col_info.type_name.value if hasattr(col_info.type_name, 'value') else str(col_info.type_name)
        ctype_lower = ctype.lower()
        if cname in result_df.columns:
            try:
                if any(t in ctype_lower for t in ['int', 'long', 'short', 'byte']):
                    result_df[cname] = pd.to_numeric(result_df[cname], errors='coerce').astype('Int64')
                elif any(t in ctype_lower for t in ['double', 'float', 'decimal', 'numeric']):
                    result_df[cname] = pd.to_numeric(result_df[cname], errors='coerce')
                elif 'date' in ctype_lower or 'timestamp' in ctype_lower:
                    result_df[cname] = pd.to_datetime(result_df[cname], errors='coerce')
            except Exception:
                pass
    return result_df


def escape_sql(val):
    return str(val).replace("'", "''")


def enhanced_dataframe(df, title="Data", key_prefix="edf", height=400, hide_index=False, show_stats=True):
    """Enhanced dataframe display with export, search, stats, and column highlight."""
    if df is None or df.empty:
        st.info("No data to display.")
        return

    n_rows, n_cols = df.shape
    num_cols = df.select_dtypes(include='number').columns.tolist()

    # --- Action bar: stats + search + exports ---
    bar1, bar2, bar3, bar4 = st.columns([2.5, 2.5, 1, 1])

    bar1.markdown(f"""<span style="color:#94a3b8; font-size:0.8rem;">
        {n_rows} rows &times; {n_cols} cols</span>""", unsafe_allow_html=True)

    search_term = bar2.text_input("Search", key=f"{key_prefix}_search",
                                   placeholder="Filter rows...", label_visibility="collapsed")

    # Apply search filter
    display_df = df.copy()
    if search_term:
        mask = display_df.astype(str).apply(lambda r: r.str.contains(search_term, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]
        if display_df.empty:
            st.warning(f"No rows match \"{search_term}\"")
            return

    # CSV download
    csv_buf = io.StringIO()
    display_df.to_csv(csv_buf, index=False)
    bar3.download_button(
        label="CSV",
        data=csv_buf.getvalue(),
        file_name=f"{title.lower().replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"{key_prefix}_csv",
        use_container_width=True,
    )

    # JSON download
    json_str = display_df.to_json(orient='records', indent=2, default_handler=str)
    bar4.download_button(
        label="JSON",
        data=json_str,
        file_name=f"{title.lower().replace(' ', '_')}.json",
        mime="application/json",
        key=f"{key_prefix}_json",
        use_container_width=True,
    )

    # --- Dataframe display ---
    st.dataframe(display_df, use_container_width=True, height=height, hide_index=hide_index)

    # --- Quick stats for numeric columns ---
    if show_stats and num_cols and len(num_cols) <= 8:
        with st.expander(f"Quick Stats ({len(num_cols)} numeric columns)", expanded=False):
            # Convert to numeric for stats
            stats_df = display_df[num_cols].apply(pd.to_numeric, errors='coerce')
            summary = stats_df.agg(['min', 'max', 'mean', 'median', 'std']).T
            summary.columns = ['Min', 'Max', 'Mean', 'Median', 'Std Dev']
            summary = summary.round(2)
            st.dataframe(summary, use_container_width=True, height=min(200, 35 * len(num_cols) + 40))


def render_genie_chart(df):
    """Auto-detect and render the best chart type for Genie query results."""
    try:
        if df is None or df.empty or len(df) < 2:
            return

        COLORS = ['#818cf8', '#00C2A8', '#f59e0b', '#ef4444', '#a78bfa', '#34d399', '#fb923c', '#f472b6']

        # Auto-convert string columns to numeric where possible
        # (execute_sql / Statement API returns all values as strings)
        df = df.copy()
        for c in df.columns:
            if df[c].dtype == object:
                try:
                    converted = pd.to_numeric(df[c], errors='coerce')
                    if converted.notna().sum() > 0 and converted.notna().mean() > 0.5:
                        df[c] = converted
                except (ValueError, TypeError):
                    pass

        cols = df.columns.tolist()
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        str_cols = [c for c in cols if c not in num_cols]

        if not num_cols:
            return

        # Detect time/month columns
        time_keywords = ['month', 'year', 'date', 'quarter', 'week', 'period', 'time']
        time_col = None
        for c in cols:
            if any(k in c.lower() for k in time_keywords):
                time_col = c
                break

        # Filter out sort/key columns from display
        skip_keywords = ['_sort', '_key', '_id', 'key_new']
        display_num = [c for c in num_cols if not any(k in c.lower() for k in skip_keywords)]
        if not display_num:
            display_num = num_cols[:4]
        else:
            display_num = display_num[:4]

        cat_col = None
        for c in str_cols:
            if not any(k in c.lower() for k in skip_keywords):
                cat_col = c
                break

        # Build chart title from columns
        metric_names = [c.replace('_', ' ').title() for c in display_num[:3]]
        title_metrics = ', '.join(metric_names)

        # Dark theme config
        theme_config = {
            'background': 'transparent',
            'title': {'color': '#e2e8f0', 'fontSize': 14, 'fontWeight': 600, 'font': 'Inter'},
            'axis': {
                'labelColor': '#94a3b8', 'titleColor': '#cbd5e1', 'gridColor': 'rgba(255,255,255,0.06)',
                'domainColor': 'rgba(255,255,255,0.1)', 'tickColor': 'rgba(255,255,255,0.1)',
                'labelFont': 'Inter', 'titleFont': 'Inter', 'labelFontSize': 11, 'titleFontSize': 12,
            },
            'legend': {'labelColor': '#94a3b8', 'titleColor': '#cbd5e1', 'labelFont': 'Inter', 'labelFontSize': 11},
            'view': {'stroke': 'transparent'},
        }

        chart = None

        # CASE 1: Time series -> line chart
        if time_col and len(display_num) >= 1:
            sort_col = None
            for c in cols:
                if 'sort' in c.lower():
                    sort_col = c
                    break

            plot_df = df.copy()
            if sort_col:
                plot_df = plot_df.sort_values(sort_col)

            melted = plot_df.melt(id_vars=[time_col], value_vars=display_num, var_name='Metric', value_name='Value')

            sort_order = plot_df[time_col].tolist()
            x_enc = alt.X(f'{time_col}:N', sort=sort_order, title=time_col.replace('_', ' ').title(),
                          axis=alt.Axis(labelAngle=-45))

            chart = alt.Chart(melted).mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=40)).encode(
                x=x_enc,
                y=alt.Y('Value:Q', title='Value'),
                color=alt.Color('Metric:N', scale=alt.Scale(range=COLORS), legend=alt.Legend(title=None)),
                tooltip=[alt.Tooltip(time_col, title='Period'), alt.Tooltip('Metric'), alt.Tooltip('Value', format=',.0f')]
            ).properties(title=f'{title_metrics} by {time_col.replace("_", " ").title()}', width='container', height=350)

        # CASE 2: Categorical + numeric -> bar chart
        elif cat_col and len(display_num) >= 1:
            plot_df = df.head(20).copy()

            if len(display_num) == 1:
                plot_df = plot_df.sort_values(display_num[0], ascending=True).tail(15)
                chart = alt.Chart(plot_df).mark_bar(cornerRadiusEnd=4, size=18).encode(
                    y=alt.Y(f'{cat_col}:N', sort='-x', title=None),
                    x=alt.X(f'{display_num[0]}:Q', title=display_num[0].replace('_', ' ').title()),
                    color=alt.value(COLORS[0]),
                    tooltip=[alt.Tooltip(cat_col), alt.Tooltip(display_num[0], format=',.0f')]
                ).properties(title=f'{display_num[0].replace("_", " ").title()} by {cat_col.replace("_", " ").title()}',
                             width='container', height=max(250, len(plot_df) * 28))
            else:
                melted = plot_df.melt(id_vars=[cat_col], value_vars=display_num[:3], var_name='Metric', value_name='Value')
                chart = alt.Chart(melted).mark_bar(cornerRadiusEnd=3).encode(
                    x=alt.X(f'{cat_col}:N', title=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Value:Q', title='Value'),
                    color=alt.Color('Metric:N', scale=alt.Scale(range=COLORS), legend=alt.Legend(title=None)),
                    xOffset='Metric:N',
                    tooltip=[alt.Tooltip(cat_col), alt.Tooltip('Metric'), alt.Tooltip('Value', format=',.0f')]
                ).properties(title=f'{title_metrics} by {cat_col.replace("_", " ").title()}', width='container', height=350)

        # CASE 3: Small dataset with single numeric -> donut
        elif len(df) <= 6 and len(display_num) == 1 and len(str_cols) >= 1:
            label_col = str_cols[0]
            chart = alt.Chart(df).mark_arc(innerRadius=60, outerRadius=120, cornerRadius=4).encode(
                theta=alt.Theta(f'{display_num[0]}:Q'),
                color=alt.Color(f'{label_col}:N', scale=alt.Scale(range=COLORS), legend=alt.Legend(title=None)),
                tooltip=[alt.Tooltip(label_col), alt.Tooltip(display_num[0], format=',.0f')]
            ).properties(title=f'{display_num[0].replace("_", " ").title()} Distribution', width='container', height=300)

        # CASE 4: Numeric only -> first col as bar
        elif len(num_cols) >= 2 and len(df) <= 30:
            chart = alt.Chart(df.head(20).reset_index()).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X('index:O', title='Row'),
                y=alt.Y(f'{display_num[0]}:Q', title=display_num[0].replace('_', ' ').title()),
                color=alt.value(COLORS[0]),
                tooltip=[alt.Tooltip(c, format=',.0f') for c in display_num[:4]]
            ).properties(title=f'{display_num[0].replace("_", " ").title()} Overview', width='container', height=300)

        if chart:
            chart = chart.configure(**theme_config)
            st.altair_chart(chart, use_container_width=True)
    except Exception:
        pass


def render_ai_response(raw_text):
    if isinstance(raw_text, str):
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict) and 'choices' in parsed:
                text = parsed['choices'][0].get('messages', parsed['choices'][0].get('message', {}).get('content', str(parsed)))
            elif isinstance(parsed, dict) and 'message' in parsed:
                text = parsed['message']
            elif isinstance(parsed, str):
                text = parsed
            else:
                text = str(parsed)
        except (json.JSONDecodeError, TypeError, KeyError, IndexError):
            text = raw_text
    else:
        text = str(raw_text)
    text = text.strip().strip('"').strip("'")
    text = text.replace('\\n', '\n').replace('\\t', '\t')
    return text

def clean_columns(dataframe):
    dataframe.columns = [c.strip('"').upper() for c in dataframe.columns]
    return dataframe

# ============================================
# FRAUD AGENT: Schema Context for Text-to-SQL
# ============================================
SCHEMA_CONTEXT = """
You are a SQL expert for Salama Insurance fraud investigation data on Databricks (Spark SQL dialect).
Generate ONLY a valid SQL SELECT query. Do NOT include any explanation or markdown.

Available tables and their columns:

1. uae_insurance.uae_silver.fact_fraud_investigation (fi)
   - INVESTIGATION_ID (string), CLAIM_KEY (decimal), FRAUD_SCORE (double): 0-100
   - INVESTIGATION_COST (double), FRAUD_AMOUNT_DETECTED (double), RECOVERY_AMOUNT (double)
   - INVESTIGATION_DAYS (decimal), FRAUD_DETECTION_RATE (decimal)
   - INVESTIGATOR_ID (string), INVESTIGATION_STATUS (string): INITIATED/IN_PROGRESS/COMPLETED/CLOSED
   - FINDINGS (string): FRAUD_CONFIRMED/FRAUD_SUSPECTED/INCONCLUSIVE/NO_FRAUD
   - FR_DATE (timestamp), MONTHYEAR (string), MONTHYEAR_SORT (decimal)

2. uae_insurance.uae_silver.fact_claim (fc)
   - CLAIM_ID (string), POLICY_ID (string), CUSTOMER_KEY (decimal)
   - CLAIM_KEY (decimal): JOIN to fi.CLAIM_KEY
   - CLAIMED_AMOUNT (double), APPROVED_AMOUNT (double), PAID_AMOUNT (double), RESERVE_AMOUNT (double)
   - DAYS_TO_REPORT (decimal), DAYS_TO_SETTLE (decimal)
   - CLAIM_RATIO (double), APPROVAL_RATIO (double)
   - BUSINESS_LINE (string), CLAIM_TYPE (string), CLAIM_STATUS (string)
   - ADJUSTER_ID (string), RISK_RATING (string), RISK_SCORE (decimal)
   - CLAIM_AGING_BUCKET (string), CL_DATE (timestamp)

3. uae_insurance.uae_silver.dim_customer (dc)
   - CUSTOMER_KEY (decimal): JOIN to fc.CUSTOMER_KEY
   - CUSTOMER_ID (string), CUSTOMER_TYPE (string), CUSTOMER_NAME (string)
   - NATIONALITY (string), EMIRATES (string), CITY (string)
   - RISK_RATING (string), CUSTOMER_SEGMENT (string), IS_ACTIVE (boolean)

4. uae_insurance.uae_silver.dim_policy (dp)
   - POLICY_KEY (decimal), POLICY_ID (string), POLICY_NUMBER (string)
   - PRODUCT_CODE (string), BUSINESS_LINE (string)
   - PREMIUM_AMOUNT (double), SUM_INSURED (double)
   - POLICY_STATUS (string), SALES_CHANNEL (string)

5. uae_insurance.uae_silver.fraud_ai_results (ai)
   - INVESTIGATION_ID (string): Links to fi.INVESTIGATION_ID
   - AI_INSIGHTS (string), AI_PRIORITY (string), AI_RECOMMENDATIONS (string)

Key joins:
- fi.CLAIM_KEY = fc.CLAIM_KEY
- fc.CUSTOMER_KEY = dc.CUSTOMER_KEY
- fc.POLICY_ID = dp.POLICY_ID
- fi.INVESTIGATION_ID = ai.INVESTIGATION_ID

Rules:
- Use Spark SQL syntax. Always LIMIT to 50 rows max unless aggregates.
- Round monetary values to 2 decimal places. Use aliases: fi, fc, dc, dp, ai
- Return ONLY the SQL query, no explanation
"""

def extract_sql_from_response(text):
    """Extract clean SQL from AI response."""
    text = render_ai_response(text)
    code_block = re.search(r'```(?:sql)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if code_block:
        return code_block.group(1).strip()
    lines = text.strip().split('\n')
    sql_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith(('SELECT', 'WITH', 'FROM', 'WHERE', 'GROUP', 'ORDER',
                                        'HAVING', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'FULL',
                                        'ON', 'AND', 'OR', 'LIMIT', 'UNION', 'CASE', 'WHEN',
                                        'THEN', 'ELSE', 'END', 'AS', 'COUNT', 'SUM', 'AVG',
                                        'MAX', 'MIN', 'ROUND', 'CAST', 'COALESCE', '--', '(',
                                        ')', ',', 'fi.', 'fc.', 'dc.', 'dp.', 'ai.')):
            sql_lines.append(line)
        elif sql_lines:
            sql_lines.append(line)
    if sql_lines:
        return '\n'.join(sql_lines).strip().rstrip(';')
    return text.strip().rstrip(';')

def fraud_agent_query(user_question):
    """Multi-step Fraud Agent: Text-to-SQL-to-Insight."""
    result = {"answer": None, "sql": None, "data": None, "error": None, "steps": []}
    try:
        result["steps"].append("Analyzing your question...")
        sql_prompt = f"""{SCHEMA_CONTEXT}\n\nUser question: {user_question}\n\nGenerate a SQL query to answer this question. Return ONLY the SQL, nothing else."""
        sql_gen_query = f"SELECT ai_query('databricks-claude-sonnet-4-6', '{escape_sql(sql_prompt)}') AS generated_sql"
        try:
            sql_result = execute_sql(sql_gen_query)
        except RuntimeError as e:
            result["error"] = f"AI model call failed: {str(e)}"
            return result
        if sql_result.empty:
            result["error"] = "Failed to generate SQL query. The AI model may be unavailable."
            return result
        raw_sql = sql_result['generated_sql'].iloc[0]
        generated_sql = extract_sql_from_response(raw_sql)
        result["sql"] = generated_sql
        result["steps"].append("SQL query generated")

        result["steps"].append("Querying fraud database...")
        try:
            data_result = execute_sql(generated_sql)
        except RuntimeError as e:
            result["steps"].append("Query error, retrying...")
            data_result = pd.DataFrame()
        if data_result.empty:
            result["steps"].append("Retrying with simplified approach...")
            fallback_prompt = f"""{SCHEMA_CONTEXT}\n\nThe previous query returned no results. Generate a simpler SQL query.\nUse only fact_fraud_investigation (fi) if possible.\nQuestion: {user_question}\n\nReturn ONLY the SQL, nothing else."""
            try:
                fallback_gen = execute_sql(f"SELECT ai_query('databricks-claude-sonnet-4-6', '{escape_sql(fallback_prompt)}') AS generated_sql")
            except RuntimeError:
                fallback_gen = pd.DataFrame()
            if not fallback_gen.empty:
                fallback_sql = extract_sql_from_response(fallback_gen['generated_sql'].iloc[0])
                try:
                    data_result = execute_sql(fallback_sql)
                    result["sql"] = fallback_sql
                except RuntimeError:
                    pass

        result["data"] = data_result
        result["steps"].append(f"Retrieved {len(data_result)} rows")

        result["steps"].append("Analyzing results with AI...")
        if not data_result.empty:
            data_preview = data_result.head(30).to_string(index=False, max_colwidth=50)
            if len(data_preview) > 3000:
                data_preview = data_preview[:3000] + "\n... (truncated)"
            insight_prompt = f"""You are a senior fraud analyst at Salama Insurance.
Based on the data below, provide a clear, professional answer to the user's question.
Use specific numbers, percentages, and AED amounts from the data.
Format your response in clean markdown with bullet points where appropriate.
Be concise but insightful. Highlight any red flags or notable patterns.

User question: {user_question}

Query results:
{data_preview}

Row count: {len(data_result)}

Provide your analysis:"""
            try:
                insight_result = execute_sql(f"SELECT ai_query('databricks-claude-sonnet-4-6', '{escape_sql(insight_prompt)}') AS analysis")
            except RuntimeError:
                insight_result = pd.DataFrame()
            if not insight_result.empty:
                result["answer"] = render_ai_response(insight_result['analysis'].iloc[0])
            else:
                result["answer"] = f"Query returned {len(data_result)} rows. Review the data table below for details."
        else:
            result["answer"] = "The query returned no results. Try rephrasing your question or broadening the scope."
        result["steps"].append("Analysis complete")
    except Exception as e:
        result["error"] = f"Agent error: {str(e)}"
        result["steps"].append(f"Error: {str(e)}")
    return result


# Consistent Altair dark theme
CHART_CONFIG = {
    "background": "transparent",
    "font": "Inter",
    "axis": {
        "labelColor": "#94a3b8",
        "titleColor": "#cbd5e1",
        "gridColor": "rgba(255,255,255,0.05)",
        "domainColor": "rgba(255,255,255,0.1)",
        "tickColor": "rgba(255,255,255,0.1)",
        "labelFont": "Inter",
        "titleFont": "Inter",
        "labelFontSize": 12,
        "titleFontSize": 13,
        "titleFontWeight": 600,
    },
    "legend": {
        "labelColor": "#cbd5e1",
        "titleColor": "#e2e8f0",
        "labelFont": "Inter",
        "titleFont": "Inter",
    },
    "title": {
        "color": "#f1f5f9",
        "font": "Inter",
        "fontWeight": 700,
    },
    "view": {
        "stroke": "transparent",
    },
}
alt.themes.register("fraud_dark", lambda: {"config": CHART_CONFIG})
alt.themes.enable("fraud_dark")

# ============================================
# LOAD DATA
# ============================================
df = load_data()

# ============================================
# SIDEBAR NAVIGATION
# ============================================
with st.sidebar:
    st.markdown("""<div class="sidebar-brand">
        <div class="sidebar-brand-title">\U0001F6E1\uFE0F Middleeast Insurance</div>
        <div class="sidebar-brand-sub">Fraud Command Center</div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="sidebar-section-label">Analytics</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigate",
        [
            "\U0001F50D  Investigation Pipeline",
            "\U0001F4C8  Trend Analysis",
            "\U0001F3C6  Investigator Performance",
            "\U0001F4B0  ROI Analysis",
            "\U0001F916  GenAI Insights",
            "\U0001F9D1\U0000200D\U0001F4BC  AI Supervisor",
            "\U0001F4CA  Observability",
        ],
        label_visibility="collapsed",
        key="main_nav"
    )

    st.divider()

    # Quick stats in sidebar
    if not df.empty:
        st.markdown('<div class="sidebar-section-label">Quick Stats</div>', unsafe_allow_html=True)
        st.metric("Investigations", f"{len(df):,}")
        st.metric("Fraud Detected", f"AED {df['FRAUD_AMOUNT_DETECTED'].sum():,.0f}")
        recovery_rate = (df['RECOVERY_AMOUNT'].sum() / df['FRAUD_AMOUNT_DETECTED'].sum() * 100) if df['FRAUD_AMOUNT_DETECTED'].sum() > 0 else 0
        st.metric("Recovery Rate", f"{recovery_rate:.1f}%")

    st.divider()
    st.caption("Powered by Databricks Data Intelligence Platform")

# ============================================
# HEADER
# ============================================
st.markdown('<h1 class="gradient-title">Insurance Fraud Investigation Command Center</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Middleeast Insurance &bull; AI-Powered Fraud Analytics &bull; Databricks</p>', unsafe_allow_html=True)
st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

# ============================================
# TOP-LEVEL KPI METRICS
# ============================================
if df.empty:
    st.info("No data available or waiting on Data Connection. UI structure is preserved.")
else:
    col1, col2, col3, col4, col5 = st.columns(5, gap="medium")
    col1.metric("Total Investigations", f"{len(df):,}")
    col2.metric("Avg Fraud Score", f"{df['FRAUD_SCORE'].mean():.1f}")
    col3.metric("Fraud Detected", f"AED {df['FRAUD_AMOUNT_DETECTED'].sum():,.0f}")
    col4.metric("Amount Recovered", f"AED {df['RECOVERY_AMOUNT'].sum():,.0f}")
    recovery_rate = (df['RECOVERY_AMOUNT'].sum() / df['FRAUD_AMOUNT_DETECTED'].sum() * 100) if df['FRAUD_AMOUNT_DETECTED'].sum() > 0 else 0
    col5.metric("Recovery Rate", f"{recovery_rate:.1f}%")

st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

# ============================================
# PAGE CONTENT BASED ON SIDEBAR SELECTION
# ============================================

# --- PAGE: Investigation Pipeline ---
if page == "\U0001F50D  Investigation Pipeline":
    if not df.empty:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F50D</span>
            <span class="section-header-text">Investigation Pipeline Command Center</span>
        </div>""", unsafe_allow_html=True)
        st.caption("Operational command center for fraud case management. Claims flagged by ML risk scoring are automatically ingested and prioritized.")

        # ============================================================
        # PRIORITY TIER CLASSIFICATION
        # ============================================================
        # AI priority score = fraud_score * 0.6 + normalized_exposure * 0.4
        pipeline_df = df.copy()
        max_exposure = pipeline_df['FRAUD_AMOUNT_DETECTED'].max() if pipeline_df['FRAUD_AMOUNT_DETECTED'].max() > 0 else 1
        pipeline_df['normalized_exposure'] = (pipeline_df['FRAUD_AMOUNT_DETECTED'] / max_exposure * 100)
        pipeline_df['priority_score'] = (pipeline_df['FRAUD_SCORE'] * 0.6 + pipeline_df['normalized_exposure'] * 0.4).round(1)
        pipeline_df['priority_tier'] = pipeline_df['priority_score'].apply(
            lambda s: 'CRITICAL' if s >= 80 else ('HIGH' if s >= 60 else ('MEDIUM' if s >= 40 else 'LOW'))
        )

        # Priority Tier KPIs
        tier_counts = pipeline_df['priority_tier'].value_counts()
        active_cases = pipeline_df[pipeline_df['INVESTIGATION_STATUS'].isin(['INITIATED', 'IN_PROGRESS'])].shape[0]
        avg_resolution = pipeline_df[pipeline_df['INVESTIGATION_STATUS'] == 'COMPLETED']['INVESTIGATION_DAYS'].mean()
        sla_breach = pipeline_df[(pipeline_df['INVESTIGATION_STATUS'].isin(['INITIATED', 'IN_PROGRESS'])) & (pipeline_df['INVESTIGATION_DAYS'] > 30)].shape[0]

        pk1, pk2, pk3, pk4, pk5, pk6 = st.columns(6, gap="small")
        pk1.metric("\U0001F534 CRITICAL", tier_counts.get('CRITICAL', 0), help="Score \u2265 80")
        pk2.metric("\U0001F7E0 HIGH", tier_counts.get('HIGH', 0), help="Score 60-79")
        pk3.metric("\U0001F7E1 MEDIUM", tier_counts.get('MEDIUM', 0), help="Score 40-59")
        pk4.metric("\U0001F7E2 LOW", tier_counts.get('LOW', 0), help="Score < 40")
        pk5.metric("Active Pipeline", f"{active_cases:,}", help="INITIATED + IN_PROGRESS")
        pk6.metric("SLA Breaches", sla_breach, delta=">30 days", delta_color="inverse")

        st.markdown("---")

        # ============================================================
        # SECTION 1: PIPELINE FLOW & STATUS
        # ============================================================
        st.subheader("\U0001F504 Pipeline Flow & Status Tracking")

        pf1, pf2 = st.columns([3, 2], gap="large")
        with pf1:
            # Status breakdown with tier overlay
            status_tier = pipeline_df.groupby(['INVESTIGATION_STATUS', 'priority_tier']).agg(
                cases=('INVESTIGATION_ID', 'count')
            ).reset_index()
            order = ['INITIATED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED']
            tier_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

            flow_chart = alt.Chart(status_tier).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X('INVESTIGATION_STATUS:N', sort=order, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y('cases:Q', title='Cases', stack='zero'),
                color=alt.Color('priority_tier:N', sort=tier_order, scale=alt.Scale(
                    domain=tier_order, range=['#dc2626', '#f59e0b', '#eab308', '#10b981']
                ), title='Priority Tier'),
                tooltip=['INVESTIGATION_STATUS', 'priority_tier', alt.Tooltip('cases:Q', title='Cases')]
            ).properties(height=320, title='Pipeline Stages by Priority Tier')
            st.altair_chart(flow_chart, use_container_width=True)

        with pf2:
            # Funnel metrics
            status_counts = pipeline_df['INVESTIGATION_STATUS'].value_counts()
            funnel_data = pd.DataFrame({
                'Stage': order,
                'Count': [status_counts.get(s, 0) for s in order]
            })
            funnel_data['Pct'] = (funnel_data['Count'] / funnel_data['Count'].sum() * 100).round(1)

            st.markdown("**Pipeline Funnel**")
            for _, row in funnel_data.iterrows():
                bar_width = int(row['Pct'] * 2.5)
                color = {'INITIATED': '#6366f1', 'IN_PROGRESS': '#f59e0b', 'COMPLETED': '#10b981', 'CLOSED': '#64748b'}.get(row['Stage'], '#888')
                st.markdown(f"""
                <div style="margin-bottom:8px;">
                    <div style="font-size:0.8rem;color:#94a3b8;">{row['Stage']}</div>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <div style="height:24px;width:{max(bar_width, 8)}%;background:{color};border-radius:4px;min-width:30px;"></div>
                        <span style="font-weight:600;">{int(row['Count'])} ({row['Pct']}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Transition rates
            initiated = status_counts.get('INITIATED', 0)
            in_progress = status_counts.get('IN_PROGRESS', 0)
            completed = status_counts.get('COMPLETED', 0)
            closed = status_counts.get('CLOSED', 0)
            st.markdown("**Transition Rates**")
            if initiated > 0:
                st.markdown(f"INITIATED \u2192 IN_PROGRESS: **{in_progress/(initiated+in_progress)*100:.0f}%**" if (initiated+in_progress) > 0 else "")
            if (in_progress + completed) > 0:
                st.markdown(f"IN_PROGRESS \u2192 COMPLETED: **{completed/(in_progress+completed)*100:.0f}%**")

        # Original charts (enhanced)
        st.markdown("---")
        oc1, oc2 = st.columns(2, gap="large")
        with oc1:
            st.markdown("""<div class="section-header">
                <span class="section-header-icon">\U0001F4CA</span>
                <span class="section-header-text">By Status</span>
            </div>""", unsafe_allow_html=True)
            status_df = df.groupby('INVESTIGATION_STATUS').agg(Count=('INVESTIGATION_ID', 'count'), Avg_Score=('FRAUD_SCORE', 'mean'), Total_Cost=('INVESTIGATION_COST', 'sum')).reset_index()
            status_df['INVESTIGATION_STATUS'] = pd.Categorical(status_df['INVESTIGATION_STATUS'], categories=order, ordered=True)
            status_df = status_df.sort_values('INVESTIGATION_STATUS')
            chart = alt.Chart(status_df).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, opacity=0.9).encode(
                x=alt.X('INVESTIGATION_STATUS:N', sort=order, title='Status', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Count:Q', title='Investigations'),
                color=alt.Color('INVESTIGATION_STATUS:N', scale=alt.Scale(domain=order, range=['#6366f1', '#f59e0b', '#10b981', '#64748b']), legend=None),
                tooltip=[alt.Tooltip('INVESTIGATION_STATUS:N', title='Status'), alt.Tooltip('Count:Q', title='Cases'), alt.Tooltip('Avg_Score:Q', format='.1f', title='Avg Score'), alt.Tooltip('Total_Cost:Q', format=',.0f', title='Total Cost (AED)')]
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)

        with oc2:
            st.markdown("""<div class="section-header">
                <span class="section-header-icon">\U0001F3AF</span>
                <span class="section-header-text">By Findings</span>
            </div>""", unsafe_allow_html=True)
            findings_df = df.groupby('FINDINGS').agg(Count=('INVESTIGATION_ID', 'count'), Avg_Score=('FRAUD_SCORE', 'mean'), Total_Detected=('FRAUD_AMOUNT_DETECTED', 'sum')).reset_index()
            chart2 = alt.Chart(findings_df).mark_arc(innerRadius=70, outerRadius=140, padAngle=0.03, cornerRadius=4).encode(
                theta=alt.Theta('Count:Q'),
                color=alt.Color('FINDINGS:N', scale=alt.Scale(domain=['FRAUD_CONFIRMED', 'FRAUD_SUSPECTED', 'INCONCLUSIVE', 'NO_FRAUD'], range=['#f43f5e', '#f59e0b', '#00C2A8', '#6366f1'])),
                tooltip=[alt.Tooltip('FINDINGS:N', title='Finding'), alt.Tooltip('Count:Q', title='Cases'), alt.Tooltip('Avg_Score:Q', format='.1f', title='Avg Score'), alt.Tooltip('Total_Detected:Q', format=',.0f', title='Fraud Detected (AED)')]
            ).properties(height=320)
            st.altair_chart(chart2, use_container_width=True)

        st.markdown("---")

        # ============================================================
        # SECTION 2: AI-RANKED CASE QUEUE
        # ============================================================
        st.subheader("\U0001F916 AI-Ranked Case Assignment Queue")
        st.caption("Cases ranked by composite priority score (60% fraud probability + 40% financial exposure). Auto-assigned to investigators based on capacity and specialization.")

        # Active queue - only INITIATED and IN_PROGRESS
        active_queue = pipeline_df[pipeline_df['INVESTIGATION_STATUS'].isin(['INITIATED', 'IN_PROGRESS'])].copy()
        active_queue = active_queue.sort_values('priority_score', ascending=False)

        if not active_queue.empty:
            aq1, aq2 = st.columns([2, 1], gap="large")
            with aq1:
                # Priority score distribution
                score_hist = alt.Chart(active_queue).mark_bar(cornerRadiusEnd=3, opacity=0.8).encode(
                    x=alt.X('priority_score:Q', bin=alt.Bin(maxbins=20), title='Priority Score'),
                    y=alt.Y('count():Q', title='Cases'),
                    color=alt.Color('priority_tier:N', sort=tier_order, scale=alt.Scale(
                        domain=tier_order, range=['#dc2626', '#f59e0b', '#eab308', '#10b981']
                    ), title='Tier'),
                    tooltip=['priority_tier:N', 'count():Q']
                ).properties(height=250, title='Active Queue: Priority Score Distribution')
                st.altair_chart(score_hist, use_container_width=True)

            with aq2:
                # Assignment concentration
                inv_load = active_queue.groupby('INVESTIGATOR_ID').agg(
                    assigned=('INVESTIGATION_ID', 'count'),
                    avg_priority=('priority_score', 'mean'),
                    critical_cases=('priority_tier', lambda x: (x == 'CRITICAL').sum())
                ).reset_index().sort_values('assigned', ascending=False)

                st.markdown("**Investigator Load (Active)**")
                overloaded = inv_load[inv_load['assigned'] > inv_load['assigned'].quantile(0.75)]
                if not overloaded.empty:
                    st.warning(f"{len(overloaded)} investigator(s) above 75th percentile workload")
                st.dataframe(
                    inv_load.head(8).rename(columns={'INVESTIGATOR_ID': 'Investigator', 'assigned': 'Active Cases', 'avg_priority': 'Avg Priority', 'critical_cases': 'Critical'}),
                    use_container_width=True, hide_index=True
                )

            # Top priority cases table
            queue_display = active_queue.head(20)[['INVESTIGATION_ID', 'priority_score', 'priority_tier', 'FRAUD_SCORE',
                                                   'FRAUD_AMOUNT_DETECTED', 'INVESTIGATION_STATUS', 'INVESTIGATION_DAYS',
                                                   'INVESTIGATOR_ID']].copy()
            queue_display.columns = ['Case ID', 'Priority Score', 'Tier', 'Fraud Score', 'Exposure (AED)', 'Status', 'Days Open', 'Assigned To']
            enhanced_dataframe(queue_display, title="Top 20 Priority Cases", key_prefix="ai_queue", height=350)
        else:
            st.success("\u2705 No active cases in pipeline. All investigations resolved.")

        st.markdown("---")

        # ============================================================
        # SECTION 3: SLA MONITORING & AGING
        # ============================================================
        st.subheader("\u23F1\uFE0F SLA Monitoring & Case Aging")

        sla1, sla2 = st.columns(2, gap="large")
        with sla1:
            # Aging distribution by priority tier
            aging_data = pipeline_df[pipeline_df['INVESTIGATION_STATUS'].isin(['INITIATED', 'IN_PROGRESS'])].copy()
            if not aging_data.empty:
                aging_data['aging_bucket'] = aging_data['INVESTIGATION_DAYS'].apply(
                    lambda d: '0-7 days' if d <= 7 else ('8-14 days' if d <= 14 else ('15-30 days' if d <= 30 else ('31-60 days' if d <= 60 else '60+ days')))
                )
                bucket_order = ['0-7 days', '8-14 days', '15-30 days', '31-60 days', '60+ days']

                aging_chart = alt.Chart(aging_data).mark_bar(cornerRadiusEnd=3).encode(
                    x=alt.X('aging_bucket:N', sort=bucket_order, title=None, axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y('count():Q', title='Cases'),
                    color=alt.Color('priority_tier:N', sort=tier_order, scale=alt.Scale(
                        domain=tier_order, range=['#dc2626', '#f59e0b', '#eab308', '#10b981']
                    ), title='Tier'),
                    tooltip=['aging_bucket:N', 'priority_tier:N', 'count():Q']
                ).properties(height=280, title='Case Aging Distribution (Active Pipeline)')
                st.altair_chart(aging_chart, use_container_width=True)
            else:
                st.info("No active cases for aging analysis.")

        with sla2:
            # SLA compliance metrics
            sla_thresholds = {'CRITICAL': 7, 'HIGH': 14, 'MEDIUM': 30, 'LOW': 60}
            sla_results = []
            for tier, threshold in sla_thresholds.items():
                tier_active = pipeline_df[(pipeline_df['priority_tier'] == tier) & (pipeline_df['INVESTIGATION_STATUS'].isin(['INITIATED', 'IN_PROGRESS']))]
                total = len(tier_active)
                breached = len(tier_active[tier_active['INVESTIGATION_DAYS'] > threshold])
                compliance = ((total - breached) / total * 100) if total > 0 else 100
                sla_results.append({'Tier': tier, 'SLA (days)': threshold, 'Active': total, 'Breached': breached, 'Compliance': compliance})

            sla_df = pd.DataFrame(sla_results)
            st.markdown("**SLA Compliance by Priority Tier**")
            for _, row in sla_df.iterrows():
                color = '#10b981' if row['Compliance'] >= 80 else ('#f59e0b' if row['Compliance'] >= 60 else '#ef4444')
                icon = '\u2705' if row['Compliance'] >= 80 else ('\u26A0\uFE0F' if row['Compliance'] >= 60 else '\U0001F6A8')
                st.markdown(f"""
                <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 12px;margin:4px 0;background:rgba(255,255,255,0.03);border-radius:6px;border-left:3px solid {color};">
                    <span>{icon} <strong>{row['Tier']}</strong> (SLA: {int(row['SLA (days)'])}d)</span>
                    <span style="color:{color};font-weight:700;">{row['Compliance']:.0f}%</span>
                    <span style="font-size:0.8rem;color:#94a3b8;">{int(row['Breached'])}/{int(row['Active'])} breached</span>
                </div>
                """, unsafe_allow_html=True)

            # Overall SLA alert
            overall_compliance = sla_df['Compliance'].mean()
            if overall_compliance < 70:
                st.error(f"\U0001F6A8 Overall SLA compliance at {overall_compliance:.0f}% \u2014 immediate resource reallocation needed")
            elif overall_compliance < 85:
                st.warning(f"\u26A0\uFE0F SLA compliance at {overall_compliance:.0f}% \u2014 monitor CRITICAL/HIGH tier closely")
            else:
                st.success(f"\u2705 SLA compliance healthy at {overall_compliance:.0f}%")

        st.markdown("---")

        # ============================================================
        # SECTION 4: INVESTIGATOR WORKLOAD & AUDIT TRAIL
        # ============================================================
        st.subheader("\U0001F4CB Audit Trail & Workload Analysis")

        at1, at2 = st.columns(2, gap="large")
        with at1:
            # Resolution time by priority tier (completed cases)
            completed_cases = pipeline_df[pipeline_df['INVESTIGATION_STATUS'].isin(['COMPLETED', 'CLOSED'])].copy()
            if not completed_cases.empty:
                resolution_by_tier = completed_cases.groupby('priority_tier').agg(
                    avg_days=('INVESTIGATION_DAYS', 'mean'),
                    median_days=('INVESTIGATION_DAYS', 'median'),
                    cases=('INVESTIGATION_ID', 'count')
                ).reset_index()
                resolution_by_tier['priority_tier'] = pd.Categorical(resolution_by_tier['priority_tier'], categories=tier_order, ordered=True)
                resolution_by_tier = resolution_by_tier.sort_values('priority_tier')

                res_chart = alt.Chart(resolution_by_tier).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X('priority_tier:N', sort=tier_order, title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('avg_days:Q', title='Avg Resolution Days'),
                    color=alt.Color('priority_tier:N', sort=tier_order, scale=alt.Scale(
                        domain=tier_order, range=['#dc2626', '#f59e0b', '#eab308', '#10b981']
                    ), legend=None),
                    tooltip=['priority_tier', alt.Tooltip('avg_days:Q', format='.1f', title='Avg Days'),
                            alt.Tooltip('median_days:Q', format='.0f', title='Median Days'),
                            alt.Tooltip('cases:Q', title='Resolved Cases')]
                ).properties(height=280, title='Avg Resolution Time by Priority Tier')
                st.altair_chart(res_chart, use_container_width=True)
            else:
                st.info("No completed cases for resolution analysis.")

        with at2:
            # Investigator efficiency scatter
            inv_efficiency = pipeline_df.groupby('INVESTIGATOR_ID').agg(
                total_cases=('INVESTIGATION_ID', 'count'),
                avg_days=('INVESTIGATION_DAYS', 'mean'),
                avg_priority=('priority_score', 'mean'),
                confirmed=('FINDINGS', lambda x: (x == 'FRAUD_CONFIRMED').sum()),
                total_recovered=('RECOVERY_AMOUNT', 'sum')
            ).reset_index()
            inv_efficiency['confirm_rate'] = (inv_efficiency['confirmed'] / inv_efficiency['total_cases'] * 100).round(1)

            scatter = alt.Chart(inv_efficiency).mark_circle(opacity=0.7).encode(
                x=alt.X('avg_days:Q', title='Avg Investigation Days', scale=alt.Scale(zero=False)),
                y=alt.Y('confirm_rate:Q', title='Confirmation Rate (%)', scale=alt.Scale(zero=False)),
                size=alt.Size('total_cases:Q', title='Caseload', scale=alt.Scale(range=[60, 400])),
                color=alt.Color('avg_priority:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True), title='Avg Priority'),
                tooltip=['INVESTIGATOR_ID', alt.Tooltip('total_cases:Q', title='Cases'),
                        alt.Tooltip('avg_days:Q', format='.1f', title='Avg Days'),
                        alt.Tooltip('confirm_rate:Q', format='.1f', title='Confirm %'),
                        alt.Tooltip('total_recovered:Q', format=',.0f', title='Recovered (AED)')]
            ).properties(height=280, title='Investigator Efficiency (Speed vs Accuracy)')
            st.altair_chart(scatter, use_container_width=True)

        # Detailed audit table
        with st.expander("\U0001F4C4 Full Case Audit Trail", expanded=False):
            audit_display = pipeline_df[['INVESTIGATION_ID', 'priority_score', 'priority_tier', 'FRAUD_SCORE',
                                         'FRAUD_AMOUNT_DETECTED', 'RECOVERY_AMOUNT', 'INVESTIGATION_STATUS',
                                         'FINDINGS', 'INVESTIGATION_DAYS', 'INVESTIGATOR_ID', 'MONTHYEAR']].copy()
            audit_display = audit_display.sort_values('priority_score', ascending=False)
            audit_display.columns = ['Case ID', 'Priority', 'Tier', 'Fraud Score', 'Exposure (AED)',
                                     'Recovery (AED)', 'Status', 'Finding', 'Days', 'Investigator', 'Month']
            st.dataframe(audit_display, use_container_width=True, hide_index=True, height=400)

        st.markdown("---")

        # ============================================================
        # SECTION 5: HIGH RISK INVESTIGATIONS TABLE
        # ============================================================
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U000026A0\U0000FE0F</span>
            <span class="section-header-text">High Risk Investigations (Fraud Score > 75)</span>
        </div>""", unsafe_allow_html=True)
        high_risk = df[df['FRAUD_SCORE'] > 75][['INVESTIGATION_ID', 'FRAUD_SCORE', 'INVESTIGATION_STATUS', 'FINDINGS', 'FRAUD_AMOUNT_DETECTED', 'RECOVERY_AMOUNT', 'INVESTIGATION_DAYS', 'INVESTIGATOR_ID']].sort_values('FRAUD_SCORE', ascending=False).reset_index(drop=True)
        enhanced_dataframe(high_risk, title="High Risk Investigations", key_prefix="hr_tbl", height=400)

# --- PAGE: Trend Analysis ---
elif page == "\U0001F4C8  Trend Analysis":
    if not df.empty:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4C8</span>
            <span class="section-header-text">Trend Analysis \u2014 Temporal & Categorical Analytics</span>
        </div>""", unsafe_allow_html=True)
        st.caption("Identify emerging schemes, geographic concentrations, and claim-type anomalies before they escalate.")

        if 'MONTHYEAR' in df.columns:
            # Ensure MONTHYEAR_SORT is numeric for proper sorting
            df['MONTHYEAR_SORT'] = pd.to_numeric(df['MONTHYEAR_SORT'], errors='coerce').fillna(0).astype(int)

            # === SECTION 1: Enhanced Time-Series with MoM% Change ===
            st.markdown("""<div class="glass-card"><div class="section-header">
                <span class="section-header-icon">\U0001F4C8</span>
                <span class="section-header-text">Time-Series Trends with Month-over-Month Change</span>
            </div>""", unsafe_allow_html=True)

            monthly = df.groupby(['MONTHYEAR', 'MONTHYEAR_SORT']).agg(
                Investigations=('INVESTIGATION_ID', 'count'),
                Avg_Fraud_Score=('FRAUD_SCORE', 'mean'),
                Fraud_Detected=('FRAUD_AMOUNT_DETECTED', 'sum'),
                Recovery=('RECOVERY_AMOUNT', 'sum'),
                Cost=('INVESTIGATION_COST', 'sum'),
            ).reset_index().sort_values('MONTHYEAR_SORT')

            # Calculate MoM% change
            for col in ['Investigations', 'Avg_Fraud_Score', 'Fraud_Detected', 'Recovery', 'Cost']:
                monthly[f'{col}_MoM'] = monthly[col].pct_change() * 100

            tc1, tc2 = st.columns([3, 1])
            with tc2:
                metric_choice = st.selectbox("Primary Metric", ["Investigations", "Avg_Fraud_Score", "Fraud_Detected", "Recovery", "Cost"], key="trend_metric")
                show_mom = st.checkbox("Show MoM% Change", value=True, key="trend_mom")

            with tc1:
                sort_order = monthly['MONTHYEAR'].tolist()
                base = alt.Chart(monthly).encode(
                    x=alt.X('MONTHYEAR:N', sort=sort_order, title=None, axis=alt.Axis(labelAngle=-45)),
                    tooltip=['MONTHYEAR', alt.Tooltip(f'{metric_choice}:Q', format=',.1f')]
                )
                area = base.mark_area(line=True, opacity=0.12, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#6366f1', offset=0), alt.GradientStop(color='transparent', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )).encode(y=alt.Y(f'{metric_choice}:Q', title=metric_choice.replace('_', ' ')))
                line = base.mark_line(strokeWidth=2.5, color='#6366f1').encode(y=alt.Y(f'{metric_choice}:Q'))
                points = base.mark_circle(size=50, color='#818cf8', opacity=1).encode(y=alt.Y(f'{metric_choice}:Q'))
                trend_chart = (area + line + points).properties(height=350)
                st.altair_chart(trend_chart, use_container_width=True)

            if show_mom and f'{metric_choice}_MoM' in monthly.columns:
                mom_col = f'{metric_choice}_MoM'
                mom_chart = alt.Chart(monthly.dropna(subset=[mom_col])).mark_bar(cornerRadiusEnd=3).encode(
                    x=alt.X('MONTHYEAR:N', sort=sort_order, title=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y(f'{mom_col}:Q', title='MoM Change (%)'),
                    color=alt.condition(
                        alt.datum[mom_col] > 0,
                        alt.value('#ef4444'),
                        alt.value('#10b981')
                    ),
                    tooltip=['MONTHYEAR', alt.Tooltip(f'{mom_col}:Q', format='+.1f', title='MoM %')]
                ).properties(height=180, title=f'{metric_choice} \u2014 Month-over-Month % Change')
                st.altair_chart(mom_chart, use_container_width=True)

            # Trend summary KPIs
            if len(monthly) >= 2:
                latest = monthly.iloc[-1]
                prev = monthly.iloc[-2]
                tm1, tm2, tm3, tm4 = st.columns(4, gap="small")
                inv_chg = ((latest['Investigations'] - prev['Investigations']) / prev['Investigations'] * 100) if prev['Investigations'] > 0 else 0
                fraud_chg = ((latest['Fraud_Detected'] - prev['Fraud_Detected']) / prev['Fraud_Detected'] * 100) if prev['Fraud_Detected'] > 0 else 0
                rec_chg = ((latest['Recovery'] - prev['Recovery']) / prev['Recovery'] * 100) if prev['Recovery'] > 0 else 0
                score_chg = latest['Avg_Fraud_Score'] - prev['Avg_Fraud_Score']
                tm1.metric("Latest Investigations", f"{int(latest['Investigations']):,}", delta=f"{inv_chg:+.1f}%")
                tm2.metric("Fraud Detected (AED)", f"{latest['Fraud_Detected']:,.0f}", delta=f"{fraud_chg:+.1f}%")
                tm3.metric("Recovery (AED)", f"{latest['Recovery']:,.0f}", delta=f"{rec_chg:+.1f}%")
                tm4.metric("Avg Fraud Score", f"{latest['Avg_Fraud_Score']:.1f}", delta=f"{score_chg:+.1f}")

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")

            # === SECTION 2: Cohort Heatmap for Emerging Scheme Detection ===
            st.markdown("""<div class="glass-card"><div class="section-header">
                <span class="section-header-icon">\U0001F9EA</span>
                <span class="section-header-text">Cohort Analysis \u2014 Emerging Scheme Detection</span>
            </div>""", unsafe_allow_html=True)

            try:
                cohort_query = """
                    SELECT fc.CLAIM_TYPE, fc.BUSINESS_LINE, fi.MONTHYEAR, fi.MONTHYEAR_SORT,
                           COUNT(*) as cases, AVG(fi.FRAUD_SCORE) as avg_score,
                           SUM(fi.FRAUD_AMOUNT_DETECTED) as total_fraud,
                           SUM(CASE WHEN fi.FINDINGS = 'FRAUD_CONFIRMED' THEN 1 ELSE 0 END) as confirmed
                    FROM uae_insurance.uae_silver.fact_fraud_investigation fi
                    JOIN uae_insurance.uae_silver.fact_claim fc
                        ON fi.FRAUD_KEY_NEW = fc.FRAUD_KEY_NEW
                    GROUP BY fc.CLAIM_TYPE, fc.BUSINESS_LINE, fi.MONTHYEAR, fi.MONTHYEAR_SORT
                    ORDER BY fi.MONTHYEAR_SORT
                """
                cohort_df = execute_sql(cohort_query)

                if not cohort_df.empty:
                    cohort_df['MONTHYEAR_SORT'] = pd.to_numeric(cohort_df['MONTHYEAR_SORT'], errors='coerce').fillna(0).astype(int)
                    cohort_df['cases'] = pd.to_numeric(cohort_df['cases'], errors='coerce').fillna(0)
                    cohort_df['avg_score'] = pd.to_numeric(cohort_df['avg_score'], errors='coerce').fillna(0)
                    cohort_df['total_fraud'] = pd.to_numeric(cohort_df['total_fraud'], errors='coerce').fillna(0)
                    cohort_df['confirmed'] = pd.to_numeric(cohort_df['confirmed'], errors='coerce').fillna(0)

                    ch_tab1, ch_tab2 = st.tabs(["\U0001F525 By Claim Type", "\U0001F3E2 By Business Line"])

                    with ch_tab1:
                        heatmap_data = cohort_df.groupby(['CLAIM_TYPE', 'MONTHYEAR', 'MONTHYEAR_SORT']).agg(
                            cases=('cases', 'sum'), avg_score=('avg_score', 'mean')
                        ).reset_index()
                        sort_months = heatmap_data.sort_values('MONTHYEAR_SORT')['MONTHYEAR'].unique().tolist()

                        heatmap = alt.Chart(heatmap_data).mark_rect(cornerRadius=3).encode(
                            x=alt.X('MONTHYEAR:N', sort=sort_months, title=None, axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y('CLAIM_TYPE:N', title=None),
                            color=alt.Color('cases:Q', scale=alt.Scale(scheme='inferno'), title='Cases'),
                            tooltip=[
                                alt.Tooltip('CLAIM_TYPE', title='Claim Type'),
                                alt.Tooltip('MONTHYEAR', title='Month'),
                                alt.Tooltip('cases:Q', title='Cases'),
                                alt.Tooltip('avg_score:Q', title='Avg Score', format='.1f')
                            ]
                        ).properties(height=380, title='Fraud Investigation Volume by Claim Type')
                        st.altair_chart(heatmap, use_container_width=True)

                        # Emerging scheme alerts
                        type_monthly = cohort_df.groupby(['CLAIM_TYPE', 'MONTHYEAR_SORT']).agg(cases=('cases', 'sum')).reset_index()
                        type_monthly = type_monthly.sort_values(['CLAIM_TYPE', 'MONTHYEAR_SORT'])
                        type_monthly['prev_cases'] = type_monthly.groupby('CLAIM_TYPE')['cases'].shift(1)
                        type_monthly['growth'] = ((type_monthly['cases'] - type_monthly['prev_cases']) / type_monthly['prev_cases'] * 100)
                        latest_sort = type_monthly['MONTHYEAR_SORT'].max()
                        alerts = type_monthly[(type_monthly['MONTHYEAR_SORT'] == latest_sort) & (type_monthly['growth'] > 50)]

                        if not alerts.empty:
                            st.markdown("**\u26A0\uFE0F Emerging Scheme Alerts** (>50% MoM growth in latest month):")
                            for _, row in alerts.iterrows():
                                st.markdown(f"- **{row['CLAIM_TYPE']}**: +{row['growth']:.0f}% ({int(row['prev_cases'])} \u2192 {int(row['cases'])} cases)")
                        else:
                            st.success("No anomalous scheme acceleration detected in the latest period.")

                    with ch_tab2:
                        bl_monthly = cohort_df.groupby(['BUSINESS_LINE', 'MONTHYEAR', 'MONTHYEAR_SORT']).agg(
                            cases=('cases', 'sum'), total_fraud=('total_fraud', 'sum')
                        ).reset_index().sort_values('MONTHYEAR_SORT')
                        sort_months_bl = bl_monthly.sort_values('MONTHYEAR_SORT')['MONTHYEAR'].unique().tolist()

                        bl_chart = alt.Chart(bl_monthly).mark_area(opacity=0.7).encode(
                            x=alt.X('MONTHYEAR:N', sort=sort_months_bl, title=None, axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y('cases:Q', title='Cases', stack='zero'),
                            color=alt.Color('BUSINESS_LINE:N', scale=alt.Scale(scheme='tableau10'), title='Business Line'),
                            tooltip=[
                                alt.Tooltip('BUSINESS_LINE'),
                                alt.Tooltip('MONTHYEAR'),
                                alt.Tooltip('cases:Q', title='Cases'),
                                alt.Tooltip('total_fraud:Q', title='Fraud Detected', format=',.0f')
                            ]
                        ).properties(height=350, title='Fraud Cases by Business Line (Stacked)')
                        st.altair_chart(bl_chart, use_container_width=True)

                        bl_total = bl_monthly.groupby('MONTHYEAR')['cases'].transform('sum')
                        bl_monthly['pct_share'] = (bl_monthly['cases'] / bl_total * 100).round(1)
                        bl_pct_chart = alt.Chart(bl_monthly).mark_area(opacity=0.85).encode(
                            x=alt.X('MONTHYEAR:N', sort=sort_months_bl, title=None, axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y('pct_share:Q', title='% Share', stack='normalize'),
                            color=alt.Color('BUSINESS_LINE:N', scale=alt.Scale(scheme='tableau10')),
                            tooltip=['BUSINESS_LINE', 'MONTHYEAR', alt.Tooltip('pct_share:Q', format='.1f', title='% Share')]
                        ).properties(height=280, title='Business Line Composition Shift Over Time')
                        st.altair_chart(bl_pct_chart, use_container_width=True)

            except Exception as e:
                st.warning(f"Cohort analysis unavailable: {e}")

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")

            # === SECTION 3: Geographic Fraud Concentration by Emirates ===
            st.markdown("""<div class="glass-card"><div class="section-header">
                <span class="section-header-icon">\U0001F30D</span>
                <span class="section-header-text">Geographic Fraud Concentration by Emirates</span>
            </div>""", unsafe_allow_html=True)

            try:
                geo_query = """
                    SELECT dc.EMIRATES as emirate,
                           COUNT(fi.INVESTIGATION_ID) as investigations,
                           AVG(fi.FRAUD_SCORE) as avg_fraud_score,
                           SUM(fi.FRAUD_AMOUNT_DETECTED) as total_fraud_detected,
                           SUM(fi.RECOVERY_AMOUNT) as total_recovery,
                           SUM(CASE WHEN fi.FINDINGS = 'FRAUD_CONFIRMED' THEN 1 ELSE 0 END) as confirmed_fraud,
                           MAX(le.`"population"`) as population
                    FROM uae_insurance.uae_silver.fact_fraud_investigation fi
                    JOIN uae_insurance.uae_silver.fact_claim fc
                        ON fi.FRAUD_KEY_NEW = fc.FRAUD_KEY_NEW
                    JOIN uae_insurance.uae_silver.dim_customer dc
                        ON fc.CUSTOMER_KEY = dc.CUSTOMER_KEY
                    LEFT JOIN uae_insurance.uae_silver.lookup_emirates le
                        ON dc.EMIRATES = le.`"emirates_code"`
                    WHERE dc.EMIRATES IS NOT NULL
                    GROUP BY dc.EMIRATES
                    ORDER BY investigations DESC
                """
                geo_df = execute_sql(geo_query)

                if not geo_df.empty:
                    for col in ['investigations', 'avg_fraud_score', 'total_fraud_detected', 'total_recovery', 'confirmed_fraud', 'population']:
                        geo_df[col] = pd.to_numeric(geo_df[col], errors='coerce').fillna(0)

                    geo_df['fraud_per_100k'] = (geo_df['investigations'] / geo_df['population'].replace(0, 1) * 100000).round(1)
                    geo_df.loc[geo_df['population'] == 0, 'fraud_per_100k'] = 0
                    geo_df['confirmation_rate'] = (geo_df['confirmed_fraud'] / geo_df['investigations'].replace(0, 1) * 100).round(1)
                    geo_df['avg_fraud_per_case'] = (geo_df['total_fraud_detected'] / geo_df['investigations'].replace(0, 1)).round(0)

                    gc1, gc2, gc3, gc4 = st.columns(4, gap="small")
                    top_emirate = geo_df.iloc[0]
                    highest_density = geo_df.loc[geo_df['fraud_per_100k'].idxmax()] if (geo_df['fraud_per_100k'] > 0).any() else geo_df.iloc[0]
                    gc1.metric("Most Cases", f"{top_emirate['emirate']}", delta=f"{int(top_emirate['investigations'])} cases")
                    gc2.metric("Highest Density", f"{highest_density['emirate']}", delta=f"{highest_density['fraud_per_100k']:.0f}/100k pop")
                    gc3.metric("Total Fraud (AED)", f"{geo_df['total_fraud_detected'].sum():,.0f}")
                    gc4.metric("Avg Confirmation", f"{geo_df['confirmation_rate'].mean():.1f}%")

                    geo_col1, geo_col2 = st.columns(2)
                    with geo_col1:
                        bar_geo = alt.Chart(geo_df).mark_bar(cornerRadiusEnd=4).encode(
                            x=alt.X('investigations:Q', title='Investigations'),
                            y=alt.Y('emirate:N', sort='-x', title=None),
                            color=alt.Color('avg_fraud_score:Q', scale=alt.Scale(scheme='reds'), title='Avg Score'),
                            tooltip=[
                                alt.Tooltip('emirate', title='Emirate'),
                                alt.Tooltip('investigations:Q', title='Cases'),
                                alt.Tooltip('avg_fraud_score:Q', format='.1f', title='Avg Fraud Score'),
                                alt.Tooltip('total_fraud_detected:Q', format=',.0f', title='Total Fraud (AED)'),
                            ]
                        ).properties(height=280, title='Fraud Investigations by Emirate')
                        st.altair_chart(bar_geo, use_container_width=True)

                    with geo_col2:
                        bar_density = alt.Chart(geo_df[geo_df['population'] > 0]).mark_bar(cornerRadiusEnd=4).encode(
                            x=alt.X('fraud_per_100k:Q', title='Cases per 100k Population'),
                            y=alt.Y('emirate:N', sort='-x', title=None),
                            color=alt.Color('confirmation_rate:Q', scale=alt.Scale(scheme='oranges'), title='Confirm %'),
                            tooltip=[
                                alt.Tooltip('emirate', title='Emirate'),
                                alt.Tooltip('fraud_per_100k:Q', format='.1f', title='Per 100k'),
                                alt.Tooltip('confirmation_rate:Q', format='.1f', title='Confirm Rate %'),
                                alt.Tooltip('population:Q', format=',.0f', title='Population'),
                            ]
                        ).properties(height=280, title='Fraud Density (Population-Normalized)')
                        st.altair_chart(bar_density, use_container_width=True)

                    with st.expander("Detailed Geographic Breakdown", expanded=False):
                        display_geo = geo_df[['emirate', 'investigations', 'fraud_per_100k', 'avg_fraud_score',
                                              'total_fraud_detected', 'total_recovery', 'confirmation_rate', 'avg_fraud_per_case']].copy()
                        display_geo.columns = ['Emirate', 'Cases', 'Per 100k Pop', 'Avg Score', 'Total Fraud (AED)',
                                              'Recovery (AED)', 'Confirm Rate %', 'Avg Fraud/Case (AED)']
                        st.dataframe(display_geo, use_container_width=True, hide_index=True)

            except Exception as e:
                st.warning(f"Geographic analysis unavailable: {e}")

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")

            # === SECTION 4: Business Line Trend Decomposition ===
            st.markdown("""<div class="glass-card"><div class="section-header">
                <span class="section-header-icon">\U0001F3ED</span>
                <span class="section-header-text">Business Line Trend Decomposition</span>
            </div>""", unsafe_allow_html=True)

            try:
                bl_decomp_query = """
                    SELECT fc.BUSINESS_LINE, fi.MONTHYEAR, fi.MONTHYEAR_SORT,
                           COUNT(*) as cases,
                           SUM(fi.FRAUD_AMOUNT_DETECTED) as fraud_amount,
                           SUM(fi.RECOVERY_AMOUNT) as recovery,
                           AVG(fi.FRAUD_SCORE) as avg_score,
                           AVG(fi.INVESTIGATION_DAYS) as avg_days
                    FROM uae_insurance.uae_silver.fact_fraud_investigation fi
                    JOIN uae_insurance.uae_silver.fact_claim fc
                        ON fi.FRAUD_KEY_NEW = fc.FRAUD_KEY_NEW
                    GROUP BY fc.BUSINESS_LINE, fi.MONTHYEAR, fi.MONTHYEAR_SORT
                    ORDER BY fi.MONTHYEAR_SORT
                """
                bl_decomp = execute_sql(bl_decomp_query)

                if not bl_decomp.empty:
                    for col in ['cases', 'fraud_amount', 'recovery', 'avg_score', 'avg_days', 'MONTHYEAR_SORT']:
                        bl_decomp[col] = pd.to_numeric(bl_decomp[col], errors='coerce').fillna(0)

                    bl_sort = bl_decomp.sort_values('MONTHYEAR_SORT')['MONTHYEAR'].unique().tolist()
                    decomp_metric = st.selectbox("Decomposition Metric", ["cases", "fraud_amount", "recovery", "avg_score"], key="bl_decomp_metric",
                                                  format_func=lambda x: {'cases': 'Case Volume', 'fraud_amount': 'Fraud Amount (AED)', 'recovery': 'Recovery (AED)', 'avg_score': 'Avg Fraud Score'}[x])

                    stacked = alt.Chart(bl_decomp).mark_area(opacity=0.75, line=True).encode(
                        x=alt.X('MONTHYEAR:N', sort=bl_sort, title=None, axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y(f'{decomp_metric}:Q', title=decomp_metric.replace('_', ' ').title(), stack='zero'),
                        color=alt.Color('BUSINESS_LINE:N', scale=alt.Scale(
                            domain=['MOTOR', 'MARINE', 'PROPERTY', 'FAMILY', 'MEDICAL'],
                            range=['#818cf8', '#34d399', '#f59e0b', '#f87171', '#60a5fa']
                        ), title='Business Line'),
                        tooltip=['BUSINESS_LINE', 'MONTHYEAR', alt.Tooltip(f'{decomp_metric}:Q', format=',.1f')]
                    ).properties(height=350, title=f'Business Line Decomposition \u2014 {decomp_metric.replace("_", " ").title()}')
                    st.altair_chart(stacked, use_container_width=True)

                    with st.expander("Individual Business Line Trends", expanded=False):
                        small_multiples = alt.Chart(bl_decomp).mark_line(strokeWidth=2).encode(
                            x=alt.X('MONTHYEAR:N', sort=bl_sort, title=None, axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y(f'{decomp_metric}:Q', title=None),
                            color=alt.Color('BUSINESS_LINE:N', legend=None),
                            tooltip=['BUSINESS_LINE', 'MONTHYEAR', alt.Tooltip(f'{decomp_metric}:Q', format=',.1f')]
                        ).properties(height=150, width=250).facet(
                            facet='BUSINESS_LINE:N', columns=3
                        )
                        st.altair_chart(small_multiples, use_container_width=True)

            except Exception as e:
                st.warning(f"Business line decomposition unavailable: {e}")

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")

            # === SECTION 5: Risk Velocity & Anomaly Detection ===
            st.markdown("""<div class="glass-card"><div class="section-header">
                <span class="section-header-icon">\u26A1</span>
                <span class="section-header-text">Risk Velocity & Anomaly Detection</span>
            </div>""", unsafe_allow_html=True)

            try:
                risk_query = """
                    SELECT fc.RISK_RATING, fi.MONTHYEAR, fi.MONTHYEAR_SORT,
                           COUNT(*) as cases,
                           AVG(fi.FRAUD_SCORE) as avg_score,
                           SUM(fi.FRAUD_AMOUNT_DETECTED) as fraud_amount,
                           SUM(CASE WHEN fi.FINDINGS = 'FRAUD_CONFIRMED' THEN 1 ELSE 0 END) as confirmed
                    FROM uae_insurance.uae_silver.fact_fraud_investigation fi
                    JOIN uae_insurance.uae_silver.fact_claim fc
                        ON fi.FRAUD_KEY_NEW = fc.FRAUD_KEY_NEW
                    GROUP BY fc.RISK_RATING, fi.MONTHYEAR, fi.MONTHYEAR_SORT
                    ORDER BY fi.MONTHYEAR_SORT
                """
                risk_df = execute_sql(risk_query)

                if not risk_df.empty:
                    for col in ['cases', 'avg_score', 'fraud_amount', 'confirmed', 'MONTHYEAR_SORT']:
                        risk_df[col] = pd.to_numeric(risk_df[col], errors='coerce').fillna(0)
                    risk_df['confirm_rate'] = (risk_df['confirmed'] / risk_df['cases'] * 100).round(1)

                    risk_sort = risk_df.sort_values('MONTHYEAR_SORT')['MONTHYEAR'].unique().tolist()

                    rv1, rv2 = st.columns(2)
                    with rv1:
                        risk_pct = alt.Chart(risk_df).mark_area(opacity=0.85).encode(
                            x=alt.X('MONTHYEAR:N', sort=risk_sort, title=None, axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y('cases:Q', title='Cases', stack='normalize'),
                            color=alt.Color('RISK_RATING:N', scale=alt.Scale(
                                domain=['HIGH', 'MEDIUM', 'LOW'],
                                range=['#ef4444', '#f59e0b', '#10b981']
                            ), title='Risk Rating'),
                            tooltip=['RISK_RATING', 'MONTHYEAR', alt.Tooltip('cases:Q', title='Cases')]
                        ).properties(height=300, title='Risk Mix Composition Shift')
                        st.altair_chart(risk_pct, use_container_width=True)

                    with rv2:
                        risk_score_trend = alt.Chart(risk_df).mark_line(strokeWidth=2.5, point=True).encode(
                            x=alt.X('MONTHYEAR:N', sort=risk_sort, title=None, axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y('avg_score:Q', title='Avg Fraud Score'),
                            color=alt.Color('RISK_RATING:N', scale=alt.Scale(
                                domain=['HIGH', 'MEDIUM', 'LOW'],
                                range=['#ef4444', '#f59e0b', '#10b981']
                            )),
                            tooltip=['RISK_RATING', 'MONTHYEAR', alt.Tooltip('avg_score:Q', format='.1f')]
                        ).properties(height=300, title='Fraud Score Trajectory by Risk Rating')
                        st.altair_chart(risk_score_trend, use_container_width=True)

                    # Velocity alerts for HIGH risk
                    high_risk = risk_df[risk_df['RISK_RATING'] == 'HIGH'].sort_values('MONTHYEAR_SORT')
                    if len(high_risk) >= 2:
                        latest_hr = high_risk.iloc[-1]
                        prev_hr = high_risk.iloc[-2]
                        hr_growth = ((latest_hr['cases'] - prev_hr['cases']) / prev_hr['cases'] * 100) if prev_hr['cases'] > 0 else 0
                        hr_score_delta = latest_hr['avg_score'] - prev_hr['avg_score']
                        total_latest = risk_df[risk_df['MONTHYEAR_SORT'] == risk_df['MONTHYEAR_SORT'].max()]['cases'].sum()
                        hr_share = (latest_hr['cases'] / total_latest * 100) if total_latest > 0 else 0

                        al1, al2, al3, al4 = st.columns(4, gap="small")
                        al1.metric("HIGH Risk Volume Change", f"{hr_growth:+.1f}%", delta="alert" if hr_growth > 25 else "stable", delta_color="inverse")
                        al2.metric("HIGH Risk Score Delta", f"{hr_score_delta:+.1f}", delta="rising" if hr_score_delta > 0 else "falling", delta_color="inverse")
                        al3.metric("HIGH Risk Share", f"{hr_share:.1f}%")
                        al4.metric("HIGH Confirm Rate", f"{latest_hr['confirm_rate']:.1f}%")

                        if hr_growth > 25 or hr_score_delta > 5:
                            st.error(f"\u26A0\uFE0F **Risk Velocity Alert**: HIGH-risk cases {'surging' if hr_growth > 25 else 'intensifying'} "
                                    f"({hr_growth:+.0f}% volume, {hr_score_delta:+.1f} score shift). "
                                    f"Recommend increased investigator allocation to HIGH-risk pipeline.")
                        elif hr_growth < -10:
                            st.success(f"\u2705 HIGH-risk volume declining ({hr_growth:+.0f}%). Current mitigation strategies appear effective.")
                        else:
                            st.info(f"\u2139\uFE0F HIGH-risk metrics stable. Volume change: {hr_growth:+.1f}%, Score delta: {hr_score_delta:+.1f}")

                    with st.expander("Risk-Findings Cross Analysis", expanded=False):
                        risk_findings = risk_df.groupby('RISK_RATING').agg(
                            total_cases=('cases', 'sum'),
                            avg_fraud_score=('avg_score', 'mean'),
                            total_fraud=('fraud_amount', 'sum'),
                            total_confirmed=('confirmed', 'sum')
                        ).reset_index()
                        risk_findings['confirm_rate'] = (risk_findings['total_confirmed'] / risk_findings['total_cases'] * 100).round(1)
                        risk_findings['avg_fraud_per_case'] = (risk_findings['total_fraud'] / risk_findings['total_cases']).round(0)
                        risk_findings.columns = ['Risk Rating', 'Total Cases', 'Avg Score', 'Total Fraud (AED)', 'Confirmed', 'Confirm Rate %', 'Fraud/Case (AED)']
                        st.dataframe(risk_findings, use_container_width=True, hide_index=True)

            except Exception as e:
                st.warning(f"Risk velocity analysis unavailable: {e}")

            st.markdown("</div>", unsafe_allow_html=True)

# --- PAGE: Investigator Performance ---
elif page == "\U0001F3C6  Investigator Performance":
    if not df.empty:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F3C6</span>
            <span class="section-header-text">Investigator Performance Analytics</span>
        </div>""", unsafe_allow_html=True)
        st.caption("Individual and team-level operational analytics for performance management, quality assurance, and training investment decisions.")

        # Build comprehensive investigator metrics
        inv_perf = df.groupby('INVESTIGATOR_ID').agg(
            Cases=('INVESTIGATION_ID', 'count'),
            Avg_Score=('FRAUD_SCORE', 'mean'),
            Avg_Days=('INVESTIGATION_DAYS', 'mean'),
            Median_Days=('INVESTIGATION_DAYS', 'median'),
            Total_Recovered=('RECOVERY_AMOUNT', 'sum'),
            Total_Cost=('INVESTIGATION_COST', 'sum'),
            Total_Fraud_Detected=('FRAUD_AMOUNT_DETECTED', 'sum'),
            Fraud_Confirmed=('FINDINGS', lambda x: (x == 'FRAUD_CONFIRMED').sum()),
            No_Fraud=('FINDINGS', lambda x: (x == 'NO_FRAUD').sum()),
            Completed=('INVESTIGATION_STATUS', lambda x: (x.isin(['COMPLETED', 'CLOSED'])).sum())
        ).reset_index()
        inv_perf['Confirm_Rate'] = (inv_perf['Fraud_Confirmed'] / inv_perf['Cases'] * 100).round(1)
        inv_perf['Resolution_Rate'] = (inv_perf['Completed'] / inv_perf['Cases'] * 100).round(1)
        inv_perf['ROI'] = ((inv_perf['Total_Recovered'] - inv_perf['Total_Cost']) / inv_perf['Total_Cost'].replace(0, 1) * 100).round(1)
        inv_perf['Recovery_Efficiency'] = (inv_perf['Total_Recovered'] / inv_perf['Total_Fraud_Detected'].replace(0, 1) * 100).round(1)
        inv_perf['Cost_Per_Case'] = (inv_perf['Total_Cost'] / inv_perf['Cases']).round(0)
        inv_perf['False_Positive_Rate'] = (inv_perf['No_Fraud'] / inv_perf['Cases'] * 100).round(1)

        # ============================================================
        # TEAM-WIDE KPIs
        # ============================================================
        team_avg_days = df['INVESTIGATION_DAYS'].mean()
        team_confirm_rate = (df['FINDINGS'] == 'FRAUD_CONFIRMED').sum() / len(df) * 100
        team_resolution_rate = df['INVESTIGATION_STATUS'].isin(['COMPLETED', 'CLOSED']).sum() / len(df) * 100
        team_recovery_eff = (df['RECOVERY_AMOUNT'].sum() / df['FRAUD_AMOUNT_DETECTED'].sum() * 100) if df['FRAUD_AMOUNT_DETECTED'].sum() > 0 else 0
        total_investigators = inv_perf['INVESTIGATOR_ID'].nunique()
        top_performer = inv_perf.sort_values('ROI', ascending=False).iloc[0]['INVESTIGATOR_ID'] if not inv_perf.empty else 'N/A'

        tk1, tk2, tk3, tk4, tk5, tk6 = st.columns(6, gap="small")
        tk1.metric("Team Size", total_investigators)
        tk2.metric("Avg Resolution", f"{team_avg_days:.1f} days")
        tk3.metric("Confirm Rate", f"{team_confirm_rate:.1f}%")
        tk4.metric("Resolution Rate", f"{team_resolution_rate:.1f}%")
        tk5.metric("Recovery Efficiency", f"{team_recovery_eff:.1f}%")
        tk6.metric("Top Performer", top_performer)

        st.markdown("---")

        # ============================================================
        # SECTION 1: PERFORMANCE QUADRANT
        # ============================================================
        st.subheader("\U0001F3AF Performance Quadrant: Speed vs Accuracy")
        st.caption("Bubble size = caseload. Ideal position: lower-left (fast) + upper (accurate). Color = ROI.")

        pq1, pq2 = st.columns([3, 1], gap="large")
        with pq1:
            quadrant = alt.Chart(inv_perf).mark_circle(opacity=0.75, stroke='#1e293b', strokeWidth=1).encode(
                x=alt.X('Avg_Days:Q', title='Avg Investigation Days (Speed)', scale=alt.Scale(zero=False)),
                y=alt.Y('Confirm_Rate:Q', title='Fraud Confirmation Rate (%) (Accuracy)', scale=alt.Scale(zero=False)),
                size=alt.Size('Cases:Q', title='Caseload', scale=alt.Scale(range=[80, 600])),
                color=alt.Color('ROI:Q', scale=alt.Scale(scheme='redyellowgreen'), title='ROI (%)'),
                tooltip=['INVESTIGATOR_ID',
                        alt.Tooltip('Cases:Q', title='Cases'),
                        alt.Tooltip('Avg_Days:Q', format='.1f', title='Avg Days'),
                        alt.Tooltip('Confirm_Rate:Q', format='.1f', title='Confirm %'),
                        alt.Tooltip('ROI:Q', format='.1f', title='ROI %'),
                        alt.Tooltip('Total_Recovered:Q', format=',.0f', title='Recovered (AED)')]
            ).properties(height=380)

            # Team average reference lines
            h_rule = alt.Chart(pd.DataFrame({'y': [team_confirm_rate]})).mark_rule(strokeDash=[4,4], color='#6366f1', opacity=0.6).encode(y='y:Q')
            v_rule = alt.Chart(pd.DataFrame({'x': [team_avg_days]})).mark_rule(strokeDash=[4,4], color='#6366f1', opacity=0.6).encode(x='x:Q')
            st.altair_chart((quadrant + h_rule + v_rule), use_container_width=True)

        with pq2:
            st.markdown("**Quadrant Legend**")
            st.markdown("""
            <div style="font-size:0.85rem;line-height:1.8;">
            \U0001F31F <strong>Top-Left</strong>: Fast & Accurate<br>
            \U0001F4AA <strong>Top-Right</strong>: Accurate but Slow<br>
            \u26A1 <strong>Bottom-Left</strong>: Fast but Low Confirm<br>
            \u26A0\uFE0F <strong>Bottom-Right</strong>: Needs Coaching
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"\n**Benchmarks** (dashed lines)")
            st.markdown(f"Avg Days: **{team_avg_days:.1f}**")
            st.markdown(f"Avg Confirm: **{team_confirm_rate:.1f}%**")

            # Identify coaching needs
            needs_coaching = inv_perf[(inv_perf['Avg_Days'] > team_avg_days) & (inv_perf['Confirm_Rate'] < team_confirm_rate)]
            if not needs_coaching.empty:
                st.warning(f"{len(needs_coaching)} investigator(s) below benchmarks on both axes")

        st.markdown("---")

        # ============================================================
        # SECTION 2: TEAM BENCHMARKING
        # ============================================================
        st.subheader("\U0001F4CA Team Benchmarking & Rankings")

        bench_metric = st.selectbox("Rank by:", ['ROI', 'Confirm_Rate', 'Avg_Days', 'Resolution_Rate', 'Recovery_Efficiency', 'Cases'], key='bench_metric')
        ascending = bench_metric == 'Avg_Days'  # Lower is better for days
        ranked = inv_perf.sort_values(bench_metric, ascending=ascending).reset_index(drop=True)
        ranked['Rank'] = range(1, len(ranked) + 1)

        bk1, bk2 = st.columns([2, 1], gap="large")
        with bk1:
            # Horizontal bar ranking
            bar_color = '#10b981' if not ascending else '#6366f1'
            rank_chart = alt.Chart(ranked.head(15)).mark_bar(cornerRadiusEnd=4, opacity=0.85).encode(
                y=alt.Y('INVESTIGATOR_ID:N', sort=alt.EncodingSortField(field=bench_metric, order='descending' if not ascending else 'ascending'), title=None),
                x=alt.X(f'{bench_metric}:Q', title=bench_metric.replace('_', ' ')),
                color=alt.Color(f'{bench_metric}:Q', scale=alt.Scale(scheme='redyellowgreen' if bench_metric != 'Avg_Days' else 'redyellowgreen', reverse=(bench_metric == 'Avg_Days')), legend=None),
                tooltip=['INVESTIGATOR_ID', 'Rank',
                        alt.Tooltip(f'{bench_metric}:Q', format='.1f'),
                        alt.Tooltip('Cases:Q', title='Caseload')]
            ).properties(height=min(400, len(ranked) * 28 + 40), title=f'Investigator Ranking by {bench_metric.replace("_", " ")}')

            # Team average rule
            team_avg_val = inv_perf[bench_metric].mean()
            avg_rule = alt.Chart(pd.DataFrame({'x': [team_avg_val]})).mark_rule(strokeDash=[5,3], color='#f59e0b', strokeWidth=2).encode(x='x:Q')
            st.altair_chart((rank_chart + avg_rule), use_container_width=True)

        with bk2:
            st.markdown("**Distribution Stats**")
            st.markdown(f"Mean: **{inv_perf[bench_metric].mean():.1f}**")
            st.markdown(f"Median: **{inv_perf[bench_metric].median():.1f}**")
            st.markdown(f"Std Dev: **{inv_perf[bench_metric].std():.1f}**")
            st.markdown(f"Top 25%: **{inv_perf[bench_metric].quantile(0.75):.1f}**")
            st.markdown(f"Bottom 25%: **{inv_perf[bench_metric].quantile(0.25):.1f}**")

            # Performance tiers
            q75 = inv_perf[bench_metric].quantile(0.75)
            q25 = inv_perf[bench_metric].quantile(0.25)
            if not ascending:
                star_count = len(inv_perf[inv_perf[bench_metric] >= q75])
                risk_count = len(inv_perf[inv_perf[bench_metric] <= q25])
            else:
                star_count = len(inv_perf[inv_perf[bench_metric] <= q25])
                risk_count = len(inv_perf[inv_perf[bench_metric] >= q75])
            st.markdown(f"\n\U0001F31F Star Performers: **{star_count}**")
            st.markdown(f"\u26A0\uFE0F Need Support: **{risk_count}**")

        st.markdown("---")

        # ============================================================
        # SECTION 3: QUALITY VS AI SIGNAL ALIGNMENT
        # ============================================================
        st.subheader("\U0001F9E0 Quality Scoring vs AI Risk Signal Alignment")
        st.caption("Measures how well investigator findings align with AI fraud scores. High alignment = investigator confirms fraud when AI score is high.")

        try:
            # For each investigator: avg AI score for confirmed vs not-confirmed cases
            alignment_data = df.copy()
            alignment_data['is_confirmed'] = (alignment_data['FINDINGS'] == 'FRAUD_CONFIRMED').astype(int)

            inv_alignment = alignment_data.groupby('INVESTIGATOR_ID').apply(
                lambda g: pd.Series({
                    'avg_score_confirmed': g[g['is_confirmed'] == 1]['FRAUD_SCORE'].mean() if g['is_confirmed'].sum() > 0 else 0,
                    'avg_score_not_confirmed': g[g['is_confirmed'] == 0]['FRAUD_SCORE'].mean() if (g['is_confirmed'] == 0).sum() > 0 else 0,
                    'cases': len(g),
                    'confirm_rate': g['is_confirmed'].mean() * 100
                })
            ).reset_index()
            inv_alignment['score_separation'] = (inv_alignment['avg_score_confirmed'] - inv_alignment['avg_score_not_confirmed']).round(1)
            inv_alignment['alignment_quality'] = inv_alignment['score_separation'].apply(
                lambda s: 'Strong' if s >= 15 else ('Moderate' if s >= 5 else 'Weak')
            )

            qa1, qa2 = st.columns(2, gap="large")
            with qa1:
                # Score separation chart
                sep_chart = alt.Chart(inv_alignment).mark_bar(cornerRadiusEnd=4).encode(
                    y=alt.Y('INVESTIGATOR_ID:N', sort=alt.EncodingSortField(field='score_separation', order='descending'), title=None),
                    x=alt.X('score_separation:Q', title='AI Score Separation (Confirmed - Not Confirmed)'),
                    color=alt.Color('alignment_quality:N', scale=alt.Scale(
                        domain=['Strong', 'Moderate', 'Weak'],
                        range=['#10b981', '#f59e0b', '#ef4444']
                    ), title='Alignment'),
                    tooltip=['INVESTIGATOR_ID',
                            alt.Tooltip('score_separation:Q', format='.1f', title='Score Separation'),
                            alt.Tooltip('avg_score_confirmed:Q', format='.1f', title='Avg Score (Confirmed)'),
                            alt.Tooltip('avg_score_not_confirmed:Q', format='.1f', title='Avg Score (Not Confirmed)'),
                            alt.Tooltip('cases:Q', title='Cases')]
                ).properties(height=min(380, len(inv_alignment) * 26 + 40), title='AI Signal Alignment by Investigator')
                st.altair_chart(sep_chart, use_container_width=True)

            with qa2:
                # Alignment quality distribution
                quality_dist = inv_alignment['alignment_quality'].value_counts()
                st.markdown("**Alignment Distribution**")
                for quality in ['Strong', 'Moderate', 'Weak']:
                    count = quality_dist.get(quality, 0)
                    icon = {'Strong': '\u2705', 'Moderate': '\u26A0\uFE0F', 'Weak': '\U0001F6A8'}[quality]
                    color = {'Strong': '#10b981', 'Moderate': '#f59e0b', 'Weak': '#ef4444'}[quality]
                    st.markdown(f"<span style='color:{color};font-weight:600;'>{icon} {quality}: {count} investigator(s)</span>", unsafe_allow_html=True)

                st.markdown("\n**What this means:**")
                st.markdown("""
                <div style="font-size:0.82rem;color:#94a3b8;line-height:1.6;">
                <strong>Strong</strong>: Confirms fraud when AI score is high, clears when low (\u226515pt gap)<br>
                <strong>Moderate</strong>: Some alignment with AI signals (5-15pt gap)<br>
                <strong>Weak</strong>: Findings don't correlate well with AI scores (<5pt gap) \u2014 may need calibration training
                </div>
                """, unsafe_allow_html=True)

                weak_investigators = inv_alignment[inv_alignment['alignment_quality'] == 'Weak']
                if not weak_investigators.empty:
                    st.error(f"\U0001F6A8 {len(weak_investigators)} investigator(s) with weak AI alignment \u2014 recommend calibration review")

        except Exception as e:
            st.warning(f"AI alignment analysis unavailable: {e}")

        st.markdown("---")

        # ============================================================
        # SECTION 4: MONTHLY TREND OVERLAYS
        # ============================================================
        st.subheader("\U0001F4C8 Performance Trend Overlays")

        try:
            trend_query = """
                SELECT INVESTIGATOR_ID, MONTHYEAR, MONTHYEAR_SORT,
                       COUNT(*) as cases,
                       AVG(INVESTIGATION_DAYS) as avg_days,
                       SUM(CASE WHEN FINDINGS = 'FRAUD_CONFIRMED' THEN 1 ELSE 0 END) as confirmed,
                       SUM(RECOVERY_AMOUNT) as recovery,
                       AVG(FRAUD_SCORE) as avg_score
                FROM uae_insurance.uae_silver.fact_fraud_investigation
                GROUP BY INVESTIGATOR_ID, MONTHYEAR, MONTHYEAR_SORT
                ORDER BY MONTHYEAR_SORT
            """
            trend_df = execute_sql(trend_query)

            if not trend_df.empty:
                trend_df['MONTHYEAR_SORT'] = pd.to_numeric(trend_df['MONTHYEAR_SORT'], errors='coerce').fillna(0).astype(int)
                for col in ['cases', 'avg_days', 'confirmed', 'recovery', 'avg_score']:
                    trend_df[col] = pd.to_numeric(trend_df[col], errors='coerce').fillna(0)
                trend_df['confirm_rate'] = (trend_df['confirmed'] / trend_df['cases'].replace(0, 1) * 100).round(1)
                trend_df = trend_df.sort_values('MONTHYEAR_SORT')
                trend_sort = trend_df['MONTHYEAR'].unique().tolist()

                # Metric selector
                trend_metric = st.selectbox("Trend Metric:", ['confirm_rate', 'avg_days', 'cases', 'recovery', 'avg_score'], key='inv_trend_metric',
                                           format_func=lambda x: {'confirm_rate': 'Confirmation Rate (%)', 'avg_days': 'Avg Days', 'cases': 'Caseload', 'recovery': 'Recovery (AED)', 'avg_score': 'Avg Fraud Score'}[x])

                # Select top investigators by case volume for readability
                top_investigators = inv_perf.nlargest(8, 'Cases')['INVESTIGATOR_ID'].tolist()
                trend_filtered = trend_df[trend_df['INVESTIGATOR_ID'].isin(top_investigators)]

                tr1, tr2 = st.columns([3, 1], gap="large")
                with tr1:
                    trend_chart = alt.Chart(trend_filtered).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=30)).encode(
                        x=alt.X('MONTHYEAR:N', sort=trend_sort, title=None, axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y(f'{trend_metric}:Q', title=trend_metric.replace('_', ' ').title()),
                        color=alt.Color('INVESTIGATOR_ID:N', title='Investigator'),
                        tooltip=['INVESTIGATOR_ID', 'MONTHYEAR',
                                alt.Tooltip(f'{trend_metric}:Q', format='.1f'),
                                alt.Tooltip('cases:Q', title='Cases')]
                    ).properties(height=350, title=f'Monthly {trend_metric.replace("_", " ").title()} by Investigator (Top 8 by Volume)')

                    # Team average overlay
                    team_trend = trend_df.groupby('MONTHYEAR').agg(**{trend_metric: (trend_metric, 'mean')}).reset_index()
                    team_line = alt.Chart(team_trend).mark_line(strokeWidth=3, strokeDash=[6,3], color='#f59e0b', opacity=0.8).encode(
                        x=alt.X('MONTHYEAR:N', sort=trend_sort),
                        y=alt.Y(f'{trend_metric}:Q')
                    )
                    st.altair_chart((trend_chart + team_line), use_container_width=True)
                    st.caption("Orange dashed line = team average")

                with tr2:
                    st.markdown("**Trend Highlights**")
                    # Identify improving/declining investigators
                    if len(trend_sort) >= 2:
                        latest_month = trend_sort[-1]
                        prev_month = trend_sort[-2]
                        latest_perf = trend_filtered[trend_filtered['MONTHYEAR'] == latest_month].set_index('INVESTIGATOR_ID')[trend_metric]
                        prev_perf = trend_filtered[trend_filtered['MONTHYEAR'] == prev_month].set_index('INVESTIGATOR_ID')[trend_metric]
                        changes = (latest_perf - prev_perf).dropna().sort_values(ascending=(trend_metric == 'avg_days'))

                        if not changes.empty:
                            best_improver = changes.index[0] if trend_metric != 'avg_days' else changes.index[-1]
                            worst_decline = changes.index[-1] if trend_metric != 'avg_days' else changes.index[0]
                            st.markdown(f"\U0001F4C8 Most improved: **{best_improver}**")
                            st.markdown(f"\U0001F4C9 Biggest decline: **{worst_decline}**")

                    st.markdown(f"\n**Showing:** Top 8 investigators by caseload")
                    st.markdown(f"**Period:** {trend_sort[0]} \u2192 {trend_sort[-1]}" if trend_sort else "")

        except Exception as e:
            st.warning(f"Trend analysis unavailable: {e}")

        st.markdown("---")

        # ============================================================
        # SECTION 5: DETAILED SCOREBOARD TABLE
        # ============================================================
        st.subheader("\U0001F4CB Full Performance Scoreboard")

        scoreboard = inv_perf[['INVESTIGATOR_ID', 'Cases', 'Confirm_Rate', 'Resolution_Rate', 'Avg_Days',
                               'Median_Days', 'ROI', 'Recovery_Efficiency', 'Cost_Per_Case',
                               'False_Positive_Rate', 'Total_Recovered']].copy()
        scoreboard = scoreboard.sort_values('ROI', ascending=False).reset_index(drop=True)
        scoreboard.columns = ['Investigator', 'Cases', 'Confirm %', 'Resolution %', 'Avg Days',
                              'Median Days', 'ROI %', 'Recovery Eff %', 'Cost/Case (AED)',
                              'False Positive %', 'Total Recovered (AED)']
        enhanced_dataframe(scoreboard, title='Investigator Performance Scoreboard', key_prefix='inv_perf_full', height=450)

# --- PAGE: ROI Analysis ---
elif page == "\U0001F4B0  ROI Analysis":
    if not df.empty:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4B0</span>
            <span class="section-header-text">Return on Investigation (ROI) Analysis</span>
        </div>""", unsafe_allow_html=True)

        # Overall ROI KPIs
        total_cost = df['INVESTIGATION_COST'].sum()
        total_recovered = df['RECOVERY_AMOUNT'].sum()
        net_benefit = total_recovered - total_cost
        overall_roi = (net_benefit / total_cost * 100) if total_cost > 0 else 0
        fraud_detected = df['FRAUD_AMOUNT_DETECTED'].sum()
        recovery_rate = (total_recovered / fraud_detected * 100) if fraud_detected > 0 else 0

        k1, k2, k3, k4 = st.columns(4, gap="small")
        k1.metric("Total Investment", f"AED {total_cost:,.0f}")
        k2.metric("Total Recovered", f"AED {total_recovered:,.0f}")
        k3.metric("Net Benefit", f"AED {net_benefit:,.0f}", delta=f"{overall_roi:.1f}% ROI")
        k4.metric("Recovery Rate", f"{recovery_rate:.1f}%", delta=f"of {fraud_detected:,.0f} detected")

        st.markdown("---")

        # ============================================================
        # SECTION 1: RECOVERY TRACKING
        # ============================================================
        st.subheader("\U0001F4C8 Recovery Tracking")

        try:
            roi_query = """
                SELECT MONTHYEAR, MONTHYEAR_SORT,
                       COUNT(*) as cases,
                       SUM(INVESTIGATION_COST) as total_cost,
                       SUM(RECOVERY_AMOUNT) as total_recovery,
                       SUM(FRAUD_AMOUNT_DETECTED) as total_fraud_detected,
                       AVG(FRAUD_SCORE) as avg_score,
                       SUM(CASE WHEN FINDINGS = 'FRAUD_CONFIRMED' THEN 1 ELSE 0 END) as confirmed_cases
                FROM uae_insurance.uae_silver.fact_fraud_investigation
                GROUP BY MONTHYEAR, MONTHYEAR_SORT
                ORDER BY MONTHYEAR_SORT
            """
            roi_monthly = execute_sql(roi_query)

            if not roi_monthly.empty:
                roi_monthly['MONTHYEAR_SORT'] = pd.to_numeric(roi_monthly['MONTHYEAR_SORT'], errors='coerce').fillna(0).astype(int)
                for col in ['cases', 'total_cost', 'total_recovery', 'total_fraud_detected', 'avg_score', 'confirmed_cases']:
                    roi_monthly[col] = pd.to_numeric(roi_monthly[col], errors='coerce').fillna(0)

                roi_monthly = roi_monthly.sort_values('MONTHYEAR_SORT')
                roi_monthly['cumulative_cost'] = roi_monthly['total_cost'].cumsum()
                roi_monthly['cumulative_recovery'] = roi_monthly['total_recovery'].cumsum()
                roi_monthly['cumulative_roi'] = ((roi_monthly['cumulative_recovery'] - roi_monthly['cumulative_cost']) / roi_monthly['cumulative_cost'] * 100).round(1)
                roi_monthly['recovery_rate'] = (roi_monthly['total_recovery'] / roi_monthly['total_fraud_detected'].replace(0, 1) * 100).round(1)
                roi_monthly['cost_per_case'] = (roi_monthly['total_cost'] / roi_monthly['cases'].replace(0, 1)).round(0)
                roi_monthly['recovery_per_case'] = (roi_monthly['total_recovery'] / roi_monthly['cases'].replace(0, 1)).round(0)

                sort_order = roi_monthly['MONTHYEAR'].tolist()

                rc1, rc2 = st.columns(2)
                with rc1:
                    # Cost vs Recovery dual-axis
                    cost_line = alt.Chart(roi_monthly).mark_line(strokeWidth=2.5, color='#ef4444', strokeDash=[5,3]).encode(
                        x=alt.X('MONTHYEAR:N', sort=sort_order, title=None, axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('total_cost:Q', title='Amount (AED)'),
                        tooltip=['MONTHYEAR', alt.Tooltip('total_cost:Q', format=',.0f', title='Cost')]
                    )
                    recovery_line = alt.Chart(roi_monthly).mark_line(strokeWidth=2.5, color='#10b981').encode(
                        x=alt.X('MONTHYEAR:N', sort=sort_order, title=None),
                        y=alt.Y('total_recovery:Q'),
                        tooltip=['MONTHYEAR', alt.Tooltip('total_recovery:Q', format=',.0f', title='Recovery')]
                    )
                    recovery_area = alt.Chart(roi_monthly).mark_area(opacity=0.1, color='#10b981').encode(
                        x=alt.X('MONTHYEAR:N', sort=sort_order),
                        y=alt.Y('total_recovery:Q')
                    )
                    st.altair_chart((recovery_area + cost_line + recovery_line).properties(
                        height=300, title='Monthly: Cost (red dashed) vs Recovery (green)'
                    ), use_container_width=True)

                with rc2:
                    # Cumulative ROI trend
                    cum_chart = alt.Chart(roi_monthly).mark_area(line=True, opacity=0.2, color='#6366f1').encode(
                        x=alt.X('MONTHYEAR:N', sort=sort_order, title=None, axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('cumulative_roi:Q', title='Cumulative ROI (%)'),
                        tooltip=['MONTHYEAR', alt.Tooltip('cumulative_roi:Q', format='.1f', title='Cum. ROI %')]
                    ).properties(height=300, title='Cumulative ROI Trajectory')
                    zero_rule = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(strokeDash=[4,4], color='gray').encode(y='y:Q')
                    st.altair_chart((cum_chart + zero_rule), use_container_width=True)

                # Recovery rate trend
                rr_chart = alt.Chart(roi_monthly).mark_bar(cornerRadiusEnd=3, color='#8b5cf6', opacity=0.7).encode(
                    x=alt.X('MONTHYEAR:N', sort=sort_order, title=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('recovery_rate:Q', title='Recovery Rate (%)'),
                    tooltip=['MONTHYEAR', alt.Tooltip('recovery_rate:Q', format='.1f', title='Recovery %')]
                ).properties(height=200, title='Monthly Recovery Rate (% of Fraud Detected that was Recovered)')
                st.altair_chart(rr_chart, use_container_width=True)

        except Exception as e:
            st.warning(f"Recovery tracking unavailable: {e}")

        st.markdown("---")

        # ============================================================
        # SECTION 2: AI LIFT ANALYSIS
        # ============================================================
        st.subheader("\U0001F916 AI Lift Analysis")

        try:
            # Compare high-score (AI-flagged) vs low-score investigations
            ai_threshold = 70
            df_ai = df.copy()
            df_ai['AI_Category'] = df_ai['FRAUD_SCORE'].apply(
                lambda x: 'AI-Flagged (Score\u226570)' if x >= ai_threshold else 'Traditional (Score<70)'
            )

            ai_summary = df_ai.groupby('AI_Category').agg(
                Cases=('INVESTIGATION_ID', 'count'),
                Avg_Cost=('INVESTIGATION_COST', 'mean'),
                Total_Recovery=('RECOVERY_AMOUNT', 'sum'),
                Avg_Recovery=('RECOVERY_AMOUNT', 'mean'),
                Avg_Days=('INVESTIGATION_DAYS', 'mean'),
                Confirmed=('FINDINGS', lambda x: (x == 'FRAUD_CONFIRMED').sum())
            ).reset_index()
            ai_summary['Confirm_Rate'] = (ai_summary['Confirmed'] / ai_summary['Cases'] * 100).round(1)
            ai_summary['ROI'] = ((ai_summary['Total_Recovery'] - ai_summary['Avg_Cost'] * ai_summary['Cases']) / (ai_summary['Avg_Cost'] * ai_summary['Cases']) * 100).round(1)

            ai1, ai2 = st.columns(2)
            with ai1:
                ai_bar = alt.Chart(ai_summary).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X('AI_Category:N', title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('Confirm_Rate:Q', title='Fraud Confirmation Rate (%)'),
                    color=alt.Color('AI_Category:N', scale=alt.Scale(
                        domain=['AI-Flagged (Score\u226570)', 'Traditional (Score<70)'],
                        range=['#6366f1', '#94a3b8']
                    ), legend=None),
                    tooltip=['AI_Category', alt.Tooltip('Confirm_Rate:Q', format='.1f'), alt.Tooltip('Cases:Q', format=',')]
                ).properties(height=280, title='Fraud Confirmation Rate: AI vs Traditional')
                st.altair_chart(ai_bar, use_container_width=True)

            with ai2:
                ai_roi_bar = alt.Chart(ai_summary).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X('AI_Category:N', title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('ROI:Q', title='ROI (%)'),
                    color=alt.Color('AI_Category:N', scale=alt.Scale(
                        domain=['AI-Flagged (Score\u226570)', 'Traditional (Score<70)'],
                        range=['#6366f1', '#94a3b8']
                    ), legend=None),
                    tooltip=['AI_Category', alt.Tooltip('ROI:Q', format='.1f'), alt.Tooltip('Avg_Days:Q', format='.1f', title='Avg Days')]
                ).properties(height=280, title='ROI Comparison: AI-Flagged vs Traditional')
                st.altair_chart(ai_roi_bar, use_container_width=True)

            # AI lift metrics
            if len(ai_summary) == 2:
                ai_flagged = ai_summary[ai_summary['AI_Category'].str.contains('AI-Flagged')].iloc[0]
                traditional = ai_summary[~ai_summary['AI_Category'].str.contains('AI-Flagged')].iloc[0]
                lift_confirm = ai_flagged['Confirm_Rate'] - traditional['Confirm_Rate']
                lift_roi = ai_flagged['ROI'] - traditional['ROI']
                speed_gain = traditional['Avg_Days'] - ai_flagged['Avg_Days']

                lm1, lm2, lm3, lm4 = st.columns(4, gap="small")
                lm1.metric("Confirmation Lift", f"+{lift_confirm:.1f}pp", help="AI-flagged confirmation rate advantage")
                lm2.metric("ROI Lift", f"+{lift_roi:.1f}%", help="AI-flagged ROI advantage")
                lm3.metric("Speed Gain", f"{speed_gain:.1f} days faster", help="Days saved per investigation")
                lm4.metric("AI Case Share", f"{ai_flagged['Cases'] / ai_summary['Cases'].sum() * 100:.0f}%")

                if lift_confirm > 10:
                    st.success(f"\u2705 **AI Scoring delivers +{lift_confirm:.1f}pp higher confirmation rate** with {speed_gain:.0f} days faster resolution. "
                             f"Consider lowering the AI-flag threshold to capture more high-value cases.")

        except Exception as e:
            st.warning(f"AI lift analysis unavailable: {e}")

        st.markdown("---")

        # ============================================================
        # SECTION 3: COST EFFICIENCY
        # ============================================================
        st.subheader("\U0001F4CA Cost Efficiency")

        try:
            # Cost efficiency by investigation status
            status_roi = df.groupby('INVESTIGATION_STATUS').agg(
                Cases=('INVESTIGATION_ID', 'count'),
                Avg_Cost=('INVESTIGATION_COST', 'mean'),
                Avg_Recovery=('RECOVERY_AMOUNT', 'mean'),
                Avg_Days=('INVESTIGATION_DAYS', 'mean'),
                Total_Cost=('INVESTIGATION_COST', 'sum'),
                Total_Recovery=('RECOVERY_AMOUNT', 'sum')
            ).reset_index()
            status_roi['Efficiency'] = ((status_roi['Avg_Recovery'] - status_roi['Avg_Cost']) / status_roi['Avg_Cost'] * 100).round(1)

            ce1, ce2 = st.columns(2)
            with ce1:
                eff_chart = alt.Chart(status_roi).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X('INVESTIGATION_STATUS:N', title=None, axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y('Efficiency:Q', title='Cost Efficiency (%)'),
                    color=alt.Color('Efficiency:Q', scale=alt.Scale(scheme='redyellowgreen'), legend=None),
                    tooltip=['INVESTIGATION_STATUS', alt.Tooltip('Efficiency:Q', format='.1f'),
                            alt.Tooltip('Avg_Cost:Q', format=',.0f', title='Avg Cost'),
                            alt.Tooltip('Avg_Recovery:Q', format=',.0f', title='Avg Recovery')]
                ).properties(height=280, title='Cost Efficiency by Investigation Status')
                st.altair_chart(eff_chart, use_container_width=True)

            with ce2:
                # Cost per confirmed fraud scatter
                inv_cost = df[df['FINDINGS'] == 'FRAUD_CONFIRMED'].copy()
                if not inv_cost.empty:
                    scatter = alt.Chart(inv_cost).mark_circle(size=60, opacity=0.6).encode(
                        x=alt.X('INVESTIGATION_COST:Q', title='Investigation Cost (AED)', scale=alt.Scale(zero=False)),
                        y=alt.Y('RECOVERY_AMOUNT:Q', title='Recovery Amount (AED)', scale=alt.Scale(zero=False)),
                        color=alt.Color('FRAUD_SCORE:Q', scale=alt.Scale(scheme='plasma'), title='Fraud Score'),
                        size=alt.Size('FRAUD_AMOUNT_DETECTED:Q', legend=None),
                        tooltip=['INVESTIGATION_ID', alt.Tooltip('INVESTIGATION_COST:Q', format=',.0f'),
                                alt.Tooltip('RECOVERY_AMOUNT:Q', format=',.0f'),
                                alt.Tooltip('FRAUD_SCORE:Q', format='.0f')]
                    ).properties(height=280, title='Cost vs Recovery (Confirmed Fraud Only)')
                    # Break-even line
                    max_val = max(inv_cost['INVESTIGATION_COST'].max(), inv_cost['RECOVERY_AMOUNT'].max())
                    be_line = alt.Chart(pd.DataFrame({'x': [0, max_val], 'y': [0, max_val]})).mark_line(
                        strokeDash=[5,3], color='gray', opacity=0.5
                    ).encode(x='x:Q', y='y:Q')
                    st.altair_chart((scatter + be_line), use_container_width=True)
                else:
                    st.info("No confirmed fraud cases for scatter analysis.")

            # Cost efficiency summary table
            with st.expander("Detailed Cost Breakdown by Status", expanded=False):
                display_roi = status_roi.copy()
                display_roi.columns = ['Status', 'Cases', 'Avg Cost', 'Avg Recovery', 'Avg Days', 'Total Cost', 'Total Recovery', 'Efficiency %']
                st.dataframe(display_roi, use_container_width=True, hide_index=True)

        except Exception as e:
            st.warning(f"Cost efficiency analysis unavailable: {e}")

        st.markdown("---")

        # ============================================================
        # SECTION 4: FORWARD-LOOKING PROJECTIONS
        # ============================================================
        st.subheader("\U0001F52E Forward-Looking Projections")

        try:
            if 'roi_monthly' in dir() and not roi_monthly.empty and len(roi_monthly) >= 3:
                # Simple linear projection based on recent trends
                recent_months = roi_monthly.tail(6)
                avg_monthly_recovery = recent_months['total_recovery'].mean()
                avg_monthly_cost = recent_months['total_cost'].mean()
                avg_monthly_cases = recent_months['cases'].mean()
                recovery_growth = recent_months['total_recovery'].pct_change().mean()

                fp1, fp2, fp3, fp4 = st.columns(4, gap="small")
                fp1.metric("Avg Monthly Recovery", f"AED {avg_monthly_recovery:,.0f}")
                fp2.metric("Avg Monthly Cost", f"AED {avg_monthly_cost:,.0f}")
                fp3.metric("Monthly Net Benefit", f"AED {avg_monthly_recovery - avg_monthly_cost:,.0f}")
                fp4.metric("Recovery Growth Rate", f"{recovery_growth * 100:+.1f}%/mo")

                # 6-month projection
                projection_months = 6
                proj_data = []
                last_recovery = recent_months.iloc[-1]['total_recovery']
                last_cost = recent_months.iloc[-1]['total_cost']
                cum_rec = roi_monthly['total_recovery'].sum()
                cum_cost = roi_monthly['total_cost'].sum()

                for i in range(1, projection_months + 1):
                    proj_recovery = last_recovery * (1 + recovery_growth) ** i
                    proj_cost = last_cost * 1.02 ** i  # 2% cost inflation assumption
                    cum_rec += proj_recovery
                    cum_cost += proj_cost
                    proj_data.append({
                        'Month': f'+{i}',
                        'Projected_Recovery': proj_recovery,
                        'Projected_Cost': proj_cost,
                        'Projected_Net': proj_recovery - proj_cost,
                        'Projected_Cum_ROI': ((cum_rec - cum_cost) / cum_cost * 100)
                    })

                proj_df = pd.DataFrame(proj_data)

                pj1, pj2 = st.columns(2)
                with pj1:
                    proj_chart = alt.Chart(proj_df).mark_bar(cornerRadiusEnd=3).encode(
                        x=alt.X('Month:N', title='Months Ahead'),
                        y=alt.Y('Projected_Net:Q', title='Projected Net Benefit (AED)'),
                        color=alt.value('#10b981'),
                        tooltip=['Month', alt.Tooltip('Projected_Recovery:Q', format=',.0f', title='Recovery'),
                                alt.Tooltip('Projected_Cost:Q', format=',.0f', title='Cost'),
                                alt.Tooltip('Projected_Net:Q', format=',.0f', title='Net')]
                    ).properties(height=250, title='6-Month Net Benefit Projection')
                    st.altair_chart(proj_chart, use_container_width=True)

                with pj2:
                    proj_roi_chart = alt.Chart(proj_df).mark_line(strokeWidth=2.5, point=True, color='#6366f1').encode(
                        x=alt.X('Month:N', title='Months Ahead'),
                        y=alt.Y('Projected_Cum_ROI:Q', title='Projected Cumulative ROI (%)'),
                        tooltip=['Month', alt.Tooltip('Projected_Cum_ROI:Q', format='.1f', title='Cum ROI %')]
                    ).properties(height=250, title='Projected Cumulative ROI Trajectory')
                    st.altair_chart(proj_roi_chart, use_container_width=True)

                st.caption("\u26A0\uFE0F Projections based on recent 6-month trends with 2% cost inflation assumption. Actual results may vary.")

                with st.expander("Projection Details", expanded=False):
                    proj_display = proj_df.copy()
                    proj_display['Projected_Recovery'] = proj_display['Projected_Recovery'].apply(lambda x: f"AED {x:,.0f}")
                    proj_display['Projected_Cost'] = proj_display['Projected_Cost'].apply(lambda x: f"AED {x:,.0f}")
                    proj_display['Projected_Net'] = proj_display['Projected_Net'].apply(lambda x: f"AED {x:,.0f}")
                    proj_display['Projected_Cum_ROI'] = proj_display['Projected_Cum_ROI'].apply(lambda x: f"{x:.1f}%")
                    proj_display.columns = ['Month', 'Recovery', 'Cost', 'Net Benefit', 'Cumulative ROI']
                    st.dataframe(proj_display, use_container_width=True, hide_index=True)
            else:
                st.info("Insufficient monthly data for forward projections (minimum 3 months required).")

        except Exception as e:
            st.warning(f"Forward projections unavailable: {e}")

# --- PAGE: GenAI Insights ---
elif page == "\U0001F916  GenAI Insights":
    st.markdown("""<div class="section-header">
        <span class="section-header-icon">\U0001F916</span>
        <span class="section-header-text">Databricks Mosaic AI Fraud Insights</span>
    </div>""", unsafe_allow_html=True)
    st.markdown("Leverage **Databricks Foundation Models** and **AI Agents** to analyze fraud data.")

    ai_tab1, ai_tab2, ai_tab3, ai_tab4, ai_tab5, ai_tab6, ai_tab7 = st.tabs([
        "\U0001F9DE  Genie",
        "\U0001F4DD  AI Summary",
        "\U0001F4C4  Claims Documents",
        "\U0001F4AC  Fraud Agent",
        "\U0001F9E0  Sentiment",
        "\U0001F4CA  Risk Scoring",
        "\U0001F52E  ML Forecast"
    ])

    with ai_tab1:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F9DE</span>
            <span class="section-header-text">AI/BI Genie</span>
        </div>""", unsafe_allow_html=True)

        # --- Genie Space Info Cards ---
        col1, = st.columns(1, gap="large")
        with col1:
            st.markdown("""<div class="glass-card">
            <h4 style="margin-top:0">\U0001F4A1 Genie Space: Fraud Investigation</h4>

This Genie space enables natural language analytics for insurance fraud detection and investigation. It covers key business domains including fraud investigations, claims, payments, premiums, policies, financials, investments, litigation, and sales performance.
Business users can ask natural language questions directly in the Genie room.
            </div>""", unsafe_allow_html=True)
            genie_url = f"https://{DATABRICKS_HOST}/genie/rooms/01f1711e8b581b708c3337d6bb25144b" if DATABRICKS_HOST else "#"
            st.link_button("\U0001F680 Open Genie Space", genie_url)

#         with col2:
#             st.markdown("""<div class="glass-card">
#             <h4 style="margin-top:0">\U0001F4AC Microsoft Teams Deployment</h4>

# **Setup Steps:**
# 1. Go to **Workspace Settings** > **AI/BI Genie Spaces**
# 2. Select *Insurance Operations and Analytics*
# 3. Click **Deploy to Microsoft Teams**
# 4. Authorize the Teams app in your M365 Admin Center
# 5. Users in the "Fraud Management" channel query: `@SalamaGenie What was total fraud detected last month?`
#             </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

        # --- Embedded Genie Chat ---
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4AC</span>
            <span class="section-header-text">Ask Genie (Embedded)</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("Query the Genie Space directly from this app. Genie uses your approved tables and business definitions.")

        GENIE_SPACE_ID = "01f1711e8b581b708c3337d6bb25144b"

        if "genie_history" not in st.session_state:
            st.session_state.genie_history = []
        if "genie_conv_id" not in st.session_state:
            st.session_state.genie_conv_id = None

        genie_examples = ["What is the total fraud amount detected?", "Show top 10 investigators by recovery amount", "How many claims are in each status?", "What is the average fraud score by business line?"]
        ge_cols = st.columns(4)
        for i, ge in enumerate(genie_examples):
            if ge_cols[i].button(ge, key=f"ge_{i}", use_container_width=True):
                st.session_state["genie_input_q"] = ge

        genie_q = st.text_area("Ask Genie a question:", value=st.session_state.get("genie_input_q", ""), placeholder="e.g., What is the recovery rate for confirmed fraud cases?", height=70, key="genie_q_input")

        gc1, gc2, gc3 = st.columns([1, 1, 4])
        ask_genie = gc1.button("\U0001F9DE Ask Genie", key="ask_genie_btn", use_container_width=True)
        new_conv = gc2.button("\U0001F504 New Conversation", key="new_genie_conv", use_container_width=True)

        if new_conv:
            st.session_state.genie_conv_id = None
            st.session_state.genie_history = []
            st.rerun()

        if ask_genie and genie_q.strip():
            import time as _time
            with st.status("Genie is thinking...", expanded=True) as genie_status:
                try:
                    gw = WorkspaceClient()
                    st.write("\U0001F4E8 Sending question to Genie Space...")

                    if st.session_state.genie_conv_id is None:
                        # Start new conversation
                        conv_resp = gw.genie.start_conversation(space_id=GENIE_SPACE_ID, content=genie_q.strip())
                        st.session_state.genie_conv_id = conv_resp.conversation_id
                        msg_id = conv_resp.message_id
                    else:
                        # Continue conversation
                        msg_resp = gw.genie.create_message(space_id=GENIE_SPACE_ID, conversation_id=st.session_state.genie_conv_id, content=genie_q.strip())
                        msg_id = msg_resp.id

                    st.write("\U0001F50D Genie is analyzing your data...")

                    # Poll for completion
                    genie_answer = None
                    genie_sql = None
                    genie_data = None
                    for attempt in range(30):
                        _time.sleep(2)
                        msg_detail = gw.genie.get_message(space_id=GENIE_SPACE_ID, conversation_id=st.session_state.genie_conv_id, message_id=msg_id)
                        if msg_detail.status and msg_detail.status.value in ("COMPLETED", "FAILED"):
                            break

                    if msg_detail.status and msg_detail.status.value == "COMPLETED":
                        st.write("\U00002705 Genie response ready!")
                        # Extract attachments
                        if msg_detail.attachments:
                            for att in msg_detail.attachments:
                                if hasattr(att, 'text') and att.text:
                                    genie_answer = att.text.content if hasattr(att.text, 'content') else str(att.text)
                                if hasattr(att, 'query') and att.query:
                                    genie_sql = att.query.query if hasattr(att.query, 'query') else str(att.query)
                                    # Try to fetch query results
                                    if hasattr(att.query, 'query') and att.query.query:
                                        try:
                                            genie_data = execute_sql(att.query.query)
                                        except Exception:
                                            pass
                        if not genie_answer and hasattr(msg_detail, 'content'):
                            genie_answer = str(msg_detail.content)
                        genie_status.update(label="Genie response ready", state="complete")
                    else:
                        genie_answer = "Genie could not complete the request. Try rephrasing your question."
                        genie_status.update(label="Genie request incomplete", state="error")

                    st.session_state.genie_history.append({
                        "question": genie_q.strip(),
                        "answer": genie_answer,
                        "sql": genie_sql,
                        "data": genie_data
                    })
                    if "genie_input_q" in st.session_state:
                        del st.session_state["genie_input_q"]

                except Exception as e:
                    st.session_state.genie_history.append({
                        "question": genie_q.strip(),
                        "answer": f"Error connecting to Genie: {str(e)}",
                        "sql": None, "data": None
                    })
                    genie_status.update(label="Genie error", state="error")

        # Display Genie conversation
        if st.session_state.genie_history:
            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
            for idx, entry in enumerate(reversed(st.session_state.genie_history)):
                turn = len(st.session_state.genie_history) - idx
                st.markdown(f'<div class="chat-user-msg"><strong>\U0001F464 You:</strong> {entry["question"]}</div>', unsafe_allow_html=True)
                if entry.get("answer"):
                    st.markdown(f'<div class="chat-agent-msg">\U0001F9DE <strong>Genie:</strong><br/><br/>{entry["answer"]}</div>', unsafe_allow_html=True)
                if entry.get("sql"):
                    with st.expander(f"\U0001F4CB Genie SQL (Turn {turn})", expanded=False):
                        st.code(entry["sql"], language="sql")
                if entry.get("data") is not None and not entry["data"].empty:
                    render_genie_chart(entry["data"])
                    with st.expander(f"\U0001F4CB Result table ({len(entry['data'])} rows)", expanded=False):
                        enhanced_dataframe(entry["data"], title=f"Genie Results Turn {turn}", key_prefix=f"genie_{turn}", height=300, show_stats=False)
        else:
            st.markdown("""<div class="glass-card" style="text-align: center; padding: 30px;">
                <div style="font-size: 2rem; margin-bottom: 8px;">\U0001F9DE</div>
                <div style="color: #cbd5e1; font-size: 0.95rem;">Ask Genie a question to query your insurance data using natural language</div>
                <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 6px;">Connected to 19 tables in uae_insurance.uae_silver</div>
            </div>""", unsafe_allow_html=True)

    with ai_tab2:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4CA</span>
            <span class="section-header-text">CXO Executive Intelligence Brief</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("AI-generated strategic summary for C-suite stakeholders. Synthesizes portfolio health, financial exposure, operational efficiency, and forward-looking risk posture.")

        sum_col1, sum_col2 = st.columns([1.5, 3.5])
        with sum_col1:
            summary_scope = st.selectbox("Summary Scope", ["Overall Portfolio", "High-Risk Cases Only", "Financial Recovery Focus", "Operational Efficiency"], key="exec_scope")
            summary_tone = st.selectbox("Audience", ["CEO / Board", "CFO / Finance", "COO / Operations", "CRO / Risk"], key="exec_tone")

        if st.button("\U0001F4CB Generate Executive Brief", key="summary_btn", use_container_width=False):
            if not df.empty:
                with st.spinner("Compiling executive intelligence from fraud portfolio data..."):
                    # Build comprehensive CXO context
                    total_inv = len(df)
                    avg_score = df['FRAUD_SCORE'].mean()
                    total_detected = df['FRAUD_AMOUNT_DETECTED'].sum()
                    total_recovered = df['RECOVERY_AMOUNT'].sum()
                    total_cost = df['INVESTIGATION_COST'].sum()
                    recovery_rate = (total_recovered / total_detected * 100) if total_detected > 0 else 0
                    roi = ((total_recovered - total_cost) / total_cost * 100) if total_cost > 0 else 0
                    avg_days = df['INVESTIGATION_DAYS'].mean()

                    # Status breakdown
                    status_counts = df['INVESTIGATION_STATUS'].value_counts().to_dict()
                    active_cases = status_counts.get('INITIATED', 0) + status_counts.get('IN_PROGRESS', 0)
                    closed_cases = status_counts.get('COMPLETED', 0) + status_counts.get('CLOSED', 0)
                    closure_rate = (closed_cases / total_inv * 100) if total_inv > 0 else 0

                    # Findings breakdown
                    findings_counts = df['FINDINGS'].value_counts().to_dict()
                    confirmed_fraud = findings_counts.get('FRAUD_CONFIRMED', 0)
                    no_fraud = findings_counts.get('NO_FRAUD', 0)
                    false_positive_rate = (no_fraud / total_inv * 100) if total_inv > 0 else 0
                    confirmation_rate = (confirmed_fraud / total_inv * 100) if total_inv > 0 else 0

                    # High risk segment
                    high_risk = df[df['FRAUD_SCORE'] > 75]
                    high_risk_pct = (len(high_risk) / total_inv * 100) if total_inv > 0 else 0
                    high_risk_exposure = high_risk['FRAUD_AMOUNT_DETECTED'].sum()

                    # SLA breaches (>30 days active)
                    active_df = df[df['INVESTIGATION_STATUS'].isin(['INITIATED', 'IN_PROGRESS'])]
                    sla_breached = len(active_df[active_df['INVESTIGATION_DAYS'] > 30])
                    sla_breach_pct = (sla_breached / len(active_df) * 100) if len(active_df) > 0 else 0

                    # MoM trend (last 2 months)
                    df['MONTHYEAR_SORT'] = pd.to_numeric(df['MONTHYEAR_SORT'], errors='coerce')
                    monthly_trend = df.groupby('MONTHYEAR_SORT').agg(
                        cases=('INVESTIGATION_ID', 'count'),
                        fraud=('FRAUD_AMOUNT_DETECTED', 'sum')
                    ).sort_index()
                    mom_case_change = 0
                    mom_fraud_change = 0
                    if len(monthly_trend) >= 2:
                        prev, latest = monthly_trend.iloc[-2], monthly_trend.iloc[-1]
                        mom_case_change = ((latest['cases'] - prev['cases']) / prev['cases'] * 100) if prev['cases'] > 0 else 0
                        mom_fraud_change = ((latest['fraud'] - prev['fraud']) / prev['fraud'] * 100) if prev['fraud'] > 0 else 0

                    # Scope-specific filter
                    scope_context = ""
                    if summary_scope == "High-Risk Cases Only":
                        scope_context = f"Focus ONLY on high-risk cases (score>75): {len(high_risk)} cases, AED {high_risk_exposure:,.0f} exposure, {high_risk_pct:.1f}% of portfolio."
                    elif summary_scope == "Financial Recovery Focus":
                        scope_context = f"Focus on FINANCIAL RECOVERY: AED {total_recovered:,.0f} recovered of AED {total_detected:,.0f} detected. Recovery rate: {recovery_rate:.1f}%. Net ROI: {roi:.1f}%. Cost basis: AED {total_cost:,.0f}."
                    elif summary_scope == "Operational Efficiency":
                        scope_context = f"Focus on OPERATIONAL EFFICIENCY: Avg resolution: {avg_days:.0f} days. Closure rate: {closure_rate:.1f}%. Active pipeline: {active_cases} cases. SLA breach rate: {sla_breach_pct:.1f}%."
                    else:
                        scope_context = "Provide a comprehensive overview across all dimensions."

                    # Audience tone
                    tone_instructions = {
                        "CEO / Board": "Write for a CEO and Board audience. Lead with strategic risk posture, business impact in AED, and actionable recommendations. Use decisive language. Include a 1-line verdict at the top.",
                        "CFO / Finance": "Write for a CFO. Emphasize financial metrics: ROI, recovery rates, cost-per-case, reserve adequacy, and P&L impact. Include variance analysis where relevant.",
                        "COO / Operations": "Write for a COO. Emphasize throughput, SLA compliance, resource utilization, bottlenecks, and process improvement opportunities.",
                        "CRO / Risk": "Write for a Chief Risk Officer. Emphasize risk exposure, emerging threats, model accuracy (false positive rate), portfolio concentration, and regulatory compliance posture."
                    }[summary_tone]

                    ctx = f"""FRAUD INVESTIGATION PORTFOLIO DATA:
- Total Investigations: {total_inv:,}
- Active Pipeline: {active_cases:,} | Closed: {closed_cases:,} | Closure Rate: {closure_rate:.1f}%
- Avg Fraud Score: {avg_score:.1f}/100
- Total Fraud Detected: AED {total_detected:,.0f}
- Total Recovered: AED {total_recovered:,.0f} | Recovery Rate: {recovery_rate:.1f}%
- Total Investigation Cost: AED {total_cost:,.0f} | Net ROI: {roi:.1f}%
- Avg Investigation Duration: {avg_days:.0f} days
- Fraud Confirmed: {confirmed_fraud} ({confirmation_rate:.1f}%) | No Fraud: {no_fraud} ({false_positive_rate:.1f}%)
- High-Risk Cases (score>75): {len(high_risk)} ({high_risk_pct:.1f}%) | Exposure: AED {high_risk_exposure:,.0f}
- SLA Breaches (>30d active): {sla_breached} ({sla_breach_pct:.1f}% of active)
- MoM Case Volume Change: {mom_case_change:+.1f}%
- MoM Fraud Amount Change: {mom_fraud_change:+.1f}%
- Findings: FRAUD_CONFIRMED={confirmed_fraud}, FRAUD_SUSPECTED={findings_counts.get('FRAUD_SUSPECTED', 0)}, INCONCLUSIVE={findings_counts.get('INCONCLUSIVE', 0)}, NO_FRAUD={no_fraud}

SCOPE: {scope_context}"""

                    prompt_text = escape_sql(f"""You are the Chief Analytics Officer at a Middle East insurance company presenting to the executive committee.

{tone_instructions}

Structure your response in markdown with these sections:
## Executive Verdict (1-2 sentences — the headline)
## Key Metrics Dashboard (use a clean bullet list with AED values)
## Risk & Exposure Assessment (what keeps you up at night)
## Operational Performance (efficiency, bottlenecks, SLA)
## Strategic Recommendations (3-5 actionable items, prioritized)
## 90-Day Outlook (forward-looking projection based on MoM trends)

Be specific with numbers. Use AED currency. Flag any metric that is in a danger zone. If ROI is strong, say so confidently. If there are concerns, be direct.

DATA:
{ctx}""")

                    try:
                        query = f"SELECT ai_query('databricks-claude-sonnet-4-6', '{prompt_text}') AS AI_SUMMARY"
                        result = execute_sql(query)
                        st.markdown(render_ai_response(result['AI_SUMMARY'].iloc[0]))
                    except Exception as e:
                        st.warning(f"Could not reach AI Serving Endpoint: {e}")

    with ai_tab3:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4C4</span>
            <span class="section-header-text">Claims Document Search</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("Search **claim submission forms**, **settlement notifications**, **investigation reports**, and **denial letters** using the RAG agent powered by Vector Search + Claude.")

        if "claims_doc_history" not in st.session_state:
            st.session_state.claims_doc_history = []

        st.markdown("**Try asking:**")
        cd_cols = st.columns(4)
        cd_examples = [
            "What claims were settled and for how much?",
            "Are there any fraud investigation reports?",
            "Which claims were denied and why?",
            "Show me claim forms with large amounts",
        ]
        for i, cdq in enumerate(cd_examples):
            if cd_cols[i].button(cdq, key=f"cdq_{i}", use_container_width=True):
                st.session_state["claims_doc_input_q"] = cdq

        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        cd_default = st.session_state.get("claims_doc_input_q", "")
        cd_question = st.text_area(
            "Ask about claim documents:",
            value=cd_default,
            placeholder="e.g., What did the investigation report say about CLM000089?",
            height=80,
            key="claims_doc_q_input",
        )

        cd_btn1, cd_btn2, _ = st.columns([1, 1, 4])
        run_claims = cd_btn1.button("\U0001F4C4 Search Documents", key="run_claims_doc_btn", use_container_width=True)
        clear_claims = cd_btn2.button("\U0001F5D1 Clear History", key="clear_claims_doc_btn", use_container_width=True)

        if clear_claims:
            st.session_state.claims_doc_history = []
            st.rerun()

        if run_claims and cd_question.strip():
            with st.status("Claims Agent is searching documents...", expanded=True) as cd_status:
                try:
                    st.write("\U0001F50D Searching claim documents with RAG agent...")
                    safe_q = escape_sql(cd_question.strip())
                    rag_query = f"""
                    SELECT element_at(
                      filter(
                        ai_query('claims_rag_agent',
                          request => named_struct(
                            'messages', array(
                              named_struct('role', 'user', 'content', '{safe_q}')
                            )
                          ),
                          returnType => 'STRUCT<messages:ARRAY<STRUCT<content:STRING, type:STRING>>>'
                        ).messages,
                        m -> m.type = 'ai' AND m.content IS NOT NULL AND length(m.content) > 50
                      ),
                      -1
                    ).content AS answer
                    """
                    result = execute_sql(rag_query)
                    st.write("\U00002705 Documents retrieved and analyzed!")
                    if not result.empty and result['answer'].iloc[0]:
                        answer = render_ai_response(result['answer'].iloc[0])
                        st.session_state.claims_doc_history.append({
                            "question": cd_question.strip(),
                            "answer": answer,
                            "error": None,
                        })
                        cd_status.update(label="Document search complete", state="complete")
                    else:
                        st.session_state.claims_doc_history.append({
                            "question": cd_question.strip(),
                            "answer": "No relevant documents found. Try rephrasing your question.",
                            "error": None,
                        })
                        cd_status.update(label="No results found", state="complete")
                except Exception as e:
                    st.session_state.claims_doc_history.append({
                        "question": cd_question.strip(),
                        "answer": None,
                        "error": str(e),
                    })
                    cd_status.update(label="Document search failed", state="error")

            if "claims_doc_input_q" in st.session_state:
                del st.session_state["claims_doc_input_q"]

        if st.session_state.claims_doc_history:
            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
            for idx, entry in enumerate(reversed(st.session_state.claims_doc_history)):
                turn = len(st.session_state.claims_doc_history) - idx
                st.markdown(f'<div class="chat-user-msg"><strong>\U0001F464 You (Turn {turn}):</strong> {entry["question"]}</div>', unsafe_allow_html=True)
                if entry.get("error"):
                    st.error(f"Agent Error: {entry['error']}")
                elif entry.get("answer"):
                    st.markdown(f'<div class="chat-agent-msg">\U0001F4C4 <strong>Claims Agent:</strong><br/><br/>{entry["answer"]}</div>', unsafe_allow_html=True)
                st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="glass-card" style="text-align: center; padding: 40px;">
                <div style="font-size: 2.5rem; margin-bottom: 12px;">\U0001F4C4</div>
                <div style="color: #cbd5e1; font-size: 1rem;">Ask a question above to search claim documents</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 8px;">
                    Searches 25 PDF documents: claim forms, settlement notifications, investigation reports, and denial letters
                </div>
            </div>""", unsafe_allow_html=True)


    with ai_tab4:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F50D</span>
            <span class="section-header-text">Fraud Investigation Agent</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("Ask natural language questions about **investigations**, **claims**, **customers**, and **fraud patterns**. "
                     "The agent generates SQL, queries your data, and provides AI-powered analysis.")
        if "agent_history" not in st.session_state:
            st.session_state.agent_history = []

        st.markdown("**Try asking:**")
        eq_cols = st.columns(4)
        example_questions = ["What are our most expensive investigations?", "Which investigators have the best recovery rates?", "Show fraud patterns by business line", "Which customers have multiple fraud cases?"]
        for i, eq in enumerate(example_questions):
            if eq_cols[i].button(eq, key=f"eq_{i}", use_container_width=True):
                st.session_state["agent_input_question"] = eq

        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        default_q = st.session_state.get("agent_input_question", "")
        user_question = st.text_area("Ask the Fraud Agent a question:", value=default_q, placeholder="e.g., What is the total fraud detected for confirmed cases?", height=80, key="agent_question_input")

        col_btn1, col_btn2, _ = st.columns([1, 1, 4])
        run_agent = col_btn1.button("\U0001F680 Ask Agent", key="run_agent_btn", use_container_width=True)
        clear_history = col_btn2.button("\U0001F5D1 Clear History", key="clear_history_btn", use_container_width=True)
        if clear_history:
            st.session_state.agent_history = []
            st.rerun()

        if run_agent and user_question.strip():
            with st.status("Fraud Agent is working...", expanded=True) as status:
                st.write("\U0001F9E0 Analyzing your question...")
                st.write("\U0001F4DD Generating SQL query from schema context...")
                agent_result = fraud_agent_query(user_question.strip())
                if agent_result["sql"]:
                    st.write("\U00002705 SQL generated successfully")
                    st.write("\U0001F50D Executing query against fraud database...")
                if agent_result["data"] is not None and not agent_result["data"].empty:
                    st.write(f"\U00002705 Retrieved {len(agent_result['data'])} rows")
                    st.write("\U0001F916 AI analyzing results...")
                if agent_result["error"]:
                    status.update(label="Agent encountered an issue", state="error")
                else:
                    status.update(label="Analysis complete", state="complete")
            st.session_state.agent_history.append({"question": user_question.strip(), "result": agent_result})
            if "agent_input_question" in st.session_state:
                del st.session_state["agent_input_question"]

        if st.session_state.agent_history:
            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
            for idx, entry in enumerate(reversed(st.session_state.agent_history)):
                q = entry["question"]
                r = entry["result"]
                turn_num = len(st.session_state.agent_history) - idx
                st.markdown(f'<div class="chat-user-msg"><strong>\U0001F464 You (Turn {turn_num}):</strong> {q}</div>', unsafe_allow_html=True)
                if r.get("error"):
                    st.error(f"Agent Error: {r['error']}")
                else:
                    if r.get("answer"):
                        st.markdown(f'<div class="chat-agent-msg">\U0001F916 <strong>Fraud Agent:</strong><br/><br/>{r["answer"]}</div>', unsafe_allow_html=True)
                    if r.get("sql"):
                        with st.expander(f"\U0001F4CB View Generated SQL (Turn {turn_num})", expanded=False):
                            st.code(r["sql"], language="sql")
                    if r.get("data") is not None and not r["data"].empty:
                        with st.expander(f"\U0001F4CA View Data ({len(r['data'])} rows) (Turn {turn_num})", expanded=False):
                            enhanced_dataframe(r["data"], title=f"Agent Query {turn_num}", key_prefix=f"agent_{turn_num}", height=300, show_stats=False)
                st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="glass-card" style="text-align: center; padding: 40px;">
                <div style="font-size: 2.5rem; margin-bottom: 12px;">\U0001F50D</div>
                <div style="color: #cbd5e1; font-size: 1rem;">Ask a question above to start investigating fraud data</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 8px;">
                    The agent queries 5 connected tables: investigations, claims, customers, policies, and AI results
                </div>
            </div>""", unsafe_allow_html=True)

    with ai_tab5:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F9E0</span>
            <span class="section-header-text">Investigation Sentiment Analysis</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("Assesses investigation sentiment from status, outcomes, and financial metrics. Toggle AI for LLM-powered analysis.")

        se_col1, se_col2, se_col3 = st.columns([1, 1, 2])
        sent_limit = se_col1.selectbox("Rows", [10, 25, 50, 100], index=1, key="sent_limit")
        use_ai_sent = se_col2.checkbox("AI-Enhanced", value=False, key="ai_sent_toggle",
                                        help="Uses ai_analyze_sentiment (slower, ~5s/row)")

        if st.button("\U0001F9E0 Run Sentiment Analysis", key="run_sentiment"):
            t_start = time.time()
            if use_ai_sent:
                with st.spinner("Running AI sentiment analysis (LLM-powered)..."):
                    sent_query = f"""
                    SELECT fi.INVESTIGATION_ID, fi.FRAUD_SCORE, fi.INVESTIGATION_STATUS, fi.FINDINGS,
                        ROUND(fi.FRAUD_AMOUNT_DETECTED, 0) AS FRAUD_AMOUNT,
                        ROUND(fi.RECOVERY_AMOUNT, 0) AS RECOVERY_AMOUNT, fi.INVESTIGATION_DAYS,
                        ai_analyze_sentiment(
                            'Investigation ' || fi.INVESTIGATION_STATUS || '. Finding: ' || fi.FINDINGS ||
                            '. Fraud score: ' || cast(fi.FRAUD_SCORE as STRING) ||
                            '. Detected: AED ' || cast(round(fi.FRAUD_AMOUNT_DETECTED, 0) as STRING) ||
                            ', Recovered: AED ' || cast(round(fi.RECOVERY_AMOUNT, 0) as STRING) ||
                            ' after ' || cast(fi.INVESTIGATION_DAYS as STRING) || ' days.'
                        ) AS SENTIMENT
                    FROM uae_insurance.uae_silver.fact_fraud_investigation fi
                    ORDER BY fi.FRAUD_SCORE DESC LIMIT {sent_limit}
                    """
                    mode_label = "AI-Enhanced (ai_analyze_sentiment)"
            else:
                with st.spinner("Running rule-based sentiment analysis..."):
                    sent_query = f"""
                    SELECT INVESTIGATION_ID, FRAUD_SCORE, INVESTIGATION_STATUS, FINDINGS,
                        ROUND(FRAUD_AMOUNT_DETECTED, 0) AS FRAUD_AMOUNT,
                        ROUND(RECOVERY_AMOUNT, 0) AS RECOVERY_AMOUNT, INVESTIGATION_DAYS,
                        CASE
                            WHEN INVESTIGATION_STATUS = 'Closed' AND RECOVERY_AMOUNT > FRAUD_AMOUNT_DETECTED * 0.5 AND FRAUD_SCORE < 40 THEN 'positive'
                            WHEN INVESTIGATION_STATUS = 'Closed' AND RECOVERY_AMOUNT > 0 THEN 'neutral'
                            WHEN FRAUD_SCORE > 70 AND FRAUD_AMOUNT_DETECTED > 50000 AND RECOVERY_AMOUNT < FRAUD_AMOUNT_DETECTED * 0.2 THEN 'negative'
                            WHEN FRAUD_SCORE > 50 AND INVESTIGATION_DAYS > 60 THEN 'negative'
                            WHEN FRAUD_SCORE > 50 AND RECOVERY_AMOUNT > FRAUD_AMOUNT_DETECTED * 0.3 THEN 'mixed'
                            WHEN FRAUD_SCORE > 30 THEN 'mixed'
                            WHEN INVESTIGATION_STATUS IN ('Open', 'Under Review') THEN 'neutral'
                            ELSE 'neutral'
                        END AS SENTIMENT
                    FROM uae_insurance.uae_silver.fact_fraud_investigation
                    ORDER BY FRAUD_SCORE DESC LIMIT {sent_limit}
                    """
                    mode_label = "Rule-Based (instant)"

            try:
                sent_result = execute_sql(sent_query)
                elapsed = time.time() - t_start
                if not sent_result.empty:
                    sent_vals = sent_result['SENTIMENT'].astype(str).str.lower()
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("Negative", f"{(sent_vals == 'negative').sum()}")
                    sc2.metric("Mixed", f"{(sent_vals == 'mixed').sum()}")
                    sc3.metric("Neutral", f"{(sent_vals == 'neutral').sum()}")
                    sc4.metric("Positive", f"{(sent_vals == 'positive').sum()}")

                    enhanced_dataframe(sent_result, title="Sentiment Analysis", key_prefix="sent_tbl", height=400)

                    st.markdown(f"""<div style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2); border-radius: 10px; padding: 12px 16px; margin-top: 12px;">
                        <span style="color: #a5b4fc; font-weight: 600; font-size: 0.82rem;">Performance</span><br/>
                        <span style="color: #94a3b8; font-size: 0.82rem;">
                            Mode: <b style="color:#e2e8f0">{mode_label}</b> &nbsp;|&nbsp;
                            Time: <b style="color:#e2e8f0">{elapsed:.1f}s</b> &nbsp;|&nbsp;
                            Rows: <b style="color:#e2e8f0">{len(sent_result)}</b> &nbsp;|&nbsp;
                            Speed: <b style="color:#e2e8f0">{elapsed/max(len(sent_result),1):.2f}s/row</b>
                        </span>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.warning("No results returned.")
            except Exception as e:
                st.warning(f"Sentiment analysis error: {e}")


    with ai_tab6:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4CA</span>
            <span class="section-header-text">Multi-Dimensional Risk Scoring</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("Scores **Severity**, **Likelihood**, and **Impact** using rule-based engine. Toggle AI for LLM-enhanced analysis.")

        rs_col1, rs_col2, rs_col3 = st.columns([1, 1, 2])
        risk_limit = rs_col1.selectbox("Rows", [10, 25, 50, 100], index=1, key="risk_limit")
        use_ai_risk = rs_col2.checkbox("AI-Enhanced", value=False, key="ai_risk_toggle",
                                        help="Uses ai_classify for nuanced scoring (slower, ~10s/row)")

        if st.button("\U0001F4CA Generate Risk Scores", key="run_risk_scoring"):
            t_start = time.time()
            if use_ai_risk:
                with st.spinner("Running AI risk classification (slower, LLM-powered)..."):
                    risk_query = f"""
                    SELECT
                        fi.INVESTIGATION_ID, fi.FRAUD_SCORE, fi.FINDINGS,
                        ROUND(fi.FRAUD_AMOUNT_DETECTED, 0) AS FRAUD_AMOUNT,
                        fi.INVESTIGATION_STATUS, ROUND(fi.RECOVERY_AMOUNT, 0) AS RECOVERY,
                        fi.INVESTIGATION_DAYS,
                        ai_classify(
                            'Fraud score: ' || cast(fi.FRAUD_SCORE as STRING) ||
                            ', Amount: AED ' || cast(round(fi.FRAUD_AMOUNT_DETECTED, 0) as STRING) ||
                            ', Finding: ' || fi.FINDINGS || ', Status: ' || fi.INVESTIGATION_STATUS ||
                            ', Recovery: AED ' || cast(round(fi.RECOVERY_AMOUNT, 0) as STRING) ||
                            ', Days: ' || cast(fi.INVESTIGATION_DAYS as STRING),
                            '{{
                                "Critical-VeryHigh-Catastrophic": "Fraud score >75, amount >AED 50k, confirmed fraud",
                                "Critical-High-Major": "Fraud score >75, amount AED 30k-AED 75k, serious case",
                                "High-High-Major": "Fraud score 50-75, significant suspicious activity",
                                "High-Medium-Moderate": "Fraud score 50-75, moderate financial exposure",
                                "Medium-Medium-Moderate": "Fraud score 25-50, standard investigation",
                                "Medium-Low-Minor": "Fraud score 25-50, routine case",
                                "Low-Low-Minor": "Fraud score <25, minimal indicators"
                            }}',
                            MAP('instructions', 'Classify this fraud investigation into a combined severity-likelihood-impact tier.')
                        ):response[0] AS RISK_COMPOSITE
                    FROM uae_insurance.uae_silver.fact_fraud_investigation fi
                    ORDER BY RANDOM() LIMIT {risk_limit}
                    """
                    try:
                        risk_result = execute_sql(risk_query)
                        elapsed = time.time() - t_start
                        if not risk_result.empty:
                            composite = risk_result['RISK_COMPOSITE'].astype(str)
                            parts = composite.str.split('-', expand=True)
                            risk_result['SEVERITY'] = parts[0].fillna('Medium') if parts.shape[1] > 0 else 'Medium'
                            risk_result['LIKELIHOOD'] = parts[1].fillna('Medium') if parts.shape[1] > 1 else 'Medium'
                            risk_result['IMPACT'] = parts[2].fillna('Moderate') if parts.shape[1] > 2 else 'Moderate'
                            display_cols = [c for c in risk_result.columns if c != 'RISK_COMPOSITE']
                            mode_label = "AI-Enhanced (ai_classify)"
                        else:
                            st.warning("No results returned.")
                            risk_result = None
                    except Exception as e:
                        st.warning(f"AI risk scoring error: {e}")
                        risk_result = None
            else:
                with st.spinner("Running rule-based risk scoring..."):
                    risk_query = f"""
                    SELECT
                        INVESTIGATION_ID, FRAUD_SCORE, FINDINGS,
                        ROUND(FRAUD_AMOUNT_DETECTED, 0) AS FRAUD_AMOUNT,
                        INVESTIGATION_STATUS,
                        ROUND(RECOVERY_AMOUNT, 0) AS RECOVERY,
                        INVESTIGATION_DAYS,
                        CASE
                            WHEN FRAUD_SCORE > 75 AND FRAUD_AMOUNT_DETECTED > 50000 THEN 'Critical'
                            WHEN FRAUD_SCORE > 75 THEN 'Critical'
                            WHEN FRAUD_SCORE > 50 THEN 'High'
                            WHEN FRAUD_SCORE > 25 THEN 'Medium'
                            ELSE 'Low'
                        END AS SEVERITY,
                        CASE
                            WHEN INVESTIGATION_STATUS IN ('Open', 'Under Review') AND FRAUD_SCORE > 60 AND INVESTIGATION_DAYS > 30 THEN 'Very High'
                            WHEN INVESTIGATION_STATUS IN ('Open', 'Under Review') AND FRAUD_SCORE > 40 THEN 'High'
                            WHEN INVESTIGATION_STATUS = 'Closed' AND FRAUD_SCORE < 30 THEN 'Low'
                            ELSE 'Medium'
                        END AS LIKELIHOOD,
                        CASE
                            WHEN FRAUD_AMOUNT_DETECTED > 75000 THEN 'Catastrophic'
                            WHEN FRAUD_AMOUNT_DETECTED > 30000 THEN 'Major'
                            WHEN FRAUD_AMOUNT_DETECTED > 10000 THEN 'Moderate'
                            ELSE 'Minor'
                        END AS IMPACT
                    FROM uae_insurance.uae_silver.fact_fraud_investigation
                    ORDER BY FRAUD_SCORE DESC
                    LIMIT {risk_limit}
                    """
                    try:
                        risk_result = execute_sql(risk_query)
                        elapsed = time.time() - t_start
                        display_cols = risk_result.columns.tolist() if not risk_result.empty else []
                        mode_label = "Rule-Based (instant)"
                    except Exception as e:
                        st.warning(f"Risk scoring error: {e}")
                        risk_result = None

            if risk_result is not None and not risk_result.empty:
                sev = risk_result['SEVERITY'].astype(str)
                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("Critical", f"{sev.str.contains('Critical', case=False).sum()}")
                rc2.metric("High", f"{sev.str.contains('High', case=False).sum()}")
                rc3.metric("Catastrophic Impact", f"{risk_result['IMPACT'].astype(str).str.contains('Catastrophic', case=False).sum()}")
                rc4.metric("Rows Scored", f"{len(risk_result)}")

                enhanced_dataframe(risk_result[display_cols] if display_cols else risk_result, title="Risk Scoring", key_prefix="risk_tbl", height=400)

                st.markdown(f"""<div style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2); border-radius: 10px; padding: 12px 16px; margin-top: 12px;">
                    <span style="color: #a5b4fc; font-weight: 600; font-size: 0.82rem;">Performance</span><br/>
                    <span style="color: #94a3b8; font-size: 0.82rem;">
                        Mode: <b style="color:#e2e8f0">{mode_label}</b> &nbsp;|&nbsp;
                        Time: <b style="color:#e2e8f0">{elapsed:.1f}s</b> &nbsp;|&nbsp;
                        Rows: <b style="color:#e2e8f0">{len(risk_result)}</b> &nbsp;|&nbsp;
                        Speed: <b style="color:#e2e8f0">{elapsed/max(len(risk_result),1):.2f}s/row</b>
                    </span>
                </div>""", unsafe_allow_html=True)


    with ai_tab7:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F52E</span>
            <span class="section-header-text">ML Fraud Trend Forecasting</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("Statistical trend analysis with **AI-powered insights** — forecasts fraud metrics using linear regression, exponential smoothing, and LLM narrative interpretation.")

        fc_col1, fc_col2, fc_col3 = st.columns([1.2, 1, 2.8])
        forecast_metric = fc_col1.selectbox("Forecast Metric", [
            "Fraud Amount Detected", "Recovery Amount", "Investigation Count",
            "Avg Fraud Score", "Investigation Cost"
        ], key="fc_metric")
        forecast_horizon = fc_col2.selectbox("Horizon (months)", [3, 6, 9, 12], index=1, key="fc_horizon")

        metric_map = {
            "Fraud Amount Detected": ("ROUND(SUM(FRAUD_AMOUNT_DETECTED), 0)", "AED ", ",.0f"),
            "Recovery Amount": ("ROUND(SUM(RECOVERY_AMOUNT), 0)", "AED ", ",.0f"),
            "Investigation Count": ("COUNT(*)", "", ",.0f"),
            "Avg Fraud Score": ("ROUND(AVG(FRAUD_SCORE), 1)", "", ",.1f"),
            "Investigation Cost": ("ROUND(SUM(INVESTIGATION_COST), 0)", "AED ", ",.0f"),
        }

        if st.button("\U0001F52E Generate Forecast", key="run_forecast"):
            with st.spinner("Building statistical forecast model + AI analysis..."):
                sql_expr, prefix, fmt = metric_map[forecast_metric]
                hist_query = f"""
                SELECT
                    DATE_TRUNC('month', FR_DATE) AS month_date,
                    {sql_expr} AS metric_value
                FROM uae_insurance.uae_silver.fact_fraud_investigation
                GROUP BY 1
                ORDER BY 1
                """
                try:
                    historical = execute_sql(hist_query)
                    if historical.empty:
                        st.warning("No historical data found.")
                    else:
                        historical['metric_value'] = pd.to_numeric(historical['metric_value'], errors='coerce').fillna(0)
                        historical['month_date'] = pd.to_datetime(historical['month_date'])
                        historical = historical.sort_values('month_date').reset_index(drop=True)

                        n = len(historical)
                        x = np.arange(n, dtype=float)
                        y = historical['metric_value'].values.astype(float)

                        # --- Linear Regression ---
                        slope, intercept = np.polyfit(x, y, 1)

                        # --- Exponential Smoothing ---
                        alpha = 0.3
                        smoothed = [y[0]]
                        for i in range(1, n):
                            smoothed.append(alpha * y[i] + (1 - alpha) * smoothed[-1])

                        # --- Residual std for confidence intervals ---
                        residuals = y - (slope * x + intercept)
                        std_err = float(np.std(residuals))

                        # --- Generate forecast ---
                        last_date = historical['month_date'].max()
                        forecast_dates = pd.date_range(
                            start=last_date + pd.DateOffset(months=1),
                            periods=forecast_horizon, freq='MS'
                        )
                        trend_per_month = slope
                        last_smoothed = smoothed[-1]

                        fc_values, fc_upper, fc_lower = [], [], []
                        for i in range(forecast_horizon):
                            linear_pred = slope * (n + i) + intercept
                            smooth_pred = last_smoothed + trend_per_month * (i + 1)
                            pred = 0.4 * linear_pred + 0.6 * smooth_pred
                            pred = max(0, pred)
                            ci = 1.96 * std_err * np.sqrt(1 + (i + 1) / n)
                            fc_values.append(round(pred, 1))
                            fc_upper.append(round(max(0, pred + ci), 1))
                            fc_lower.append(round(max(0, pred - ci), 1))

                        forecast_df = pd.DataFrame({
                            'month_date': forecast_dates,
                            'metric_value': fc_values,
                            'upper_bound': fc_upper,
                            'lower_bound': fc_lower,
                            'type': 'Forecast'
                        })

                        historical['type'] = 'Historical'
                        historical['upper_bound'] = historical['metric_value']
                        historical['lower_bound'] = historical['metric_value']

                        combined = pd.concat([historical, forecast_df], ignore_index=True)
                        combined['month_label'] = combined['month_date'].dt.strftime('%b-%Y')

                        # ======== SUMMARY METRICS ========
                        last_actual = float(y[-1])
                        last_forecast = fc_values[-1]
                        avg_historical = float(np.mean(y[-6:])) if n >= 6 else float(np.mean(y))
                        pct_change = ((last_forecast - last_actual) / last_actual * 100) if last_actual != 0 else 0
                        trend_dir = "Upward \U0001F4C8" if slope > 0 else "Downward \U0001F4C9" if slope < 0 else "Flat \U000027A1"

                        mc1, mc2, mc3, mc4 = st.columns(4)
                        mc1.metric("Current (Last Month)", f"{prefix}{last_actual:{fmt}}")
                        mc2.metric(f"Forecast ({forecast_horizon}mo)", f"{prefix}{last_forecast:{fmt}}",
                                   delta=f"{pct_change:+.1f}%")
                        mc3.metric("6-Month Avg", f"{prefix}{avg_historical:{fmt}}")
                        mc4.metric("Trend Direction", trend_dir)

                        st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

                        # ======== ALTAIR CHART ========
                        COLORS = ['#818cf8', '#00C2A8', '#f59e0b', '#ef4444']

                        # Confidence band (forecast only)
                        fc_band = combined[combined['type'] == 'Forecast'].copy()
                        band = alt.Chart(fc_band).mark_area(opacity=0.15, color=COLORS[1]).encode(
                            x=alt.X('month_date:T', title=None),
                            y=alt.Y('lower_bound:Q'),
                            y2=alt.Y2('upper_bound:Q'),
                            tooltip=[
                                alt.Tooltip('month_label', title='Month'),
                                alt.Tooltip('lower_bound:Q', title='Lower', format=fmt),
                                alt.Tooltip('upper_bound:Q', title='Upper', format=fmt),
                            ]
                        )

                        # Historical line
                        hist_line = alt.Chart(combined[combined['type'] == 'Historical']).mark_line(
                            strokeWidth=2.5, color=COLORS[0]
                        ).encode(
                            x=alt.X('month_date:T', title=None),
                            y=alt.Y('metric_value:Q', title=forecast_metric),
                            tooltip=[
                                alt.Tooltip('month_label', title='Month'),
                                alt.Tooltip('metric_value:Q', title='Actual', format=fmt),
                            ]
                        )
                        hist_points = alt.Chart(combined[combined['type'] == 'Historical']).mark_circle(
                            size=25, color=COLORS[0]
                        ).encode(
                            x='month_date:T', y='metric_value:Q'
                        )

                        # Forecast line
                        # Include last historical point for continuity
                        last_hist = combined[combined['type'] == 'Historical'].tail(1).copy()
                        last_hist['type'] = 'Forecast'
                        fc_line_data = pd.concat([last_hist, fc_band], ignore_index=True)

                        fc_line = alt.Chart(fc_line_data).mark_line(
                            strokeWidth=2.5, strokeDash=[6, 4], color=COLORS[1]
                        ).encode(
                            x='month_date:T',
                            y='metric_value:Q',
                            tooltip=[
                                alt.Tooltip('month_label', title='Month'),
                                alt.Tooltip('metric_value:Q', title='Forecast', format=fmt),
                            ]
                        )
                        fc_points = alt.Chart(fc_band).mark_circle(
                            size=35, color=COLORS[1]
                        ).encode(x='month_date:T', y='metric_value:Q')

                        chart = (band + hist_line + hist_points + fc_line + fc_points).properties(
                            title=f'{forecast_metric} — {forecast_horizon}-Month Forecast',
                            width='container', height=380
                        ).configure(
                            background='transparent',
                            title={'color': '#e2e8f0', 'fontSize': 14, 'fontWeight': 600, 'font': 'Inter'},
                            axis={
                                'labelColor': '#94a3b8', 'titleColor': '#cbd5e1',
                                'gridColor': 'rgba(255,255,255,0.06)',
                                'domainColor': 'rgba(255,255,255,0.1)',
                                'tickColor': 'rgba(255,255,255,0.1)',
                                'labelFont': 'Inter', 'titleFont': 'Inter',
                                'labelFontSize': 11, 'titleFontSize': 12,
                            },
                            legend={'labelColor': '#94a3b8', 'titleColor': '#cbd5e1', 'labelFont': 'Inter'},
                            view={'stroke': 'transparent'},
                        )
                        st.altair_chart(chart, use_container_width=True)

                        # ======== LEGEND ========
                        st.markdown("""
                        <div style="display: flex; gap: 24px; justify-content: center; margin: -8px 0 16px 0; font-size: 0.82rem;">
                            <span><span style="color: #818cf8;">\U00002501\U00002501</span> <span style="color: #94a3b8;">Historical</span></span>
                            <span><span style="color: #00C2A8;">\U00002504\U00002504</span> <span style="color: #94a3b8;">Forecast</span></span>
                            <span><span style="color: rgba(0,194,168,0.2);">\U00002588\U00002588</span> <span style="color: #94a3b8;">95% Confidence</span></span>
                        </div>""", unsafe_allow_html=True)

                        # ======== FORECAST TABLE ========
                        with st.expander(f"\U0001F4CB Forecast Data ({forecast_horizon} months)", expanded=False):
                            display_fc = forecast_df[['month_date', 'metric_value', 'lower_bound', 'upper_bound']].copy()
                            display_fc.columns = ['Month', 'Forecast', 'Lower (95%)', 'Upper (95%)']
                            display_fc['Month'] = display_fc['Month'].dt.strftime('%B %Y')
                            enhanced_dataframe(display_fc, title="Forecast Data", key_prefix="fc_tbl", height=250, hide_index=True)

                        # ======== AI NARRATIVE ANALYSIS ========
                        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
                        with st.spinner("Generating AI trend analysis..."):
                            try:
                                recent_6 = ', '.join([f"{historical['month_label'].iloc[-(6-j)]}: {prefix}{y[-(6-j)]:{fmt}}" for j in range(min(6, n))])
                                fc_summary = ', '.join([f"{forecast_df['month_date'].iloc[j].strftime('%b-%Y')}: {prefix}{fc_values[j]:{fmt}}" for j in range(forecast_horizon)])

                                ai_prompt = (
                                    f"You are a senior insurance fraud analyst. Analyze this {forecast_metric} trend. "
                                    f"Recent 6 months: [{recent_6}]. "
                                    f"Forecasted: [{fc_summary}]. "
                                    f"Trend slope: {slope:.1f}/month. Projected change: {pct_change:+.1f}%. "
                                    f"Provide: 1) Trend summary (2 sentences), 2) Key risk or opportunity (1 sentence), "
                                    f"3) Recommended action (1 sentence). Keep it concise and professional."
                                )

                                ai_query = f"""SELECT ai_query('databricks-claude-sonnet-4-6', '{ai_prompt.replace("'", "''")}') AS analysis"""
                                ai_result = execute_sql(ai_query)
                                if not ai_result.empty:
                                    analysis_text = ai_result.iloc[0, 0]
                                    st.markdown(f"""<div class="glass-card">
                                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                                            <span style="font-size: 1.2rem;">&#129504;</span>
                                            <span style="color: #e2e8f0; font-weight: 600; font-size: 0.95rem;">AI Trend Analysis</span>
                                        </div>
                                        <div style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.7;">{analysis_text}</div>
                                    </div>""", unsafe_allow_html=True)
                            except Exception:
                                st.caption("AI narrative analysis unavailable — statistical forecast displayed above.")

                except Exception as e:
                    st.warning(f"Forecast error: {e}")



# ============================================
# PAGE: AI SUPERVISOR
# ============================================
if page == "\U0001F9D1\U0000200D\U0001F4BC  AI Supervisor":
    st.markdown("""<div class="section-header">
        <span class="section-header-icon">\U0001F9D1\U0000200D\U0001F4BC</span>
        <span class="section-header-text">AI Supervisor Agent</span>
    </div>""", unsafe_allow_html=True)
    st.markdown("""This **multi-agent supervisor** orchestrates your Genie Space (structured data) and Claims Document Search (unstructured PDFs) to answer complex questions that span both data sources. Powered by **Databricks Agent Bricks**.""")

    SUPERVISOR_ENDPOINT = "mas-5c4a9766-endpoint"

    if "supervisor_history" not in st.session_state:
        st.session_state.supervisor_history = []
    if "supervisor_thread_id" not in st.session_state:
        st.session_state.supervisor_thread_id = None

    # Example questions
    st.markdown("**Try asking:**")
    sq_cols = st.columns(2)
    supervisor_examples = [
        "Investigate claim CLM000089 — show fraud score, amounts, and what the investigation report says",
        "Which claims were denied? Show the financial impact and explain the rejection reasons from the denial letters",
        "Show top 5 investigators by recovery rate and pull any investigation reports they authored",
        "Summarize all settled claims — amounts from the database and details from the settlement letters",
    ]
    for i, sq in enumerate(supervisor_examples):
        if sq_cols[i % 2].button(sq, key=f"sq_{i}", use_container_width=True):
            st.session_state["supervisor_input_q"] = sq

    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
    sv_default = st.session_state.get("supervisor_input_q", "")
    sv_question = st.text_area(
        "Ask the Supervisor Agent:",
        value=sv_default,
        placeholder="e.g., Compare fraud exposure across business lines and show any related investigation reports",
        height=100,
        key="supervisor_q_input",
    )

    sv_btn1, sv_btn2, _ = st.columns([1, 1, 4])
    run_supervisor = sv_btn1.button("\U0001F680 Ask Supervisor", key="run_supervisor_btn", use_container_width=True)
    clear_supervisor = sv_btn2.button("\U0001F5D1 New Conversation", key="clear_supervisor_btn", use_container_width=True)

    if clear_supervisor:
        st.session_state.supervisor_history = []
        st.session_state.supervisor_thread_id = None
        st.rerun()

    if run_supervisor and sv_question.strip():
        with st.status("Supervisor Agent is coordinating subagents...", expanded=True) as sv_status:
            try:
                st.write("\U0001F9D1\U0000200D\U0001F4BC Routing to specialized agents...")
                st.write("\U0001F50D Querying structured data and searching documents...")

                # Use execute_sql + ai_query — auth handled by SQL warehouse
                safe_q = escape_sql(sv_question.strip())
                supervisor_query = f"""
                SELECT ai_query(
                    '{SUPERVISOR_ENDPOINT}',
                    '{safe_q}',
                    returnType => 'STRING'
                ) AS answer
                """
                result = execute_sql(supervisor_query, max_wait=600)

                answer = None
                if not result.empty and result['answer'].iloc[0]:
                    answer = render_ai_response(result['answer'].iloc[0])

                if not answer:
                    answer = "No response generated. The supervisor may need more context."

                st.write("\U00002705 Supervisor response ready!")
                st.session_state.supervisor_history.append({
                    "question": sv_question.strip(),
                    "answer": answer,
                    "error": None,
                    "raw": {"method": "ai_query", "endpoint": SUPERVISOR_ENDPOINT},
                })
                sv_status.update(label="Supervisor analysis complete", state="complete")

            except Exception as e:
                st.session_state.supervisor_history.append({
                    "question": sv_question.strip(),
                    "answer": None,
                    "error": str(e),
                })
                sv_status.update(label="Supervisor error", state="error")

        if "supervisor_input_q" in st.session_state:
            del st.session_state["supervisor_input_q"]

    # Display conversation history
    if st.session_state.supervisor_history:
        st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
        for idx, entry in enumerate(reversed(st.session_state.supervisor_history)):
            turn = len(st.session_state.supervisor_history) - idx
            st.markdown(f'<div class="chat-user-msg"><strong>\U0001F464 You (Turn {turn}):</strong> {entry["question"]}</div>', unsafe_allow_html=True)
            if entry.get("error"):
                st.error(f"Supervisor Error: {entry['error']}")
            elif entry.get("answer"):
                st.markdown(f'<div class="chat-agent-msg">\U0001F9D1\U0000200D\U0001F4BC <strong>Supervisor Agent:</strong><br/><br/>{entry["answer"]}</div>', unsafe_allow_html=True)
            # Show raw response in expander for debugging
            if entry.get("raw"):
                with st.expander(f"\U0001F50D Raw Response (Turn {turn})", expanded=False):
                    st.json(entry["raw"])
            st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="glass-card" style="text-align: center; padding: 40px;">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">\U0001F9D1\U0000200D\U0001F4BC</div>
            <div style="color: #cbd5e1; font-size: 1rem;">Ask a question to the Supervisor Agent</div>
            <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 8px;">
                Orchestrates multiple AI agents: Genie Space (structured data) + Claims Document Search (PDFs) for comprehensive answers
            </div>
        </div>""", unsafe_allow_html=True)

    # Architecture info
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    with st.expander("\U0001F3D7 Supervisor Architecture", expanded=False):
        st.markdown("""
**How it works:**

The Supervisor Agent receives your question and intelligently routes it to the right subagent(s):

| Subagent | Type | Handles |
|----------|------|---------|
| **Fraud Investigation** | Genie Space | Structured queries — fraud scores, claim amounts, investigator stats, trends across 19 tables |
| **Claims Document Search** | UC Function | Unstructured search — claim forms, settlement letters, investigation reports, denial letters (25 PDFs) |

**Routing logic:**
- Questions about **numbers, aggregations, comparisons** → Genie Space
- Questions about **document contents, reasons, findings** → Claims Document Search
- Questions needing **both** → Calls both and synthesizes the results

**Endpoint:** `mas-5c4a9766-endpoint` | **Built with:** Databricks Agent Bricks
        """)





# --- PAGE: Observability ---
if page == "\U0001F4CA  Observability":
    st.markdown("""<div class="section-header">
        <span class="section-header-icon">\U0001F4CA</span>
        <span class="section-header-text">AI Observability &amp; Cost Monitoring</span>
    </div>""", unsafe_allow_html=True)
    st.markdown("<div style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 16px;'>Performance, token usage, and actual $ cost for Genie, Claims RAG Agent, Supervisor, and LLM endpoints</div>", unsafe_allow_html=True)

    obs_range = st.selectbox("Time Range", ["Last 24 Hours", "Last 7 Days", "Last 30 Days"], index=1, key="obs_range")
    obs_interval_map = {"Last 24 Hours": "1 DAY", "Last 7 Days": "7 DAYS", "Last 30 Days": "30 DAYS"}
    obs_interval = obs_interval_map[obs_range]
    obs_days_map = {"Last 24 Hours": 1, "Last 7 Days": 7, "Last 30 Days": 30}
    obs_days = obs_days_map[obs_range]

    obs_tab1, obs_tab2, obs_tab3, obs_tab4, obs_tab5 = st.tabs([
        "\U0001F4B0 Token Cost ($)",
        "\U0001F916 RAG Agent",
        "\U00002699 Endpoint Usage",
        "\U0001F4AC AI Query Perf",
        "\U000026A0 Errors & Scoring",
    ])

    # =====================================================
    # TAB 1: ACTUAL $ COST (Billing)
    # =====================================================
    with obs_tab1:
        try:
            cost_by_endpoint = execute_sql(f"""
                WITH usage AS (
                    SELECT
                        u.usage_metadata.endpoint_name AS endpoint_name,
                        u.sku_name,
                        u.usage_date,
                        u.usage_quantity AS dbus
                    FROM system.billing.usage u
                    WHERE u.billing_origin_product = 'MODEL_SERVING'
                      AND u.usage_metadata.endpoint_name IN (
                          'claims_rag_agent', 'databricks-claude-sonnet-4-5', 'databricks-bge-large-en',
                          'databricks-meta-llama-3-3-70b-instruct', 'databricks-ai-analyze-sentiment',
                          'mas-5c4a9766-endpoint'
                      )
                      AND u.usage_date >= current_date() - INTERVAL {obs_days} DAYS
                ),
                prices AS (
                    SELECT sku_name, MAX(pricing.effective_list.default) AS price_per_dbu
                    FROM system.billing.list_prices
                    WHERE cloud = 'AZURE' AND currency_code = 'USD'
                    GROUP BY sku_name
                )
                SELECT
                    u.endpoint_name,
                    u.sku_name,
                    ROUND(SUM(u.dbus), 4) AS total_dbus,
                    ROUND(SUM(u.dbus) * MAX(p.price_per_dbu), 2) AS total_cost_usd
                FROM usage u
                LEFT JOIN prices p ON u.sku_name = p.sku_name
                GROUP BY u.endpoint_name, u.sku_name
                ORDER BY total_cost_usd DESC
            """)

            if not cost_by_endpoint.empty:
                grand_total = cost_by_endpoint['total_cost_usd'].sum()

                llm_cost = cost_by_endpoint[cost_by_endpoint['endpoint_name'].isin(['databricks-claude-sonnet-4-5', 'databricks-meta-llama-3-3-70b-instruct'])]['total_cost_usd'].sum()
                agent_cost = cost_by_endpoint[cost_by_endpoint['endpoint_name'].isin(['claims_rag_agent', 'mas-5c4a9766-endpoint'])]['total_cost_usd'].sum()
                embed_cost = cost_by_endpoint[cost_by_endpoint['endpoint_name'].isin(['databricks-bge-large-en'])]['total_cost_usd'].sum()

                kc1, kc2, kc3, kc4 = st.columns(4, gap="medium")
                kc1.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Total AI Cost</div>
                    <div style="color:#f87171; font-size:2rem; font-weight:700;">${grand_total:,.2f}</div>
                    <div style="color:#64748b; font-size:0.75rem;">{obs_range}</div>
                </div>""", unsafe_allow_html=True)
                kc2.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">LLM Cost</div>
                    <div style="color:#818cf8; font-size:2rem; font-weight:700;">${llm_cost:,.2f}</div>
                    <div style="color:#64748b; font-size:0.75rem;">Claude, Llama</div>
                </div>""", unsafe_allow_html=True)
                kc3.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Agent Cost</div>
                    <div style="color:#fbbf24; font-size:2rem; font-weight:700;">${agent_cost:,.2f}</div>
                    <div style="color:#64748b; font-size:0.75rem;">RAG + Supervisor</div>
                </div>""", unsafe_allow_html=True)
                kc4.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Embedding Cost</div>
                    <div style="color:#34d399; font-size:2rem; font-weight:700;">${embed_cost:,.2f}</div>
                    <div style="color:#64748b; font-size:0.75rem;">BGE-Large</div>
                </div>""", unsafe_allow_html=True)

                st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
                st.markdown("**Cost Breakdown by Endpoint**")
                display_cost = cost_by_endpoint.copy()
                display_cost['cost_display'] = display_cost['total_cost_usd'].apply(lambda x: f"${x:,.2f}")
                display_cost['dbu_display'] = display_cost['total_dbus'].apply(lambda x: f"{x:,.2f}")
                st.dataframe(
                    display_cost[['endpoint_name', 'sku_name', 'dbu_display', 'cost_display']].rename(columns={
                        'endpoint_name': 'Endpoint', 'sku_name': 'SKU',
                        'dbu_display': 'DBUs', 'cost_display': 'Cost ($)',
                    }),
                    use_container_width=True, hide_index=True
                )

                daily_cost = execute_sql(f"""
                    WITH usage AS (
                        SELECT
                            u.usage_metadata.endpoint_name AS endpoint_name,
                            u.sku_name,
                            u.usage_date,
                            u.usage_quantity AS dbus
                        FROM system.billing.usage u
                        WHERE u.billing_origin_product = 'MODEL_SERVING'
                          AND u.usage_metadata.endpoint_name IN (
                              'claims_rag_agent', 'databricks-claude-sonnet-4-5', 'databricks-bge-large-en',
                              'databricks-meta-llama-3-3-70b-instruct', 'databricks-ai-analyze-sentiment',
                              'mas-5c4a9766-endpoint'
                          )
                          AND u.usage_date >= current_date() - INTERVAL {obs_days} DAYS
                    ),
                    prices AS (
                        SELECT sku_name, MAX(pricing.effective_list.default) AS price_per_dbu
                        FROM system.billing.list_prices
                        WHERE cloud = 'AZURE' AND currency_code = 'USD'
                        GROUP BY sku_name
                    )
                    SELECT
                        u.usage_date,
                        u.endpoint_name,
                        ROUND(SUM(u.dbus * p.price_per_dbu), 4) AS daily_cost_usd
                    FROM usage u
                    LEFT JOIN prices p ON u.sku_name = p.sku_name
                    GROUP BY u.usage_date, u.endpoint_name
                    ORDER BY u.usage_date
                """)
                if not daily_cost.empty and len(daily_cost) > 1:
                    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
                    st.markdown("**Daily Cost Trend by Endpoint ($)**")
                    import pandas as _pd
                    pivot_cost = daily_cost.pivot_table(index='usage_date', columns='endpoint_name', values='daily_cost_usd', aggfunc='sum').fillna(0)
                    st.bar_chart(pivot_cost)
            else:
                st.info("No billing data for AI endpoints in selected time range.")
        except Exception as e:
            st.warning(f"Cost data unavailable: {e}")

    # =====================================================
    # TAB 2: Claims RAG Agent Performance
    # =====================================================
    with obs_tab2:
        try:
            rag_metrics = execute_sql(f"""
                SELECT
                    COUNT(*) AS total_requests,
                    ROUND(AVG(execution_duration_ms) / 1000.0, 1) AS avg_latency_sec,
                    ROUND(MIN(execution_duration_ms) / 1000.0, 1) AS min_latency_sec,
                    ROUND(MAX(execution_duration_ms) / 1000.0, 1) AS max_latency_sec,
                    ROUND(PERCENTILE(execution_duration_ms, 0.5) / 1000.0, 1) AS p50_latency_sec,
                    ROUND(PERCENTILE(execution_duration_ms, 0.95) / 1000.0, 1) AS p95_latency_sec,
                    SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) AS success_count,
                    ROUND(SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS success_rate
                FROM uae_insurance.uae_silver.claims_rag_agent_payload
                WHERE request_time >= current_timestamp() - INTERVAL {obs_interval}
            """)
            if not rag_metrics.empty and rag_metrics['total_requests'].iloc[0] > 0:
                r = rag_metrics.iloc[0]
                c1, c2, c3, c4 = st.columns(4, gap="medium")
                c1.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Total Requests</div>
                    <div style="color:#e2e8f0; font-size:1.8rem; font-weight:700;">{int(r['total_requests'])}</div>
                </div>""", unsafe_allow_html=True)
                c2.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Avg Latency</div>
                    <div style="color:#fbbf24; font-size:1.8rem; font-weight:700;">{r['avg_latency_sec']}s</div>
                </div>""", unsafe_allow_html=True)
                c3.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">P95 Latency</div>
                    <div style="color:#f87171; font-size:1.8rem; font-weight:700;">{r['p95_latency_sec']}s</div>
                </div>""", unsafe_allow_html=True)
                c4.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Success Rate</div>
                    <div style="color:#34d399; font-size:1.8rem; font-weight:700;">{r['success_rate']}%</div>
                </div>""", unsafe_allow_html=True)

                rag_timeline = execute_sql(f"""
                    SELECT
                        DATE_TRUNC('hour', request_time) AS time_bucket,
                        COUNT(*) AS requests,
                        ROUND(AVG(execution_duration_ms) / 1000.0, 1) AS avg_latency_sec,
                        ROUND(PERCENTILE(execution_duration_ms, 0.95) / 1000.0, 1) AS p95_latency_sec
                    FROM uae_insurance.uae_silver.claims_rag_agent_payload
                    WHERE request_time >= current_timestamp() - INTERVAL {obs_interval}
                    GROUP BY 1
                    ORDER BY 1
                """)
                if not rag_timeline.empty and len(rag_timeline) > 1:
                    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
                    st.markdown("**Latency Over Time** (Claims RAG Agent)")
                    st.line_chart(rag_timeline.set_index('time_bucket')[['avg_latency_sec', 'p95_latency_sec']], color=["#818cf8", "#f87171"])
            else:
                st.info("No Claims RAG Agent requests in selected time range.")
        except Exception as e:
            st.warning(f"Claims RAG Agent metrics unavailable: {e}")

    # =====================================================
    # TAB 3: Endpoint Token Usage
    # =====================================================
    with obs_tab3:
        try:
            endpoint_usage = execute_sql(f"""
                SELECT
                    se.endpoint_name,
                    se.entity_type,
                    COUNT(*) AS total_requests,
                    SUM(CASE WHEN eu.status_code = 200 THEN 1 ELSE 0 END) AS successes,
                    SUM(CASE WHEN eu.status_code != 200 THEN 1 ELSE 0 END) AS errors,
                    ROUND(SUM(CASE WHEN eu.status_code = 200 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS success_rate,
                    SUM(COALESCE(eu.input_token_count, 0)) AS total_input_tokens,
                    SUM(COALESCE(eu.output_token_count, 0)) AS total_output_tokens,
                    SUM(COALESCE(eu.input_token_count, 0) + COALESCE(eu.output_token_count, 0)) AS total_tokens
                FROM system.serving.endpoint_usage eu
                JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id
                WHERE se.endpoint_name IN ('claims_rag_agent', 'mas-5c4a9766-endpoint',
                                            'databricks-claude-sonnet-4-5', 'databricks-bge-large-en',
                                            'databricks-meta-llama-3-3-70b-instruct', 'databricks-ai-analyze-sentiment')
                  AND eu.request_time >= current_timestamp() - INTERVAL {obs_interval}
                GROUP BY se.endpoint_name, se.entity_type
                ORDER BY total_requests DESC
            """)
            if not endpoint_usage.empty:
                total_tkns = endpoint_usage['total_tokens'].sum()
                total_reqs = endpoint_usage['total_requests'].sum()
                total_errs = endpoint_usage['errors'].sum()
                c1, c2, c3 = st.columns(3, gap="medium")
                c1.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Total Endpoint Requests</div>
                    <div style="color:#e2e8f0; font-size:1.8rem; font-weight:700;">{int(total_reqs):,}</div>
                </div>""", unsafe_allow_html=True)
                c2.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Total Tokens</div>
                    <div style="color:#818cf8; font-size:1.8rem; font-weight:700;">{int(total_tkns):,}</div>
                </div>""", unsafe_allow_html=True)
                c3.markdown(f"""<div class="glass-card" style="text-align:center; padding:16px;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Total Errors</div>
                    <div style="color:{'#f87171' if total_errs > 0 else '#34d399'}; font-size:1.8rem; font-weight:700;">{int(total_errs)}</div>
                </div>""", unsafe_allow_html=True)

                st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
                st.markdown("**Per-Endpoint Breakdown**")
                st.dataframe(
                    endpoint_usage[['endpoint_name', 'entity_type', 'total_requests', 'success_rate', 'total_input_tokens', 'total_output_tokens']].rename(columns={
                        'endpoint_name': 'Endpoint', 'entity_type': 'Type', 'total_requests': 'Requests',
                        'success_rate': 'Success %', 'total_input_tokens': 'Input Tokens', 'total_output_tokens': 'Output Tokens'
                    }),
                    use_container_width=True, hide_index=True
                )

                if len(endpoint_usage) > 1:
                    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
                    st.markdown("**Token Usage by Endpoint**")
                    chart_data = endpoint_usage.set_index('endpoint_name')[['total_input_tokens', 'total_output_tokens']]
                    chart_data.columns = ['Input Tokens', 'Output Tokens']
                    st.bar_chart(chart_data, color=["#818cf8", "#34d399"])
            else:
                st.info("No endpoint usage data in selected time range.")
        except Exception as e:
            st.warning(f"Endpoint usage metrics unavailable: {e}")

    # =====================================================
    # TAB 4: AI Query Performance (SQL History)
    # =====================================================
    with obs_tab4:
        try:
            ai_query_perf = execute_sql(f"""
                SELECT
                    CASE
                        WHEN statement_text LIKE '%mas-5c4a9766-endpoint%' THEN 'Supervisor Agent'
                        WHEN statement_text LIKE '%claims_rag_agent%' THEN 'Claims RAG Agent'
                        WHEN statement_text LIKE '%databricks-meta-llama%' THEN 'Llama (FinOps)'
                        WHEN statement_text LIKE '%analyze-sentiment%' THEN 'Sentiment Analysis'
                        WHEN statement_text LIKE '%ai_query%' THEN 'Other ai_query'
                        ELSE 'Other'
                    END AS agent_type,
                    COUNT(*) AS total_calls,
                    SUM(CASE WHEN execution_status = 'FINISHED' THEN 1 ELSE 0 END) AS successes,
                    SUM(CASE WHEN execution_status = 'FAILED' THEN 1 ELSE 0 END) AS failures,
                    ROUND(AVG(total_duration_ms) / 1000.0, 1) AS avg_duration_sec,
                    ROUND(MAX(total_duration_ms) / 1000.0, 1) AS max_duration_sec,
                    ROUND(PERCENTILE(total_duration_ms, 0.5) / 1000.0, 1) AS p50_duration_sec
                FROM system.query.history
                WHERE statement_text LIKE '%ai_query%'
                  AND start_time >= current_timestamp() - INTERVAL {obs_interval}
                GROUP BY 1
                ORDER BY total_calls DESC
            """)
            if not ai_query_perf.empty:
                st.dataframe(
                    ai_query_perf.rename(columns={
                        'agent_type': 'Agent / Endpoint', 'total_calls': 'Calls',
                        'successes': 'Success', 'failures': 'Failed',
                        'avg_duration_sec': 'Avg (s)', 'max_duration_sec': 'Max (s)',
                        'p50_duration_sec': 'P50 (s)',
                    }),
                    use_container_width=True, hide_index=True
                )

                ai_timeline = execute_sql(f"""
                    SELECT
                        DATE_TRUNC('hour', start_time) AS time_bucket,
                        CASE
                            WHEN statement_text LIKE '%mas-5c4a9766-endpoint%' THEN 'Supervisor'
                            WHEN statement_text LIKE '%claims_rag_agent%' THEN 'Claims RAG'
                            ELSE 'Other'
                        END AS agent,
                        COUNT(*) AS calls,
                        ROUND(AVG(total_duration_ms) / 1000.0, 1) AS avg_sec
                    FROM system.query.history
                    WHERE statement_text LIKE '%ai_query%'
                      AND start_time >= current_timestamp() - INTERVAL {obs_interval}
                    GROUP BY 1, 2
                    ORDER BY 1
                """)
                if not ai_timeline.empty and len(ai_timeline) > 1:
                    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
                    st.markdown("**AI Query Call Volume Over Time**")
                    import pandas as _pd
                    pivot = ai_timeline.pivot_table(index='time_bucket', columns='agent', values='calls', aggfunc='sum').fillna(0)
                    st.bar_chart(pivot)
            else:
                st.info("No ai_query calls found in selected time range.")
        except Exception as e:
            st.warning(f"AI Query metrics unavailable: {e}")

    # =====================================================
    # TAB 5: Errors & MLflow Scoring
    # =====================================================
    with obs_tab5:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U000026A0</span>
            <span class="section-header-text">Recent Errors &amp; Failures</span>
        </div>""", unsafe_allow_html=True)

        try:
            error_log = execute_sql(f"""
                (
                    SELECT
                        'Claims RAG Agent' AS source,
                        request_time AS event_time,
                        CAST(status_code AS STRING) AS status,
                        CAST(execution_duration_ms AS STRING) || 'ms' AS duration,
                        LEFT(request, 200) AS detail
                    FROM uae_insurance.uae_silver.claims_rag_agent_payload
                    WHERE status_code != 200
                      AND request_time >= current_timestamp() - INTERVAL {obs_interval}
                )
                UNION ALL
                (
                    SELECT
                        'ai_query (SQL)' AS source,
                        start_time AS event_time,
                        'FAILED' AS status,
                        CAST(total_duration_ms AS STRING) || 'ms' AS duration,
                        LEFT(error_message, 200) AS detail
                    FROM system.query.history
                    WHERE statement_text LIKE '%ai_query%'
                      AND execution_status = 'FAILED'
                      AND start_time >= current_timestamp() - INTERVAL {obs_interval}
                )
                ORDER BY event_time DESC
                LIMIT 20
            """)
            if not error_log.empty:
                st.dataframe(
                    error_log.rename(columns={
                        'source': 'Source', 'event_time': 'Time',
                        'status': 'Status', 'duration': 'Duration', 'detail': 'Detail'
                    }),
                    use_container_width=True, hide_index=True
                )
            else:
                st.markdown("""<div class="glass-card" style="text-align:center; padding:24px;">
                    <div style="font-size:2rem; margin-bottom:8px;">\U00002705</div>
                    <div style="color:#34d399; font-size:1rem;">No errors in selected time range</div>
                </div>""", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Error log unavailable: {e}")

        st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
        with st.expander("\U0001F9EA MLflow Evaluation Scorers (Setup Guide)", expanded=False):
            st.markdown("""
**Add continuous quality monitoring with MLflow built-in judges:**

| Scorer | What it checks | Needs ground truth? |
|--------|---------------|-------------------|
| **RelevanceToQuery** | Is the response relevant to the question? | No |
| **Safety** | Is content free from harmful material? | No |
| **RetrievalGroundedness** | Is the answer grounded in retrieved context? | No |
| **ToolCallEfficiency** | Are tool calls non-redundant? | No |
| **Correctness** | Does it match expected facts? | Yes |

**Quick setup** (run in a notebook):
```python
import mlflow
from mlflow.genai.scorers import RelevanceToQuery, Safety, RetrievalGroundedness

mlflow.set_experiment("/Users/cyrils@systechusa.com/mas-d55c51ee-dev-experiment")
traces = mlflow.search_traces(experiment_ids=["3798428402426688"])
mlflow.genai.evaluate(data=traces, scorers=[RelevanceToQuery(), Safety(), RetrievalGroundedness()])
```

Scorer results appear in the MLflow experiment UI under the **Evaluation** tab.
            """)


# ============================================
# FOOTER
# ============================================
st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="footer-bar">
    Fraud Investigation Command Center &nbsp;&bull;&nbsp; <span>Middleeast Insurance</span> &nbsp;&bull;&nbsp; Powered by <span>Databricks Data Intelligence Platform</span>
</div>
""", unsafe_allow_html=True)
