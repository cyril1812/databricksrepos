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
            statement="SELECT * FROM salama_insurance.salama_silver.fact_fraud_investigation LIMIT 50000",
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

1. salama_insurance.salama_silver.fact_fraud_investigation (fi)
   - INVESTIGATION_ID (string), CLAIM_KEY (decimal), FRAUD_SCORE (double): 0-100
   - INVESTIGATION_COST (double), FRAUD_AMOUNT_DETECTED (double), RECOVERY_AMOUNT (double)
   - INVESTIGATION_DAYS (decimal), FRAUD_DETECTION_RATE (decimal)
   - INVESTIGATOR_ID (string), INVESTIGATION_STATUS (string): INITIATED/IN_PROGRESS/COMPLETED/CLOSED
   - FINDINGS (string): FRAUD_CONFIRMED/FRAUD_SUSPECTED/INCONCLUSIVE/NO_FRAUD
   - FR_DATE (timestamp), MONTHYEAR (string), MONTHYEAR_SORT (decimal)

2. salama_insurance.salama_silver.fact_claim (fc)
   - CLAIM_ID (string), POLICY_ID (string), CUSTOMER_KEY (decimal)
   - CLAIM_KEY (decimal): JOIN to fi.CLAIM_KEY
   - CLAIMED_AMOUNT (double), APPROVED_AMOUNT (double), PAID_AMOUNT (double), RESERVE_AMOUNT (double)
   - DAYS_TO_REPORT (decimal), DAYS_TO_SETTLE (decimal)
   - CLAIM_RATIO (double), APPROVAL_RATIO (double)
   - BUSINESS_LINE (string), CLAIM_TYPE (string), CLAIM_STATUS (string)
   - ADJUSTER_ID (string), RISK_RATING (string), RISK_SCORE (decimal)
   - CLAIM_AGING_BUCKET (string), CL_DATE (timestamp)

3. salama_insurance.salama_silver.dim_customer (dc)
   - CUSTOMER_KEY (decimal): JOIN to fc.CUSTOMER_KEY
   - CUSTOMER_ID (string), CUSTOMER_TYPE (string), CUSTOMER_NAME (string)
   - NATIONALITY (string), EMIRATES (string), CITY (string)
   - RISK_RATING (string), CUSTOMER_SEGMENT (string), IS_ACTIVE (boolean)

4. salama_insurance.salama_silver.dim_policy (dp)
   - POLICY_KEY (decimal), POLICY_ID (string), POLICY_NUMBER (string)
   - PRODUCT_CODE (string), BUSINESS_LINE (string)
   - PREMIUM_AMOUNT (double), SUM_INSURED (double)
   - POLICY_STATUS (string), SALES_CHANNEL (string)

5. salama_insurance.salama_silver.fraud_ai_results (ai)
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
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("""<div class="section-header">
                <span class="section-header-icon">\U0001F4CA</span>
                <span class="section-header-text">By Status</span>
            </div>""", unsafe_allow_html=True)
            status_df = df.groupby('INVESTIGATION_STATUS').agg(Count=('INVESTIGATION_ID', 'count'), Avg_Score=('FRAUD_SCORE', 'mean'), Total_Cost=('INVESTIGATION_COST', 'sum')).reset_index()
            order = ['INITIATED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED']
            status_df['INVESTIGATION_STATUS'] = pd.Categorical(status_df['INVESTIGATION_STATUS'], categories=order, ordered=True)
            status_df = status_df.sort_values('INVESTIGATION_STATUS')
            chart = alt.Chart(status_df).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, opacity=0.9).encode(
                x=alt.X('INVESTIGATION_STATUS:N', sort=order, title='Status', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Count:Q', title='Investigations'),
                color=alt.Color('INVESTIGATION_STATUS:N', scale=alt.Scale(domain=order, range=['#6366f1', '#f59e0b', '#10b981', '#64748b']), legend=None),
                tooltip=[alt.Tooltip('INVESTIGATION_STATUS:N', title='Status'), alt.Tooltip('Count:Q', title='Cases'), alt.Tooltip('Avg_Score:Q', format='.1f', title='Avg Score'), alt.Tooltip('Total_Cost:Q', format=',.0f', title='Total Cost (AED)')]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)

        with c2:
            st.markdown("""<div class="section-header">
                <span class="section-header-icon">\U0001F3AF</span>
                <span class="section-header-text">By Findings</span>
            </div>""", unsafe_allow_html=True)
            findings_df = df.groupby('FINDINGS').agg(Count=('INVESTIGATION_ID', 'count'), Avg_Score=('FRAUD_SCORE', 'mean'), Total_Detected=('FRAUD_AMOUNT_DETECTED', 'sum')).reset_index()
            chart2 = alt.Chart(findings_df).mark_arc(innerRadius=70, outerRadius=140, padAngle=0.03, cornerRadius=4).encode(
                theta=alt.Theta('Count:Q'),
                color=alt.Color('FINDINGS:N', scale=alt.Scale(domain=['FRAUD_CONFIRMED', 'FRAUD_SUSPECTED', 'INCONCLUSIVE', 'NO_FRAUD'], range=['#f43f5e', '#f59e0b', '#00C2A8', '#6366f1'])),
                tooltip=[alt.Tooltip('FINDINGS:N', title='Finding'), alt.Tooltip('Count:Q', title='Cases'), alt.Tooltip('Avg_Score:Q', format='.1f', title='Avg Score'), alt.Tooltip('Total_Detected:Q', format=',.0f', title='Fraud Detected (AED)')]
            ).properties(height=360)
            st.altair_chart(chart2, use_container_width=True)

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
            <span class="section-header-text">Monthly Fraud Trends</span>
        </div>""", unsafe_allow_html=True)
        if 'MONTHYEAR' in df.columns:
            monthly = df.groupby('MONTHYEAR').agg(Investigations=('INVESTIGATION_ID', 'count'), Avg_Fraud_Score=('FRAUD_SCORE', 'mean'), Fraud_Detected=('FRAUD_AMOUNT_DETECTED', 'sum'), Recovery=('RECOVERY_AMOUNT', 'sum'), Cost=('INVESTIGATION_COST', 'sum'), Sort=('MONTHYEAR_SORT', 'first')).reset_index().sort_values('Sort')
            metric_choice = st.selectbox("Select Metric", ["Investigations", "Avg_Fraud_Score", "Fraud_Detected", "Recovery", "Cost"])
            base = alt.Chart(monthly).encode(x=alt.X('MONTHYEAR:N', sort=alt.EncodingSortField(field='Sort'), title='Month', axis=alt.Axis(labelAngle=-45)), tooltip=['MONTHYEAR', alt.Tooltip(f'{metric_choice}:Q', format=',.1f')])
            area = base.mark_area(line=True, opacity=0.15, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#6366f1', offset=0), alt.GradientStop(color='transparent', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(y=alt.Y(f'{metric_choice}:Q', title=metric_choice.replace('_', ' ')))
            line = base.mark_line(strokeWidth=2.5, color='#6366f1').encode(y=alt.Y(f'{metric_choice}:Q'))
            points = base.mark_circle(size=50, color='#818cf8', opacity=1).encode(y=alt.Y(f'{metric_choice}:Q'))
            trend_chart = (area + line + points).properties(height=420)
            st.altair_chart(trend_chart, use_container_width=True)

# --- PAGE: Investigator Performance ---
elif page == "\U0001F3C6  Investigator Performance":
    if not df.empty:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F3C6</span>
            <span class="section-header-text">Investigator Performance Scoreboard</span>
        </div>""", unsafe_allow_html=True)
        inv_perf = df.groupby('INVESTIGATOR_ID').agg(Cases=('INVESTIGATION_ID', 'count'), Avg_Score=('FRAUD_SCORE', 'mean'), Avg_Days=('INVESTIGATION_DAYS', 'mean'), Total_Recovered=('RECOVERY_AMOUNT', 'sum'), Total_Cost=('INVESTIGATION_COST', 'sum'), Fraud_Confirmed=('FINDINGS', lambda x: (x == 'FRAUD_CONFIRMED').sum())).reset_index()
        inv_perf['ROI'] = ((inv_perf['Total_Recovered'] - inv_perf['Total_Cost']) / inv_perf['Total_Cost'] * 100).round(1)
        enhanced_dataframe(inv_perf.sort_values('ROI', ascending=False).reset_index(drop=True), title='Investigator Performance', key_prefix='inv_perf', height=500)

# --- PAGE: ROI Analysis ---
elif page == "\U0001F4B0  ROI Analysis":
    if not df.empty:
        st.markdown("""<div class="section-header">
            <span class="section-header-icon">\U0001F4B0</span>
            <span class="section-header-text">Return on Investigation (ROI) Analysis</span>
        </div>""", unsafe_allow_html=True)
        total_cost = df['INVESTIGATION_COST'].sum()
        total_recovered = df['RECOVERY_AMOUNT'].sum()
        net_benefit = total_recovered - total_cost
        overall_roi = (net_benefit / total_cost * 100) if total_cost > 0 else 0
        c1, c2, c3 = st.columns(3, gap="large")
        c1.metric("Total Investigation Cost", f"AED {total_cost:,.0f}")
        c2.metric("Total Recovered", f"AED {total_recovered:,.0f}")
        c3.metric("Net Benefit", f"AED {net_benefit:,.0f}", delta=f"{overall_roi:.1f}% ROI")

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
            <h4 style="margin-top:0">\U0001F4A1 Genie Space: Insurance Operations</h4>

The **Insurance Operations and Analytics** Genie Space is live and connected to **19 tables** including fraud investigations, claims, customers, policies, financials, and AI results.

Business users can ask natural language questions directly in the Genie room.
            </div>""", unsafe_allow_html=True)
            genie_url = f"https://{DATABRICKS_HOST}/genie/rooms/01f13ca173fa16e99feabaf195b2830a" if DATABRICKS_HOST else "#"
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

        GENIE_SPACE_ID = "01f13ca173fa16e99feabaf195b2830a"

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
                <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 6px;">Connected to 19 tables in salama_insurance.salama_silver</div>
            </div>""", unsafe_allow_html=True)

    with ai_tab2:
        st.markdown("**Databricks AI Query** - Generate executive summaries")
        summary_scope = st.selectbox("Summary Scope", ["Overall Portfolio"])
        if st.button("Generate AI Summary", key="summary_btn"):
            if not df.empty:
                with st.spinner("Generating summary via Databricks Foundation Models..."):
                    ctx = f"Investigations: {len(df)}, Avg Score: {df['FRAUD_SCORE'].mean():.1f}, Det: AED {df['FRAUD_AMOUNT_DETECTED'].sum():,.0f}, Rec: AED {df['RECOVERY_AMOUNT'].sum():,.0f}"
                    prompt_text = escape_sql(f"You are a senior fraud analyst. Write an executive markdown summary based on this: {ctx}. Keep it concise.")
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
                    FROM salama_insurance.salama_silver.fact_fraud_investigation fi
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
                    FROM salama_insurance.salama_silver.fact_fraud_investigation
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
                    FROM salama_insurance.salama_silver.fact_fraud_investigation fi
                    ORDER BY fi.FRAUD_SCORE DESC LIMIT {risk_limit}
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
                    FROM salama_insurance.salama_silver.fact_fraud_investigation
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
                FROM salama_insurance.salama_silver.fact_fraud_investigation
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

    SUPERVISOR_ENDPOINT = "mas-d55c51ee-endpoint"

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
| **Insurance Operations** | Genie Space | Structured queries — fraud scores, claim amounts, investigator stats, trends across 19 tables |
| **Claims Document Search** | UC Function | Unstructured search — claim forms, settlement letters, investigation reports, denial letters (25 PDFs) |

**Routing logic:**
- Questions about **numbers, aggregations, comparisons** → Genie Space
- Questions about **document contents, reasons, findings** → Claims Document Search
- Questions needing **both** → Calls both and synthesizes the results

**Endpoint:** `mas-d55c51ee-endpoint` | **Built with:** Databricks Agent Bricks
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
                          'mas-d55c51ee-endpoint'
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
                agent_cost = cost_by_endpoint[cost_by_endpoint['endpoint_name'].isin(['claims_rag_agent', 'mas-d55c51ee-endpoint'])]['total_cost_usd'].sum()
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
                              'mas-d55c51ee-endpoint'
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
                FROM salama_insurance.salama_silver.claims_rag_agent_payload
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
                    FROM salama_insurance.salama_silver.claims_rag_agent_payload
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
                WHERE se.endpoint_name IN ('claims_rag_agent', 'mas-d55c51ee-endpoint',
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
                        WHEN statement_text LIKE '%mas-d55c51ee-endpoint%' THEN 'Supervisor Agent'
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
                            WHEN statement_text LIKE '%mas-d55c51ee-endpoint%' THEN 'Supervisor'
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
                    FROM salama_insurance.salama_silver.claims_rag_agent_payload
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
