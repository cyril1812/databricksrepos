# =============================================================================
# UC Readiness Accelerator — Databricks App
# =============================================================================
# Tabs: Executive Summary, Detailed Assessment, Recommendations,
#       FinOps Insights, Performance, Genie Readiness, Assessment Rules, Actions
# =============================================================================

import io
import os
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from databricks import sql
from databricks.sdk.core import Config
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ---------------------------------------------------------------------------
# Page config & styles
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GovernIQ",
    page_icon="\U0001f3db\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
    .stApp { background-color: #f7f8fa; }
    h1, h2, h3, h4 { color: #1e293b !important; }
    .metric-card {
        background: white; border-radius: 12px; padding: 20px;
        text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin: 4px 0;
    }
    .metric-card h2 { margin: 0; font-size: 32px; font-weight: 700; }
    .metric-card p  {
        color: #64748b; margin: 6px 0 0 0; font-size: 13px;
        font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;
    }
    .rag-green {
        background: #f0fdf4; border-left: 4px solid #22c55e;
        padding: 14px 18px; border-radius: 8px; margin: 8px 0; color: #166534; font-size: 15px;
    }
    .rag-amber {
        background: #fffbeb; border-left: 4px solid #f59e0b;
        padding: 14px 18px; border-radius: 8px; margin: 8px 0; color: #92400e; font-size: 15px;
    }
    .rag-red {
        background: #fef2f2; border-left: 4px solid #ef4444;
        padding: 14px 18px; border-radius: 8px; margin: 8px 0; color: #991b1b; font-size: 15px;
    }
    .recommend-box {
        background: #f0fdf4; border-left: 4px solid #22c55e;
        padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #166534; font-weight: 500;
    }
    .tip-box {
        background: #eff6ff; border-left: 4px solid #3b82f6;
        padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #1e40af; font-weight: 500;
    }
    .warn-box {
        background: #fffbeb; border-left: 4px solid #f59e0b;
        padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #92400e; font-weight: 500;
    }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e2e8f0;
        border-radius: 10px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .section-header {
        color: #1e293b; font-size: 20px; font-weight: 600;
        margin: 20px 0 10px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0;
    }
    .rule-card {
        background: white; border-radius: 10px; padding: 16px 20px;
        margin: 8px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-left: 4px solid #3b82f6;
    }
    .rule-card .rule-id { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; }
    .rule-card .rule-name { font-size: 16px; font-weight: 600; color: #1e293b; margin: 4px 0; }
    .rule-card .rule-desc { font-size: 13px; color: #475569; margin: 4px 0 8px; }
    .rule-card .rule-meta span { display: inline-block; margin-right: 14px; font-size: 12px; }
    .sev-high   { color: #dc2626; font-weight: 600; }
    .sev-medium { color: #d97706; font-weight: 600; }
    .sev-low    { color: #2563eb; font-weight: 600; }
    .method-card {
        background: white; border-radius: 10px; padding: 20px 24px;
        margin: 10px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .method-card h4 { margin: 0 0 8px !important; font-size: 16px; }
    .method-card p  { color: #475569; font-size: 14px; margin: 4px 0; }
    .filter-pill {
        display: inline-block; background: #dbeafe; color: #1e40af;
        padding: 4px 12px; border-radius: 16px; font-size: 13px;
        font-weight: 600; margin-right: 8px;
    }
    .action-card {
        background: white; border-radius: 10px; padding: 20px 24px;
        margin: 10px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 4px solid #8b5cf6;
    }
    .action-card h4 { margin: 0 0 8px !important; font-size: 16px; color: #1e293b; }
    .action-card p  { color: #475569; font-size: 13px; margin: 4px 0 12px; }
    .success-box {
        background: #f0fdf4; border-left: 4px solid #22c55e;
        padding: 12px 16px; border-radius: 8px; margin: 8px 0;
        color: #166534; font-weight: 500;
    }
    .error-box {
        background: #fef2f2; border-left: 4px solid #ef4444;
        padding: 12px 16px; border-radius: 8px; margin: 8px 0;
        color: #991b1b; font-weight: 500;
    }
    .bulk-section {
        background: white; border-radius: 12px; padding: 24px;
        margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-top: 3px solid #8b5cf6;
    }
    .bulk-section h4 { margin: 0 0 6px !important; font-size: 17px; color: #1e293b; }
    .bulk-section p  { color: #64748b; font-size: 13px; margin: 0 0 14px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Plotly defaults & palette
# ---------------------------------------------------------------------------
CHART_LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#f8fafc", font_color="#334155")
CLR_BLUE   = "#3b82f6"
CLR_RED    = "#ef4444"
CLR_AMBER  = "#f59e0b"
CLR_GREEN  = "#22c55e"
CLR_PURPLE = "#8b5cf6"

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
FULL_SCHEMA = "governiq.uc_assessment"
cfg = Config()


def get_connection(warehouse_id: str):
    host = cfg.host.replace("https://", "").replace("http://", "")
    return sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
        _use_arrow_native_complex_types=False,
    )


@st.cache_data(ttl=300, show_spinner=False)
def run_query(_conn, query: str) -> pd.DataFrame:
    with _conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall_arrow().to_pandas()


def run_action(_conn, query: str) -> str:
    """Execute a write/DDL statement (non-cached). Returns success/error message."""
    try:
        with _conn.cursor() as cur:
            cur.execute(query)
        return "OK"
    except Exception as e:
        return str(e)


@st.cache_data(ttl=300, show_spinner=False)
def get_table_columns(_conn, catalog: str, schema: str, table: str) -> list[str]:
    df_cols = run_query(
        _conn,
        f"SELECT lower(column_name) AS column_name "
        f"FROM {catalog}.information_schema.columns "
        f"WHERE lower(table_schema) = lower('{schema}') "
        f"AND lower(table_name) = lower('{table}')"
    )
    if df_cols.empty:
        return []
    return sorted({str(col).lower() for col in df_cols["column_name"].dropna().tolist()})


def get_assessment_rule_columns(_conn, full_schema: str) -> set[str]:
    catalog, schema = full_schema.split(".", 1)
    return set(get_table_columns(_conn, catalog, schema, "assessment_rules"))


def get_assessment_rules(_conn, full_schema: str) -> pd.DataFrame:
    available_cols = get_assessment_rule_columns(_conn, full_schema)
    select_exprs = [
        "rule_id",
        "category",
        "rule_name",
        "description",
        "weight",
        "severity",
        "enabled" if "enabled" in available_cols else "TRUE AS enabled",
        "formula" if "formula" in available_cols else "CAST(NULL AS STRING) AS formula",
        "threshold" if "threshold" in available_cols else "CAST(NULL AS STRING) AS threshold",
    ]
    return run_query(
        _conn,
        f"SELECT {', '.join(select_exprs)} "
        f"FROM {full_schema}.assessment_rules ORDER BY category, rule_id"
    )


def metric_card(label: str, value, color=CLR_RED):
    st.markdown(
        f'<div class="metric-card" style="border-top:3px solid {color}">'
        f'<h2 style="color:{color}">{value}</h2>'
        f'<p>{label}</p></div>', unsafe_allow_html=True)


def rag_badge(status):
    styles = {
        "RED":   "background:#fef2f2;color:#dc2626;border:1px solid #fecaca",
        "AMBER": "background:#fffbeb;color:#d97706;border:1px solid #fed7aa",
        "GREEN": "background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0",
    }
    return (f'<span style="{styles.get(status,"")};padding:4px 14px;'
            f'border-radius:20px;font-size:13px;font-weight:600">{status}</span>')


def generate_excel_scorecard(_conn, filter_where, filter_and, full_schema):
    """Generate a multi-sheet Excel scorecard matching enterprise format."""
    # Fetch last assessment refresh date
    _df_date = run_query(_conn, f"SELECT assessment_date FROM {full_schema}.gold_executive_summary LIMIT 1")
    if not _df_date.empty and pd.notna(_df_date.iloc[0]['assessment_date']):
        _assess_date = pd.to_datetime(_df_date.iloc[0]['assessment_date']).strftime("%B %d, %Y at %H:%M")
    else:
        _assess_date = datetime.now().strftime("%B %d, %Y at %H:%M")

    wb = Workbook()

    # Styles
    hdr_font = Font(bold=True, color="FFFFFF", size=12)
    hdr_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    sub_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
    title_font = Font(bold=True, color="1F4E79", size=18)
    sec_font = Font(bold=True, color="FFFFFF", size=11)
    sec_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    amber_fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
    red_fill = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")
    green_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'))
    wrap_align = Alignment(wrap_text=True, vertical='center')

    dimension_map = {
        "Metadata Readiness": "1. Foundation & Architecture",
        "Governance": "2. Identity & Access Management",
        "Data Quality": "3. Data Security & Privacy",
        "Performance": "4. Data Lineage & Observability",
        "Genie Readiness": "5. Data Discovery & Cataloging",
        "UC Functions": "6. UC Functions Governance",
        "Functions": "6. UC Functions Governance",
        "ML Models": "7. ML Model Governance",
        "Volumes": "8. Volume Management",
        "Clusters": "9. Cluster Governance",
        "SQL Warehouses": "10. SQL Warehouse Governance",
    }

    # ===== SHEET 1: Instructions =====
    ws = wb.active
    ws.title = "Instructions"
    ws.sheet_properties.tabColor = "1F4E79"
    ws.merge_cells('A1:F2')
    c = ws['A1']
    c.value = "Databricks Unity Catalog\nAssessment Scorecard"
    c.font = title_font
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 30

    ws['A4'] = (f"Enterprise Data Governance Readiness Framework | Version 1.0 | "
                f"Last Assessment: {_assess_date}")
    ws['A4'].font = Font(italic=True, color="666666")
    ws.merge_cells('A4:F4')

    ws.merge_cells('A6:F6')
    ws['A6'] = "HOW TO USE THIS SCORECARD"
    ws['A6'].font = hdr_font
    ws['A6'].fill = hdr_fill
    ws['A6'].alignment = Alignment(horizontal='center')

    steps = [
        ("1. Open the Scorecard tab", "Navigate to the 'Scorecard' sheet — this is your main working area."),
        ("2. Rate each control", "For each assessment item, enter a score 1-4 in the 'Score' column using the rating guide below."),
        ("3. Add observations", "Use the 'Observations / Evidence' column to document findings, gaps, or evidence."),
        ("4. Review the Dashboard", "The 'Dashboard' sheet auto-calculates dimension scores and overall maturity."),
        ("5. Prioritize remediation", "Use the 'Recommendations' tab to plan and track remediation actions."),
    ]
    for i, (step, desc) in enumerate(steps, start=7):
        ws[f'A{i}'] = step
        ws[f'A{i}'].font = Font(bold=True)
        ws[f'C{i}'] = desc

    ws.merge_cells('A14:F14')
    ws['A14'] = "RATING GUIDE"
    ws['A14'].font = hdr_font
    ws['A14'].fill = hdr_fill
    ws['A14'].alignment = Alignment(horizontal='center')

    ratings = [
        ("1 \u2013 Initial", "Not implemented; ad hoc or absent", red_fill),
        ("2 \u2013 Developing", "Partially implemented; inconsistent", amber_fill),
        ("3 \u2013 Defined", "Fully implemented; documented and consistent", green_fill),
        ("4 \u2013 Optimized", "Mature, automated, continuously improved", green_fill),
    ]
    for i, (level, desc, fill) in enumerate(ratings, start=15):
        ws[f'A{i}'] = level
        ws[f'A{i}'].font = Font(bold=True)
        ws[f'A{i}'].fill = fill
        ws[f'C{i}'] = desc

    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['C'].width = 65

    # ===== SHEET 2: Scorecard =====
    ws2 = wb.create_sheet("Scorecard")
    ws2.sheet_properties.tabColor = "2E75B6"
    ws2.merge_cells('A1:G2')
    t = ws2['A1']
    t.value = "Databricks Unity Catalog \u2014 Assessment Scorecard"
    t.font = Font(bold=True, color="FFFFFF", size=16)
    t.fill = hdr_fill
    t.alignment = Alignment(horizontal='center', vertical='center')

    ws2['A3'] = f"Rate each item 1 (Initial) \u2192 4 (Optimized)  |  Enter score in column E  |  Assessed: {_assess_date}"
    ws2['A3'].font = Font(italic=True, color="2E75B6")
    ws2.merge_cells('A3:G3')

    for col, h in enumerate(["#", "Dimension", "Assessment Criteria", "Sub-Category",
                              "Score\n(1\u20134)", "Max\nScore", "Observations / Evidence"], start=1):
        c = ws2.cell(row=4, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.alignment = Alignment(horizontal='center', wrap_text=True, vertical='center')
        c.border = thin_border
    ws2.row_dimensions[4].height = 30

    df_rules = run_query(_conn,
        f"SELECT rule_id, category, rule_name, description, weight, severity "
        f"FROM {full_schema}.assessment_rules "
        f"ORDER BY CASE category "
        f"WHEN 'Metadata Readiness' THEN 1 WHEN 'Governance' THEN 2 "
        f"WHEN 'Data Quality' THEN 3 WHEN 'Performance' THEN 4 "
        f"WHEN 'Genie Readiness' THEN 5 WHEN 'UC Functions' THEN 6 WHEN 'Functions' THEN 6 "
        f"WHEN 'ML Models' THEN 7 WHEN 'Volumes' THEN 8 "
        f"WHEN 'Clusters' THEN 9 WHEN 'SQL Warehouses' THEN 10 "
        f"ELSE 99 END, rule_id")

    row = 5
    current_dim = None
    rule_num = 0
    for _, rule in df_rules.iterrows():
        dim = dimension_map.get(rule['category'], rule['category'])
        if dim != current_dim:
            ws2.merge_cells(f'A{row}:G{row}')
            ws2[f'A{row}'] = dim
            ws2[f'A{row}'].font = sec_font
            ws2[f'A{row}'].fill = sec_fill
            current_dim = dim
            row += 1
            rule_num = 0

        rule_num += 1
        prefix = rule['category'][:2].upper()
        rid = f"{prefix}-{rule_num:02d}"
        ws2.cell(row=row, column=1, value=rid).border = thin_border
        ws2.cell(row=row, column=2, value=dim).border = thin_border
        c3 = ws2.cell(row=row, column=3, value=rule['rule_name'])
        c3.border = thin_border
        c3.alignment = wrap_align
        ws2.cell(row=row, column=4, value=rule['category']).border = thin_border

        sev_score = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(rule['severity'], 2)
        sc = ws2.cell(row=row, column=5, value=sev_score)
        sc.border = thin_border
        sc.alignment = Alignment(horizontal='center')
        sc.fill = red_fill if sev_score == 1 else amber_fill if sev_score == 2 else green_fill

        ws2.cell(row=row, column=6, value=4).border = thin_border
        ws2.cell(row=row, column=6).alignment = Alignment(horizontal='center')
        ws2.cell(row=row, column=7, value="").border = thin_border
        row += 1

    ws2.column_dimensions['A'].width = 8
    ws2.column_dimensions['B'].width = 28
    ws2.column_dimensions['C'].width = 52
    ws2.column_dimensions['D'].width = 20
    ws2.column_dimensions['E'].width = 10
    ws2.column_dimensions['F'].width = 8
    ws2.column_dimensions['G'].width = 38

    # ===== SHEET 3: Dashboard =====
    ws3 = wb.create_sheet("Dashboard")
    ws3.sheet_properties.tabColor = "00B050"
    ws3.merge_cells('A1:F2')
    d = ws3['A1']
    d.value = "Unity Catalog Assessment \u2014 Executive Dashboard"
    d.font = Font(bold=True, color="FFFFFF", size=16)
    d.fill = hdr_fill
    d.alignment = Alignment(horizontal='center', vertical='center')

    ws3['A4'] = "Scores auto-update from the Scorecard tab"
    ws3['A4'].font = Font(italic=True, color="666666")
    ws3.merge_cells('A4:F4')

    ws3.merge_cells('A6:F6')
    ws3['A6'] = "OVERALL MATURITY SCORE"
    ws3['A6'].font = hdr_font
    ws3['A6'].fill = sub_fill
    ws3['A6'].alignment = Alignment(horizontal='center')

    df_exec = run_query(_conn, f"SELECT * FROM {full_schema}.gold_executive_summary")
    overall = float(df_exec.iloc[0].get('overall_readiness_score') or 0) if not df_exec.empty else 0

    ws3.merge_cells('A7:F7')
    ws3['A7'] = f"{overall:.1f}%"
    ws3['A7'].font = Font(bold=True, size=28, color="1F4E79")
    ws3['A7'].alignment = Alignment(horizontal='center')

    for col, h in enumerate(["Dimension", "Score (Avg)", "Max", "Maturity %",
                              "Maturity Level", "Status"], start=1):
        c = ws3.cell(row=9, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin_border

    df_cat = run_query(_conn,
        f"SELECT * FROM {full_schema}.gold_category_scores WHERE catalog_name = 'ALL'")

    dims = [
        ("1. Foundation & Architecture", "Metadata Readiness"),
        ("2. Identity & Access Management", "Governance"),
        ("3. Data Security & Privacy", "Data Quality"),
        ("4. Data Lineage & Observability", "Performance"),
        ("5. Data Discovery & Cataloging", "Genie Readiness"),
        ("6. UC Functions Governance", "UC Functions"),
        ("7. ML Model Governance", "ML Models"),
        ("8. Volume Management", "Volumes"),
        ("9. Cluster Governance", "Clusters"),
        ("10. SQL Warehouse Governance", "SQL Warehouses"),
    ]
    r = 10
    for dim_name, cat_key in dims:
        cat_row = df_cat[df_cat['category'] == cat_key]
        pct = float(cat_row['pct'].iloc[0] if pd.notna(cat_row['pct'].iloc[0]) else 0) if not cat_row.empty else 0
        score_val = pct / 25.0
        level = ("Initial" if pct < 25 else "Developing" if pct < 50
                 else "Defined" if pct < 75 else "Optimized")

        ws3.cell(row=r, column=1, value=dim_name).border = thin_border
        ws3.cell(row=r, column=1).font = Font(bold=True)
        ws3.cell(row=r, column=2, value=round(score_val, 1)).border = thin_border
        ws3.cell(row=r, column=3, value=4).border = thin_border
        pct_cell = ws3.cell(row=r, column=4, value=f"{pct:.0f}%")
        pct_cell.border = thin_border
        lvl_cell = ws3.cell(row=r, column=5, value=level)
        lvl_cell.border = thin_border
        lvl_cell.fill = (red_fill if pct < 25 else amber_fill if pct < 50
                         else green_fill)
        ws3.cell(row=r, column=6, value="\u2611").border = thin_border
        r += 1

    # Priority areas
    r += 1
    ws3.merge_cells(f'A{r}:F{r}')
    ws3[f'A{r}'] = "PRIORITY ASSESSMENT AREAS (Dimensions scoring < 2.5)"
    ws3[f'A{r}'].font = Font(bold=True, color="FFFFFF", size=11)
    ws3[f'A{r}'].fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    ws3[f'A{r}'].alignment = Alignment(horizontal='center')

    r += 1
    for col, h in enumerate(["Dimension", "Score", "Gap to Target (3.5)",
                              "Recommended Priority"], start=1):
        c = ws3.cell(row=r, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin_border

    r += 1
    for dim_name, cat_key in dims:
        cat_row = df_cat[df_cat['category'] == cat_key]
        pct = float(cat_row['pct'].iloc[0] if pd.notna(cat_row['pct'].iloc[0]) else 0) if not cat_row.empty else 0
        score_val = pct / 25.0
        if score_val < 2.5:
            ws3.cell(row=r, column=1, value=dim_name).border = thin_border
            ws3.cell(row=r, column=2, value=round(score_val, 1)).border = thin_border
            ws3.cell(row=r, column=3, value=round(3.5 - score_val, 1)).border = thin_border
            ws3.cell(row=r, column=4, value="High").border = thin_border
            ws3.cell(row=r, column=4).fill = red_fill
            r += 1

    ws3.column_dimensions['A'].width = 32
    ws3.column_dimensions['B'].width = 12
    ws3.column_dimensions['C'].width = 10
    ws3.column_dimensions['D'].width = 14
    ws3.column_dimensions['E'].width = 16
    ws3.column_dimensions['F'].width = 10

    # ===== SHEET 4: Recommendations =====
    ws4 = wb.create_sheet("Recommendations")
    ws4.sheet_properties.tabColor = "FF0000"
    ws4.merge_cells('A1:I2')
    h4 = ws4['A1']
    h4.value = "Unity Catalog \u2014 Remediation & Action Plan"
    h4.font = Font(bold=True, color="FFFFFF", size=16)
    h4.fill = hdr_fill
    h4.alignment = Alignment(horizontal='center', vertical='center')

    for col, h in enumerate(["#", "Dimension", "Remediation Action", "Expected Outcome",
                              "Priority", "Effort", "Target Date", "Owner", "Status"], start=1):
        c = ws4.cell(row=3, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin_border

    df_recs = run_query(_conn,
        f"SELECT category, recommendation, target_value, severity, "
        f"COUNT(*) AS affected_tables "
        f"FROM {full_schema}.gold_recommendations {filter_where} "
        f"GROUP BY category, recommendation, target_value, severity "
        f"ORDER BY CASE category "
        f"WHEN 'Metadata Readiness' THEN 1 WHEN 'Governance' THEN 2 "
        f"WHEN 'Data Quality' THEN 3 WHEN 'Performance' THEN 4 "
        f"WHEN 'Genie Readiness' THEN 5 WHEN 'UC Functions' THEN 6 WHEN 'Functions' THEN 6 "
        f"WHEN 'ML Models' THEN 7 WHEN 'Volumes' THEN 8 "
        f"WHEN 'Clusters' THEN 9 WHEN 'SQL Warehouses' THEN 10 "
        f"ELSE 99 END, "
        f"CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END "
        f"LIMIT 50")

    priority_map = {"HIGH": "Critical", "MEDIUM": "High", "LOW": "Medium"}
    effort_map = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}

    r = 4
    for i, (_, rec) in enumerate(df_recs.iterrows(), start=1):
        dim = dimension_map.get(rec['category'], rec['category'])
        pri = priority_map.get(rec['severity'], "Medium")
        eff = effort_map.get(rec['severity'], "Medium")

        ws4.cell(row=r, column=1, value=i).border = thin_border
        ws4.cell(row=r, column=2, value=dim).border = thin_border
        action_text = f"{rec['recommendation']} ({int(rec['affected_tables'])} tables)"
        c3 = ws4.cell(row=r, column=3, value=action_text)
        c3.border = thin_border
        c3.alignment = wrap_align
        ws4.cell(row=r, column=4, value=rec['target_value'] or "").border = thin_border

        pc = ws4.cell(row=r, column=5, value=pri)
        pc.border = thin_border
        pc.font = Font(bold=True)
        pc.fill = red_fill if pri == "Critical" else amber_fill if pri == "High" else green_fill

        ec = ws4.cell(row=r, column=6, value=eff)
        ec.border = thin_border
        ec.fill = red_fill if eff == "High" else amber_fill if eff == "Medium" else green_fill

        ws4.cell(row=r, column=7, value="").border = thin_border
        ws4.cell(row=r, column=8, value="").border = thin_border
        sc = ws4.cell(row=r, column=9, value="To Do")
        sc.border = thin_border
        sc.alignment = Alignment(horizontal='center')
        r += 1

    ws4.column_dimensions['A'].width = 5
    ws4.column_dimensions['B'].width = 22
    ws4.column_dimensions['C'].width = 42
    ws4.column_dimensions['D'].width = 32
    ws4.column_dimensions['E'].width = 12
    ws4.column_dimensions['F'].width = 10
    ws4.column_dimensions['G'].width = 14
    ws4.column_dimensions['H'].width = 16
    ws4.column_dimensions['I'].width = 10


    # ===== SHEET 5: Asset Details =====
    ws5 = wb.create_sheet("Asset Details")
    ws5.sheet_properties.tabColor = "8B5CF6"
    ws5.merge_cells('A1:K2')
    h5 = ws5['A1']
    h5.value = "Unity Catalog \u2014 Asset Rule Details"
    h5.font = Font(bold=True, color="FFFFFF", size=16)
    h5.fill = hdr_fill
    h5.alignment = Alignment(horizontal='center', vertical='center')

    ws5['A3'] = "Per-asset breakdown of every assessed rule with current state, target, and improvement actions"
    ws5['A3'].font = Font(italic=True, color="2E75B6")
    ws5.merge_cells('A3:K3')

    for col, h in enumerate(["#", "Catalog", "Schema", "Table", "Overall\nScore",
                              "RAG\nStatus", "Rule ID", "Category", "Severity",
                              "Current Value", "What Needs Improvement"], start=1):
        c = ws5.cell(row=4, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.alignment = Alignment(horizontal='center', wrap_text=True, vertical='center')
        c.border = thin_border
    ws5.row_dimensions[4].height = 32

    df_details = run_query(_conn,
        f"SELECT r.table_catalog, r.table_schema, r.table_name, "
        f"r.rule_id, r.category, r.severity, r.recommendation, "
        f"r.current_value, r.target_value, "
        f"s.overall_score, s.rag_status "
        f"FROM {full_schema}.gold_recommendations r "
        f"LEFT JOIN {full_schema}.gold_table_scores s "
        f"ON r.table_catalog = s.table_catalog "
        f"AND r.table_schema = s.table_schema "
        f"AND r.table_name = s.table_name "
        f"{filter_where} "
        f"ORDER BY s.overall_score ASC, r.table_catalog, r.table_schema, "
        f"r.table_name, CASE r.severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END")

    r5 = 5
    current_table = None
    for idx, (_, det) in enumerate(df_details.iterrows(), start=1):
        fqn = f"{det['table_catalog']}.{det['table_schema']}.{det['table_name']}"
        score_val = float(det['overall_score']) if pd.notna(det.get('overall_score')) else 0
        rag_val = det.get('rag_status', '') or ''

        # Track table changes (no blank rows between assets)
        current_table = fqn

        ws5.cell(row=r5, column=1, value=idx).border = thin_border
        ws5.cell(row=r5, column=2, value=det['table_catalog']).border = thin_border
        ws5.cell(row=r5, column=3, value=det['table_schema']).border = thin_border
        c_name = ws5.cell(row=r5, column=4, value=det['table_name'])
        c_name.border = thin_border
        c_name.font = Font(bold=True)

        sc = ws5.cell(row=r5, column=5, value=round(score_val, 1))
        sc.border = thin_border
        sc.alignment = Alignment(horizontal='center')
        sc.fill = red_fill if score_val < 40 else amber_fill if score_val < 70 else green_fill

        rc = ws5.cell(row=r5, column=6, value=rag_val)
        rc.border = thin_border
        rc.alignment = Alignment(horizontal='center')
        rc.font = Font(bold=True)
        rc.fill = red_fill if rag_val == 'RED' else amber_fill if rag_val == 'AMBER' else green_fill if rag_val == 'GREEN' else PatternFill()

        ws5.cell(row=r5, column=7, value=det['rule_id']).border = thin_border

        ws5.cell(row=r5, column=8, value=det['category']).border = thin_border

        sev_c = ws5.cell(row=r5, column=9, value=det['severity'])
        sev_c.border = thin_border
        sev_c.font = Font(bold=True)
        sev_c.fill = red_fill if det['severity'] == 'HIGH' else amber_fill if det['severity'] == 'MEDIUM' else green_fill

        cv = ws5.cell(row=r5, column=10, value=det.get('current_value', '') or '')
        cv.border = thin_border
        cv.alignment = wrap_align

        improvement = det.get('recommendation', '') or ''
        target = det.get('target_value', '') or ''
        if target:
            improvement = f"{improvement} (Target: {target})"
        imp_c = ws5.cell(row=r5, column=11, value=improvement)
        imp_c.border = thin_border
        imp_c.alignment = wrap_align

        r5 += 1

    ws5.column_dimensions['A'].width = 5
    ws5.column_dimensions['B'].width = 16
    ws5.column_dimensions['C'].width = 16
    ws5.column_dimensions['D'].width = 28
    ws5.column_dimensions['E'].width = 10
    ws5.column_dimensions['F'].width = 8
    ws5.column_dimensions['G'].width = 14
    ws5.column_dimensions['H'].width = 18
    ws5.column_dimensions['I'].width = 10
    ws5.column_dimensions['J'].width = 30
    ws5.column_dimensions['K'].width = 50


    # ===== SHEET 6: UC Functions, ML Models & Volumes =====
    ws6 = wb.create_sheet("Functions, Models & Volumes")
    ws6.sheet_properties.tabColor = "8B5CF6"
    ws6.merge_cells('A1:G2')
    h6 = ws6['A1']
    h6.value = "Unity Catalog \u2014 UC Functions, ML Models & Volumes Inventory"
    h6.font = Font(bold=True, color="FFFFFF", size=16)
    h6.fill = hdr_fill
    h6.alignment = Alignment(horizontal='center', vertical='center')

    # Functions section
    ws6.merge_cells('A4:G4')
    ws6['A4'] = "UC FUNCTIONS"
    ws6['A4'].font = sec_font
    ws6['A4'].fill = sec_fill
    ws6['A4'].alignment = Alignment(horizontal='center')

    for col, h in enumerate(["#", "Catalog", "Schema", "Function Name",
                              "Type", "Return Type", "Documented"], start=1):
        c = ws6.cell(row=5, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin_border

    df_fn_xl = run_query(_conn,
        f"SELECT routine_catalog, routine_schema, routine_name, routine_type, "
        f"data_type AS return_type, "
        f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 'Yes' ELSE 'No' END AS documented "
        f"FROM system.information_schema.routines "
        f"ORDER BY routine_catalog, routine_schema, routine_name")

    r6 = 6
    if not df_fn_xl.empty:
        for i, (_, fn) in enumerate(df_fn_xl.iterrows(), start=1):
            ws6.cell(row=r6, column=1, value=i).border = thin_border
            ws6.cell(row=r6, column=2, value=fn['routine_catalog']).border = thin_border
            ws6.cell(row=r6, column=3, value=fn['routine_schema']).border = thin_border
            ws6.cell(row=r6, column=4, value=fn['routine_name']).border = thin_border
            ws6.cell(row=r6, column=5, value=fn.get('routine_type', '')).border = thin_border
            ws6.cell(row=r6, column=6, value=fn.get('return_type', '')).border = thin_border
            dc = ws6.cell(row=r6, column=7, value=fn['documented'])
            dc.border = thin_border
            dc.fill = green_fill if fn['documented'] == 'Yes' else red_fill
            r6 += 1
    else:
        ws6.cell(row=r6, column=1, value="No UC Functions found")
        r6 += 1

    # ML Models section
    r6 += 1
    ws6.merge_cells(f'A{r6}:G{r6}')
    ws6[f'A{r6}'] = "ML MODELS"
    ws6[f'A{r6}'].font = sec_font
    ws6[f'A{r6}'].fill = sec_fill
    ws6[f'A{r6}'].alignment = Alignment(horizontal='center')
    r6 += 1

    for col, h in enumerate(["#", "Catalog", "Schema", "Model Name",
                              "Description", "Registered At", "Documented"], start=1):
        c = ws6.cell(row=r6, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin_border
    r6 += 1

    df_ml_xl = run_query(_conn,
        f"SELECT model_catalog, model_schema, model_name, "
        f"CASE WHEN has_description = 1 THEN 'Documented' ELSE '' END AS description, "
        f"model_readiness_score, rag_status, "
        f"CASE WHEN has_description = 1 THEN 'Yes' ELSE 'No' END AS documented "
        f"FROM {full_schema}.gold_models_summary "
        f"ORDER BY model_catalog, model_schema, model_name")

    if not df_ml_xl.empty:
        for i, (_, ml) in enumerate(df_ml_xl.iterrows(), start=1):
            ws6.cell(row=r6, column=1, value=i).border = thin_border
            ws6.cell(row=r6, column=2, value=ml['model_catalog']).border = thin_border
            ws6.cell(row=r6, column=3, value=ml['model_schema']).border = thin_border
            ws6.cell(row=r6, column=4, value=ml['model_name']).border = thin_border
            ws6.cell(row=r6, column=5, value=ml.get('description', '') or '').border = thin_border
            ws6.cell(row=r6, column=6, value=str(ml.get('model_readiness_score', '') or '')).border = thin_border
            dc = ws6.cell(row=r6, column=7, value=ml['documented'])
            dc.border = thin_border
            dc.fill = green_fill if ml['documented'] == 'Yes' else red_fill
            r6 += 1
    else:
        ws6.cell(row=r6, column=1, value="No ML Models found")

    # Volumes section
    r6 += 2
    ws6.merge_cells(f'A{r6}:G{r6}')
    ws6[f'A{r6}'] = "UC VOLUMES"
    ws6[f'A{r6}'].font = sec_font
    ws6[f'A{r6}'].fill = sec_fill
    ws6[f'A{r6}'].alignment = Alignment(horizontal='center')
    r6 += 1

    for col, h in enumerate(["#", "Catalog", "Schema", "Volume Name",
                              "Type", "Description", "Documented"], start=1):
        c = ws6.cell(row=r6, column=col, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin_border
    r6 += 1

    df_vol_xl = run_query(_conn,
        f"SELECT volume_catalog, volume_schema, volume_name, volume_type, "
        f"comment AS description, "
        f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 'Yes' ELSE 'No' END AS documented "
        f"FROM system.information_schema.volumes "
        f"ORDER BY volume_catalog, volume_schema, volume_name")

    if not df_vol_xl.empty:
        for i, (_, vol) in enumerate(df_vol_xl.iterrows(), start=1):
            ws6.cell(row=r6, column=1, value=i).border = thin_border
            ws6.cell(row=r6, column=2, value=vol['volume_catalog']).border = thin_border
            ws6.cell(row=r6, column=3, value=vol['volume_schema']).border = thin_border
            ws6.cell(row=r6, column=4, value=vol['volume_name']).border = thin_border
            ws6.cell(row=r6, column=5, value=vol.get('volume_type', '')).border = thin_border
            ws6.cell(row=r6, column=6, value=vol.get('description', '') or '').border = thin_border
            dc = ws6.cell(row=r6, column=7, value=vol['documented'])
            dc.border = thin_border
            dc.fill = green_fill if vol['documented'] == 'Yes' else red_fill
            r6 += 1
    else:
        ws6.cell(row=r6, column=1, value="No Volumes found")

    ws6.column_dimensions['A'].width = 5
    ws6.column_dimensions['B'].width = 18
    ws6.column_dimensions['C'].width = 18
    ws6.column_dimensions['D'].width = 32
    ws6.column_dimensions['E'].width = 16
    ws6.column_dimensions['F'].width = 20
    ws6.column_dimensions['G'].width = 12

    # ===== SHEET 7: Compute =====
    ws7 = wb.create_sheet("Compute")
    ws7.sheet_properties.tabColor = "F59E0B"
    ws7.merge_cells('A1:G2')
    h7 = ws7['A1']
    h7.value = "Unity Catalog \u2014 Compute Governance"
    h7.font = Font(bold=True, color="FFFFFF", size=16)
    h7.fill = hdr_fill
    h7.alignment = Alignment(horizontal='center', vertical='center')

    # Clusters section
    ws7.merge_cells('A4:G4')
    ws7['A4'] = "CLUSTERS"
    ws7['A4'].font = sec_font
    ws7['A4'].fill = sec_fill
    ws7['A4'].alignment = Alignment(horizontal='center')

    df_cl_xl = run_query(_conn,
        f"SELECT * FROM {full_schema}.gold_clusters_summary ORDER BY cluster_readiness_score ASC")
    if not df_cl_xl.empty:
        cl_cols = [c for c in df_cl_xl.columns[:8]]
        for col, h in enumerate(cl_cols, start=1):
            c = ws7.cell(row=5, column=col, value=h)
            c.font = hdr_font
            c.fill = hdr_fill
            c.border = thin_border
        r7 = 6
        for _, row_data in df_cl_xl.iterrows():
            for col_idx, col_name in enumerate(cl_cols, start=1):
                val = row_data.get(col_name, '')
                ws7.cell(row=r7, column=col_idx, value=str(val) if val is not None else '').border = thin_border
            r7 += 1
    else:
        ws7['A5'] = "No cluster data available"

    # SQL Warehouses section
    r7 = r7 + 2 if not df_cl_xl.empty else 8
    ws7.merge_cells(f'A{r7}:G{r7}')
    ws7[f'A{r7}'] = "SQL WAREHOUSES"
    ws7[f'A{r7}'].font = sec_font
    ws7[f'A{r7}'].fill = sec_fill
    ws7[f'A{r7}'].alignment = Alignment(horizontal='center')
    r7 += 1

    df_wh_xl = run_query(_conn,
        f"SELECT * FROM {full_schema}.gold_warehouses_summary ORDER BY warehouse_readiness_score ASC")
    if not df_wh_xl.empty:
        wh_cols = [c for c in df_wh_xl.columns[:8]]
        for col, h in enumerate(wh_cols, start=1):
            c = ws7.cell(row=r7, column=col, value=h)
            c.font = hdr_font
            c.fill = hdr_fill
            c.border = thin_border
        r7 += 1
        for _, row_data in df_wh_xl.iterrows():
            for col_idx, col_name in enumerate(wh_cols, start=1):
                val = row_data.get(col_name, '')
                ws7.cell(row=r7, column=col_idx, value=str(val) if val is not None else '').border = thin_border
            r7 += 1
    else:
        ws7[f'A{r7}'] = "No warehouse data available"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Sidebar — connection & global filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.databricks.com/wp-content/uploads/2022/06/db-nav-logo.svg", width=160)
    st.markdown(
        '<p style="color:#334155;font-size:22px;font-weight:700;margin:0">GovernIQ v1.0</p>',
        unsafe_allow_html=True)
    st.divider()
    warehouse_id = st.text_input(
        "SQL Warehouse ID",
        value=os.environ.get("DATABRICKS_WAREHOUSE_ID", ""),
        help="Found in the warehouse HTTP path: /sql/1.0/warehouses/<ID>")

conn = None
if warehouse_id:
    try:
        conn = get_connection(warehouse_id)
    except Exception as e:
        st.error(f"Connection failed: {e}")
if not conn:
    st.title("\U0001f3db\ufe0f GovernIQ")
    st.info("Enter a **SQL Warehouse ID** in the sidebar to connect.")
    st.stop()

st.sidebar.success("Connected")

# ---- First-Run Detection: Check if assessment tables exist ----
_init_check = run_query(conn,
    f"SELECT COUNT(*) AS cnt FROM system.information_schema.tables "
    f"WHERE table_catalog = '{FULL_SCHEMA.split('.')[0]}' "
    f"AND table_schema = '{FULL_SCHEMA.split('.')[1]}' "
    f"AND table_name = 'gold_executive_summary'")
_tables_exist = (not _init_check.empty and int(_init_check.iloc[0]['cnt']) > 0)

if not _tables_exist:
    st.title("\U0001f680 GovernIQ — First Time Setup")
    st.markdown(
        '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:16px;'
        'border-radius:0 8px 8px 0;margin-bottom:20px">'
        '<strong style="color:#1e40af">Welcome!</strong> '
        'No assessment data found. Run the pipeline below to scan your Unity Catalog '
        'and generate scores, recommendations, and the executive summary.</div>',
        unsafe_allow_html=True)

    st.markdown("### Pipeline Steps")
    st.markdown("""
1. **Create Schema** — `{schema}` if it doesn't exist
2. **Bronze Layer** — Ingest from `system.information_schema`, billing, lineage
3. **Silver Layer** — Assess metadata, governance, quality, Genie readiness
4. **Gold Layer** — Aggregate scores, generate recommendations
    """.format(schema=FULL_SCHEMA))

    st.warning("\u26a0\ufe0f This will create tables in `" + FULL_SCHEMA + "`. Ensure your SQL Warehouse has access to `system.information_schema` and `system.access`.")

    if st.button("\U0001f680 Initialize & Run Full Pipeline", type="primary", key="first_run_btn"):
        progress = st.progress(0, text="Initializing...")
        status = st.container()
        try:
            total = 12
            step_n = [0]

            def _run(sql, label):
                step_n[0] += 1
                progress.progress(step_n[0] / total, text=f"Step {step_n[0]}/{total}: {label}...")
                run_query(conn, sql)
                status.markdown(f"\u2705 {label}")

            # Create schema
            _run(f"CREATE SCHEMA IF NOT EXISTS {FULL_SCHEMA}", "Schema created")

            # Bronze
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_tables AS SELECT * FROM system.information_schema.tables WHERE table_schema != 'information_schema'", "Bronze: Tables")
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_columns AS SELECT * FROM system.information_schema.columns WHERE table_schema != 'information_schema'", "Bronze: Columns")
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_privileges AS SELECT * FROM system.information_schema.table_privileges", "Bronze: Privileges")
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_tags AS SELECT * FROM system.information_schema.table_tags", "Bronze: Tags")
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_lineage AS SELECT * FROM system.access.table_lineage WHERE event_time >= current_date() - INTERVAL 30 DAYS", "Bronze: Lineage")

            # Silver
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_metadata_assessment AS WITH col_stats AS (SELECT table_catalog, table_schema, table_name, COUNT(*) AS total_columns, SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END) AS documented_columns FROM {FULL_SCHEMA}.bronze_columns GROUP BY table_catalog, table_schema, table_name) SELECT t.table_catalog, t.table_schema, t.table_name, t.table_type, CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 1 ELSE 0 END AS has_table_description, COALESCE(c.total_columns, 0) AS total_columns, COALESCE(c.documented_columns, 0) AS documented_columns, ROUND(COALESCE(c.documented_columns, 0) * 100.0 / NULLIF(c.total_columns, 0), 1) AS column_doc_pct, CASE WHEN t.table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END AS naming_score, ROUND((CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 2.0 ELSE 0 END) + (COALESCE(c.documented_columns, 0) * 2.0 / NULLIF(c.total_columns, 0)) + (CASE WHEN t.table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1.0 ELSE 0 END), 2) AS metadata_score FROM {FULL_SCHEMA}.bronze_tables t LEFT JOIN col_stats c ON t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema AND t.table_name = c.table_name", "Silver: Metadata")

            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_governance_assessment AS WITH tag_stats AS (SELECT catalog_name AS table_catalog, schema_name AS table_schema, table_name, COUNT(*) AS tag_count FROM {FULL_SCHEMA}.bronze_table_tags GROUP BY catalog_name, schema_name, table_name), priv_stats AS (SELECT table_catalog, table_schema, table_name, COUNT(*) AS grant_count, SUM(CASE WHEN privilege_type = 'ALL PRIVILEGES' THEN 1 ELSE 0 END) AS over_permissioned_grants FROM {FULL_SCHEMA}.bronze_table_privileges GROUP BY table_catalog, table_schema, table_name) SELECT t.table_catalog, t.table_schema, t.table_name, CASE WHEN tg.tag_count > 0 THEN 1 ELSE 0 END AS has_tags, CASE WHEN p.grant_count > 0 THEN 1 ELSE 0 END AS has_explicit_grants, CASE WHEN COALESCE(p.over_permissioned_grants, 0) > 0 THEN 0 ELSE 1 END AS no_over_permission, CASE WHEN t.table_type = 'MANAGED' THEN 1 ELSE 0 END AS is_managed, ROUND((CASE WHEN tg.tag_count > 0 THEN 1.5 ELSE 0 END) + (CASE WHEN p.grant_count > 0 THEN 1.5 ELSE 0 END) + (CASE WHEN COALESCE(p.over_permissioned_grants, 0) = 0 THEN 1.0 ELSE 0 END) + (CASE WHEN t.table_type = 'MANAGED' THEN 1.0 ELSE 0 END), 2) AS governance_score FROM {FULL_SCHEMA}.bronze_tables t LEFT JOIN tag_stats tg ON t.table_catalog = tg.table_catalog AND t.table_schema = tg.table_schema AND t.table_name = tg.table_name LEFT JOIN priv_stats p ON t.table_catalog = p.table_catalog AND t.table_schema = p.table_schema AND t.table_name = p.table_name", "Silver: Governance")

            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_quality_assessment AS SELECT table_catalog, table_schema, table_name, CASE WHEN data_source_format = 'DELTA' THEN 1 ELSE 0 END AS is_delta, CASE WHEN last_altered >= current_date() - INTERVAL 30 DAYS THEN 1 ELSE 0 END AS is_fresh, ROUND((CASE WHEN data_source_format = 'DELTA' THEN 2.5 ELSE 0 END) + (CASE WHEN last_altered >= current_date() - INTERVAL 30 DAYS THEN 2.5 ELSE 0 END), 2) AS quality_score FROM {FULL_SCHEMA}.bronze_tables", "Silver: Quality")

            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_genie_readiness AS WITH lineage_stats AS (SELECT target_table_catalog AS table_catalog, target_table_schema AS table_schema, target_table_name AS table_name, COUNT(*) AS lineage_connection_count FROM {FULL_SCHEMA}.bronze_table_lineage GROUP BY target_table_catalog, target_table_schema, target_table_name) SELECT m.table_catalog, m.table_schema, m.table_name, m.has_table_description AS has_description, m.column_doc_pct, m.naming_score AS naming_compliant, CASE WHEN l.lineage_connection_count > 0 THEN 1 ELSE 0 END AS has_lineage, COALESCE(l.lineage_connection_count, 0) AS lineage_connection_count, CASE WHEN LOWER(m.table_schema) RLIKE '(gold|curated|mart)' OR LOWER(m.table_name) RLIKE '^(fact|dim)_' THEN 1 ELSE 0 END AS is_gold_layer_candidate, ROUND((m.has_table_description * 20.0) + (LEAST(COALESCE(m.column_doc_pct, 0), 100) / 100.0 * 30.0) + (m.naming_score * 15.0) + (CASE WHEN l.lineage_connection_count > 0 THEN 15.0 ELSE 0 END) + (CASE WHEN LOWER(m.table_schema) RLIKE '(gold|curated|mart)' OR LOWER(m.table_name) RLIKE '^(fact|dim)_' THEN 20.0 ELSE 0 END), 1) AS genie_readiness_score FROM {FULL_SCHEMA}.silver_metadata_assessment m LEFT JOIN lineage_stats l ON m.table_catalog = l.table_catalog AND m.table_schema = l.table_schema AND m.table_name = l.table_name", "Silver: Genie Readiness")

            # Gold - table scores + executive summary
            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_table_scores AS SELECT m.table_catalog, m.table_schema, m.table_name, ROUND(m.metadata_score, 2) AS metadata_score, ROUND(COALESCE(g.governance_score, 0), 2) AS governance_score, ROUND(COALESCE(q.quality_score, 0), 2) AS quality_score, ROUND(COALESCE(gr.genie_readiness_score, 0), 2) AS genie_score, ROUND((COALESCE(m.metadata_score, 0)/5.0*25) + (COALESCE(g.governance_score, 0)/5.0*25) + (COALESCE(q.quality_score, 0)/5.0*25) + (COALESCE(gr.genie_readiness_score, 0)/100.0*25), 2) AS overall_score, CASE WHEN ((COALESCE(m.metadata_score,0)/5.0*25)+(COALESCE(g.governance_score,0)/5.0*25)+(COALESCE(q.quality_score,0)/5.0*25)+(COALESCE(gr.genie_readiness_score,0)/100.0*25)) >= 70 THEN 'GREEN' WHEN ((COALESCE(m.metadata_score,0)/5.0*25)+(COALESCE(g.governance_score,0)/5.0*25)+(COALESCE(q.quality_score,0)/5.0*25)+(COALESCE(gr.genie_readiness_score,0)/100.0*25)) >= 40 THEN 'AMBER' ELSE 'RED' END AS rag_status FROM {FULL_SCHEMA}.silver_metadata_assessment m LEFT JOIN {FULL_SCHEMA}.silver_governance_assessment g ON m.table_catalog=g.table_catalog AND m.table_schema=g.table_schema AND m.table_name=g.table_name LEFT JOIN {FULL_SCHEMA}.silver_quality_assessment q ON m.table_catalog=q.table_catalog AND m.table_schema=q.table_schema AND m.table_name=q.table_name LEFT JOIN {FULL_SCHEMA}.silver_genie_readiness gr ON m.table_catalog=gr.table_catalog AND m.table_schema=gr.table_schema AND m.table_name=gr.table_name", "Gold: Table scores")

            _run(f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_executive_summary AS SELECT (SELECT COUNT(DISTINCT table_catalog) FROM {FULL_SCHEMA}.gold_table_scores) AS total_catalogs, (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_table_scores) AS total_tables, (SELECT COUNT(*) FROM {FULL_SCHEMA}.bronze_columns) AS total_columns, 0 AS total_functions, 0 AS avg_function_score, 0 AS total_models, 0 AS avg_model_score, 0 AS total_volumes, 0 AS avg_volume_score, 0 AS total_clusters, NULL AS avg_cluster_score, 0 AS total_warehouses, NULL AS avg_warehouse_score, ROUND((SELECT AVG(overall_score) FROM {FULL_SCHEMA}.gold_table_scores), 1) AS overall_readiness_score, CASE WHEN (SELECT AVG(overall_score) FROM {FULL_SCHEMA}.gold_table_scores) >= 70 THEN 'GREEN' WHEN (SELECT AVG(overall_score) FROM {FULL_SCHEMA}.gold_table_scores) >= 40 THEN 'AMBER' ELSE 'RED' END AS overall_rag_status, NULL AS metadata_score, NULL AS governance_score, NULL AS quality_score, NULL AS performance_score, NULL AS genie_score, ROUND((SELECT SUM(CASE WHEN has_table_description=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) FROM {FULL_SCHEMA}.silver_metadata_assessment), 1) AS tables_with_descriptions_pct, ROUND((SELECT AVG(column_doc_pct) FROM {FULL_SCHEMA}.silver_metadata_assessment), 1) AS columns_documented_pct, ROUND((SELECT SUM(CASE WHEN is_delta=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) FROM {FULL_SCHEMA}.silver_quality_assessment), 1) AS delta_format_pct, ROUND((SELECT SUM(CASE WHEN is_fresh=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) FROM {FULL_SCHEMA}.silver_quality_assessment), 1) AS fresh_tables_pct, (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_table_scores WHERE overall_score >= 70) AS genie_ready_tables, ROUND((SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_table_scores WHERE overall_score >= 70) * 100.0 / NULLIF((SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_table_scores), 0), 1) AS genie_ready_pct, 0 AS total_recommendations, 0 AS high_priority_recommendations, 0 AS total_dbus_consumed, current_timestamp() AS assessment_date", "Gold: Executive summary")

            progress.progress(1.0, text="\u2705 Pipeline complete!")
            st.success("\U0001f389 First-time setup complete! Assessment data is ready. **Please reload the page** to see the full dashboard.")
            st.balloons()

        except Exception as e:
            st.error(f"\u274c Setup failed at step {step_n[0]}: {str(e)}")
            st.markdown("**Troubleshooting:** Ensure your SQL Warehouse has access to `system.information_schema`, `system.access`, and `system.billing`.")

    st.stop()

# ---- Fetch last assessment refresh date ----
_last_refresh_df = run_query(conn, f"SELECT assessment_date FROM {FULL_SCHEMA}.gold_executive_summary LIMIT 1")
_last_refresh = _last_refresh_df.iloc[0]['assessment_date'] if not _last_refresh_df.empty else None
if _last_refresh is not None:
    try:
        _refresh_str = pd.to_datetime(_last_refresh).strftime("%b %d, %Y at %H:%M")
    except Exception:
        _refresh_str = str(_last_refresh)[:19]
    st.sidebar.caption(f"\U0001f4c5 Last Assessment: {_refresh_str}")
else:
    st.sidebar.caption("\U0001f4c5 Last Assessment: Unknown")

# ---- Global catalog / schema filters ----
with st.sidebar:
    st.divider()
    st.markdown("**Scope Filters**")
    df_filter_opts = run_query(
        conn,
        f"SELECT DISTINCT table_catalog, table_schema "
        f"FROM {FULL_SCHEMA}.gold_table_scores ORDER BY table_catalog, table_schema",
    )
    cat_list = sorted(df_filter_opts["table_catalog"].unique().tolist()) if not df_filter_opts.empty else []
    selected_catalog = st.selectbox("Catalog", ["All"] + cat_list, key="gf_catalog")

    if selected_catalog != "All":
        schema_list = sorted(
            df_filter_opts[df_filter_opts["table_catalog"] == selected_catalog]["table_schema"]
            .unique().tolist()
        )
    else:
        schema_list = sorted(df_filter_opts["table_schema"].unique().tolist()) if not df_filter_opts.empty else []
    selected_schema = st.selectbox("Schema", ["All"] + schema_list, key="gf_schema")

    # ---- Asset Category (table_type) filter ----
    df_type_opts = run_query(
        conn,
        f"SELECT DISTINCT table_type "
        f"FROM {FULL_SCHEMA}.silver_metadata_assessment ORDER BY table_type",
    )
    table_type_list = sorted(df_type_opts["table_type"].unique().tolist()) if not df_type_opts.empty else []
    type_list = table_type_list + ["FUNCTION", "ML_MODEL", "VOLUME", "CLUSTER", "SQL_WAREHOUSE"]
    selected_asset_types = st.multiselect(
        "Asset Category", type_list, default=type_list,
        key="gf_asset_type",
        help="Filter by: MANAGED, VIEW, STREAMING_TABLE, FUNCTION, ML_MODEL, VOLUME, CLUSTER, SQL_WAREHOUSE, etc.",
    )

    st.divider()
    if st.button("\U0001f504 Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Source: {FULL_SCHEMA}")

# ---- Build SQL filter fragments ----
_fp = []
if selected_catalog != "All":
    _fp.append(f"table_catalog = '{selected_catalog}'")
if selected_schema != "All":
    _fp.append(f"table_schema = '{selected_schema}'")

# Asset category filter — apply when not all types are selected
_all_types = sorted(df_type_opts["table_type"].unique().tolist()) if not df_type_opts.empty else []
extra_asset_types = ["FUNCTION", "ML_MODEL", "VOLUME", "CLUSTER", "SQL_WAREHOUSE"]
all_filter_types = _all_types + extra_asset_types
# Only filter table types (FUNCTION/ML_MODEL are inventory-only categories)
selected_table_types = [t for t in selected_asset_types if t in _all_types]
if selected_table_types and set(selected_table_types) != set(_all_types):
    quoted = ", ".join(f"'{t}'" for t in selected_table_types)
    _fp.append(f"table_name IN (SELECT table_name FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE table_type IN ({quoted}))")

FILTER_COND  = " AND ".join(_fp)
FILTER_WHERE = f"WHERE {FILTER_COND}" if FILTER_COND else ""
FILTER_AND   = f"AND {FILTER_COND}" if FILTER_COND else ""

_cp = []
if selected_catalog != "All":
    _cp.append(f"catalog_name = '{selected_catalog}'")
CAT_FILTER_WHERE = f"WHERE {' AND '.join(_cp)}" if _cp else ""
CAT_FILTER_AND   = f"AND {' AND '.join(_cp)}" if _cp else ""

IS_FILTERED = bool(FILTER_COND)
SHOW_FUNCTIONS = "FUNCTION" in selected_asset_types
SHOW_ML_MODELS = "ML_MODEL" in selected_asset_types
SHOW_VOLUMES = "VOLUME" in selected_asset_types
SHOW_CLUSTERS = "CLUSTER" in selected_asset_types
SHOW_WAREHOUSES = "SQL_WAREHOUSE" in selected_asset_types

# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------
st.markdown(
    '<div style="background:linear-gradient(135deg,#1e40af 0%,#3b82f6 100%);'
    'padding:24px 32px;border-radius:12px;margin-bottom:20px">'
    '<h1 style="color:#bfdbfe;margin:0;font-size:28px;font-weight:700">'
    'GovernIQ</h1>'
    '<p style="color:#bfdbfe;margin:4px 0 0;font-size:14px">'
    'Unity Catalog Assessment Dashboard</p></div>',
    unsafe_allow_html=True)

if IS_FILTERED:
    pills = []
    if selected_catalog != "All":
        pills.append(f'<span class="filter-pill">Catalog: {selected_catalog}</span>')
    if selected_schema != "All":
        pills.append(f'<span class="filter-pill">Schema: {selected_schema}</span>')
    if selected_asset_types and set(selected_asset_types) != set(all_filter_types):
        pills.append(f'<span class="filter-pill">Types: {", ".join(selected_asset_types)}</span>')
    st.markdown(
        f'<div class="tip-box">Showing filtered results: {"".join(pills)}</div>',
        unsafe_allow_html=True)

# ===========================================================================
# TABS
# ===========================================================================
tab_exec, tab_detail, tab_compute, tab_recs, tab_finops, tab_perf, tab_genie, tab_compliance, tab_ai, tab_rules, tab_actions = st.tabs([
    "\U0001f4ca Executive Summary",
    "\U0001f50d Detailed Assessment",
    "\U0001f5a5\ufe0f Compute",
    "\U0001f4a1 Recommendations",
    "\U0001f4b0 FinOps Insights",
    "\u26a1 Performance",
    "\U0001f916 Genie Readiness",
    "\U0001f4dc Compliance",
    "\U0001f9e0 AI Insights",
    "\U0001f4d6 Assessment Rules",
    "\U0001f527 Actions",
])

# ===========================================================================
# TAB 1 — EXECUTIVE SUMMARY
# ===========================================================================
with tab_exec:
    # --- Query executive data ---
    if not IS_FILTERED:
        df_exec = run_query(conn, f"SELECT * FROM {FULL_SCHEMA}.gold_executive_summary")
    else:
        df_exec = run_query(conn, f"""
            WITH meta AS (
                SELECT COUNT(DISTINCT table_catalog) AS total_catalogs,
                    COUNT(*) AS total_tables,
                    COALESCE(SUM(total_columns), 0) AS total_columns,
                    ROUND(AVG(has_table_description) * 100, 1) AS tables_with_descriptions_pct,
                    ROUND(AVG(column_doc_pct), 1) AS columns_documented_pct
                FROM {FULL_SCHEMA}.silver_metadata_assessment {FILTER_WHERE}
            ),
            qual AS (
                SELECT ROUND(AVG(is_fresh) * 100, 1) AS fresh_tables_pct,
                    ROUND(AVG(is_delta) * 100, 1) AS delta_format_pct
                FROM {FULL_SCHEMA}.silver_quality_assessment {FILTER_WHERE}
            ),
            genie AS (
                SELECT COALESCE(SUM(CASE WHEN genie_readiness_score >= 70 THEN 1 ELSE 0 END), 0) AS genie_ready_tables,
                    ROUND(COALESCE(SUM(CASE WHEN genie_readiness_score >= 70 THEN 1 ELSE 0 END) * 100.0
                          / NULLIF(COUNT(*), 0), 0), 1) AS genie_ready_pct
                FROM {FULL_SCHEMA}.silver_genie_readiness {FILTER_WHERE}
            ),
            scores AS (
                SELECT ROUND(AVG(metadata_score / 5.0 * 100), 1) AS metadata_score,
                    ROUND(AVG(governance_score / 5.0 * 100), 1) AS governance_score,
                    ROUND(AVG(quality_score / 5.0 * 100), 1) AS quality_score,
                    ROUND(AVG(genie_score / 100.0 * 100), 1) AS genie_score,
                    ROUND(AVG(overall_score), 1) AS overall_readiness_score
                FROM {FULL_SCHEMA}.gold_table_scores {FILTER_WHERE}
            ),
            recs AS (
                SELECT COUNT(*) AS total_recommendations,
                    COALESCE(SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END), 0) AS high_priority_recommendations
                FROM {FULL_SCHEMA}.gold_recommendations {FILTER_WHERE}
            ),
            dbus AS (
                SELECT ROUND(COALESCE(SUM(total_dbus), 0), 2) AS total_dbus_consumed
                FROM {FULL_SCHEMA}.gold_cost_by_sku
            )
            SELECT m.total_catalogs, m.total_tables, m.total_columns,
                s.overall_readiness_score,
                CASE WHEN s.overall_readiness_score < 40 THEN 'RED'
                     WHEN s.overall_readiness_score < 70 THEN 'AMBER' ELSE 'GREEN' END AS overall_rag_status,
                s.metadata_score, s.governance_score, s.quality_score,
                NULL AS performance_score, s.genie_score,
                m.tables_with_descriptions_pct, m.columns_documented_pct,
                q.delta_format_pct, q.fresh_tables_pct,
                g.genie_ready_tables, g.genie_ready_pct,
                r.total_recommendations, r.high_priority_recommendations,
                d.total_dbus_consumed, current_timestamp() AS assessment_date
            FROM meta m CROSS JOIN qual q CROSS JOIN genie g
            CROSS JOIN scores s CROSS JOIN recs r CROSS JOIN dbus d
        """)

    if df_exec.empty:
        st.warning("No executive summary data. Run the assessment pipeline first.")
    else:
        row = df_exec.iloc[0]
        overall = float(row.get("overall_readiness_score") or 0)
        rag = row.get("overall_rag_status", "RED")

        # ===== HERO SECTION: Overall Score + RAG Distribution =====
        hero_left, hero_right = st.columns([2, 3])

        with hero_left:
            # Large overall gauge
            rag_color = CLR_RED if rag == "RED" else CLR_AMBER if rag == "AMBER" else CLR_GREEN
            fig_hero = go.Figure(go.Indicator(
                mode="gauge+number",
                value=overall,
                number={"suffix": "%", "font": {"size": 42, "color": "#1e293b"}},
                title={"text": "Overall UC Readiness", "font": {"size": 16, "color": "#475569"}},
                gauge={
                    "axis": {"range": [0, 100], "tickfont": {"size": 11, "color": "#94a3b8"}},
                    "bar": {"color": rag_color, "thickness": 0.7},
                    "bgcolor": "#f1f5f9",
                    "steps": [
                        {"range": [0, 40], "color": "#fef2f2"},
                        {"range": [40, 70], "color": "#fffbeb"},
                        {"range": [70, 100], "color": "#f0fdf4"}
                    ],
                    "threshold": {"line": {"color": "#1e293b", "width": 3}, "thickness": 0.8, "value": overall}
                }
            ))
            fig_hero.update_layout(height=260, margin=dict(t=50, b=20, l=30, r=30), **CHART_LAYOUT)
            st.plotly_chart(fig_hero, use_container_width=True)

            # RAG badge + assessment date
            _assess_dt = row.get("assessment_date")
            _dt_str = pd.to_datetime(_assess_dt).strftime("%b %d, %Y") if pd.notna(_assess_dt) else "—"
            st.markdown(
                f'<div style="text-align:center;margin-top:-10px">'
                f'{rag_badge(rag)}'
                f'<span style="margin-left:12px;color:#64748b;font-size:12px">Assessed: {_dt_str}</span>'
                f'</div>', unsafe_allow_html=True)

        with hero_right:
            # RAG distribution donut + key stats
            df_rag_dist = run_query(conn,
                f"SELECT rag_status, COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_table_scores "
                f"{FILTER_WHERE} GROUP BY rag_status")

            if not df_rag_dist.empty:
                _r_top, _r_bot = st.columns([1, 1])
                with _r_top:
                    fig_donut = px.pie(
                        df_rag_dist, values="cnt", names="rag_status",
                        color="rag_status",
                        color_discrete_map={"RED": CLR_RED, "AMBER": CLR_AMBER, "GREEN": CLR_GREEN},
                        hole=0.55)
                    fig_donut.update_traces(textposition="inside", textinfo="value+percent",
                                           textfont_size=12)
                    fig_donut.update_layout(
                        height=220, margin=dict(t=20, b=10, l=10, r=10),
                        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
                        **CHART_LAYOUT)
                    st.plotly_chart(fig_donut, use_container_width=True)

                with _r_bot:
                    _red_n = int(df_rag_dist[df_rag_dist["rag_status"] == "RED"]["cnt"].sum()) if "RED" in df_rag_dist["rag_status"].values else 0
                    _amb_n = int(df_rag_dist[df_rag_dist["rag_status"] == "AMBER"]["cnt"].sum()) if "AMBER" in df_rag_dist["rag_status"].values else 0
                    _grn_n = int(df_rag_dist[df_rag_dist["rag_status"] == "GREEN"]["cnt"].sum()) if "GREEN" in df_rag_dist["rag_status"].values else 0
                    _total_n = _red_n + _amb_n + _grn_n

                    st.markdown(
                        f'<div style="background:white;border-radius:12px;padding:16px 20px;'
                        f'box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-top:10px">'
                        f'<p style="font-size:13px;color:#64748b;margin:0 0 10px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Table Health</p>'
                        f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
                        f'<span style="color:{CLR_RED};font-weight:700;font-size:22px">{_red_n}</span>'
                        f'<span style="color:{CLR_AMBER};font-weight:700;font-size:22px">{_amb_n}</span>'
                        f'<span style="color:{CLR_GREEN};font-weight:700;font-size:22px">{_grn_n}</span>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8">'
                        f'<span>Critical</span><span>Needs Work</span><span>Healthy</span></div>'
                        f'<div style="height:6px;border-radius:3px;margin-top:10px;background:#e2e8f0;overflow:hidden;display:flex">'
                        f'<div style="width:{_red_n*100/max(_total_n,1):.0f}%;background:{CLR_RED}"></div>'
                        f'<div style="width:{_amb_n*100/max(_total_n,1):.0f}%;background:{CLR_AMBER}"></div>'
                        f'<div style="width:{_grn_n*100/max(_total_n,1):.0f}%;background:{CLR_GREEN}"></div>'
                        f'</div>'
                        f'<p style="text-align:center;margin:8px 0 0;font-size:12px;color:#64748b">'
                        f'{_total_n:,} tables assessed</p>'
                        f'</div>', unsafe_allow_html=True)

        # ===== INVENTORY METRICS ROW =====
        st.markdown("")
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: metric_card("\U0001f4c1 Catalogs", int(row.get("total_catalogs") or 0), CLR_BLUE)
        with k2: metric_card("\U0001f4ca Tables", f"{int(row.get('total_tables') or 0):,}", CLR_BLUE)
        with k3: metric_card("\U0001f4dd Columns", f"{int(row.get('total_columns') or 0):,}", CLR_BLUE)
        with k4: metric_card("\U0001f4a1 Recommendations", f"{int(row.get('total_recommendations') or 0):,}", CLR_RED)
        with k5: metric_card("\u26a0\ufe0f HIGH Priority", f"{int(row.get('high_priority_recommendations') or 0):,}", CLR_RED)
        with k6: metric_card("\u26a1 DBUs (30d)", f"{float(row.get('total_dbus_consumed') or 0):,.0f}", CLR_PURPLE)

        # --- Additional asset counts ---
        _fn_cat_cond = f"routine_catalog = '{selected_catalog}'" if selected_catalog != "All" else "1=1"
        _fn_sch_cond = f"routine_schema = '{selected_schema}'" if selected_schema != "All" else "1=1"
        df_fn_count = run_query(conn,
            f"SELECT COUNT(*) AS cnt FROM system.information_schema.routines "
            f"WHERE {_fn_cat_cond} AND {_fn_sch_cond}")
        uc_fn_count = int(df_fn_count.iloc[0]["cnt"]) if not df_fn_count.empty else 0

        _ml_cat_cond = f"model_catalog = '{selected_catalog}'" if selected_catalog != "All" else "1=1"
        _ml_sch_cond = f"model_schema = '{selected_schema}'" if selected_schema != "All" else "1=1"
        df_ml_count = run_query(conn,
            f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_models_summary "
            f"WHERE {_ml_cat_cond} AND {_ml_sch_cond}")
        ml_model_count = int(df_ml_count.iloc[0]["cnt"]) if not df_ml_count.empty else 0

        _vol_cat_cond = f"volume_catalog = '{selected_catalog}'" if selected_catalog != "All" else "1=1"
        _vol_sch_cond = f"volume_schema = '{selected_schema}'" if selected_schema != "All" else "1=1"
        df_vol_count = run_query(conn,
            f"SELECT COUNT(*) AS cnt FROM system.information_schema.volumes "
            f"WHERE {_vol_cat_cond} AND {_vol_sch_cond}")
        vol_count = int(df_vol_count.iloc[0]["cnt"]) if not df_vol_count.empty else 0

        cluster_count = int(row.get('total_clusters') or 0) if not IS_FILTERED else 0
        warehouse_count = int(row.get('total_warehouses') or 0) if not IS_FILTERED else 0

        df_type_counts = run_query(conn,
            f"SELECT table_type, COUNT(*) AS cnt "
            f"FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE 1=1 {FILTER_AND} "
            f"GROUP BY table_type")
        _type_cnt = dict(zip(df_type_counts['table_type'], df_type_counts['cnt'])) if not df_type_counts.empty else {}

        k7, k8, k9, k10, k11, k12 = st.columns(6)
        with k7: metric_card("\u2699\ufe0f Functions", f"{uc_fn_count:,}", CLR_PURPLE)
        with k8: metric_card("\U0001f9e0 ML Models", f"{ml_model_count:,}", CLR_GREEN)
        with k9: metric_card("\U0001f4e6 Volumes", f"{vol_count:,}", CLR_PURPLE)
        with k10: metric_card("\U0001f5a5\ufe0f Clusters", f"{cluster_count:,}", CLR_AMBER)
        with k11: metric_card("\U0001f3ed Warehouses", f"{warehouse_count:,}", CLR_GREEN)
        with k12: metric_card("\U0001f4a8 Streaming", f"{int(_type_cnt.get('STREAMING_TABLE', 0)):,}", CLR_BLUE)

        # ===== CATEGORY SCORES — Horizontal Bar + Gauges =====
        st.markdown("---")
        st.subheader("Category Readiness Breakdown")

        categories = [
            ("Metadata", float(row.get("metadata_score") or 0), "\U0001f4d1"),
            ("Governance", float(row.get("governance_score") or 0), "\U0001f512"),
            ("Data Quality", float(row.get("quality_score") or 0), "\u2705"),
            ("Performance", float(row.get("performance_score") or 0), "\u26a1"),
            ("Genie Ready", float(row.get("genie_score") or 0), "\U0001f916"),
        ]

        # Horizontal stacked bar showing all categories at a glance
        bar_data = []
        for name, score, _ in categories:
            rag_s = "RED" if score < 40 else "AMBER" if score < 70 else "GREEN"
            bar_data.append({"Category": name, "Score": score, "RAG": rag_s})
        df_bar = pd.DataFrame(bar_data)

        fig_bar = go.Figure()
        for _, brow in df_bar.iterrows():
            bar_color = CLR_RED if brow["RAG"] == "RED" else CLR_AMBER if brow["RAG"] == "AMBER" else CLR_GREEN
            fig_bar.add_trace(go.Bar(
                y=[brow["Category"]], x=[brow["Score"]],
                orientation="h", marker_color=bar_color,
                text=f"{brow['Score']:.0f}%", textposition="inside",
                textfont=dict(color="white", size=13, family="Arial Black"),
                showlegend=False, hovertemplate=f"{brow['Category']}: {brow['Score']:.1f}%<extra></extra>"
            ))
        fig_bar.update_layout(
            height=200, barmode="stack",
            xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#e2e8f0", title=""),
            yaxis=dict(title="", autorange="reversed"),
            margin=dict(t=10, b=30, l=100, r=20), **CHART_LAYOUT)
        fig_bar.add_vline(x=40, line_dash="dot", line_color="#ef4444", line_width=1)
        fig_bar.add_vline(x=70, line_dash="dot", line_color="#22c55e", line_width=1)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Gauge row
        cols = st.columns(5)
        for i, (name, score, icon) in enumerate(categories):
            with cols[i]:
                color = CLR_RED if score < 40 else CLR_AMBER if score < 70 else CLR_GREEN
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=score,
                    title={"text": f"{icon} {name}", "font": {"size": 12, "color": "#334155"}},
                    number={"suffix": "%", "font": {"size": 20, "color": "#1e293b"}},
                    gauge={"axis": {"range": [0, 100], "tickfont": {"size": 9, "color": "#64748b"}},
                           "bar": {"color": color, "thickness": 0.7},
                           "bgcolor": "#f1f5f9",
                           "steps": [{"range": [0, 40], "color": "#fef2f2"},
                                     {"range": [40, 70], "color": "#fffbeb"},
                                     {"range": [70, 100], "color": "#f0fdf4"}]}))
                fig.update_layout(height=160, margin=dict(t=35, b=0, l=10, r=10), **CHART_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        # ===== KEY INDICATORS =====
        st.markdown("---")
        st.subheader("Key Health Indicators")
        i1, i2, i3, i4, i5 = st.columns(5)
        with i1: st.metric("Tables with Descriptions", f"{row.get('tables_with_descriptions_pct') or 0}%")
        with i2: st.metric("Columns Documented", f"{row.get('columns_documented_pct') or 0}%")
        with i3: st.metric("Delta Format", f"{row.get('delta_format_pct') or 0}%")
        with i4: st.metric("Fresh Tables (30d)", f"{row.get('fresh_tables_pct') or 0}%")
        with i5: st.metric("Genie-Ready", f"{int(row.get('genie_ready_tables') or 0)} ({row.get('genie_ready_pct') or 0}%)")

        # ===== TOP 5 AT-RISK TABLES =====
        st.markdown("---")
        st.subheader("\U0001f6a8 Top Tables Needing Attention")
        df_at_risk = run_query(conn,
            f"SELECT table_catalog, table_schema, table_name, overall_score, rag_status "
            f"FROM {FULL_SCHEMA}.gold_table_scores {FILTER_WHERE} "
            f"ORDER BY overall_score ASC LIMIT 8")
        if not df_at_risk.empty:
            # Format as a styled HTML table
            _risk_rows = ""
            for _, r in df_at_risk.iterrows():
                _sc = float(r['overall_score']) if pd.notna(r['overall_score']) else 0
                _rag_c = CLR_RED if _sc < 40 else CLR_AMBER if _sc < 70 else CLR_GREEN
                _risk_rows += (
                    f'<tr><td style="font-weight:600;color:#1e293b">'
                    f'{r["table_catalog"]}.{r["table_schema"]}.{r["table_name"]}</td>'
                    f'<td style="text-align:center"><span style="background:{_rag_c};color:white;'
                    f'padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600">{_sc:.1f}%</span></td>'
                    f'<td style="text-align:center">{rag_badge(r["rag_status"])}</td></tr>')
            st.markdown(
                f'<div style="background:white;border-radius:12px;padding:16px 20px;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:3px solid {CLR_RED}">'
                f'<table style="width:100%;border-collapse:collapse">'
                f'<tr style="border-bottom:2px solid #e2e8f0">'
                f'<th style="text-align:left;padding:8px;color:#475569;font-size:13px">Table</th>'
                f'<th style="text-align:center;padding:8px;color:#475569;font-size:13px">Score</th>'
                f'<th style="text-align:center;padding:8px;color:#475569;font-size:13px">Status</th></tr>'
                f'{_risk_rows}</table></div>', unsafe_allow_html=True)
        else:
            st.info("No table scores available.")

        # ===== EXTENDED CATEGORY SCORES =====
        df_cat_scores = run_query(conn,
            f"SELECT category, pct FROM {FULL_SCHEMA}.gold_category_scores WHERE catalog_name = 'ALL'")
        if not df_cat_scores.empty:
            cat_score_map = dict(zip(df_cat_scores['category'], df_cat_scores['pct']))
            ext_categories = [
                ("UC Functions", cat_score_map.get("UC Functions", 0)),
                ("ML Models", cat_score_map.get("ML Models", 0)),
                ("Volumes", cat_score_map.get("Volumes", 0)),
                ("Clusters", cat_score_map.get("Clusters", 0)),
                ("SQL Warehouses", cat_score_map.get("SQL Warehouses", 0)),
            ]
            ext_with_data = [(n, s) for n, s in ext_categories if s is not None and s > 0]
            if ext_with_data:
                st.markdown("---")
                st.subheader("Extended Category Scores")
                ext_cols = st.columns(len(ext_with_data))
                for i, (name, score) in enumerate(ext_with_data):
                    with ext_cols[i]:
                        color = CLR_RED if score < 40 else CLR_AMBER if score < 70 else CLR_GREEN
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number", value=float(score),
                            title={"text": name, "font": {"size": 12, "color": "#334155"}},
                            number={"suffix": "%", "font": {"size": 18, "color": "#1e293b"}},
                            gauge={"axis": {"range": [0, 100], "tickfont": {"size": 9, "color": "#64748b"}},
                                   "bar": {"color": color, "thickness": 0.7},
                                   "bgcolor": "#f1f5f9",
                                   "steps": [{"range": [0, 40], "color": "#fef2f2"},
                                             {"range": [40, 70], "color": "#fffbeb"},
                                             {"range": [70, 100], "color": "#f0fdf4"}]}))
                        fig.update_layout(height=160, margin=dict(t=35, b=0, l=10, r=10), **CHART_LAYOUT)
                        st.plotly_chart(fig, use_container_width=True)

    # --- UC Functions, ML Models, Volumes Inventory Panel ---
    if SHOW_FUNCTIONS or SHOW_ML_MODELS or SHOW_VOLUMES:
        st.markdown("---")
        st.subheader("\U0001f9e9 Additional Asset Inventory")

    if SHOW_FUNCTIONS:
        _fn_catalog_filter = f"WHERE routine_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
        _fn_schema_filter = (
            f" AND routine_schema = '{selected_schema}'" if selected_schema != "All" and _fn_catalog_filter
            else f"WHERE routine_schema = '{selected_schema}'" if selected_schema != "All"
            else ""
        )
        df_functions = run_query(conn,
            f"SELECT routine_catalog, routine_schema, routine_name, routine_type, "
            f"data_type AS return_type, created AS created_at "
            f"FROM system.information_schema.routines "
            f"{_fn_catalog_filter}{_fn_schema_filter} "
            f"ORDER BY routine_catalog, routine_schema, routine_name")
        fn_count = len(df_functions) if not df_functions.empty else 0
        st.markdown(
            f'<div class="method-card" style="border-left:4px solid {CLR_PURPLE}">'
            f'<h4 style="color:{CLR_PURPLE} !important">\u2699\ufe0f UC Functions ({fn_count})</h4>'
            f'<p>User-defined functions registered in Unity Catalog across accessible catalogs.</p></div>',
            unsafe_allow_html=True)
        if not df_functions.empty:
            st.dataframe(df_functions, use_container_width=True, height=250)
        else:
            st.info("No UC Functions found for the current scope.")

    if SHOW_ML_MODELS:
        _ml_cat_inv = f"AND model_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
        _ml_sch_inv = f"AND model_schema = '{selected_schema}'" if selected_schema != "All" else ""
        df_models = run_query(conn,
            f"SELECT model_catalog, model_schema, model_name, "
            f"model_readiness_score, rag_status, "
            f"CASE WHEN has_description = 1 THEN 'Documented' ELSE '' END AS description "
            f"FROM {FULL_SCHEMA}.gold_models_summary "
            f"WHERE 1=1 {_ml_cat_inv} {_ml_sch_inv} "
            f"ORDER BY model_catalog, model_schema, model_name")
        ml_count = len(df_models) if not df_models.empty else 0
        st.markdown(
            f'<div class="method-card" style="border-left:4px solid {CLR_GREEN}">'
            f'<h4 style="color:{CLR_GREEN} !important">\U0001f916 ML Models ({ml_count})</h4>'
            f'<p>Registered ML models in Unity Catalog (MODEL type assets).</p></div>',
            unsafe_allow_html=True)
        if not df_models.empty:
            st.dataframe(df_models, use_container_width=True, height=250)
        else:
            st.info("No ML Models found for the current scope.")

    if SHOW_VOLUMES:
        _vol_catalog_filter = f"WHERE volume_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
        _vol_schema_filter = (
            f" AND volume_schema = '{selected_schema}'" if selected_schema != "All" and _vol_catalog_filter
            else f"WHERE volume_schema = '{selected_schema}'" if selected_schema != "All"
            else ""
        )
        df_volumes = run_query(conn,
            f"SELECT volume_catalog, volume_schema, volume_name, volume_type, "
            f"comment AS description, created AS created_at "
            f"FROM system.information_schema.volumes "
            f"{_vol_catalog_filter}{_vol_schema_filter} "
            f"ORDER BY volume_catalog, volume_schema, volume_name")
        vol_inv_count = len(df_volumes) if not df_volumes.empty else 0
        st.markdown(
            f'<div class="method-card" style="border-left:4px solid {CLR_PURPLE}">'
            f'<h4 style="color:{CLR_PURPLE} !important">\U0001f4e6 UC Volumes ({vol_inv_count})</h4>'
            f'<p>Unity Catalog managed and external volumes for unstructured data storage.</p></div>',
            unsafe_allow_html=True)
        if not df_volumes.empty:
            st.dataframe(df_volumes, use_container_width=True, height=250)
        else:
            st.info("No Volumes found for the current scope.")


# ===========================================================================
# TAB 2 — DETAILED ASSESSMENT
# ===========================================================================
with tab_detail:
    st.header("Detailed Assessment \u2014 Table Scores")

    df_scores = run_query(conn, f"SELECT * FROM {FULL_SCHEMA}.gold_table_scores {FILTER_WHERE} ORDER BY overall_score DESC")
    if df_scores.empty:
        st.warning("No table score data available for the current filter.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            rag_dist = df_scores["rag_status"].value_counts().reset_index()
            rag_dist.columns = ["Status", "Count"]
            fig = px.pie(rag_dist, values="Count", names="Status", color="Status",
                         color_discrete_map={"RED": CLR_RED, "AMBER": CLR_AMBER, "GREEN": CLR_GREEN},
                         title="Table Health Distribution")
            fig.update_layout(height=350, **CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.histogram(df_scores, x="overall_score", nbins=25,
                                color_discrete_sequence=[CLR_BLUE], title="Score Distribution")
            fig2.add_vline(x=40, line_dash="dash", line_color=CLR_RED, annotation_text="RED")
            fig2.add_vline(x=70, line_dash="dash", line_color=CLR_GREEN, annotation_text="GREEN")
            fig2.update_layout(height=350, **CHART_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

        df_cat = run_query(conn,
            f"SELECT * FROM {FULL_SCHEMA}.gold_category_scores "
            f"{'WHERE catalog_name != ' + chr(39) + 'ALL' + chr(39) + ' ' + CAT_FILTER_AND if CAT_FILTER_AND else ''} "
            f"ORDER BY catalog_name")
        if not df_cat.empty:
            st.subheader("Scores by Catalog & Category")
            fig3 = px.bar(df_cat, x="catalog_name", y="pct", color="category",
                          barmode="group", title="Category Scores by Catalog (%)",
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_layout(height=400, xaxis_tickangle=-45, **CHART_LAYOUT)
            st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Table Detail")
        filter_rag = st.multiselect("Filter by RAG Status", ["RED", "AMBER", "GREEN"],
                                    default=["RED", "AMBER", "GREEN"])
        df_filtered = df_scores[df_scores["rag_status"].isin(filter_rag)]
        st.dataframe(
            df_filtered.style.applymap(
                lambda v: "background-color: #fef2f2; color: #991b1b" if v == "RED" else
                          "background-color: #fffbeb; color: #92400e" if v == "AMBER" else
                          "background-color: #f0fdf4; color: #166534" if v == "GREEN" else "",
                subset=["rag_status"]),
            use_container_width=True, height=400)

        # --- UC Functions, ML Models & Volumes in Detailed Assessment ---
        if SHOW_FUNCTIONS or SHOW_VOLUMES:
            st.markdown("---")
            st.subheader("\U0001f9e9 UC Functions & Volumes Detail")

        if SHOW_FUNCTIONS:
            _fn_cat_f = f"WHERE routine_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _fn_sch_f = (
                f" AND routine_schema = '{selected_schema}'" if selected_schema != "All" and _fn_cat_f
                else f"WHERE routine_schema = '{selected_schema}'" if selected_schema != "All"
                else ""
            )
            df_fn_detail = run_query(conn,
                f"SELECT routine_catalog, routine_schema, routine_name, routine_type, "
                f"data_type AS return_type, created AS created_at, "
                f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 'Yes' ELSE 'No' END AS has_description "
                f"FROM system.information_schema.routines "
                f"{_fn_cat_f}{_fn_sch_f} "
                f"ORDER BY routine_catalog, routine_schema, routine_name")
            fn_detail_ct = len(df_fn_detail) if not df_fn_detail.empty else 0
            fn_documented = len(df_fn_detail[df_fn_detail['has_description'] == 'Yes']) if not df_fn_detail.empty else 0
            fn_doc_pct = round(fn_documented / fn_detail_ct * 100, 1) if fn_detail_ct > 0 else 0
            fc1, fc2, fc3 = st.columns(3)
            with fc1: metric_card("UC Functions", fn_detail_ct, CLR_PURPLE)
            with fc2: metric_card("Documented", fn_documented, CLR_GREEN)
            with fc3: metric_card("Doc Coverage", f"{fn_doc_pct}%", CLR_BLUE)
            if not df_fn_detail.empty:
                st.dataframe(df_fn_detail, use_container_width=True, height=250)
            else:
                st.info("No UC Functions found for the current scope.")

        # --- ML Models Detailed Assessment (standalone section) ---
        if SHOW_ML_MODELS:
            st.markdown("---")
            st.subheader("\U0001f9e0 ML Models Assessment")
            st.markdown(
                '<div class="tip-box">'
                'Registered ML models assessed for documentation, naming conventions, versioning, '
                'tagging, and production readiness. Data sourced from the assessment pipeline.</div>',
                unsafe_allow_html=True)

            _ml_cat_f = f"AND model_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _ml_sch_f = f"AND model_schema = '{selected_schema}'" if selected_schema != "All" else ""
            df_ml_detail = run_query(conn,
                f"SELECT model_catalog, model_schema, model_name, "
                f"has_description, naming_compliant, has_versions, has_tags, "
                f"is_production_ready, model_readiness_score, rag_status "
                f"FROM {FULL_SCHEMA}.gold_models_summary "
                f"WHERE 1=1 {_ml_cat_f} {_ml_sch_f} "
                f"ORDER BY model_readiness_score ASC")

            if not df_ml_detail.empty:
                ml_detail_ct = len(df_ml_detail)
                ml_documented = int(df_ml_detail['has_description'].sum())
                ml_naming = int(df_ml_detail['naming_compliant'].sum())
                ml_versioned = int(df_ml_detail['has_versions'].sum())
                ml_tagged = int(df_ml_detail['has_tags'].sum())
                ml_prod_ready = int(df_ml_detail['is_production_ready'].sum())
                ml_avg_score = round(float(df_ml_detail['model_readiness_score'].mean()), 1) if not df_ml_detail['model_readiness_score'].isna().all() else 0

                # Summary metrics row
                mm1, mm2, mm3, mm4, mm5, mm6 = st.columns(6)
                with mm1: metric_card("Total Models", ml_detail_ct, CLR_PURPLE)
                with mm2: metric_card("Documented", f"{ml_documented}/{ml_detail_ct}", CLR_GREEN if ml_documented == ml_detail_ct else CLR_AMBER)
                with mm3: metric_card("Name Compliant", f"{ml_naming}/{ml_detail_ct}", CLR_GREEN if ml_naming == ml_detail_ct else CLR_AMBER)
                with mm4: metric_card("Versioned", f"{ml_versioned}/{ml_detail_ct}", CLR_GREEN if ml_versioned == ml_detail_ct else CLR_AMBER)
                with mm5: metric_card("Tagged", f"{ml_tagged}/{ml_detail_ct}", CLR_GREEN if ml_tagged == ml_detail_ct else CLR_AMBER)
                with mm6: metric_card("Prod Ready", f"{ml_prod_ready}/{ml_detail_ct}", CLR_GREEN if ml_prod_ready == ml_detail_ct else CLR_AMBER)

                # Average score gauge
                avg_color = CLR_RED if ml_avg_score < 40 else CLR_AMBER if ml_avg_score < 70 else CLR_GREEN
                sc1, sc2 = st.columns([1, 2])
                with sc1:
                    fig_ml_gauge = go.Figure(go.Indicator(
                        mode="gauge+number", value=ml_avg_score,
                        title={"text": "Avg Model Readiness", "font": {"size": 14}},
                        number={"suffix": "%"},
                        gauge={"axis": {"range": [0, 100]},
                               "bar": {"color": avg_color},
                               "steps": [{"range": [0, 40], "color": "#fef2f2"},
                                         {"range": [40, 70], "color": "#fffbeb"},
                                         {"range": [70, 100], "color": "#f0fdf4"}]}))
                    fig_ml_gauge.update_layout(height=220, margin=dict(t=40, b=20, l=30, r=30))
                    st.plotly_chart(fig_ml_gauge, use_container_width=True)
                with sc2:
                    # RAG distribution chart
                    rag_counts = df_ml_detail['rag_status'].value_counts().reset_index()
                    rag_counts.columns = ['RAG Status', 'Count']
                    rag_color_map = {"RED": CLR_RED, "AMBER": CLR_AMBER, "GREEN": CLR_GREEN}
                    fig_ml_rag = px.bar(rag_counts, x="RAG Status", y="Count",
                                        color="RAG Status",
                                        color_discrete_map=rag_color_map,
                                        title="Model RAG Distribution")
                    fig_ml_rag.update_layout(height=220, showlegend=False, **CHART_LAYOUT)
                    st.plotly_chart(fig_ml_rag, use_container_width=True)

                # Detailed table
                st.markdown("**Model Details:**")
                display_df = df_ml_detail.copy()
                display_df.columns = ['Catalog', 'Schema', 'Model', 'Documented', 'Naming OK',
                                      'Versioned', 'Tagged', 'Prod Ready', 'Score', 'RAG']
                st.dataframe(display_df, use_container_width=True, height=300)

                # Models needing attention
                ml_at_risk = df_ml_detail[df_ml_detail['rag_status'].isin(['RED', 'AMBER'])]
                if not ml_at_risk.empty:
                    st.markdown(
                        f'<div class="rag-amber"><strong>\u26a0\ufe0f {len(ml_at_risk)} model(s) '
                        f'need improvement</strong> (RED/AMBER status)</div>',
                        unsafe_allow_html=True)
            else:
                st.info("No ML Models found for the current scope.")

        if SHOW_VOLUMES:
            _vol_cat_d = f"WHERE volume_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _vol_sch_d = (
                f" AND volume_schema = '{selected_schema}'" if selected_schema != "All" and _vol_cat_d
                else f"WHERE volume_schema = '{selected_schema}'" if selected_schema != "All"
                else ""
            )
            df_vol_detail = run_query(conn,
                f"SELECT volume_catalog, volume_schema, volume_name, volume_type, "
                f"comment AS description, created AS created_at, "
                f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 'Yes' ELSE 'No' END AS has_description, "
                f"CASE WHEN volume_type = 'MANAGED' THEN 'Yes' ELSE 'No' END AS is_managed "
                f"FROM system.information_schema.volumes "
                f"{_vol_cat_d}{_vol_sch_d} "
                f"ORDER BY volume_catalog, volume_schema, volume_name")
            vol_detail_ct = len(df_vol_detail) if not df_vol_detail.empty else 0
            vol_documented = len(df_vol_detail[df_vol_detail['has_description'] == 'Yes']) if not df_vol_detail.empty else 0
            vol_doc_pct = round(vol_documented / vol_detail_ct * 100, 1) if vol_detail_ct > 0 else 0
            vol_managed = len(df_vol_detail[df_vol_detail['is_managed'] == 'Yes']) if not df_vol_detail.empty else 0
            vc1, vc2, vc3, vc4 = st.columns(4)
            with vc1: metric_card("UC Volumes", vol_detail_ct, CLR_PURPLE)
            with vc2: metric_card("Documented", vol_documented, CLR_GREEN)
            with vc3: metric_card("Doc Coverage", f"{vol_doc_pct}%", CLR_BLUE)
            with vc4: metric_card("Managed", vol_managed, CLR_GREEN)
            if not df_vol_detail.empty:
                st.dataframe(df_vol_detail, use_container_width=True, height=250)
            else:
                st.info("No Volumes found for the current scope.")

# ===========================================================================
# TAB — COMPUTE (Clusters & SQL Warehouses)
# ===========================================================================
with tab_compute:
    st.header("Compute Assessment")
    st.markdown(
        '<div class="tip-box">Assessment of interactive clusters and SQL warehouses against '
        'UC best practices: autoscaling, auto-termination, security mode, DBR currency, '
        'serverless adoption, and tagging.</div>', unsafe_allow_html=True)

    comp_sub = st.radio("View", ["Clusters", "SQL Warehouses", "Compute Recommendations"],
                        horizontal=True, key="compute_sub_radio")

    if comp_sub == "Clusters" and SHOW_CLUSTERS:
        df_clusters = run_query(conn,
            f"SELECT * FROM {FULL_SCHEMA}.gold_clusters_summary ORDER BY cluster_readiness_score ASC")
        if df_clusters.empty:
            st.warning("No cluster assessment data. Run the pipeline first.")
        else:
            cl1, cl2, cl3, cl4 = st.columns(4)
            total_cl = len(df_clusters)
            red_cl = len(df_clusters[df_clusters['rag_status'] == 'RED']) if 'rag_status' in df_clusters.columns else 0
            amber_cl = len(df_clusters[df_clusters['rag_status'] == 'AMBER']) if 'rag_status' in df_clusters.columns else 0
            green_cl = len(df_clusters[df_clusters['rag_status'] == 'GREEN']) if 'rag_status' in df_clusters.columns else 0
            with cl1: metric_card("Total Clusters", total_cl, CLR_BLUE)
            with cl2: metric_card("RED", red_cl, CLR_RED)
            with cl3: metric_card("AMBER", amber_cl, CLR_AMBER)
            with cl4: metric_card("GREEN", green_cl, CLR_GREEN)

            c1, c2 = st.columns(2)
            with c1:
                if 'rag_status' in df_clusters.columns:
                    rag_dist = df_clusters['rag_status'].value_counts().reset_index()
                    rag_dist.columns = ['Status', 'Count']
                    fig = px.pie(rag_dist, values='Count', names='Status', color='Status',
                                 color_discrete_map={'RED': CLR_RED, 'AMBER': CLR_AMBER, 'GREEN': CLR_GREEN},
                                 title='Cluster Health Distribution')
                    fig.update_layout(height=350, **CHART_LAYOUT)
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                if 'cluster_readiness_score' in df_clusters.columns:
                    fig2 = px.histogram(df_clusters, x='cluster_readiness_score', nbins=20,
                                        color_discrete_sequence=[CLR_BLUE], title='Cluster Score Distribution')
                    fig2.add_vline(x=40, line_dash='dash', line_color=CLR_RED, annotation_text='RED')
                    fig2.add_vline(x=70, line_dash='dash', line_color=CLR_GREEN, annotation_text='GREEN')
                    fig2.update_layout(height=350, **CHART_LAYOUT)
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Cluster Details")
            st.dataframe(df_clusters, use_container_width=True, height=400)

    elif comp_sub == "Clusters" and not SHOW_CLUSTERS:
        st.info("Enable 'CLUSTER' in the Asset Category filter to view cluster data.")

    elif comp_sub == "SQL Warehouses" and SHOW_WAREHOUSES:
        df_wh = run_query(conn,
            f"SELECT * FROM {FULL_SCHEMA}.gold_warehouses_summary ORDER BY warehouse_readiness_score ASC")
        if df_wh.empty:
            st.warning("No warehouse assessment data. Run the pipeline first.")
        else:
            wh1, wh2, wh3, wh4 = st.columns(4)
            total_wh = len(df_wh)
            red_wh = len(df_wh[df_wh['rag_status'] == 'RED']) if 'rag_status' in df_wh.columns else 0
            amber_wh = len(df_wh[df_wh['rag_status'] == 'AMBER']) if 'rag_status' in df_wh.columns else 0
            green_wh = len(df_wh[df_wh['rag_status'] == 'GREEN']) if 'rag_status' in df_wh.columns else 0
            with wh1: metric_card("Total Warehouses", total_wh, CLR_BLUE)
            with wh2: metric_card("RED", red_wh, CLR_RED)
            with wh3: metric_card("AMBER", amber_wh, CLR_AMBER)
            with wh4: metric_card("GREEN", green_wh, CLR_GREEN)

            st.subheader("SQL Warehouse Details")
            st.dataframe(df_wh, use_container_width=True, height=400)

    elif comp_sub == "SQL Warehouses" and not SHOW_WAREHOUSES:
        st.info("Enable 'SQL_WAREHOUSE' in the Asset Category filter to view warehouse data.")

    elif comp_sub == "Compute Recommendations":
        df_comp_recs = run_query(conn,
            f"SELECT * FROM {FULL_SCHEMA}.gold_compute_recommendations ORDER BY severity, category")
        if df_comp_recs.empty:
            st.warning("No compute recommendations available.")
        else:
            cr1, cr2, cr3 = st.columns(3)
            with cr1: metric_card("HIGH", len(df_comp_recs[df_comp_recs['severity'] == 'HIGH']), CLR_RED)
            with cr2: metric_card("MEDIUM", len(df_comp_recs[df_comp_recs['severity'] == 'MEDIUM']), CLR_AMBER)
            with cr3: metric_card("LOW", len(df_comp_recs[df_comp_recs['severity'] == 'LOW']), CLR_BLUE)

            st.subheader("Top Compute Issues")
            if 'recommendation' in df_comp_recs.columns:
                top_issues = df_comp_recs.groupby('recommendation').size().reset_index(name='count').sort_values('count', ascending=False).head(10)
                fig2 = px.bar(top_issues, x='count', y='recommendation', orientation='h',
                              title='Top 10 Compute Issues', color_discrete_sequence=[CLR_RED])
                fig2.update_layout(height=400, yaxis={'categoryorder': 'total ascending'}, **CHART_LAYOUT)
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("All Compute Recommendations")
            st.dataframe(df_comp_recs, use_container_width=True, height=400)

# ===========================================================================
# TAB 3 — RECOMMENDATIONS
# ===========================================================================
with tab_recs:
    st.header("Recommendations")

    # Combine table recommendations with extended recommendations (functions/models/volumes)
    df_recs = run_query(conn,
        f"SELECT * FROM {FULL_SCHEMA}.gold_recommendations {FILTER_WHERE} ORDER BY severity, category")
    df_ext_recs = run_query(conn,
        f"SELECT * FROM {FULL_SCHEMA}.gold_extended_recommendations ORDER BY severity, category")
    # Merge both recommendation sets
    if not df_ext_recs.empty and not df_recs.empty:
        common_cols = list(set(df_recs.columns) & set(df_ext_recs.columns))
        df_all_recs = pd.concat([df_recs[common_cols], df_ext_recs[common_cols]], ignore_index=True)
    elif not df_ext_recs.empty:
        df_all_recs = df_ext_recs
    else:
        df_all_recs = df_recs

    if df_all_recs.empty:
        st.warning("No recommendations for the current filter.")
    else:
        r1, r2, r3, r4 = st.columns(4)
        with r1: metric_card("Total", f"{len(df_all_recs):,}", CLR_BLUE)
        with r2: metric_card("HIGH", len(df_all_recs[df_all_recs['severity'] == 'HIGH']), CLR_RED)
        with r3: metric_card("MEDIUM", len(df_all_recs[df_all_recs['severity'] == 'MEDIUM']), CLR_AMBER)
        with r4: metric_card("LOW", len(df_all_recs[df_all_recs['severity'] == 'LOW']), CLR_BLUE)

        df_abac_ui = run_query(conn, f"""
            SELECT
                inventory_status,
                COUNT(*) AS table_count,
                SUM(COALESCE(effective_policy_count, 0)) AS effective_policy_count,
                SUM(COALESCE(column_mask_policy_count, 0)) AS column_mask_policy_count,
                SUM(COALESCE(row_filter_policy_count, 0)) AS row_filter_policy_count
            FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
            GROUP BY inventory_status
            ORDER BY CASE inventory_status WHEN 'SCANNED' THEN 1 WHEN 'UNSUPPORTED' THEN 2 ELSE 3 END, inventory_status
        """)
        if not df_abac_ui.empty:
            st.subheader("ABAC Inventory Summary")
            st.dataframe(df_abac_ui, use_container_width=True, hide_index=True)

        df_abac_only = df_all_recs[df_all_recs['recommendation'].astype(str).str.contains('ABAC', case=False, na=False)]
        if not df_abac_only.empty:
            st.subheader("ABAC-Focused Recommendations")
            st.dataframe(df_abac_only[display_cols if 'display_cols' in locals() else ['table_catalog', 'table_schema', 'table_name', 'category', 'severity', 'recommendation', 'current_value', 'target_value']], use_container_width=True, height=220, hide_index=True)

        summary = df_all_recs.groupby(["category", "severity"]).size().reset_index(name="count")
        fig = px.bar(summary, x="category", y="count", color="severity",
                     color_discrete_map={"HIGH": CLR_RED, "MEDIUM": CLR_AMBER, "LOW": CLR_BLUE},
                     title="Recommendations by Category & Severity", barmode="group")
        fig.update_layout(height=400, xaxis_tickangle=-30, **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Actionable Recommendations")
        sev_filter = st.selectbox("Severity", ["All", "HIGH", "MEDIUM", "LOW"])
        cat_filter = st.selectbox("Category", ["All"] + sorted(df_all_recs["category"].unique().tolist()))
        df_rf = df_all_recs.copy()
        if sev_filter != "All":
            df_rf = df_rf[df_rf["severity"] == sev_filter]
        if cat_filter != "All":
            df_rf = df_rf[df_rf["category"] == cat_filter]
        display_cols = [c for c in ["table_catalog", "table_schema", "table_name", "category",
                            "severity", "recommendation", "current_value", "target_value"] if c in df_rf.columns]
        st.dataframe(df_rf[display_cols], use_container_width=True, height=400)

        # --- Function & ML Model Recommendations ---
        if SHOW_FUNCTIONS or SHOW_ML_MODELS:
            st.markdown("---")
            st.subheader("\U0001f9e9 UC Functions & ML Models Recommendations")

        if SHOW_FUNCTIONS:
            _fn_cat_r = f"WHERE routine_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _fn_sch_r = (
                f" AND routine_schema = '{selected_schema}'" if selected_schema != "All" and _fn_cat_r
                else f"WHERE routine_schema = '{selected_schema}'" if selected_schema != "All"
                else ""
            )
            df_fn_recs = run_query(conn,
                f"SELECT routine_catalog, routine_schema, routine_name, routine_type, "
                f"data_type AS return_type, comment "
                f"FROM system.information_schema.routines "
                f"{_fn_cat_r}{_fn_sch_r} "
                f"ORDER BY routine_catalog, routine_schema, routine_name")
            if not df_fn_recs.empty:
                fn_no_doc = df_fn_recs[df_fn_recs['comment'].isna() | (df_fn_recs['comment'] == '')]
                if not fn_no_doc.empty:
                    st.markdown(
                        f'<div class="rag-amber"><strong>\u26a0\ufe0f {len(fn_no_doc)} UC Function(s) '
                        f'missing documentation.</strong> Add COMMENT to improve discoverability.</div>',
                        unsafe_allow_html=True)
                    fn_rec_data = []
                    for _, fr in fn_no_doc.iterrows():
                        fn_rec_data.append({
                            "catalog": fr['routine_catalog'],
                            "schema": fr['routine_schema'],
                            "function_name": fr['routine_name'],
                            "recommendation": "Add function description via COMMENT ON FUNCTION",
                            "severity": "MEDIUM",
                            "category": "Metadata Readiness",
                        })
                    st.dataframe(pd.DataFrame(fn_rec_data), use_container_width=True, height=200)
                else:
                    st.markdown(
                        '<div class="rag-green"><strong>\u2705 All UC Functions are documented!</strong></div>',
                        unsafe_allow_html=True)
            else:
                st.info("No UC Functions found for the current scope.")

        if SHOW_ML_MODELS:
            _ml_cat_r = f"AND model_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _ml_sch_r = f"AND model_schema = '{selected_schema}'" if selected_schema != "All" else ""
            df_ml_recs = run_query(conn,
                f"SELECT model_catalog, model_schema, model_name, "
                f"has_description, naming_compliant, has_versions, model_readiness_score "
                f"FROM {FULL_SCHEMA}.gold_models_summary "
                f"WHERE 1=1 {_ml_cat_r} {_ml_sch_r} "
                f"ORDER BY model_catalog, model_schema, model_name")
            if not df_ml_recs.empty:
                ml_no_doc = df_ml_recs[df_ml_recs['has_description'] == 0]
                if not ml_no_doc.empty:
                    st.markdown(
                        f'<div class="rag-amber"><strong>\u26a0\ufe0f {len(ml_no_doc)} ML Model(s) '
                        f'missing documentation.</strong> Add COMMENT to improve cataloging.</div>',
                        unsafe_allow_html=True)
                    ml_rec_data = []
                    for _, mr in ml_no_doc.iterrows():
                        ml_rec_data.append({
                            "catalog": mr['model_catalog'],
                            "schema": mr['model_schema'],
                            "model_name": mr['model_name'],
                            "recommendation": "Add model description via COMMENT ON TABLE",
                            "severity": "MEDIUM",
                            "category": "Metadata Readiness",
                        })
                    st.dataframe(pd.DataFrame(ml_rec_data), use_container_width=True, height=200)
                else:
                    st.markdown(
                        '<div class="rag-green"><strong>\u2705 All ML Models are documented!</strong></div>',
                        unsafe_allow_html=True)
            else:
                st.info("No ML Models found for the current scope.")

# ===========================================================================
# TAB 4 — FINOPS INSIGHTS  (workspace-level — not filtered)
# ===========================================================================
with tab_finops:
    st.header("\U0001f4b0 FinOps Insights")
    if IS_FILTERED:
        st.markdown('<div class="warn-box">FinOps data is workspace-level and not affected by catalog/schema filters.</div>',
                    unsafe_allow_html=True)

    # === KPI HERO ROW ===
    df_billing_totals = run_query(conn,
        f"SELECT ROUND(SUM(usage_quantity), 1) AS total_dbus, "
        f"COUNT(DISTINCT usage_date) AS days_covered, "
        f"MIN(usage_date) AS period_start, MAX(usage_date) AS period_end, "
        f"COUNT(DISTINCT identity_metadata.created_by) AS unique_users, "
        f"ROUND(SUM(usage_quantity) / NULLIF(COUNT(DISTINCT usage_date), 0), 1) AS daily_avg "
        f"FROM {FULL_SCHEMA}.bronze_billing_usage WHERE usage_type = 'COMPUTE_TIME'")

    if not df_billing_totals.empty:
        bt = df_billing_totals.iloc[0]
        _total_dbus = float(bt.get('total_dbus') or 0)
        _days = int(bt.get('days_covered') or 0)
        _daily_avg = float(bt.get('daily_avg') or 0)
        _users = int(bt.get('unique_users') or 0)
        _monthly_est = _daily_avg * 30
        _period = f"{bt.get('period_start', '')} to {bt.get('period_end', '')}"

        kf1, kf2, kf3, kf4, kf5 = st.columns(5)
        with kf1: metric_card("Total DBUs", f"{_total_dbus:,.0f}", CLR_BLUE)
        with kf2: metric_card("Daily Average", f"{_daily_avg:,.0f}", CLR_PURPLE)
        with kf3: metric_card("30-Day Forecast", f"{_monthly_est:,.0f}", CLR_AMBER)
        with kf4: metric_card("Active Users", f"{_users}", CLR_GREEN)
        with kf5: metric_card("Period (Days)", f"{_days}", CLR_BLUE)

        st.caption(f"Billing period: {_period}")

    st.markdown("---")

    # === SECTION 1: Daily Cost Trend ===
    st.subheader("\U0001f4c8 Daily DBU Consumption Trend")
    df_daily = run_query(conn,
        f"SELECT usage_date, "
        f"ROUND(SUM(CASE WHEN sku_name LIKE '%SERVERLESS%' THEN usage_quantity ELSE 0 END), 1) AS serverless_dbus, "
        f"ROUND(SUM(CASE WHEN sku_name NOT LIKE '%SERVERLESS%' THEN usage_quantity ELSE 0 END), 1) AS classic_dbus, "
        f"ROUND(SUM(usage_quantity), 1) AS total_dbus "
        f"FROM {FULL_SCHEMA}.bronze_billing_usage WHERE usage_type = 'COMPUTE_TIME' "
        f"GROUP BY usage_date ORDER BY usage_date")

    if not df_daily.empty:
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_daily['usage_date'], y=df_daily['serverless_dbus'],
            mode='lines+markers', name='Serverless', line=dict(color=CLR_BLUE, width=2),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.1)'))
        fig_trend.add_trace(go.Scatter(x=df_daily['usage_date'], y=df_daily['classic_dbus'],
            mode='lines+markers', name='Classic', line=dict(color=CLR_PURPLE, width=2),
            fill='tozeroy', fillcolor='rgba(139,92,246,0.1)'))
        # Add 7-day moving average
        if len(df_daily) >= 7:
            df_daily['ma_7d'] = df_daily['total_dbus'].rolling(window=7).mean()
            fig_trend.add_trace(go.Scatter(x=df_daily['usage_date'], y=df_daily['ma_7d'],
                mode='lines', name='7-Day Avg', line=dict(color=CLR_RED, width=2, dash='dash')))
        fig_trend.update_layout(height=320, title="Daily DBU Burn — Serverless vs Classic",
            xaxis_title="", yaxis_title="DBUs", legend=dict(orientation="h", y=1.12), **CHART_LAYOUT)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No daily billing data available.")

    st.markdown("---")

    # === SECTION 2: Cost Breakdown (Product + SKU side by side) ===
    st.subheader("\U0001f4ca Cost Breakdown")
    cb1, cb2 = st.columns(2)

    with cb1:
        df_product = run_query(conn, f"SELECT * FROM {FULL_SCHEMA}.gold_cost_by_product ORDER BY total_dbus DESC")
        if not df_product.empty:
            fig_prod = px.bar(df_product.head(10), x="total_dbus", y="billing_origin_product",
                orientation='h', title="DBUs by Product",
                color_discrete_sequence=[CLR_BLUE])
            fig_prod.update_layout(height=350, yaxis={'categoryorder': 'total ascending'},
                xaxis_title="DBUs", yaxis_title="", **CHART_LAYOUT)
            st.plotly_chart(fig_prod, use_container_width=True)

    with cb2:
        # Serverless vs Classic pie
        df_svc = run_query(conn,
            f"SELECT CASE WHEN sku_name LIKE '%SERVERLESS%' THEN 'Serverless' ELSE 'Classic/Pro' END AS compute_type, "
            f"ROUND(SUM(usage_quantity), 1) AS total_dbus "
            f"FROM {FULL_SCHEMA}.bronze_billing_usage WHERE usage_type = 'COMPUTE_TIME' "
            f"GROUP BY CASE WHEN sku_name LIKE '%SERVERLESS%' THEN 'Serverless' ELSE 'Classic/Pro' END")
        if not df_svc.empty:
            fig_svc = px.pie(df_svc, values='total_dbus', names='compute_type',
                title="Serverless vs Classic Split",
                color_discrete_map={'Serverless': CLR_BLUE, 'Classic/Pro': CLR_PURPLE},
                hole=0.4)
            fig_svc.update_traces(textposition='inside', textinfo='percent+value')
            fig_svc.update_layout(height=350, **CHART_LAYOUT)
            st.plotly_chart(fig_svc, use_container_width=True)

    st.markdown("---")

    # === SECTION 3: Cost by User ===
    st.subheader("\U0001f465 Cost by User / Identity")
    df_by_user = run_query(conn,
        f"SELECT COALESCE(identity_metadata.created_by, 'Unknown') AS user_identity, "
        f"ROUND(SUM(usage_quantity), 1) AS total_dbus, "
        f"COUNT(*) AS usage_records, "
        f"COUNT(DISTINCT billing_origin_product) AS products_used "
        f"FROM {FULL_SCHEMA}.bronze_billing_usage WHERE usage_type = 'COMPUTE_TIME' "
        f"GROUP BY COALESCE(identity_metadata.created_by, 'Unknown') "
        f"ORDER BY total_dbus DESC LIMIT 15")

    if not df_by_user.empty:
        u1, u2 = st.columns([2, 1])
        with u1:
            fig_user = px.bar(df_by_user, x='total_dbus', y='user_identity',
                orientation='h', title="Top Users by DBU Consumption",
                color='total_dbus', color_continuous_scale=['#93c5fd', '#1d4ed8'])
            fig_user.update_layout(height=380, yaxis={'categoryorder': 'total ascending'},
                xaxis_title="DBUs", yaxis_title="", coloraxis_showscale=False, **CHART_LAYOUT)
            st.plotly_chart(fig_user, use_container_width=True)
        with u2:
            st.markdown(
                '<div style="background:white;border-radius:12px;padding:16px;'
                'box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-top:30px">'
                '<p style="font-weight:600;color:#1e293b;margin:0 0 8px">User Breakdown</p></div>',
                unsafe_allow_html=True)
            st.dataframe(df_by_user[['user_identity', 'total_dbus', 'products_used']].rename(
                columns={'user_identity': 'User', 'total_dbus': 'DBUs', 'products_used': 'Products'}),
                use_container_width=True, height=300, hide_index=True)
    else:
        st.info("No user-level billing data available.")

    st.markdown("---")

    # === SECTION 4: Usage Type Heatmap (Day of Week × Usage Type) ===
    st.subheader("\U0001f5d3\ufe0f Usage Patterns — Day of Week")
    df_dow = run_query(conn,
        f"SELECT DAYOFWEEK(usage_date) AS dow, billing_origin_product, "
        f"ROUND(SUM(usage_quantity), 1) AS total_dbus "
        f"FROM {FULL_SCHEMA}.bronze_billing_usage WHERE usage_type = 'COMPUTE_TIME' "
        f"GROUP BY DAYOFWEEK(usage_date), billing_origin_product "
        f"ORDER BY dow")

    if not df_dow.empty:
        # Map day numbers to names
        day_map = {1: 'Sun', 2: 'Mon', 3: 'Tue', 4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'}
        df_dow['day_name'] = df_dow['dow'].map(day_map)
        pivot = df_dow.pivot_table(index='billing_origin_product', columns='day_name',
            values='total_dbus', fill_value=0)
        # Reorder columns
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        pivot = pivot[[d for d in day_order if d in pivot.columns]]

        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
            colorscale='Blues', texttemplate='%{z:.0f}', textfont={"size": 10}))
        fig_heat.update_layout(height=320, title="DBU Heatmap — Product × Day of Week",
            xaxis_title="", yaxis_title="", **CHART_LAYOUT)
        st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("---")

    # === SECTION 5: Top SKUs Table ===
    st.subheader("\U0001f3af Top SKUs by DBU Usage")
    df_sku_detail = run_query(conn,
        f"SELECT sku_name, ROUND(SUM(total_dbus), 1) AS total_dbus, "
        f"SUM(usage_records) AS records, MIN(usage_date) AS first_seen, MAX(usage_date) AS last_seen "
        f"FROM {FULL_SCHEMA}.gold_cost_by_sku GROUP BY sku_name ORDER BY total_dbus DESC LIMIT 15")
    if not df_sku_detail.empty:
        # Classify as serverless or classic
        df_sku_detail['type'] = df_sku_detail['sku_name'].apply(
            lambda x: '\u2601\ufe0f Serverless' if 'SERVERLESS' in str(x) else '\U0001f5a5\ufe0f Classic')
        st.dataframe(df_sku_detail[['sku_name', 'type', 'total_dbus', 'records', 'first_seen', 'last_seen']].rename(
            columns={'sku_name': 'SKU', 'type': 'Type', 'total_dbus': 'Total DBUs',
                     'records': 'Records', 'first_seen': 'First Seen', 'last_seen': 'Last Seen'}),
            use_container_width=True, height=400, hide_index=True)

    st.markdown("---")

    # === SECTION 6: Top Expensive Queries ===
    st.subheader("\U0001f525 Top 10 Most Expensive Queries")
    df_exp = run_query(conn,
        f"SELECT executed_by, statement_type, "
        f"ROUND(total_duration_ms / 1000.0, 1) AS duration_sec, "
        f"ROUND(COALESCE(read_bytes, 0) / 1048576.0, 1) AS read_mb, "
        f"COALESCE(read_rows, 0) AS read_rows, "
        f"execution_status "
        f"FROM {FULL_SCHEMA}.gold_expensive_queries "
        f"WHERE total_duration_ms IS NOT NULL "
        f"ORDER BY total_duration_ms DESC LIMIT 10")
    if not df_exp.empty:
        st.dataframe(df_exp.rename(columns={
            'executed_by': 'User', 'statement_type': 'Type',
            'duration_sec': 'Duration (s)', 'read_mb': 'Read (MB)',
            'read_rows': 'Rows Read', 'execution_status': 'Status'}),
            use_container_width=True, height=350, hide_index=True)
    else:
        st.info("No expensive query data available.")

    st.markdown("---")

    # === SECTION 7: Monthly Forecast & Budget Insight ===
    st.subheader("\U0001f4b8 Monthly Burn Rate & Forecast")
    if not df_daily.empty and len(df_daily) >= 7:
        _last7 = df_daily['total_dbus'].tail(7).mean()
        _last14 = df_daily['total_dbus'].tail(14).mean() if len(df_daily) >= 14 else _last7
        _trend = "\u2197\ufe0f Increasing" if _last7 > _last14 * 1.1 else "\u2198\ufe0f Decreasing" if _last7 < _last14 * 0.9 else "\u2194\ufe0f Stable"
        _30d_forecast = _last7 * 30

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.metric("Last 7-Day Avg (Daily)", f"{_last7:,.0f} DBUs")
        with fc2:
            st.metric("30-Day Projection", f"{_30d_forecast:,.0f} DBUs")
        with fc3:
            st.metric("Trend", _trend)

        st.markdown(
            f'<div class="tip-box">'
            f'<strong>Budget Insight:</strong> Based on the last 7 days, projected monthly consumption is '
            f'<strong>{_30d_forecast:,.0f} DBUs</strong>. '
            f'{"Consider scaling down underutilized resources." if _30d_forecast > _total_dbus else "Consumption is within the observed period total."}'
            f'</div>', unsafe_allow_html=True)

# ===========================================================================
# TAB 5 — PERFORMANCE  (workspace-level — not filtered)
# ===========================================================================
with tab_perf:
    st.header("\u26a1 Performance Analytics")
    if IS_FILTERED:
        st.markdown('<div class="warn-box">Performance data is aggregated at workspace level and not affected by catalog/schema filters.</div>',
                    unsafe_allow_html=True)

    # === KPI HERO ROW ===
    df_perf_kpi = run_query(conn,
        f"SELECT COUNT(*) AS total_queries, "
        f"ROUND(AVG(total_duration_ms), 0) AS avg_duration_ms, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.5), 0) AS p50_ms, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.95), 0) AS p95_ms, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.99), 0) AS p99_ms, "
        f"ROUND(AVG(waiting_for_compute_duration_ms), 0) AS avg_queue_ms, "
        f"ROUND(AVG(execution_duration_ms), 0) AS avg_exec_ms, "
        f"SUM(CASE WHEN execution_status = 'FAILED' THEN 1 ELSE 0 END) AS failed_queries, "
        f"SUM(CASE WHEN spilled_local_bytes > 0 THEN 1 ELSE 0 END) AS spill_queries, "
        f"COUNT(DISTINCT executed_by) AS unique_users "
        f"FROM {FULL_SCHEMA}.bronze_query_history")

    if not df_perf_kpi.empty:
        pk = df_perf_kpi.iloc[0]
        _total_q = int(pk.get('total_queries') or 0)
        _p50 = float(pk.get('p50_ms') or 0)
        _p95 = float(pk.get('p95_ms') or 0)
        _p99 = float(pk.get('p99_ms') or 0)
        _avg_queue = float(pk.get('avg_queue_ms') or 0)
        _failed = int(pk.get('failed_queries') or 0)
        _spills = int(pk.get('spill_queries') or 0)
        _fail_pct = round(_failed * 100.0 / max(_total_q, 1), 1)

        pk1, pk2, pk3, pk4, pk5, pk6 = st.columns(6)
        with pk1: metric_card("Total Queries", f"{_total_q:,}", CLR_BLUE)
        with pk2: metric_card("P50 Latency", f"{_p50/1000:.1f}s", CLR_GREEN)
        with pk3: metric_card("P95 Latency", f"{_p95/1000:.1f}s", CLR_AMBER)
        with pk4: metric_card("P99 Latency", f"{_p99/1000:.1f}s", CLR_RED)
        with pk5: metric_card("Avg Queue Time", f"{_avg_queue/1000:.1f}s", CLR_PURPLE)
        with pk6: metric_card("Failed Queries", f"{_failed} ({_fail_pct}%)", CLR_RED)

    st.markdown("---")

    # === SECTION 1: Latency Distribution ===
    st.subheader("\U0001f4ca Latency Distribution (P50 / P95 / P99)")
    df_lat_dist = run_query(conn,
        f"SELECT statement_type, COUNT(*) AS query_count, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.5) / 1000.0, 2) AS p50_sec, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.95) / 1000.0, 2) AS p95_sec, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.99) / 1000.0, 2) AS p99_sec "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"WHERE statement_type IS NOT NULL "
        f"GROUP BY statement_type HAVING COUNT(*) >= 5 "
        f"ORDER BY query_count DESC LIMIT 10")

    if not df_lat_dist.empty:
        fig_lat = go.Figure()
        fig_lat.add_trace(go.Bar(x=df_lat_dist['statement_type'], y=df_lat_dist['p50_sec'],
            name='P50', marker_color=CLR_GREEN))
        fig_lat.add_trace(go.Bar(x=df_lat_dist['statement_type'], y=df_lat_dist['p95_sec'],
            name='P95', marker_color=CLR_AMBER))
        fig_lat.add_trace(go.Bar(x=df_lat_dist['statement_type'], y=df_lat_dist['p99_sec'],
            name='P99', marker_color=CLR_RED))
        fig_lat.update_layout(height=350, barmode='group', title="Latency Percentiles by Statement Type",
            xaxis_title="", yaxis_title="Seconds", legend=dict(orientation="h", y=1.1), **CHART_LAYOUT)
        st.plotly_chart(fig_lat, use_container_width=True)

    st.markdown("---")

    # === SECTION 2: Queue Time vs Execution Time ===
    st.subheader("\u23f3 Queue Time vs Execution Time")
    df_queue = run_query(conn,
        f"SELECT statement_type, "
        f"ROUND(AVG(waiting_for_compute_duration_ms) / 1000.0, 2) AS avg_queue_sec, "
        f"ROUND(AVG(waiting_at_capacity_duration_ms) / 1000.0, 2) AS avg_capacity_wait_sec, "
        f"ROUND(AVG(execution_duration_ms) / 1000.0, 2) AS avg_exec_sec, "
        f"ROUND(AVG(compilation_duration_ms) / 1000.0, 2) AS avg_compile_sec, "
        f"COUNT(*) AS cnt "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"WHERE statement_type IS NOT NULL "
        f"GROUP BY statement_type HAVING COUNT(*) >= 5 "
        f"ORDER BY cnt DESC LIMIT 8")

    if not df_queue.empty:
        fig_q = go.Figure()
        fig_q.add_trace(go.Bar(x=df_queue['statement_type'], y=df_queue['avg_queue_sec'],
            name='Queue (Compute)', marker_color='#f87171'))
        fig_q.add_trace(go.Bar(x=df_queue['statement_type'], y=df_queue['avg_capacity_wait_sec'],
            name='Queue (Capacity)', marker_color='#fb923c'))
        fig_q.add_trace(go.Bar(x=df_queue['statement_type'], y=df_queue['avg_compile_sec'],
            name='Compilation', marker_color='#a78bfa'))
        fig_q.add_trace(go.Bar(x=df_queue['statement_type'], y=df_queue['avg_exec_sec'],
            name='Execution', marker_color=CLR_BLUE))
        fig_q.update_layout(height=350, barmode='stack', title="Time Breakdown by Query Phase",
            xaxis_title="", yaxis_title="Seconds (avg)", legend=dict(orientation="h", y=1.12), **CHART_LAYOUT)
        st.plotly_chart(fig_q, use_container_width=True)

        # Capacity insight
        _total_wait = df_queue['avg_queue_sec'].sum() + df_queue['avg_capacity_wait_sec'].sum()
        _total_exec = df_queue['avg_exec_sec'].sum()
        if _total_wait > _total_exec * 0.3:
            st.markdown(
                f'<div class="warn-box"><strong>\u26a0\ufe0f Capacity Insight:</strong> '
                f'Average queue time is significant ({_total_wait:.1f}s). '
                f'Consider scaling up your warehouse or enabling auto-scaling.</div>',
                unsafe_allow_html=True)

    st.markdown("---")

    # === SECTION 3: Peak Hour Heatmap ===
    st.subheader("\U0001f5d3\ufe0f Peak Hour Heatmap")
    df_peak = run_query(conn,
        f"SELECT DAYOFWEEK(start_time) AS dow, HOUR(start_time) AS hour_of_day, "
        f"COUNT(*) AS query_count "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"GROUP BY DAYOFWEEK(start_time), HOUR(start_time)")

    if not df_peak.empty:
        day_map = {1: 'Sun', 2: 'Mon', 3: 'Tue', 4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'}
        df_peak['day_name'] = df_peak['dow'].map(day_map)
        pivot_peak = df_peak.pivot_table(index='day_name', columns='hour_of_day',
            values='query_count', fill_value=0)
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        pivot_peak = pivot_peak.reindex([d for d in day_order if d in pivot_peak.index])

        fig_peak = go.Figure(data=go.Heatmap(
            z=pivot_peak.values, x=[f"{h:02d}:00" for h in pivot_peak.columns],
            y=pivot_peak.index.tolist(), colorscale='YlOrRd',
            texttemplate='%{z}', textfont={"size": 9}))
        fig_peak.update_layout(height=280, title="Query Volume — Day of Week x Hour",
            xaxis_title="Hour (UTC)", yaxis_title="", **CHART_LAYOUT)
        st.plotly_chart(fig_peak, use_container_width=True)

    st.markdown("---")

    # === SECTION 4: Query Duration Trend ===
    st.subheader("\U0001f4c8 Query Duration Trend (Daily)")
    df_trend = run_query(conn,
        f"SELECT DATE(start_time) AS query_date, "
        f"ROUND(AVG(total_duration_ms) / 1000.0, 2) AS avg_sec, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.95) / 1000.0, 2) AS p95_sec, "
        f"COUNT(*) AS query_count "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"GROUP BY DATE(start_time) ORDER BY query_date")

    if not df_trend.empty and len(df_trend) > 3:
        fig_tr = go.Figure()
        fig_tr.add_trace(go.Scatter(x=df_trend['query_date'], y=df_trend['avg_sec'],
            mode='lines+markers', name='Avg Duration', line=dict(color=CLR_BLUE, width=2)))
        fig_tr.add_trace(go.Scatter(x=df_trend['query_date'], y=df_trend['p95_sec'],
            mode='lines', name='P95', line=dict(color=CLR_RED, width=2, dash='dash')))
        fig_tr.add_trace(go.Bar(x=df_trend['query_date'], y=df_trend['query_count'],
            name='Query Count', marker_color='rgba(59,130,246,0.15)', yaxis='y2'))
        fig_tr.update_layout(
            height=350, title="Query Latency Trend Over Time",
            yaxis=dict(title="Seconds", side='left'),
            yaxis2=dict(title="Count", side='right', overlaying='y', showgrid=False),
            legend=dict(orientation="h", y=1.12), **CHART_LAYOUT)
        st.plotly_chart(fig_tr, use_container_width=True)

        # Trend detection
        if len(df_trend) >= 14:
            _recent = df_trend['avg_sec'].tail(7).mean()
            _prior = df_trend['avg_sec'].iloc[-14:-7].mean()
            if _recent > _prior * 1.2:
                st.markdown('<div class="warn-box"><strong>\u26a0\ufe0f Regression Detected:</strong> Average latency increased >20% in the last 7 days vs prior week. Investigate recent schema changes or data growth.</div>', unsafe_allow_html=True)
            elif _recent < _prior * 0.8:
                st.markdown('<div class="recommend-box"><strong>\u2705 Improvement Detected:</strong> Average latency decreased >20% in the last 7 days. Good performance trend!</div>', unsafe_allow_html=True)

    st.markdown("---")

    # === SECTION 5: Failed Queries Analysis ===
    st.subheader("\u274c Failed Query Patterns")
    df_failed = run_query(conn,
        f"SELECT executed_by, statement_type, "
        f"SUBSTRING(error_message, 1, 120) AS error_snippet, "
        f"COUNT(*) AS fail_count "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"WHERE execution_status = 'FAILED' AND error_message IS NOT NULL AND error_message != '' "
        f"GROUP BY executed_by, statement_type, SUBSTRING(error_message, 1, 120) "
        f"ORDER BY fail_count DESC LIMIT 10")

    if not df_failed.empty:
        f1, f2 = st.columns([1, 2])
        with f1:
            # Failures by user
            df_fail_user = run_query(conn,
                f"SELECT executed_by, COUNT(*) AS failures "
                f"FROM {FULL_SCHEMA}.bronze_query_history WHERE execution_status = 'FAILED' "
                f"GROUP BY executed_by ORDER BY failures DESC LIMIT 8")
            if not df_fail_user.empty:
                fig_fu = px.bar(df_fail_user, x='failures', y='executed_by', orientation='h',
                    title="Failures by User", color_discrete_sequence=[CLR_RED])
                fig_fu.update_layout(height=300, yaxis={'categoryorder': 'total ascending'},
                    xaxis_title="", yaxis_title="", **CHART_LAYOUT)
                st.plotly_chart(fig_fu, use_container_width=True)
        with f2:
            st.markdown("**Top Error Patterns:**")
            st.dataframe(df_failed[['statement_type', 'error_snippet', 'fail_count']].rename(
                columns={'statement_type': 'Type', 'error_snippet': 'Error', 'fail_count': 'Count'}),
                use_container_width=True, height=280, hide_index=True)
    else:
        st.success("No failed queries with error messages found.")

    st.markdown("---")

    # === SECTION 6: Spill-to-Disk Detection ===
    st.subheader("\U0001f4be Spill-to-Disk Detection")
    df_spill = run_query(conn,
        f"SELECT executed_by, statement_type, "
        f"ROUND(total_duration_ms / 1000.0, 1) AS duration_sec, "
        f"ROUND(spilled_local_bytes / 1048576.0, 1) AS spill_mb, "
        f"ROUND(read_bytes / 1048576.0, 1) AS read_mb "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"WHERE spilled_local_bytes > 0 "
        f"ORDER BY spilled_local_bytes DESC LIMIT 10")

    if not df_spill.empty:
        st.markdown(
            f'<div class="warn-box"><strong>{len(df_spill)} queries spilled to disk.</strong> '
            f'This indicates memory pressure. Consider increasing warehouse size or optimizing queries.</div>',
            unsafe_allow_html=True)
        st.dataframe(df_spill.rename(columns={
            'executed_by': 'User', 'statement_type': 'Type', 'duration_sec': 'Duration (s)',
            'spill_mb': 'Spill (MB)', 'read_mb': 'Read (MB)'}),
            use_container_width=True, height=300, hide_index=True)
    else:
        st.success("\u2705 No spill-to-disk detected! Memory utilization is healthy.")

    st.markdown("---")

    # === SECTION 7: Most Scanned Tables (Hot Tables) ===
    st.subheader("\U0001f525 Hot Tables (Most Queried)")
    df_hot = run_query(conn,
        f"SELECT target_table_catalog AS table_catalog, target_table_schema AS table_schema, target_table_name AS table_name, "
        f"COUNT(*) AS times_queried "
        f"FROM {FULL_SCHEMA}.bronze_table_lineage "
        f"WHERE target_table_name IS NOT NULL "
        f"GROUP BY target_table_catalog, target_table_schema, target_table_name "
        f"ORDER BY times_queried DESC LIMIT 10")

    if not df_hot.empty:
        h1, h2 = st.columns([2, 1])
        with h1:
            df_hot['full_name'] = df_hot['table_catalog'] + '.' + df_hot['table_schema'] + '.' + df_hot['table_name']
            fig_hot = px.bar(df_hot, x='times_queried', y='full_name', orientation='h',
                title="Top 10 Most Referenced Tables (Lineage)",
                color='times_queried', color_continuous_scale=['#bfdbfe', '#1d4ed8'])
            fig_hot.update_layout(height=350, yaxis={'categoryorder': 'total ascending'},
                xaxis_title="References", yaxis_title="", coloraxis_showscale=False, **CHART_LAYOUT)
            st.plotly_chart(fig_hot, use_container_width=True)
        with h2:
            st.markdown(
                '<div style="background:white;border-radius:12px;padding:16px;'
                'box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-top:30px">'
                '<p style="font-weight:600;color:#1e293b;margin:0 0 8px">\U0001f4a1 Optimization Tips</p>'
                '<ul style="color:#475569;font-size:13px;padding-left:16px">'
                '<li>Consider caching frequently accessed tables</li>'
                '<li>Pre-aggregate hot tables for dashboards</li>'
                '<li>Add Z-ORDER on filter columns</li>'
                '<li>Enable predictive optimization</li>'
                '</ul></div>', unsafe_allow_html=True)
    else:
        st.info("No table lineage data available for hot table analysis.")

    st.markdown("---")

    # === SECTION 8: Warehouse Sizing Recommendation ===
    st.subheader("\U0001f3ed Warehouse Sizing Insight")
    df_wh_perf = run_query(conn,
        f"SELECT compute.warehouse_id AS warehouse_id, "
        f"COUNT(*) AS total_queries, "
        f"ROUND(AVG(total_duration_ms) / 1000.0, 1) AS avg_sec, "
        f"ROUND(AVG(waiting_for_compute_duration_ms) / 1000.0, 2) AS avg_queue_sec, "
        f"ROUND(AVG(waiting_at_capacity_duration_ms) / 1000.0, 2) AS avg_capacity_sec, "
        f"ROUND(PERCENTILE(total_duration_ms, 0.95) / 1000.0, 1) AS p95_sec, "
        f"SUM(CASE WHEN waiting_at_capacity_duration_ms > 5000 THEN 1 ELSE 0 END) AS throttled_queries "
        f"FROM {FULL_SCHEMA}.bronze_query_history "
        f"WHERE compute.warehouse_id IS NOT NULL "
        f"GROUP BY compute.warehouse_id ORDER BY total_queries DESC")

    if not df_wh_perf.empty:
        for _, wh in df_wh_perf.iterrows():
            _wh_id = wh['warehouse_id']
            _q_count = int(wh['total_queries'])
            _avg_q = float(wh.get('avg_queue_sec') or 0)
            _throttled = int(wh.get('throttled_queries') or 0)
            _p95 = float(wh.get('p95_sec') or 0)

            if _avg_q > 2 or _throttled > _q_count * 0.1:
                _rec = "\U0001f534 **Scale Up** — High queue/throttle times suggest undersized warehouse"
                _color = CLR_RED
            elif _avg_q < 0.1 and _p95 < 5:
                _rec = "\U0001f7e2 **Right-Sized** — Low latency and minimal queuing"
                _color = CLR_GREEN
            else:
                _rec = "\U0001f7e1 **Monitor** — Moderate performance, consider auto-scaling"
                _color = CLR_AMBER

            st.markdown(
                f'<div style="background:white;border-radius:10px;padding:14px 18px;margin:6px 0;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.06);border-left:4px solid {_color}">'
                f'<strong>Warehouse:</strong> <code>{_wh_id}</code> &nbsp;|&nbsp; '
                f'<strong>Queries:</strong> {_q_count:,} &nbsp;|&nbsp; '
                f'<strong>P95:</strong> {_p95:.1f}s &nbsp;|&nbsp; '
                f'<strong>Avg Queue:</strong> {_avg_q:.2f}s &nbsp;|&nbsp; '
                f'<strong>Throttled:</strong> {_throttled}<br/>'
                f'{_rec}</div>', unsafe_allow_html=True)
    else:
        st.info("No warehouse-level query data available.")

    st.markdown("---")

    # === SECTION 9: Original Performance Summary Table ===
    st.subheader("\U0001f4cb Performance Summary by Statement Type")
    df_perf = run_query(conn, f"SELECT * FROM {FULL_SCHEMA}.silver_performance_assessment ORDER BY query_count DESC")
    if not df_perf.empty:
        st.dataframe(df_perf, use_container_width=True, height=300, hide_index=True)

# ===========================================================================
# TAB 6 — GENIE READINESS  (filtered)
# ===========================================================================
with tab_genie:
    st.header("Genie Readiness View")

    df_genie = run_query(conn,
        f"SELECT * FROM {FULL_SCHEMA}.silver_genie_readiness {FILTER_WHERE} ORDER BY genie_readiness_score DESC")
    if df_genie.empty:
        st.warning("No Genie readiness data for the current filter.")
    else:
        ready_count = len(df_genie[df_genie["genie_readiness_score"] >= 70])
        not_ready = len(df_genie) - ready_count
        gold_count = int(df_genie["is_gold_layer_candidate"].sum())

        g1, g2, g3, g4 = st.columns(4)
        with g1: metric_card("Total Tables", len(df_genie), CLR_BLUE)
        with g2: metric_card("Genie Ready", ready_count, CLR_GREEN)
        with g3: metric_card("Not Ready", not_ready, CLR_RED)
        with g4: metric_card("Gold Candidates", gold_count, CLR_PURPLE)

        fig = px.histogram(df_genie, x="genie_readiness_score", nbins=20,
                           title="Genie Readiness Score Distribution",
                           color_discrete_sequence=[CLR_BLUE])
        fig.add_vline(x=70, line_dash="dash", line_color=CLR_GREEN,
                      annotation_text="Ready Threshold (70%)")
        fig.update_layout(height=350, **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("\u2705 Genie-Ready Tables (Score >= 70%)")
        df_ready = df_genie[df_genie["genie_readiness_score"] >= 70]
        if not df_ready.empty:
            st.dataframe(df_ready[["table_catalog", "table_schema", "table_name",
                                   "has_description", "column_doc_pct", "naming_compliant",
                                   "has_lineage", "is_gold_layer_candidate", "genie_readiness_score"]],
                         use_container_width=True, height=300)
        else:
            st.info("No tables meet the 70% Genie readiness threshold yet.")

        st.subheader("\u274c Tables Needing Improvement")
        df_not_ready = df_genie[df_genie["genie_readiness_score"] < 70].tail(30)
        st.dataframe(df_not_ready[["table_catalog", "table_schema", "table_name",
                                    "has_description", "column_doc_pct", "naming_compliant",
                                    "has_lineage", "genie_readiness_score"]],
                     use_container_width=True, height=300)

        st.subheader("\U0001f4a1 Quick Wins for Genie Readiness")
        no_desc = len(df_genie[df_genie["has_description"] == 0])
        low_doc = len(df_genie[df_genie["column_doc_pct"] < 50])
        no_lineage = len(df_genie[df_genie["has_lineage"] == 0])
        bad_names = len(df_genie[df_genie["naming_compliant"] == 0])
        tips = [
            (f"Add table descriptions ({no_desc} tables missing)", no_desc),
            (f"Document columns ({low_doc} tables below 50%)", low_doc),
            (f"Establish data lineage ({no_lineage} tables isolated)", no_lineage),
            (f"Fix naming conventions ({bad_names} tables non-compliant)", bad_names),
        ]
        for tip, count in sorted(tips, key=lambda x: -x[1]):
            if count > 0:
                st.markdown(f'<div class="recommend-box">{tip}</div>', unsafe_allow_html=True)

        # --- UC Functions Genie Readiness ---
        if SHOW_FUNCTIONS:
            st.markdown("---")
            st.subheader("\U0001f9e9 UC Functions \u2014 Genie Readiness")
            st.markdown(
                '<div class="tip-box">'
                'Functions enhance Genie capabilities when properly documented. '
                'Well-described functions enable AI-assisted analytics and '
                'automated discovery.</div>', unsafe_allow_html=True)

        if SHOW_FUNCTIONS:
            _fn_cat_g = f"WHERE routine_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _fn_sch_g = (
                f" AND routine_schema = '{selected_schema}'" if selected_schema != "All" and _fn_cat_g
                else f"WHERE routine_schema = '{selected_schema}'" if selected_schema != "All"
                else ""
            )
            df_fn_genie = run_query(conn,
                f"SELECT routine_catalog, routine_schema, routine_name, "
                f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END AS has_description, "
                f"CASE WHEN routine_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END AS naming_compliant "
                f"FROM system.information_schema.routines "
                f"{_fn_cat_g}{_fn_sch_g}")
            if not df_fn_genie.empty:
                fn_total = len(df_fn_genie)
                fn_desc_ct = int(df_fn_genie['has_description'].sum())
                fn_name_ct = int(df_fn_genie['naming_compliant'].sum())
                fn_genie_score = round((fn_desc_ct + fn_name_ct) / (fn_total * 2) * 100, 1) if fn_total > 0 else 0
                gf1, gf2, gf3, gf4 = st.columns(4)
                with gf1: metric_card("UC Functions", fn_total, CLR_PURPLE)
                with gf2: metric_card("Described", fn_desc_ct, CLR_GREEN if fn_desc_ct == fn_total else CLR_AMBER)
                with gf3: metric_card("Name Compliant", fn_name_ct, CLR_GREEN if fn_name_ct == fn_total else CLR_AMBER)
                with gf4: metric_card("Genie Score", f"{fn_genie_score}%", CLR_GREEN if fn_genie_score >= 70 else CLR_AMBER if fn_genie_score >= 40 else CLR_RED)
                fn_not_ready = df_fn_genie[(df_fn_genie['has_description'] == 0) | (df_fn_genie['naming_compliant'] == 0)]
                if not fn_not_ready.empty:
                    st.markdown(f"**{len(fn_not_ready)} function(s) need improvement for Genie readiness:**")
                    st.dataframe(fn_not_ready, use_container_width=True, height=200)
            else:
                st.info("No UC Functions found.")





# ===========================================================================
# TAB 7 — COMPLIANCE
# ===========================================================================
with tab_compliance:
    st.header("Compliance Readiness")
    st.markdown(
        (
            '<div class="tip-box">'
            'This view is intentionally limited to Databricks-native, cloud-agnostic controls so the app stays portable across AWS, Azure, and GCP. '
            'It measures only controls observable from Unity Catalog, system tables, lineage, audit history, and Databricks compute metadata. '
            'Controls that require cloud-provider services, external identity tooling, or enterprise process evidence are listed separately as out of scope for this in-app score.</div>'
        ),
        unsafe_allow_html=True,
    )

    df_compliance = run_query(conn, f"""
        WITH base AS (
            SELECT
                m.table_catalog,
                m.table_schema,
                m.table_name,
                m.table_type,
                m.has_table_description,
                m.column_doc_pct,
                COALESCE(g.tag_count, 0) AS tag_count,
                COALESCE(g.privilege_count, 0) AS grant_count,
                COALESCE(g.has_all_privileges, 0) AS has_all_privileges,
                COALESCE(g.abac_effective_policy_count, 0) AS abac_effective_policy_count,
                COALESCE(g.abac_column_mask_policy_count, 0) AS abac_column_mask_policy_count,
                COALESCE(g.abac_row_filter_policy_count, 0) AS abac_row_filter_policy_count,
                COALESCE(g.abac_policy_inventory_status, 'NOT_SCANNED') AS abac_policy_inventory_status,
                COALESCE(q.data_source_format, 'UNKNOWN') AS data_source_format,
                q.last_altered,
                COALESCE(gr.lineage_connection_count, 0) AS lineage_count
            FROM {FULL_SCHEMA}.silver_metadata_assessment m
            LEFT JOIN {FULL_SCHEMA}.silver_governance_assessment g
                ON m.table_catalog = g.table_catalog
                AND m.table_schema = g.table_schema
                AND m.table_name = g.table_name
            LEFT JOIN {FULL_SCHEMA}.silver_quality_assessment q
                ON m.table_catalog = q.table_catalog
                AND m.table_schema = q.table_schema
                AND m.table_name = q.table_name
            LEFT JOIN {FULL_SCHEMA}.silver_genie_readiness gr
                ON m.table_catalog = gr.table_catalog
                AND m.table_schema = gr.table_schema
                AND m.table_name = gr.table_name
            {FILTER_WHERE}
        )
        SELECT
            *,
            CASE WHEN tag_count > 0 THEN 1 ELSE 0 END AS data_classified,
            CASE WHEN grant_count > 0 THEN 1 ELSE 0 END AS rbac_defined,
            CASE WHEN has_all_privileges = 0 THEN 1 ELSE 0 END AS least_privilege_enforced,
            CASE WHEN abac_effective_policy_count > 0 THEN 1 ELSE 0 END AS abac_protected,
            CASE WHEN has_table_description = 1 AND column_doc_pct >= 80 THEN 1 ELSE 0 END AS retention_and_context_documented,
            CASE WHEN lineage_count > 0 THEN 1 ELSE 0 END AS audit_traceable,
            CASE WHEN table_type = 'MANAGED' AND UPPER(COALESCE(data_source_format, '')) = 'DELTA' THEN 1 ELSE 0 END AS governed_storage,
            CASE WHEN DATEDIFF(current_date(), CAST(last_altered AS DATE)) <= 30 THEN 1 ELSE 0 END AS monitoring_signal_current,
            ROUND(
                (
                    (CASE WHEN tag_count > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN grant_count > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN has_all_privileges = 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN has_table_description = 1 AND column_doc_pct >= 80 THEN 1 ELSE 0 END) +
                    (CASE WHEN lineage_count > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN table_type = 'MANAGED' AND UPPER(COALESCE(data_source_format, '')) = 'DELTA' THEN 1 ELSE 0 END) +
                    (CASE WHEN DATEDIFF(current_date(), CAST(last_altered AS DATE)) <= 30 THEN 1 ELSE 0 END)
                ) / 7.0 * 100,
                1
            ) AS compliance_score
        FROM base
        ORDER BY compliance_score DESC, table_catalog, table_schema, table_name
    """)

    if df_compliance.empty:
        st.warning("No compliance readiness data for the current filter.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        avg_score = round(float(df_compliance['compliance_score'].mean()), 1)
        classified_assets = int(df_compliance['data_classified'].sum())
        least_priv_assets = int(df_compliance['least_privilege_enforced'].sum())
        traceable_assets = int(df_compliance['audit_traceable'].sum())
        with c1: metric_card("Avg Compliance Score", f"{avg_score}%", CLR_PURPLE if avg_score >= 70 else CLR_AMBER if avg_score >= 40 else CLR_RED)
        with c2: metric_card("Classified Assets", classified_assets, CLR_BLUE)
        with c3: metric_card("Least Privilege", least_priv_assets, CLR_GREEN if least_priv_assets > 0 else CLR_AMBER)
        with c4: metric_card("Audit Traceable", traceable_assets, CLR_PURPLE)

        ab1, ab2, ab3, ab4 = st.columns(4)
        abac_protected_assets = int(df_compliance['abac_protected'].sum())
        abac_masked_assets = int((df_compliance['abac_column_mask_policy_count'] > 0).sum())
        abac_filtered_assets = int((df_compliance['abac_row_filter_policy_count'] > 0).sum())
        abac_unsupported_assets = int((df_compliance['abac_policy_inventory_status'] == 'UNSUPPORTED').sum())
        with ab1: metric_card("ABAC Protected", abac_protected_assets, CLR_PURPLE if abac_protected_assets > 0 else CLR_AMBER)
        with ab2: metric_card("Masked Tables", abac_masked_assets, CLR_BLUE)
        with ab3: metric_card("Row-Filtered Tables", abac_filtered_assets, CLR_BLUE)
        with ab4: metric_card("ABAC Unsupported", abac_unsupported_assets, CLR_AMBER if abac_unsupported_assets > 0 else CLR_GREEN)

        fig_comp = px.histogram(
            df_compliance,
            x="compliance_score",
            nbins=20,
            title="Databricks-Native Compliance Score Distribution",
            color_discrete_sequence=[CLR_PURPLE],
        )
        fig_comp.add_vline(x=70, line_dash="dash", line_color=CLR_GREEN, annotation_text="Target >= 70%")
        fig_comp.update_layout(height=340, **CHART_LAYOUT)
        st.plotly_chart(fig_comp, use_container_width=True)

        st.subheader("ABAC Coverage Overview")
        df_abac_summary = run_query(conn, f"""
            SELECT
                inventory_status,
                COUNT(*) AS table_count,
                SUM(COALESCE(effective_policy_count, 0)) AS effective_policy_count,
                SUM(COALESCE(column_mask_policy_count, 0)) AS column_mask_policy_count,
                SUM(COALESCE(row_filter_policy_count, 0)) AS row_filter_policy_count
            FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
            GROUP BY inventory_status
            ORDER BY CASE inventory_status WHEN 'SCANNED' THEN 1 WHEN 'UNSUPPORTED' THEN 2 ELSE 3 END, inventory_status
        """)
        if not df_abac_summary.empty:
            st.dataframe(df_abac_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No ABAC inventory summary is available yet.")

        st.subheader("Unsupported Tables for ABAC Inventory")
        df_abac_unsupported = run_query(conn, f"""
            SELECT
                table_catalog,
                table_schema,
                table_name,
                error_message
            FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
            WHERE inventory_status = 'UNSUPPORTED'
            ORDER BY table_catalog, table_schema, table_name
            LIMIT 50
        """)
        if not df_abac_unsupported.empty:
            st.dataframe(df_abac_unsupported, use_container_width=True, height=260, hide_index=True)
        else:
            st.info("No unsupported tables were encountered during ABAC inventory.")

        st.subheader("Cloud-Agnostic Controls Covered In-App")
        covered_rows = [
            ("Data classification", "Covered", "UC tags on tables and columns"),
            ("RBAC", "Covered", "Explicit grants from Unity Catalog privileges"),
            ("Least privilege", "Covered", "Detection of ALL PRIVILEGES / broad grants"),
            ("Audit logging and monitoring", "Partially covered", "Lineage, query history, and freshness signals available in Databricks system data"),
            ("Retention and deletion evidence", "Partially covered", "Documentation and metadata readiness only; not policy enforcement"),
            ("Governed storage posture", "Covered", "Managed Delta preference for stronger control surface"),
            ("Regular security assessment signal", "Covered", "Assessment can be re-run from current Databricks metadata"),
            ("ABAC coverage visibility", "Covered", "Effective row-filter and column-mask inventory from Unity Catalog policies"),
        ]
        st.dataframe(
            pd.DataFrame(covered_rows, columns=["Control Area", "Coverage", "Databricks-Native Evidence"]),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Out of Scope for Databricks-Only, Cloud-Agnostic Scoring")
        out_of_scope_rows = [
            ("Encryption at rest", "Cloud storage / KMS evidence required"),
            ("Encryption in transit", "Network / endpoint evidence required"),
            ("MFA", "External IdP or account-layer evidence required"),
            ("Data masking or tokenization outside Databricks", "External tokenization or application-layer masking evidence required"),
            ("Backup and disaster recovery", "Cloud backup / recovery design evidence required"),
            ("Incident response procedures", "Process and runbook evidence required"),
            ("Vulnerability scans", "External scanner or security platform evidence required"),
        ]
        st.dataframe(
            pd.DataFrame(out_of_scope_rows, columns=["Control Area", "Why Not Scored Here"]),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Compliance Starter Rules")
        df_comp_rules = get_assessment_rules(conn, FULL_SCHEMA)
        df_comp_rules = df_comp_rules[df_comp_rules['category'] == 'Compliance']
        if not df_comp_rules.empty:
            st.dataframe(
                df_comp_rules[["rule_id", "rule_name", "description", "severity", "weight", "threshold"]],
                use_container_width=True,
                hide_index=True,
                height=260,
            )
        else:
            st.info("No Compliance rules found yet. Run the pipeline refresh to load starter rules.")

        st.subheader("ABAC Recommendations")
        df_abac_recs = run_query(conn, f"""
            SELECT
                table_catalog,
                table_schema,
                table_name,
                severity,
                recommendation,
                current_value,
                target_value
            FROM {FULL_SCHEMA}.gold_recommendations
            WHERE rule_id IN ('ABAC_001', 'ABAC_002')
            {FILTER_WHERE}
            ORDER BY severity, table_catalog, table_schema, table_name
            LIMIT 100
        """)
        if not df_abac_recs.empty:
            st.dataframe(df_abac_recs, use_container_width=True, height=260, hide_index=True)
        else:
            st.info("No ABAC-specific recommendations for the current filter.")

        st.subheader("Assets Needing Compliance Attention")
        df_gaps = df_compliance.sort_values('compliance_score').head(50).copy()
        if not df_gaps.empty:
            df_gaps['top_gap'] = df_gaps.apply(
                lambda r: 'Missing data classification tags' if r['data_classified'] == 0 else (
                    'RBAC not explicitly defined' if r['rbac_defined'] == 0 else (
                        'Least privilege gap detected' if r['least_privilege_enforced'] == 0 else (
                            'Documentation or retention context is weak' if r['retention_and_context_documented'] == 0 else (
                                'No audit traceability via lineage' if r['audit_traceable'] == 0 else (
                                    'ABAC inventory unsupported for this table' if r['abac_policy_inventory_status'] == 'UNSUPPORTED' else (
                                        'Governed storage posture should improve' if r['governed_storage'] == 0 else 'Monitoring signal is stale'
                                    )
                                )
                            )
                        )
                    )
                ),
                axis=1,
            )
            st.dataframe(
                df_gaps[[
                    'table_catalog', 'table_schema', 'table_name', 'compliance_score', 'top_gap',
                    'data_classified', 'rbac_defined', 'least_privilege_enforced',
                    'abac_policy_inventory_status', 'abac_effective_policy_count', 'abac_column_mask_policy_count',
                    'abac_row_filter_policy_count', 'retention_and_context_documented', 'audit_traceable', 'governed_storage', 'monitoring_signal_current'
                ]],
                use_container_width=True,
                height=320,
                hide_index=True,
            )

# ===========================================================================
# TAB — AI INSIGHTS (AI-powered analysis using ai_query)
# ===========================================================================
with tab_ai:
    st.header("\U0001f9e0 AI-Powered Insights")
    st.markdown(
        '<div class="tip-box">'
        'This tab uses Databricks AI functions (<code>ai_query</code>) to generate intelligent analysis '
        'of your UC readiness data. Powered by foundation models for natural language insights.</div>',
        unsafe_allow_html=True)

    ai_section = st.radio(
        "Select analysis type",
        ["\U0001f4dd Executive Narrative", "\U0001f50d Root Cause Analysis",
         "\U0001f4cb Prioritized Action Plan", "\U0001f916 AI Table Descriptions"],
        horizontal=True, key="ai_section_radio")

    st.markdown("---")

    # -------------------------------------------------------------------
    # AI SECTION 1: Executive Narrative
    # -------------------------------------------------------------------
    if ai_section == "\U0001f4dd Executive Narrative":
        st.subheader("AI-Generated Executive Summary")
        st.markdown(
            '<div class="recommend-box">'
            'Generate a natural language executive briefing from your assessment scores. '
            'Perfect for stakeholder presentations and governance reports.</div>',
            unsafe_allow_html=True)

        if st.button("\U0001f680 Generate Executive Narrative", type="primary", key="ai_exec_btn"):
            with st.spinner("AI is analyzing your assessment data..."):
                try:
                    df_ai_exec = run_query(conn, f"""
                        WITH scores AS (
                            SELECT
                                ROUND(AVG(metadata_score / 5.0 * 100), 1) AS metadata_pct,
                                ROUND(AVG(governance_score / 5.0 * 100), 1) AS governance_pct,
                                ROUND(AVG(quality_score / 5.0 * 100), 1) AS quality_pct,
                                ROUND(AVG(genie_score / 100.0 * 100), 1) AS genie_pct,
                                ROUND(AVG(overall_score), 1) AS overall_pct,
                                COUNT(*) AS total_tables,
                                SUM(CASE WHEN rag_status = 'RED' THEN 1 ELSE 0 END) AS red_tables,
                                SUM(CASE WHEN rag_status = 'AMBER' THEN 1 ELSE 0 END) AS amber_tables,
                                SUM(CASE WHEN rag_status = 'GREEN' THEN 1 ELSE 0 END) AS green_tables
                            FROM {FULL_SCHEMA}.gold_table_scores {FILTER_WHERE}
                        ),
                        recs AS (
                            SELECT COUNT(*) AS total_recs,
                                SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) AS high_recs
                            FROM {FULL_SCHEMA}.gold_recommendations {FILTER_WHERE}
                        )
                        SELECT ai_query(
                            'databricks-meta-llama-3-3-70b-instruct',
                            CONCAT(
                                'You are a data governance consultant. Write a concise executive briefing (3-4 paragraphs) ',
                                'about this Unity Catalog readiness assessment. Use professional tone suitable for C-level stakeholders. ',
                                'Include specific numbers and actionable recommendations. ',
                                'Assessment Data: ',
                                'Overall Readiness: ', CAST(s.overall_pct AS STRING), '%. ',
                                'Metadata Readiness: ', CAST(s.metadata_pct AS STRING), '%. ',
                                'Governance: ', CAST(s.governance_pct AS STRING), '%. ',
                                'Data Quality: ', CAST(s.quality_pct AS STRING), '%. ',
                                'Genie Readiness: ', CAST(s.genie_pct AS STRING), '%. ',
                                'Total Tables Assessed: ', CAST(s.total_tables AS STRING), '. ',
                                'RED (Critical): ', CAST(s.red_tables AS STRING), ' tables. ',
                                'AMBER (Needs Work): ', CAST(s.amber_tables AS STRING), ' tables. ',
                                'GREEN (Healthy): ', CAST(s.green_tables AS STRING), ' tables. ',
                                'Total Recommendations: ', CAST(r.total_recs AS STRING), '. ',
                                'HIGH Priority Issues: ', CAST(r.high_recs AS STRING), '.'
                            ),
                            modelParameters => named_struct('max_tokens', 800, 'temperature', 0.3)
                        ) AS narrative
                        FROM scores s CROSS JOIN recs r
                    """)
                    if not df_ai_exec.empty and df_ai_exec.iloc[0]['narrative']:
                        st.markdown(
                            f'<div style="background:white;border-radius:12px;padding:24px;'
                            f'box-shadow:0 2px 8px rgba(0,0,0,0.08);border-top:3px solid {CLR_BLUE};'
                            f'line-height:1.7;font-size:14px;color:#334155">'
                            f'{df_ai_exec.iloc[0]["narrative"]}</div>',
                            unsafe_allow_html=True)
                    else:
                        st.warning("AI did not return a response. Ensure your warehouse supports ai_query().")
                except Exception as e:
                    st.error(f"AI analysis failed: {str(e)[:300]}")
                    st.markdown(
                        '<div class="warn-box">'
                        '<strong>Troubleshooting:</strong> Ensure your SQL Warehouse has access to '
                        'Foundation Model APIs (ai_query). This requires a workspace with '
                        'Foundation Model APIs enabled.</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # AI SECTION 2: Root Cause Analysis
    # -------------------------------------------------------------------
    elif ai_section == "\U0001f50d Root Cause Analysis":
        st.subheader("AI Root Cause Analysis")
        st.markdown(
            '<div class="recommend-box">'
            'AI analyzes your lowest-scoring tables to identify patterns and root causes '
            'behind governance gaps.</div>',
            unsafe_allow_html=True)

        num_tables = st.slider("Number of tables to analyze", 3, 10, 5, key="ai_rca_count")

        if st.button("\U0001f50d Analyze Root Causes", type="primary", key="ai_rca_btn"):
            with st.spinner("AI is performing root cause analysis..."):
                try:
                    df_ai_rca = run_query(conn, f"""
                        WITH worst_tables AS (
                            SELECT
                                CONCAT(s.table_catalog, '.', s.table_schema, '.', s.table_name) AS full_name,
                                s.overall_score,
                                s.metadata_score,
                                s.governance_score,
                                s.quality_score,
                                s.genie_score,
                                s.rag_status
                            FROM {FULL_SCHEMA}.gold_table_scores s
                            {FILTER_WHERE}
                            ORDER BY s.overall_score ASC
                            LIMIT {num_tables}
                        ),
                        table_summary AS (
                            SELECT CONCAT_WS('; ',
                                COLLECT_LIST(
                                    CONCAT(full_name, ' [score=', CAST(ROUND(overall_score,1) AS STRING),
                                           ', meta=', CAST(ROUND(metadata_score,1) AS STRING),
                                           ', gov=', CAST(ROUND(governance_score,1) AS STRING),
                                           ', qual=', CAST(ROUND(quality_score,1) AS STRING),
                                           ', genie=', CAST(ROUND(genie_score,1) AS STRING), ']')
                                )
                            ) AS details
                            FROM worst_tables
                        )
                        SELECT ai_query(
                            'databricks-meta-llama-3-3-70b-instruct',
                            CONCAT(
                                'You are a data governance expert. Analyze these low-scoring Unity Catalog tables and identify: ',
                                '1) Common patterns and root causes for the low scores. ',
                                '2) Which governance dimension is the biggest bottleneck across tables. ',
                                '3) Systemic issues (e.g., entire schemas undocumented, missing tags workspace-wide). ',
                                '4) Quick wins vs. structural fixes needed. ',
                                'Format your response with clear sections and bullet points. ',
                                'Table Details (format: name [overall_score, metadata, governance, quality, genie]): ',
                                t.details
                            ),
                            modelParameters => named_struct('max_tokens', 1000, 'temperature', 0.2)
                        ) AS analysis
                        FROM table_summary t
                    """)
                    if not df_ai_rca.empty and df_ai_rca.iloc[0]['analysis']:
                        st.markdown(
                            f'<div style="background:white;border-radius:12px;padding:24px;'
                            f'box-shadow:0 2px 8px rgba(0,0,0,0.08);border-top:3px solid {CLR_RED};'
                            f'line-height:1.7;font-size:14px;color:#334155">'
                            f'{df_ai_rca.iloc[0]["analysis"]}</div>',
                            unsafe_allow_html=True)
                    else:
                        st.warning("AI did not return a response.")
                except Exception as e:
                    st.error(f"AI analysis failed: {str(e)[:300]}")
                    st.markdown(
                        '<div class="warn-box">'
                        '<strong>Troubleshooting:</strong> Ensure Foundation Model APIs are enabled.</div>',
                        unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # AI SECTION 3: Prioritized Action Plan
    # -------------------------------------------------------------------
    elif ai_section == "\U0001f4cb Prioritized Action Plan":
        st.subheader("AI-Generated Action Plan")
        st.markdown(
            '<div class="recommend-box">'
            'AI creates a prioritized, time-bound remediation plan based on your current '
            'assessment gaps and organizational impact.</div>',
            unsafe_allow_html=True)

        timeframe = st.selectbox("Target timeframe", ["2 weeks", "1 month", "1 quarter"], key="ai_plan_tf")

        if st.button("\U0001f4cb Generate Action Plan", type="primary", key="ai_plan_btn"):
            with st.spinner("AI is building your action plan..."):
                try:
                    df_ai_plan = run_query(conn, f"""
                        WITH rec_summary AS (
                            SELECT category, severity, recommendation,
                                COUNT(*) AS affected_tables
                            FROM {FULL_SCHEMA}.gold_recommendations
                            {FILTER_WHERE}
                            GROUP BY category, severity, recommendation
                            ORDER BY
                                CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                                affected_tables DESC
                            LIMIT 15
                        ),
                        rec_details AS (
                            SELECT CONCAT_WS('; ',
                                COLLECT_LIST(
                                    CONCAT('[', severity, '] ', category, ': ', recommendation,
                                           ' (', CAST(affected_tables AS STRING), ' tables)')
                                )
                            ) AS all_recs
                            FROM rec_summary
                        )
                        SELECT ai_query(
                            'databricks-meta-llama-3-3-70b-instruct',
                            CONCAT(
                                'You are a data governance program manager. Create a prioritized action plan for a {timeframe} timeframe. ',
                                'Structure the plan as: ',
                                '**Week 1-2 (Quick Wins):** Actions that can be done immediately with minimal effort. ',
                                '**Week 3-4 (Medium Effort):** Actions requiring coordination or tooling. ',
                                '**Ongoing (Structural):** Process changes and automation needed long-term. ',
                                'For each action, specify: the action, expected impact, effort level, and owner role. ',
                                'Use a professional tone. Include specific SQL commands where relevant. ',
                                'Current Assessment Gaps: ',
                                r.all_recs
                            ),
                            modelParameters => named_struct('max_tokens', 1200, 'temperature', 0.3)
                        ) AS plan
                        FROM rec_details r
                    """.replace("{timeframe}", timeframe))
                    if not df_ai_plan.empty and df_ai_plan.iloc[0]['plan']:
                        st.markdown(
                            f'<div style="background:white;border-radius:12px;padding:24px;'
                            f'box-shadow:0 2px 8px rgba(0,0,0,0.08);border-top:3px solid {CLR_GREEN};'
                            f'line-height:1.7;font-size:14px;color:#334155">'
                            f'{df_ai_plan.iloc[0]["plan"]}</div>',
                            unsafe_allow_html=True)
                    else:
                        st.warning("AI did not return a response.")
                except Exception as e:
                    st.error(f"AI analysis failed: {str(e)[:300]}")
                    st.markdown(
                        '<div class="warn-box">'
                        '<strong>Troubleshooting:</strong> Ensure Foundation Model APIs are enabled.</div>',
                        unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # AI SECTION 4: AI Table Descriptions
    # -------------------------------------------------------------------
    elif ai_section == "\U0001f916 AI Table Descriptions":
        st.subheader("AI-Powered Description Generator")
        st.markdown(
            '<div class="recommend-box">'
            'Use AI to automatically generate meaningful table and column descriptions '
            'based on schema metadata, column names, and data types. Review and apply with one click.</div>',
            unsafe_allow_html=True)

        # --- AI Table Description Generator ---
        st.markdown('<div class="section-header">\U0001f4dd Generate Table Description</div>',
                    unsafe_allow_html=True)

        df_ai_no_desc = run_query(conn,
            f"SELECT table_catalog, table_schema, table_name "
            f"FROM {FULL_SCHEMA}.silver_metadata_assessment "
            f"WHERE has_table_description = 0 {FILTER_AND} "
            f"ORDER BY table_catalog, table_schema, table_name")

        if df_ai_no_desc.empty:
            st.success("\u2705 All tables already have descriptions!")
        else:
            opts_ai = [f"{r.table_catalog}.{r.table_schema}.{r.table_name}" for _, r in df_ai_no_desc.iterrows()]
            sel_ai_table = st.selectbox("Select table to describe", opts_ai, key="ai_desc_table")

            ai_col1, ai_col2 = st.columns([2, 1])
            with ai_col1:
                if st.button("\U0001f9e0 Generate Description with AI", type="primary", key="ai_gen_desc_btn"):
                    with st.spinner("AI is analyzing table structure..."):
                        try:
                            parts = sel_ai_table.split(".")
                            df_ai_desc = run_query(conn, f"""
                                WITH col_info AS (
                                    SELECT CONCAT_WS(', ',
                                        COLLECT_LIST(
                                            CONCAT(column_name, ' (', full_data_type, ')')
                                        )
                                    ) AS columns_list
                                    FROM {FULL_SCHEMA}.bronze_columns
                                    WHERE table_catalog = '{parts[0]}'
                                    AND table_schema = '{parts[1]}'
                                    AND table_name = '{parts[2]}'
                                )
                                SELECT ai_query(
                                    'databricks-meta-llama-3-3-70b-instruct',
                                    CONCAT(
                                        'Generate a concise, business-friendly table description (1-2 sentences) for a database table. ',
                                        'The description should explain what data the table contains and its business purpose. ',
                                        'Do NOT include technical details like column types. Only return the description text, nothing else. ',
                                        'Table: {sel_ai_table}. ',
                                        'Columns: ', c.columns_list
                                    ),
                                    modelParameters => named_struct('max_tokens', 150, 'temperature', 0.2)
                                ) AS description
                                FROM col_info c
                            """.replace("{sel_ai_table}", sel_ai_table))

                            if not df_ai_desc.empty and df_ai_desc.iloc[0]['description']:
                                ai_generated_desc = df_ai_desc.iloc[0]['description'].strip()
                                st.session_state['ai_generated_table_desc'] = ai_generated_desc
                                st.session_state['ai_desc_target_table'] = sel_ai_table
                            else:
                                st.warning("AI did not return a description.")
                        except Exception as e:
                            st.error(f"AI generation failed: {str(e)[:300]}")

            # Show generated description and apply button
            if 'ai_generated_table_desc' in st.session_state and st.session_state.get('ai_desc_target_table') == sel_ai_table:
                st.markdown(
                    f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                    f'padding:16px;margin:12px 0">'
                    f'<p style="font-size:11px;color:#16a34a;font-weight:600;margin:0 0 6px;'
                    f'text-transform:uppercase;letter-spacing:0.5px">AI-Generated Description</p>'
                    f'<p style="font-size:14px;color:#166534;margin:0">'
                    f'{st.session_state["ai_generated_table_desc"]}</p></div>',
                    unsafe_allow_html=True)

                ac1, ac2 = st.columns(2)
                with ac1:
                    if st.button("\u2705 Apply This Description", key="ai_apply_desc_btn", type="primary"):
                        safe_desc = st.session_state['ai_generated_table_desc'].replace("'", "''")
                        result = run_action(conn, f"COMMENT ON TABLE {sel_ai_table} IS '{safe_desc}'")
                        if result == "OK":
                            st.markdown('<div class="success-box">\u2705 AI description applied successfully!</div>',
                                        unsafe_allow_html=True)
                            del st.session_state['ai_generated_table_desc']
                            st.cache_data.clear()
                        else:
                            st.markdown(f'<div class="error-box">Error: {result[:200]}</div>',
                                        unsafe_allow_html=True)
                with ac2:
                    if st.button("\U0001f504 Regenerate", key="ai_regen_desc_btn"):
                        del st.session_state['ai_generated_table_desc']
                        st.rerun()

        # --- AI Column Description Generator ---
        st.markdown("---")
        st.markdown('<div class="section-header">\U0001f4cb Bulk Generate Column Descriptions</div>',
                    unsafe_allow_html=True)

        df_ai_low_doc = run_query(conn,
            f"SELECT table_catalog, table_schema, table_name, column_doc_pct, total_columns "
            f"FROM {FULL_SCHEMA}.silver_metadata_assessment "
            f"WHERE column_doc_pct < 80 AND total_columns > 0 {FILTER_AND} "
            f"ORDER BY column_doc_pct ASC LIMIT 100")

        if df_ai_low_doc.empty:
            st.success("\u2705 All tables have >= 80% column documentation!")
        else:
            opts_ai_col = [f"{r.table_catalog}.{r.table_schema}.{r.table_name} ({r.column_doc_pct:.0f}% documented)"
                           for _, r in df_ai_low_doc.iterrows()]
            sel_ai_col_table_display = st.selectbox("Select under-documented table", opts_ai_col, key="ai_col_table")
            sel_ai_col_table = sel_ai_col_table_display.rsplit(" (", 1)[0]

            if st.button("\U0001f9e0 Generate Column Descriptions with AI", type="primary", key="ai_gen_cols_btn"):
                with st.spinner("AI is generating column descriptions..."):
                    try:
                        parts = sel_ai_col_table.split(".")
                        df_ai_cols = run_query(conn, f"""
                            SELECT
                                column_name,
                                full_data_type,
                                ai_query(
                                    'databricks-meta-llama-3-3-70b-instruct',
                                    CONCAT(
                                        'Generate a concise column description (max 15 words) for a database column. ',
                                        'Only return the description, nothing else. ',
                                        'Table: {sel_ai_col_table}, Column: ', column_name,
                                        ', Type: ', full_data_type
                                    ),
                                    modelParameters => named_struct('max_tokens', 50, 'temperature', 0.1)
                                ) AS ai_description
                            FROM {FULL_SCHEMA}.bronze_columns
                            WHERE table_catalog = '{parts[0]}'
                            AND table_schema = '{parts[1]}'
                            AND table_name = '{parts[2]}'
                            AND (comment IS NULL OR comment = '')
                            LIMIT 20
                        """.replace("{sel_ai_col_table}", sel_ai_col_table))

                        if not df_ai_cols.empty:
                            st.session_state['ai_generated_col_descs'] = df_ai_cols
                            st.session_state['ai_col_target_table'] = sel_ai_col_table
                        else:
                            st.success("All columns in this table are already documented!")
                    except Exception as e:
                        st.error(f"AI generation failed: {str(e)[:300]}")

            # Show generated column descriptions
            if 'ai_generated_col_descs' in st.session_state and st.session_state.get('ai_col_target_table') == sel_ai_col_table:
                df_gen_cols = st.session_state['ai_generated_col_descs']
                st.markdown(
                    f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'
                    f'padding:12px 16px;margin:12px 0">'
                    f'<p style="font-size:11px;color:#1e40af;font-weight:600;margin:0 0 4px;'
                    f'text-transform:uppercase;letter-spacing:0.5px">'
                    f'AI-Generated Descriptions for {len(df_gen_cols)} columns</p></div>',
                    unsafe_allow_html=True)

                st.dataframe(
                    df_gen_cols[['column_name', 'full_data_type', 'ai_description']].rename(
                        columns={'column_name': 'Column', 'full_data_type': 'Type', 'ai_description': 'AI Description'}),
                    use_container_width=True, height=300, hide_index=True)

                if st.button("\u2705 Apply All Column Descriptions", key="ai_apply_cols_btn", type="primary"):
                    success_count = 0
                    errors = []
                    progress_ai = st.progress(0)
                    for idx, (_, col_row) in enumerate(df_gen_cols.iterrows()):
                        if col_row['ai_description'] and str(col_row['ai_description']).strip():
                            safe_cd = str(col_row['ai_description']).strip().replace("'", "''")
                            result = run_action(conn,
                                f"ALTER TABLE {sel_ai_col_table} ALTER COLUMN {col_row['column_name']} COMMENT '{safe_cd}'")
                            if result == "OK":
                                success_count += 1
                            else:
                                errors.append(f"{col_row['column_name']}: {result[:80]}")
                        progress_ai.progress((idx + 1) / len(df_gen_cols))
                    progress_ai.empty()
                    st.markdown(
                        f'<div class="success-box">\u2705 Applied {success_count}/{len(df_gen_cols)} '
                        f'column descriptions successfully!</div>', unsafe_allow_html=True)
                    if errors:
                        with st.expander(f"\u26a0\ufe0f {len(errors)} errors"):
                            for e in errors:
                                st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)
                    del st.session_state['ai_generated_col_descs']
                    st.cache_data.clear()

# ===========================================================================
with tab_rules:
    st.header("Assessment Rules & Scoring Methodology")

    st.markdown(
        '<div class="tip-box">'
        'This page explains every rule the accelerator evaluates, how scores '
        'are calculated, and what the RAG thresholds mean. Use it as a '
        'reference when reviewing recommendations.</div>', unsafe_allow_html=True)

    st.subheader("Scoring Methodology")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            '<div class="method-card">'
            '<h4 style="color:#dc2626 !important">\u2b24 RED &mdash; Below 40%</h4>'
            '<p>Critical gaps that block Genie adoption, governance compliance, '
            'or efficient operations. Immediate action required.</p></div>',
            unsafe_allow_html=True)
    with m2:
        st.markdown(
            '<div class="method-card">'
            '<h4 style="color:#d97706 !important">\u2b24 AMBER &mdash; 40 &ndash; 70%</h4>'
            '<p>Partial readiness with notable improvement areas. Tables are '
            'functional but not optimised for self-service analytics.</p></div>',
            unsafe_allow_html=True)
    with m3:
        st.markdown(
            '<div class="method-card">'
            '<h4 style="color:#16a34a !important">\u2b24 GREEN &mdash; Above 70%</h4>'
            '<p>Well-governed, documented, and performant. Ready for Genie '
            'onboarding, sharing, and production workloads.</p></div>',
            unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Category Weights in Overall Score")
    st.markdown(
        '<div class="method-card">'
        '<p>The <strong>overall readiness score</strong> is a weighted average '
        'of five category scores, each contributing <strong>equally at 25 %</strong> '
        'for Metadata, Governance, Data Quality, and Genie Readiness. '
        'Performance is assessed at the workspace level and reported separately.</p>'
        '<p style="margin-top:10px">'
        '<strong>Metadata Readiness</strong> &mdash; table descriptions, column '
        'documentation percentage, naming conventions<br>'
        '<strong>Governance</strong> &mdash; tag coverage, explicit privilege grants, '
        'over-permissioning detection<br>'
        '<strong>Data Quality</strong> &mdash; freshness (modified within 30 days), '
        'Delta format adoption<br>'
        '<strong>Genie Readiness</strong> &mdash; composite of the above plus '
        'lineage connections and gold-layer candidacy</p></div>',
        unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("\U0001f4af How the Overall Score is Calculated")

    # Query current category scores
    df_calc_scores = run_query(conn,
        f"SELECT category, ROUND(AVG(pct), 1) AS avg_pct, COUNT(*) AS catalog_count "
        f"FROM {FULL_SCHEMA}.gold_category_scores "
        f"WHERE catalog_name = 'ALL' GROUP BY category ORDER BY category")

    if not df_calc_scores.empty:
        # Build the calculation breakdown
        weight_map = {
            "Metadata Readiness": 25, "Governance": 25,
            "Data Quality": 25, "Genie Readiness": 25,
            "Compliance": 0, "Performance": 0, "UC Functions": 0, "ML Models": 0,
            "Volumes": 0, "Clusters": 0, "SQL Warehouses": 0,
        }
        core_categories = {}
        ext_categories = {}
        for _, r in df_calc_scores.iterrows():
            cat = r['category']
            pct = float(r['avg_pct']) if pd.notna(r['avg_pct']) else 0
            w = weight_map.get(cat, 0)
            if w > 0:
                core_categories[cat] = pct
            else:
                ext_categories[cat] = pct

        # Calculate overall
        if core_categories:
            overall_calc = round(sum(core_categories.values()) / len(core_categories), 1)
        else:
            overall_calc = 0
        rag_color = CLR_RED if overall_calc < 40 else CLR_AMBER if overall_calc < 70 else CLR_GREEN
        rag_label = "RED" if overall_calc < 40 else "AMBER" if overall_calc < 70 else "GREEN"

        # --- STEP 1: Plain English explanation with worked example ---
        st.markdown(
            '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:16px;'
            'border-radius:0 8px 8px 0;margin-bottom:20px">'
            '<strong style="font-size:15px;color:#1e40af">How It Works</strong><br>'
            '<span style="color:#334155">The overall score is the <strong>simple average</strong> '
            'of 4 equally-weighted core categories (25% each). Each category scores your assets '
            'from 0% to 100% based on assessment rules.</span><br><br>'
            '<strong style="color:#1e40af">Worked Example:</strong><br>'
            '<span style="color:#334155">Suppose your workspace scores:</span><br>'
            '<span style="color:#334155;padding-left:12px">'
            '\U0001f4dd Metadata Readiness = <strong>72%</strong> &nbsp;|&nbsp; '
            '\U0001f6e1\ufe0f Governance = <strong>45%</strong> &nbsp;|&nbsp; '
            '\u2705 Data Quality = <strong>88%</strong> &nbsp;|&nbsp; '
            '\U0001f916 Genie Readiness = <strong>35%</strong></span><br><br>'
            '<span style="color:#334155">Overall = (72 + 45 + 88 + 35) / 4 = '
            '<strong style="color:#d97706">60.0% (AMBER)</strong></span><br>'
            '<span style="color:#64748b;font-size:12px">'
            'In this example, Governance and Genie Readiness pull the score down. '
            'Improving documentation and tagging would lift the overall into GREEN territory (&gt;70%).</span>'
            '</div>', unsafe_allow_html=True)

        # --- STEP 2: Visual breakdown with progress bars ---
        st.markdown('<p style="font-weight:600;font-size:15px;margin:16px 0 8px">Step 1: Score each category</p>',
                    unsafe_allow_html=True)

        cat_icons = {"Metadata Readiness": "\U0001f4dd", "Governance": "\U0001f6e1\ufe0f",
                     "Data Quality": "\u2705", "Genie Readiness": "\U0001f916"}
        for cat, score in core_categories.items():
            bar_color = CLR_RED if score < 40 else CLR_AMBER if score < 70 else CLR_GREEN
            icon = cat_icons.get(cat, "")
            st.markdown(
                f'<div style="display:flex;align-items:center;margin:8px 0;gap:12px">'
                f'<span style="min-width:180px;font-size:14px">{icon} {cat}</span>'
                f'<div style="flex:1;background:#e2e8f0;border-radius:8px;height:28px;position:relative">'
                f'<div style="width:{min(score, 100)}%;background:{bar_color};height:100%;'
                f'border-radius:8px;transition:width 0.3s"></div>'
                f'<span style="position:absolute;right:8px;top:4px;font-weight:600;font-size:13px;'
                f'color:#1e293b">{score:.1f}%</span></div>'
                f'<span style="min-width:50px;font-weight:600;color:{bar_color}">{score:.1f}%</span>'
                f'</div>', unsafe_allow_html=True)

        # --- Show result below progress bars ---
        if core_categories:
            scores_str = " + ".join([f"{s:.1f}" for s in core_categories.values()])
            st.markdown(
                f'<div style="margin-top:16px;padding:12px 16px;background:#f8fafc;'
                f'border-radius:8px;border:1px solid #e2e8f0;display:flex;'
                f'align-items:center;justify-content:space-between">'
                f'<span style="color:#64748b;font-size:13px">'
                f'Average: ({scores_str}) / {len(core_categories)}</span>'
                f'<span style="font-size:20px;font-weight:700;color:{rag_color}">'
                f'{overall_calc}% <span style="font-size:12px;font-weight:400">({rag_label})</span></span>'
                f'</div>', unsafe_allow_html=True)

        # --- Extended categories note ---
        if ext_categories:
            with st.expander("\U0001f4cb Extended Categories (not in overall score)"):
                st.markdown(
                    "These categories are assessed independently and shown on the Executive Summary, "
                    "but are **not included** in the overall weighted score:")
                for cat, score in ext_categories.items():
                    if score > 0:
                        bar_color = CLR_RED if score < 40 else CLR_AMBER if score < 70 else CLR_GREEN
                        st.markdown(
                            f'<div style="display:flex;align-items:center;margin:6px 0;gap:12px">'
                            f'<span style="min-width:150px;font-size:13px">{cat}</span>'
                            f'<div style="flex:1;background:#e2e8f0;border-radius:6px;height:22px;position:relative">'
                            f'<div style="width:{min(score, 100)}%;background:{bar_color};height:100%;'
                            f'border-radius:6px"></div>'
                            f'<span style="position:absolute;right:8px;top:2px;font-size:12px;'
                            f'color:#1e293b">{score:.1f}%</span></div></div>', unsafe_allow_html=True)
    else:
        st.info("No category scores available. Run the assessment pipeline first.")

    st.markdown("---")
    st.subheader("\U0001f4ca Confidence & Coverage Metrics")
    st.markdown(
        '<div class="tip-box">'
        'Confidence levels indicate how representative the scores are based on the number of assets assessed '
        'versus the total discoverable in the workspace. Higher coverage = higher confidence in the reported scores.</div>',
        unsafe_allow_html=True)

    # Query assessment coverage stats
    df_coverage = run_query(conn, f"""
        SELECT
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_table_scores) AS tables_scored,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.bronze_tables) AS tables_discovered,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_models_summary) AS models_scored,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_functions_summary) AS functions_scored,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_volumes_summary) AS volumes_scored,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_warehouses_summary) AS warehouses_scored,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_clusters_summary) AS clusters_scored,
            (SELECT COUNT(DISTINCT table_catalog) FROM {FULL_SCHEMA}.gold_table_scores) AS catalogs_assessed,
            (SELECT COUNT(*) FROM {FULL_SCHEMA}.gold_recommendations) AS total_recommendations
    """)

    if not df_coverage.empty:
        row = df_coverage.iloc[0]
        tables_scored = int(row.get('tables_scored') or 0)
        tables_discovered = int(row.get('tables_discovered') or 0)
        models_scored = int(row.get('models_scored') or 0)
        functions_scored = int(row.get('functions_scored') or 0)
        volumes_scored = int(row.get('volumes_scored') or 0)
        warehouses_scored = int(row.get('warehouses_scored') or 0)
        clusters_scored = int(row.get('clusters_scored') or 0)
        catalogs_assessed = int(row.get('catalogs_assessed') or 0)

        # Calculate coverage percentage
        table_coverage = round(tables_scored / tables_discovered * 100, 1) if tables_discovered > 0 else 0

        # Confidence level based on coverage
        if table_coverage >= 90:
            confidence_level = "HIGH"
            confidence_color = CLR_GREEN
            confidence_desc = "Comprehensive assessment covering 90%+ of discovered assets"
        elif table_coverage >= 60:
            confidence_level = "MEDIUM"
            confidence_color = CLR_AMBER
            confidence_desc = "Moderate coverage — some assets may be excluded due to permissions or filters"
        else:
            confidence_level = "LOW"
            confidence_color = CLR_RED
            confidence_desc = "Limited coverage — scores may not represent the full workspace state"

        # Display confidence banner
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:16px;margin-bottom:16px;display:flex;align-items:center;gap:20px">'
            f'<div style="text-align:center;min-width:120px">'
            f'<span style="font-size:24px;font-weight:700;color:{confidence_color}">{confidence_level}</span><br>'
            f'<span style="font-size:12px;color:#64748b">Confidence Level</span></div>'
            f'<div style="flex:1">'
            f'<span style="font-size:14px;font-weight:600;color:#1e293b">{confidence_desc}</span><br>'
            f'<span style="font-size:12px;color:#64748b">Based on {tables_scored:,} tables scored out of '
            f'{tables_discovered:,} discovered ({table_coverage}% coverage) across {catalogs_assessed} catalogs</span>'
            f'</div></div>', unsafe_allow_html=True)

        # Coverage breakdown by asset type
        coverage_data = [
            ("Tables/Views", tables_scored, tables_discovered, "Primary governance target"),
            ("ML Models", models_scored, models_scored, "REST API — all registered models"),
            ("UC Functions", functions_scored, functions_scored, "information_schema.routines"),
            ("Volumes", volumes_scored, volumes_scored, "information_schema.volumes"),
            ("SQL Warehouses", warehouses_scored, warehouses_scored, "system.compute"),
            ("Clusters", clusters_scored, clusters_scored, "system.compute (interactive only)"),
        ]

        st.markdown('<p style="font-weight:600;font-size:14px;margin:12px 0 8px">Assessment Coverage by Asset Type</p>',
                    unsafe_allow_html=True)
        for asset_type, scored, total, source in coverage_data:
            pct = round(scored / total * 100) if total > 0 else 0
            bar_color = CLR_GREEN if pct >= 90 else CLR_AMBER if pct >= 60 else CLR_RED
            status_text = f"{scored:,}" if scored == total else f"{scored:,} / {total:,} ({pct}%)"
            st.markdown(
                f'<div style="display:flex;align-items:center;margin:6px 0;gap:10px">'
                f'<span style="min-width:130px;font-size:13px;font-weight:500">{asset_type}</span>'
                f'<span style="min-width:100px;font-size:13px;color:{bar_color};font-weight:600">{status_text}</span>'
                f'<span style="font-size:11px;color:#94a3b8">Source: {source}</span>'
                f'</div>', unsafe_allow_html=True)

        # Methodology note
        with st.expander("\U0001f9ee Scoring Methodology Details"):
            st.markdown("""
**Scoring Approach:** Deterministic rule-based assessment (not statistical sampling).

Every discovered asset is evaluated against ALL applicable rules — there is no sampling or estimation.
Confidence reflects **coverage completeness**, not statistical uncertainty.

**Why coverage might be < 100%:**
- Assets excluded by permission boundaries (service principal access)
- System/internal schemas filtered out (`information_schema`, internal catalogs)
- Transient or ephemeral assets (job clusters, temporary tables)

**Score Interpretation:**
- Each rule produces a binary (0 or 1) or percentage score per asset
- Category scores = average of all rule scores within that category, normalized to 0–100%
- Overall score = simple average of the 4 core category scores
- RAG thresholds: RED < 40% < AMBER < 70% < GREEN

**Data Freshness:**
Assessment reflects the state at pipeline execution time. Re-run the pipeline to capture
recent changes (new tables, added documentation, permission updates).
            """)

    st.markdown("---")
    st.subheader("\U0001f527 Manage Rules")
    st.markdown(
        '<div class="tip-box">'
        'Add, edit, or remove assessment rules. Changes take effect on the next pipeline refresh. '
        'Rules define what the accelerator checks and how scores are weighted.</div>',
        unsafe_allow_html=True)

    rule_table_cols = get_assessment_rule_columns(conn, FULL_SCHEMA)
    missing_rule_cols = [c for c in ["enabled", "formula", "threshold"] if c not in rule_table_cols]
    if missing_rule_cols:
        st.info(
            f"The rules table is using a reduced schema. Missing columns: {', '.join(missing_rule_cols)}. "
            f"The app will use defaults for those fields until the table is extended."
        )

    rule_action = st.radio(
        "Select action", ["\U0001f4cb View Rules", "\u2795 Add Rule", "\u270f\ufe0f Edit Rule", "\U0001f5d1\ufe0f Delete Rule"],
        horizontal=True, key="rule_mgmt_action")

    if rule_action == "\u2795 Add Rule":
        st.markdown("#### Add New Assessment Rule")

        with st.expander("\U0001f4a1 Formula Helper — Available Columns & Examples", expanded=False):
            _helper_cat = st.selectbox("Show columns for category:", [
                "Metadata Readiness", "Governance", "Data Quality", "Performance",
                "Genie Readiness", "Functions", "ML Models", "Volumes",
                "Clusters", "SQL Warehouses"], key="formula_helper_cat")

            FORMULA_HELPER = {
                "Metadata Readiness": {
                    "columns": [
                        ("`has_table_description`", "INT", "1 if table has a non-empty comment"),
                        ("`total_columns`", "INT", "Total number of columns in the table"),
                        ("`documented_columns`", "INT", "Columns that have descriptions"),
                        ("`column_doc_pct`", "DECIMAL", "Percentage of documented columns (0-100)"),
                        ("`table_name`", "STRING", "Name of the table"),
                        ("`table_type`", "STRING", "MANAGED, EXTERNAL, VIEW, STREAMING_TABLE"),
                    ],
                    "examples": [
                        ("Table has description", "CASE WHEN has_table_description = 1 THEN 1 ELSE 0 END"),
                        (">=50% columns documented", "CASE WHEN column_doc_pct >= 50 THEN 1 ELSE 0 END"),
                        ("Table name is snake_case", "CASE WHEN table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END"),
                        ("Table name has prefix", "CASE WHEN table_name LIKE 'dim_%' OR table_name LIKE 'fact_%' THEN 1 ELSE 0 END"),
                    ]
                },
                "Governance": {
                    "columns": [
                        ("`tag_count`", "INT", "Number of governance tags on the table"),
                        ("`grant_count`", "INT", "Number of explicit privilege grants"),
                        ("`over_permissioned_grants`", "INT", "Count of ALL PRIVILEGES grants"),
                        ("`table_type`", "STRING", "MANAGED, EXTERNAL, VIEW"),
                        ("`table_owner`", "STRING", "Owner of the table"),
                    ],
                    "examples": [
                        ("Has at least N tags", "CASE WHEN tag_count >= 2 THEN 1 ELSE 0 END"),
                        ("Has explicit grants", "CASE WHEN grant_count > 0 THEN 1 ELSE 0 END"),
                        ("No over-permissioning", "CASE WHEN over_permissioned_grants = 0 THEN 1 ELSE 0 END"),
                        ("Is managed table", "CASE WHEN table_type = 'MANAGED' THEN 1 ELSE 0 END"),
                        ("Owner is not admin", "CASE WHEN table_owner != 'admin' THEN 1 ELSE 0 END"),
                    ]
                },
                "Data Quality": {
                    "columns": [
                        ("`data_source_format`", "STRING", "DELTA, PARQUET, CSV, JSON, etc."),
                        ("`last_altered`", "TIMESTAMP", "When the table was last modified"),
                        ("`created`", "TIMESTAMP", "When the table was created"),
                        ("`total_columns`", "INT", "Column count"),
                    ],
                    "examples": [
                        ("Is Delta format", "CASE WHEN data_source_format = 'DELTA' THEN 1 ELSE 0 END"),
                        ("Modified within N days", "CASE WHEN DATEDIFF(current_date(), last_altered) <= 30 THEN 1 ELSE 0 END"),
                        ("Has minimum columns", "CASE WHEN total_columns >= 3 THEN 1 ELSE 0 END"),
                    ]
                },
                "Performance": {
                    "columns": [
                        ("`data_source_format`", "STRING", "Table format (DELTA preferred)"),
                        ("`avg_duration_ms`", "DOUBLE", "Average query duration in milliseconds"),
                        ("`query_count`", "INT", "Number of queries against this table"),
                        ("`total_read_bytes`", "BIGINT", "Total bytes read from table"),
                    ],
                    "examples": [
                        ("Format supports optimization", "CASE WHEN data_source_format = 'DELTA' THEN 1 ELSE 0 END"),
                        ("Avg query under threshold", "CASE WHEN avg_duration_ms < 5000 THEN 1 ELSE 0 END"),
                    ]
                },
                "Genie Readiness": {
                    "columns": [
                        ("`has_table_description`", "INT", "Table has documentation"),
                        ("`column_doc_pct`", "DECIMAL", "Column documentation percentage"),
                        ("`naming_compliant`", "INT", "1 if business-friendly naming"),
                        ("`lineage_count`", "INT", "Number of lineage connections"),
                        ("`table_schema`", "STRING", "Schema name (gold/silver/bronze)"),
                        ("`table_name`", "STRING", "Table name (check for fact_/dim_ prefix)"),
                    ],
                    "examples": [
                        ("Column docs >= N%", "CASE WHEN column_doc_pct >= 80 THEN 1 ELSE 0 END"),
                        ("Has lineage", "CASE WHEN lineage_count > 0 THEN 1 ELSE 0 END"),
                        ("Gold layer schema", "CASE WHEN table_schema RLIKE '(gold|curated|mart|analytics)' THEN 1 ELSE 0 END"),
                        ("Dimensional naming", "CASE WHEN table_name RLIKE '^(fact_|dim_)' THEN 1 ELSE 0 END"),
                        ("Custom layer pattern", "CASE WHEN table_schema RLIKE '(gold|curated|mart|analytics|reporting|publish)' THEN 1 ELSE 0 END"),
                    ],
                    "threshold_note": "For Gold Layer Candidate (GENIE_004), threshold format: schemas=pattern1|pattern2;names=^(prefix1_|prefix2_)"
                },
                "Functions": {
                    "columns": [
                        ("`function_name`", "STRING", "Name of the UC function"),
                        ("`comment`", "STRING", "Function description/comment"),
                        ("`security_type`", "STRING", "DEFINER or INVOKER"),
                        ("`is_deterministic`", "STRING", "YES or NO"),
                    ],
                    "examples": [
                        ("Has description", "CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END"),
                        ("Is DEFINER mode", "CASE WHEN security_type = 'DEFINER' THEN 1 ELSE 0 END"),
                        ("Name is snake_case", "CASE WHEN function_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END"),
                    ]
                },
                "ML Models": {
                    "columns": [
                        ("`model_name`", "STRING", "Registered model name"),
                        ("`has_description`", "INT", "1 if model has documentation"),
                        ("`has_versions`", "INT", "1 if model has at least one version"),
                        ("`has_tags`", "INT", "1 if model has governance tags"),
                        ("`is_production_ready`", "INT", "1 if meets all production criteria"),
                    ],
                    "examples": [
                        ("Has description", "CASE WHEN has_description = 1 THEN 1 ELSE 0 END"),
                        ("Has multiple versions", "CASE WHEN has_versions = 1 THEN 1 ELSE 0 END"),
                        ("Production ready", "CASE WHEN is_production_ready = 1 THEN 1 ELSE 0 END"),
                    ]
                },
                "Volumes": {
                    "columns": [
                        ("`volume_name`", "STRING", "Name of the UC volume"),
                        ("`comment`", "STRING", "Volume description"),
                        ("`volume_type`", "STRING", "MANAGED or EXTERNAL"),
                    ],
                    "examples": [
                        ("Has description", "CASE WHEN comment IS NOT NULL THEN 1 ELSE 0 END"),
                        ("Is managed type", "CASE WHEN volume_type = 'MANAGED' THEN 1 ELSE 0 END"),
                        ("Name is snake_case", "CASE WHEN volume_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END"),
                    ]
                },
                "Clusters": {
                    "columns": [
                        ("`data_security_mode`", "STRING", "UC security mode (SINGLE_USER, USER_ISOLATION, etc.)"),
                        ("`dbr_version`", "STRING", "Full Databricks Runtime version string"),
                        ("`auto_termination_minutes`", "INT", "Minutes before auto-stop"),
                        ("`has_cluster_policy`", "INT", "1 if policy attached"),
                        ("`has_autoscaling`", "INT", "1 if min_workers < max_workers"),
                        ("`has_tags`", "INT", "1 if custom tags are set"),
                    ],
                    "examples": [
                        ("Has security mode", "CASE WHEN data_security_mode IS NOT NULL THEN 1 ELSE 0 END"),
                        ("Auto-term under N min", "CASE WHEN auto_termination_minutes <= 120 THEN 1 ELSE 0 END"),
                        ("Has policy", "CASE WHEN has_cluster_policy = 1 THEN 1 ELSE 0 END"),
                    ]
                },
                "SQL Warehouses": {
                    "columns": [
                        ("`warehouse_type`", "STRING", "SERVERLESS, PRO, CLASSIC"),
                        ("`warehouse_size`", "STRING", "2X-Small, X-Small, Small, Medium, Large, etc."),
                        ("`is_serverless`", "INT", "1 if type is SERVERLESS"),
                        ("`has_scaling`", "INT", "1 if max_num_clusters > 1"),
                        ("`has_tags`", "INT", "1 if tags are configured"),
                        ("`auto_stop_mins`", "INT", "Minutes before auto-stop"),
                    ],
                    "examples": [
                        ("Is serverless", "CASE WHEN is_serverless = 1 THEN 1 ELSE 0 END"),
                        ("Auto-stop efficient", "CASE WHEN auto_stop_mins <= 15 THEN 1 ELSE 0 END"),
                        ("Has scaling", "CASE WHEN has_scaling = 1 THEN 1 ELSE 0 END"),
                    ]
                },
            }

            helper = FORMULA_HELPER.get(_helper_cat, {})
            if helper:
                st.markdown("**Available Columns:**")
                _col_rows = "".join(
                    f"<tr><td><code>{c[0]}</code></td><td>{c[1]}</td><td>{c[2]}</td></tr>"
                    for c in helper.get("columns", []))
                st.markdown(
                    f'<table style="width:100%;font-size:13px;border-collapse:collapse">'
                    f'<tr style="background:#f1f5f9"><th style="text-align:left;padding:6px">Column</th>'
                    f'<th style="text-align:left;padding:6px">Type</th>'
                    f'<th style="text-align:left;padding:6px">Description</th></tr>'
                    f'{_col_rows}</table>', unsafe_allow_html=True)

                st.markdown("**Example Formulas:**")
                for ex_name, ex_formula in helper.get("examples", []):
                    st.markdown(
                        f'<div style="margin:4px 0;padding:6px 12px;background:#f8fafc;'
                        f'border-radius:6px;border-left:3px solid #3b82f6;font-size:13px">'
                        f'<strong>{ex_name}:</strong><br/>'
                        f'<code style="color:#1e40af">{ex_formula}</code></div>',
                        unsafe_allow_html=True)

                st.markdown(
                    '<div style="margin-top:12px;padding:10px;background:#fffbeb;'
                    'border-radius:8px;border:1px solid #fbbf24;font-size:12px">'
                    '<strong>\U0001f4dd Formula Tips:</strong><br/>'
                    '\u2022 Formulas should return <strong>1</strong> (pass) or <strong>0</strong> (fail)<br/>'
                    '\u2022 Use <code>threshold</code> keyword for configurable values (e.g., days, percentages)<br/>'
                    '\u2022 Use SQL-compatible syntax (CASE WHEN, RLIKE, LIKE, IN)<br/>'
                    '\u2022 Rule takes effect after next pipeline refresh</div>',
                    unsafe_allow_html=True)

        with st.form("add_rule_form", clear_on_submit=True):
            ar_col1, ar_col2 = st.columns(2)
            with ar_col1:
                new_rule_id = st.text_input("Rule ID", placeholder="e.g., META_004, GOV_005, CUSTOM_001")
                new_category = st.selectbox("Category", [
                    "Metadata Readiness", "Governance", "Data Quality", "Performance",
                    "Genie Readiness", "Functions", "ML Models", "Volumes",
                    "Clusters", "SQL Warehouses"])
                new_severity = st.selectbox("Severity", ["HIGH", "MEDIUM", "LOW"])
                new_weight = st.number_input("Weight", min_value=1, max_value=25, value=10)
            with ar_col2:
                new_rule_name = st.text_input("Rule Name", placeholder="e.g., Column Naming Convention")
                new_description = st.text_area("Description", placeholder="What this rule checks...", height=68)
                new_formula = st.text_input("Scoring Formula", placeholder="e.g., CASE WHEN column_count > 5 THEN 1 ELSE 0 END")
                new_threshold = st.text_input("Threshold (optional)", placeholder="e.g., 30, 80, 15",
                    help="Single value (30, 80, 120) for simple checks. "
                         "For pattern rules: schemas=gold|curated|mart;names=^(fact_|dim_)")

            submitted = st.form_submit_button("\u2795 Add Rule", type="primary")
            if submitted:
                if not new_rule_id or not new_rule_name or not new_description:
                    st.error("Please fill in Rule ID, Rule Name, and Description.")
                else:
                    try:
                        _esc_name = new_rule_name.replace("'", "''")
                        _esc_desc = new_description.replace("'", "''")
                        _esc_formula = new_formula.replace("'", "''") if new_formula else ""
                        _thresh_val = f"'{new_threshold}'" if new_threshold else "NULL"
                        insert_cols = ["rule_id", "category", "rule_name", "description", "weight", "severity"]
                        insert_vals = [
                            f"'{new_rule_id}'",
                            f"'{new_category}'",
                            f"'{_esc_name}'",
                            f"'{_esc_desc}'",
                            str(new_weight),
                            f"'{new_severity}'",
                        ]
                        if "enabled" in rule_table_cols:
                            insert_cols.append("enabled")
                            insert_vals.append("TRUE")
                        if "formula" in rule_table_cols:
                            insert_cols.append("formula")
                            insert_vals.append(f"'{_esc_formula}'")
                        if "threshold" in rule_table_cols:
                            insert_cols.append("threshold")
                            insert_vals.append(_thresh_val)
                        run_query(conn,
                            f"INSERT INTO {FULL_SCHEMA}.assessment_rules "
                            f"({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})")
                        st.success(f"\u2705 Rule **{new_rule_id}** added successfully! Refresh the page to see it below.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Failed to add rule: {e}")

    elif rule_action == "\u270f\ufe0f Edit Rule":
        st.markdown("#### Edit Existing Rule")
        df_edit_rules = get_assessment_rules(conn, FULL_SCHEMA)
        if not df_edit_rules.empty:
            edit_rule_id = st.selectbox("Select Rule to Edit",
                df_edit_rules['rule_id'].tolist(),
                format_func=lambda x: f"{x} — {df_edit_rules[df_edit_rules['rule_id']==x]['rule_name'].iloc[0]}",
                key="edit_rule_select")

            existing = df_edit_rules[df_edit_rules['rule_id'] == edit_rule_id].iloc[0]
            try:
                _existing_weight = int(existing['weight']) if pd.notna(existing['weight']) else 1
            except Exception:
                _existing_weight = 1
            _existing_weight = max(1, min(25, _existing_weight))

            with st.form("edit_rule_form"):
                er_col1, er_col2 = st.columns(2)
                _all_cats = ["Metadata Readiness", "Governance", "Data Quality", "Performance",
                             "Genie Readiness", "Functions", "ML Models", "Volumes",
                             "Clusters", "SQL Warehouses"]
                with er_col1:
                    edit_category = st.selectbox("Category", _all_cats,
                        index=_all_cats.index(existing['category']) if existing['category'] in _all_cats else 0)
                    edit_severity = st.selectbox("Severity", ["HIGH", "MEDIUM", "LOW"],
                        index=["HIGH", "MEDIUM", "LOW"].index(existing['severity']) if existing['severity'] in ["HIGH", "MEDIUM", "LOW"] else 1)
                    edit_weight = st.number_input("Weight", min_value=1, max_value=25, value=_existing_weight)
                    edit_enabled = st.checkbox(
                        "Enabled",
                        value=bool(existing.get('enabled', True)),
                        disabled="enabled" not in rule_table_cols,
                    )
                with er_col2:
                    edit_rule_name = st.text_input("Rule Name", value=existing['rule_name'])
                    edit_description = st.text_area("Description", value=existing['description'], height=68)
                    edit_formula = st.text_input(
                        "Scoring Formula",
                        value=str(existing.get('formula') or ''),
                        disabled="formula" not in rule_table_cols,
                    )
                    edit_threshold = st.text_input(
                        "Threshold",
                        value=str(existing.get('threshold') or ''),
                        help="Format depends on rule type: single number (e.g., 30, 80, 120) for simple thresholds, "
                             "or structured pattern for Gold Layer: schemas=pattern1|pattern2;names=^(prefix1_|prefix2_)",
                        disabled="threshold" not in rule_table_cols,
                    )

                edit_submitted = st.form_submit_button("\U0001f4be Save Changes", type="primary")
                if edit_submitted:
                    try:
                        _esc_en = edit_rule_name.replace("'", "''")
                        _esc_ed = edit_description.replace("'", "''")
                        _esc_ef = edit_formula.replace("'", "''") if edit_formula else ""
                        _thresh = f"'{edit_threshold}'" if edit_threshold else "NULL"
                        update_clauses = [
                            f"category = '{edit_category}'",
                            f"rule_name = '{_esc_en}'",
                            f"description = '{_esc_ed}'",
                            f"weight = {edit_weight}",
                            f"severity = '{edit_severity}'",
                        ]
                        if "enabled" in rule_table_cols:
                            update_clauses.append(f"enabled = {str(edit_enabled).upper()}")
                        if "formula" in rule_table_cols:
                            update_clauses.append(f"formula = '{_esc_ef}'")
                        if "threshold" in rule_table_cols:
                            update_clauses.append(f"threshold = {_thresh}")
                        run_query(conn,
                            f"UPDATE {FULL_SCHEMA}.assessment_rules SET "
                            f"{', '.join(update_clauses)} "
                            f"WHERE rule_id = '{edit_rule_id}'")
                        st.success(f"\u2705 Rule **{edit_rule_id}** updated! Refresh to see changes.")
                    except Exception as e:
                        st.error(f"Failed to update rule: {e}")

    elif rule_action == "\U0001f5d1\ufe0f Delete Rule":
        st.markdown("#### Delete Rule")
        df_del_rules = run_query(conn,
            f"SELECT rule_id, category, rule_name, severity "
            f"FROM {FULL_SCHEMA}.assessment_rules ORDER BY category, rule_id")
        if not df_del_rules.empty:
            del_rule_id = st.selectbox("Select Rule to Delete",
                df_del_rules['rule_id'].tolist(),
                format_func=lambda x: f"{x} — {df_del_rules[df_del_rules['rule_id']==x]['rule_name'].iloc[0]} [{df_del_rules[df_del_rules['rule_id']==x]['severity'].iloc[0]}]",
                key="del_rule_select")

            st.warning(f"\u26a0\ufe0f This will permanently delete rule **{del_rule_id}**. This cannot be undone.")
            if st.button(f"\U0001f5d1\ufe0f Confirm Delete {del_rule_id}", type="primary", key="confirm_del_rule"):
                try:
                    run_query(conn, f"DELETE FROM {FULL_SCHEMA}.assessment_rules WHERE rule_id = '{del_rule_id}'")
                    st.success(f"\u2705 Rule **{del_rule_id}** deleted. Refresh the page to update the list.")
                except Exception as e:
                    st.error(f"Failed to delete: {e}")

    st.markdown("---")
    st.subheader("Defined Rules")

    # KPI Formula definitions for each rule
    RULE_FORMULAS = {
        "META_001": "Score = 1 if table has a non-empty COMMENT/description, else 0",
        "META_002": "Score = documented_columns / total_columns × 100 (percentage of columns with comments)",
        "META_003": "Score = 1 if table_name matches ^[a-z][a-z0-9_]*$ (lowercase snake_case), else 0",
        "GOV_001": "Score = 1 if table has at least one governance tag applied, else 0",
        "GOV_002": "Score = 1 if explicit privilege grants exist (not inherited only), else 0",
        "GOV_003": "Score = 0 if ALL PRIVILEGES is granted (over-permissioned), else 1",
        "GOV_004": "Score = 1 if table_type = 'MANAGED', else 0 (external/foreign penalized)",
        "DQ_001": "Score = 1 if (current_date − last_modified_date) ≤ 30 days, else 0",
        "DQ_002": "Score = 1 if data_source_format = 'DELTA', else 0",
        "GENIE_001": "Score = 1 if table name has no numeric suffixes or cryptic abbreviations (>3 consecutive consonants), else 0",
        "GENIE_002": "Score = 1 if table has upstream or downstream lineage connections, else 0",
        "GENIE_003": "Score = 1 if column_doc_pct ≥ 80%, else 0",
        "GENIE_004": "Score = 1 if table_schema matches (gold|curated|mart|analytics) OR table_name matches ^(fact_|dim_). Configure patterns in Threshold field.",
        "COMP_001": "Score = 1 if asset has at least one governance/classification tag, else 0",
        "COMP_002": "Score = 1 if explicit Unity Catalog privileges are defined, else 0",
        "COMP_003": "Score = 1 if ALL PRIVILEGES is not granted, else 0",
        "COMP_004": "Score = 1 if table has description AND column_doc_pct ≥ 80%, else 0",
        "COMP_005": "Score = 1 if lineage_count > 0 for auditability and traceability, else 0",
        "COMP_006": "Legacy naming-pattern compliance rule retained for backward compatibility; prefer Databricks-native controls in app scoring",
        "COMP_007": "Score = 1 if table_type = 'MANAGED' AND data_source_format = 'DELTA', else 0",
        "COMP_008": "Score = 1 if last_altered is within threshold days, else 0",
        "PERF_001": "Score = 1 if format is DELTA (enables OPTIMIZE, Z-ORDER, liquid clustering), else 0",
        "PERF_002": "Category = GOOD if avg_duration < 1s | MODERATE if 1−5s | POOR if > 5s",
        # UC Functions rules
        "FN_001": "Score = 1 if function has a non-empty COMMENT/description, else 0",
        "FN_002": "Score = 1 if function_name matches ^[a-z][a-z0-9_]*$ (lowercase snake_case), else 0",
        "FN_003": "Score = 1 if function security_type = 'DEFINER', else 0 (DEFINER mode for governed execution)",
        # ML Models rules
        "ML_001": "Score = 1 if model has a non-empty COMMENT/description, else 0",
        "ML_002": "Score = 1 if model_name matches ^[a-z][a-z0-9_]*$ (lowercase snake_case), else 0",
        "ML_003": "Score = 1 if model has > 1 version (versioning practiced), else 0",
        # Volumes rules
        "VOL_001": "Score = 1 if volume has a non-empty COMMENT/description, else 0",
        "VOL_002": "Score = 1 if volume_type = 'MANAGED' (managed preferred over external), else 0",
        # Clusters rules
        "CLU_001": "Score = 1 if data_security_mode is set (UC-enabled), else 0",
        "CLU_002": "Score = 1 if DBR version ≥ 15.x (current runtime), else 0",
        "CLU_003": "Score = 1 if auto_termination_minutes ≤ 120, else 0",
        "CLU_004": "Score = 1 if cluster uses a cluster policy, else 0",
        "CLU_005": "Score = 1 if autoscaling is enabled (min_workers < max_workers), else 0",
        "CLU_006": "Score = 1 if cluster has at least one custom tag, else 0",
        # SQL Warehouses rules
        "WH_001": "Score = 1 if warehouse_type = 'SERVERLESS', else 0",
        "WH_002": "Score = 1 if auto_stop_mins ≤ 15 (efficient auto-stop), else 0",
        "WH_003": "Score = 1 if warehouse has scaling configured (max_clusters > 1), else 0",
    }

    df_rules = get_assessment_rules(conn, FULL_SCHEMA)

    if df_rules.empty:
        st.warning("No assessment rules found. Run the pipeline notebook first.")
    else:
        fig_w = px.bar(df_rules, x="rule_name", y="weight", color="category",
                       title="Rule Weights by Category",
                       color_discrete_sequence=px.colors.qualitative.Set2)
        fig_w.update_layout(height=350, xaxis_tickangle=-45, **CHART_LAYOUT)
        st.plotly_chart(fig_w, use_container_width=True)

        sev_class = {"HIGH": "sev-high", "MEDIUM": "sev-medium", "LOW": "sev-low"}
        cat_icons = {
            "Metadata Readiness": "\U0001f4dd",
            "Governance": "\U0001f6e1\ufe0f",
            "Data Quality": "\u2705",
            "Performance": "\u26a1",
            "Genie Readiness": "\U0001f916",
            "UC Functions": "\u2699\ufe0f",
            "ML Models": "\U0001f9e0",
            "Volumes": "\U0001f4e6",
            "Clusters": "\U0001f5a5\ufe0f",
            "SQL Warehouses": "\U0001f3ed",
        }
        for cat_name, grp in df_rules.groupby("category", sort=False):
            icon = cat_icons.get(cat_name, "\U0001f4cb")
            st.markdown(f'<div class="section-header">{icon} {cat_name}</div>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            for idx, (_, rule) in enumerate(grp.iterrows()):
                sev = rule["severity"]
                formula = str(rule.get("formula") or RULE_FORMULAS.get(rule["rule_id"], ""))
                formula_html = (
                    f'<div style="margin-top:8px;padding:8px 12px;background:#f1f5f9;'
                    f'border-radius:6px;font-size:12px;color:#334155;'
                    f'font-family:monospace;">'
                    f'<strong style="color:#1e40af;">Formula:</strong> {formula}</div>'
                ) if formula else ""
                _is_enabled = rule.get("enabled", True)
                _threshold = rule.get("threshold", "")
                _enabled_badge = '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:4px;font-size:11px">ACTIVE</span>' if _is_enabled else '<span style="background:#fef2f2;color:#991b1b;padding:2px 8px;border-radius:4px;font-size:11px">DISABLED</span>'
                _threshold_html = f'<span style="color:#64748b">Threshold: {_threshold}</span>' if _threshold and str(_threshold) != 'None' else ''
                with (col_a if idx % 2 == 0 else col_b):
                    st.markdown(
                        f'<div class="rule-card" style="opacity:{"1" if _is_enabled else "0.5"}">'
                        f'<div class="rule-id">{rule["rule_id"]} {_enabled_badge}</div>'
                        f'<div class="rule-name">{rule["rule_name"]}</div>'
                        f'<div class="rule-desc">{rule["description"]}</div>'
                        f'{formula_html}'
                        f'<div class="rule-meta">'
                        f'<span class="{sev_class.get(sev, "")}">Severity: {sev}</span>'
                        f'<span style="color:#64748b">Weight: {rule["weight"]}</span>'
                        f'{_threshold_html}'
                        f'</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("\U0001f4d6 Technical Deep-Dive: KPI Calculation Methodology")

    with st.expander("\U0001f522 Per-Table Score Derivation", expanded=False):
        st.markdown("""
**Each table receives 4 sub-scores (0–5 scale) that combine into an overall percentage (0–100%):**

| Category | Max Points | Components | Formula |
|----------|-----------|------------|---------|
| **Metadata** | 5.0 | Description (2pts) + Column Doc % (2pts) + Naming (1pt) | `has_desc×2 + (doc_cols/total_cols)×2 + naming×1` |
| **Governance** | 5.0 | Tags (1.5pts) + Grants (1.5pts) + No Over-Permission (1pt) + Managed (1pt) | `has_tags×1.5 + has_grants×1.5 + no_overperm×1 + is_managed×1` |
| **Data Quality** | 5.0 | Delta Format (2.5pts) + Freshness <30d (2.5pts) | `is_delta×2.5 + is_fresh×2.5` |
| **Genie Readiness** | 100 | Description (20) + Col Docs (30) + Naming (15) + Lineage (15) + Gold Layer (20) | Composite weighted sum |

**Overall Table Score** = `(Metadata/5×25) + (Governance/5×25) + (Quality/5×25) + (Genie/100×25)` → 0 to 100%
        """)

    with st.expander("\U0001f3af Category Score Aggregation", expanded=False):
        st.markdown("""
**From individual table scores to workspace-level category percentages:**

1. **Per-catalog scores**: Average all table scores within each catalog, normalize to 0–100%
2. **Workspace-level ('ALL')**: Average across ALL tables regardless of catalog
3. **Overall Readiness**: Simple average of the 4 core categories at workspace level

```
Category Score (%) = AVG(table_category_score) / max_possible × 100
Overall (%) = (Metadata% + Governance% + Data Quality% + Genie%) / 4
```

**Why simple average?** Equal weighting ensures no single dimension dominates.
A table can score well on quality but poorly on documentation — both matter equally for production readiness.
        """)

    with st.expander("\U0001f6a6 RAG Threshold Logic", expanded=False):
        st.markdown("""
**Three-tier classification applied at every level (table, category, overall):**

| Level | Threshold | Interpretation | Action Required |
|-------|-----------|---------------|-----------------|
| **GREEN** | ≥ 70% | Production-ready, well-governed | Monitor & maintain |
| **AMBER** | 40–70% | Functional but gaps exist | Plan remediation within quarter |
| **RED** | < 40% | Critical gaps blocking adoption | Immediate action required |

**Thresholds are consistent** across all dimensions — same rules whether looking at a single table, a catalog, or the entire workspace.

**Why 40/70?** Based on industry governance maturity models:
- 70%+ indicates systematic governance practices are in place
- 40–70% indicates ad-hoc governance with inconsistent application
- <40% indicates governance gaps that create compliance/operational risk
        """)

    with st.expander("\U0001f9e9 Extended Category Scoring (Functions, Models, Volumes, Compute)", expanded=False):
        st.markdown("""
**These categories are assessed independently and do NOT contribute to the overall score:**

| Category | Score Formula | Max | Key Rules |
|----------|--------------|-----|-----------|
| **UC Functions** | `description×25 + naming×20 + deterministic×15 + security×20 + language×20` | 100 | FN_001–FN_003 |
| **ML Models** | `description×25 + naming×20 + versions×20 + tags×15 + prod_ready×20` | 100 | ML_001–ML_003 |
| **Volumes** | `description×25 + managed×25 + naming×25 + tags×25` | 100 | VOL_001–VOL_002 |
| **Clusters** | `security_mode + current_dbr + auto_term + policy + autoscaling + tags` | 100 | CLU_001–CLU_006 |
| **SQL Warehouses** | `serverless + modern_type + auto_stop + scaling + tags + channel` | 100 | WH_001–WH_003 |

**Why separate?** These assets have different governance characteristics than tables/views.
They're supplementary indicators that inform operational readiness rather than data readiness.
        """)

    with st.expander("\U0001f50d Data Sources & Pipeline Architecture", expanded=False):
        st.markdown(f"""
**Three-layer medallion architecture:**

**Bronze (Raw Ingestion)**
- `system.information_schema.tables` → 1,209 tables/views
- `system.information_schema.columns` → 11,336 columns
- `system.information_schema.table_tags` / `column_tags` → governance tags
- `system.information_schema.table_privileges` → access grants
- `system.billing.usage` → FinOps data (30-day window)
- `system.query.history` → performance data (30-day window)
- `system.access.table_lineage` → data lineage (30-day window)
- Databricks REST API → registered ML models (74 models)
- `system.information_schema.routines` → UC functions
- `system.information_schema.volumes` → UC volumes
- `system.compute.clusters` / `warehouses` → compute assets

**Silver (Assessment)**
- Each bronze source → deterministic rule evaluation → scored assessment table
- Every discovered asset is evaluated (no sampling)

**Gold (Aggregation)**
- Per-table scores (`gold_table_scores`)
- Per-catalog category rollups (`gold_category_scores`)
- Workspace-level executive summary (`gold_executive_summary`)
- Actionable recommendations (`gold_recommendations`)

**Schema**: `{FULL_SCHEMA}`
        """)

# ===========================================================================
# TAB 8 — ACTIONS (with sub-navigation)
# ===========================================================================
with tab_actions:
    st.header("Actions")

    action_mode = st.radio(
        "Select action type",
        ["\U0001f527 Quick Fix", "\U0001f4e5 Export & Scripts", "\U0001f4e4 Bulk Import", "\U0001f504 Refresh Pipeline"],
        horizontal=True, key="action_mode_radio")

    st.markdown("---")

    # -------------------------------------------------------------------
    # SUB-VIEW 1: Quick Fix Actions
    # -------------------------------------------------------------------
    if action_mode == "\U0001f527 Quick Fix":
        st.markdown(
            '<div class="tip-box">'
            'Run actions directly against your Unity Catalog to fix assessment gaps. '
            'Changes take effect immediately. Re-run the assessment pipeline to update scores.'
            '</div>', unsafe_allow_html=True)

        act1, act2 = st.columns(2)

        with act1:
            st.markdown(
                '<div class="action-card">'
                '<h4>\U0001f4dd Add Table Description</h4>'
                '<p>Set a COMMENT on tables missing descriptions to improve metadata and Genie readiness.</p>'
                '</div>', unsafe_allow_html=True)

            df_no_desc = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name "
                f"FROM {FULL_SCHEMA}.silver_metadata_assessment "
                f"WHERE has_table_description = 0 {FILTER_AND} "
                f"ORDER BY table_catalog, table_schema, table_name")
            if df_no_desc.empty:
                st.success("All tables have descriptions!")
            else:
                opts = [f"{r.table_catalog}.{r.table_schema}.{r.table_name}" for _, r in df_no_desc.iterrows()]
                sel_table = st.selectbox("Select table", opts, key="act_desc_table")
                new_desc = st.text_area("Description", key="act_desc_text",
                                         placeholder="Enter a business-friendly table description...")
                if st.button("\u2705 Apply Description", key="act_desc_btn", type="primary"):
                    if new_desc.strip():
                        safe_desc = new_desc.replace("'", "''")
                        result = run_action(conn, f"COMMENT ON TABLE {sel_table} IS '{safe_desc}'")
                        if result == "OK":
                            st.markdown('<div class="success-box">Description applied successfully!</div>',
                                        unsafe_allow_html=True)
                            st.cache_data.clear()
                        else:
                            st.markdown(f'<div class="error-box">Error: {result[:200]}</div>',
                                        unsafe_allow_html=True)
                    else:
                        st.warning("Please enter a description.")

        with act2:
            st.markdown(
                '<div class="action-card">'
                '<h4>\U0001f6e1\ufe0f Add Governance Tags</h4>'
                '<p>Apply tags to tables for classification, governance, and access control.</p>'
                '</div>', unsafe_allow_html=True)

            df_no_tags = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name "
                f"FROM {FULL_SCHEMA}.silver_governance_assessment "
                f"WHERE has_tags = 0 {FILTER_AND} "
                f"ORDER BY table_catalog, table_schema, table_name")
            if df_no_tags.empty:
                st.success("All tables have tags!")
            else:
                opts_t = [f"{r.table_catalog}.{r.table_schema}.{r.table_name}" for _, r in df_no_tags.iterrows()]
                sel_tag_table = st.selectbox("Select table", opts_t, key="act_tag_table")
                tc1, tc2 = st.columns(2)
                with tc1:
                    tag_name = st.text_input("Tag name", key="act_tag_name", placeholder="e.g. sensitivity")
                with tc2:
                    tag_value = st.text_input("Tag value", key="act_tag_val", placeholder="e.g. high")
                if st.button("\u2705 Apply Tag", key="act_tag_btn", type="primary"):
                    if tag_name.strip() and tag_value.strip():
                        safe_name = tag_name.strip().replace("'", "''")
                        safe_val = tag_value.strip().replace("'", "''")
                        result = run_action(conn, f"ALTER TABLE {sel_tag_table} SET TAGS ('{safe_name}' = '{safe_val}')")
                        if result == "OK":
                            st.markdown('<div class="success-box">Tag applied successfully!</div>',
                                        unsafe_allow_html=True)
                            st.cache_data.clear()
                        else:
                            st.markdown(f'<div class="error-box">Error: {result[:200]}</div>',
                                        unsafe_allow_html=True)
                    else:
                        st.warning("Please enter both tag name and value.")

        st.markdown("---")
        act3, act4 = st.columns(2)

        with act3:
            st.markdown(
                '<div class="action-card">'
                '<h4>\u26a1 Run OPTIMIZE</h4>'
                '<p>Optimize Delta tables to compact small files and improve query performance.</p>'
                '</div>', unsafe_allow_html=True)

            df_delta = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name "
                f"FROM {FULL_SCHEMA}.silver_quality_assessment "
                f"WHERE is_delta = 1 {FILTER_AND} "
                f"ORDER BY table_catalog, table_schema, table_name")
            if df_delta.empty:
                st.info("No Delta tables found in the current scope.")
            else:
                opts_o = [f"{r.table_catalog}.{r.table_schema}.{r.table_name}" for _, r in df_delta.iterrows()]
                sel_opt_table = st.selectbox("Select Delta table", opts_o, key="act_opt_table")
                if st.button("\u26a1 Run OPTIMIZE", key="act_opt_btn", type="primary"):
                    with st.spinner("Running OPTIMIZE..."):
                        result = run_action(conn, f"OPTIMIZE {sel_opt_table}")
                        if result == "OK":
                            st.markdown('<div class="success-box">OPTIMIZE completed!</div>',
                                        unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="error-box">Error: {result[:200]}</div>',
                                        unsafe_allow_html=True)

        with act4:
            st.markdown(
                '<div class="action-card">'
                '<h4>\U0001f4cb Add Column Description</h4>'
                '<p>Document individual columns to improve discoverability and Genie readiness.</p>'
                '</div>', unsafe_allow_html=True)

            df_low_doc = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name, column_doc_pct "
                f"FROM {FULL_SCHEMA}.silver_metadata_assessment "
                f"WHERE column_doc_pct < 80 AND total_columns > 0 {FILTER_AND} "
                f"ORDER BY column_doc_pct ASC LIMIT 200")
            if df_low_doc.empty:
                st.success("All tables have >= 80% column documentation!")
            else:
                opts_c = [f"{r.table_catalog}.{r.table_schema}.{r.table_name} ({r.column_doc_pct:.0f}%)"
                          for _, r in df_low_doc.iterrows()]
                sel_col_table_display = st.selectbox("Select under-documented table", opts_c, key="act_col_table")
                sel_col_table = sel_col_table_display.rsplit(" (", 1)[0]

                parts = sel_col_table.split(".")
                if len(parts) == 3:
                    df_cols = run_query(conn,
                        f"SELECT column_name, comment FROM {FULL_SCHEMA}.bronze_columns "
                        f"WHERE table_catalog = '{parts[0]}' AND table_schema = '{parts[1]}' "
                        f"AND table_name = '{parts[2]}' AND (comment IS NULL OR comment = '') "
                        f"ORDER BY ordinal_position")
                    if not df_cols.empty:
                        undoc_cols = df_cols["column_name"].tolist()
                        sel_col = st.selectbox("Column", undoc_cols, key="act_col_name")
                        col_desc = st.text_input("Column description", key="act_col_desc",
                                                 placeholder="e.g. Unique customer identifier")
                        if st.button("\u2705 Apply Column Description", key="act_col_btn", type="primary"):
                            if col_desc.strip():
                                safe_cd = col_desc.strip().replace("'", "''")
                                result = run_action(conn,
                                    f"ALTER TABLE {sel_col_table} ALTER COLUMN {sel_col} COMMENT '{safe_cd}'")
                                if result == "OK":
                                    st.markdown('<div class="success-box">Column description applied!</div>',
                                                unsafe_allow_html=True)
                                    st.cache_data.clear()
                                else:
                                    st.markdown(f'<div class="error-box">Error: {result[:200]}</div>',
                                                unsafe_allow_html=True)
                            else:
                                st.warning("Please enter a column description.")
                    else:
                        st.success("All columns in this table are documented!")


        st.markdown("---")
        act5, act6 = st.columns(2)

        with act5:
            st.markdown(
                '<div class="action-card">'
                '<h4>\U0001f4e6 External / Foreign Tables</h4>'
                '<p>Review tables that are external or foreign (not UC managed). '
                'Managed tables provide better governance, lineage tracking, and lifecycle management.</p>'
                '</div>', unsafe_allow_html=True)

            df_ext = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name "
                f"FROM {FULL_SCHEMA}.silver_governance_assessment "
                f"WHERE is_managed = 0 {FILTER_AND} "
                f"ORDER BY table_catalog, table_schema, table_name")
            if df_ext.empty:
                st.success("All tables are UC managed!")
            else:
                st.markdown(
                    f'<div class="warn-box">{len(df_ext)} external/foreign table(s) found. '
                    f'Consider migrating to managed tables using CREATE TABLE ... AS SELECT.</div>',
                    unsafe_allow_html=True)
                st.dataframe(df_ext, use_container_width=True, height=250)

        with act6:
            st.markdown(
                '<div class="action-card">'
                '<h4>\U0001f50d Managed Table Overview</h4>'
                '<p>Summary of managed vs non-managed tables across your catalogs.</p>'
                '</div>', unsafe_allow_html=True)

            df_mgd_summary = run_query(conn,
                f"SELECT table_catalog, "
                f"SUM(CASE WHEN is_managed = 1 THEN 1 ELSE 0 END) AS managed_count, "
                f"SUM(CASE WHEN is_managed = 0 THEN 1 ELSE 0 END) AS external_count, "
                f"COUNT(*) AS total, "
                f"ROUND(AVG(is_managed) * 100, 1) AS pct_managed "
                f"FROM {FULL_SCHEMA}.silver_governance_assessment "
                f"WHERE 1=1 {FILTER_AND} "
                f"GROUP BY table_catalog ORDER BY pct_managed ASC")
            if not df_mgd_summary.empty:
                st.dataframe(df_mgd_summary, use_container_width=True, height=250)
            else:
                st.info("No governance assessment data available.")



        # -------------------------------------------------------------------
        # AI-Powered Quick Fix: Auto-Generate Descriptions
        # -------------------------------------------------------------------
        st.markdown("---")
        st.markdown(
            '<div style="background:linear-gradient(135deg,#7c3aed 0%,#a78bfa 100%);'
            'border-radius:12px;padding:20px 24px;margin:10px 0">'
            '<h4 style="color:white !important;margin:0 0 8px">\U0001f9e0 AI-Powered Quick Fix</h4>'
            '<p style="color:#e9d5ff;font-size:13px;margin:0">'
            'Use AI to auto-generate descriptions for your undocumented tables. '
            'Select a table below and let AI analyze its schema to produce a meaningful description.</p>'
            '</div>', unsafe_allow_html=True)

        ai_qf1, ai_qf2 = st.columns(2)
        with ai_qf1:
            st.markdown(
                '<div class="action-card" style="border-left-color:#8b5cf6">'
                '<h4>\U0001f9e0 AI Table Description</h4>'
                '<p>Auto-generate a business-friendly table description using AI analysis of column names and types.</p>'
                '</div>', unsafe_allow_html=True)

            df_ai_qf_tables = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name "
                f"FROM {FULL_SCHEMA}.silver_metadata_assessment "
                f"WHERE has_table_description = 0 {FILTER_AND} "
                f"ORDER BY table_catalog, table_schema, table_name LIMIT 50")
            if df_ai_qf_tables.empty:
                st.success("All tables have descriptions!")
            else:
                opts_qf_ai = [f"{r.table_catalog}.{r.table_schema}.{r.table_name}" for _, r in df_ai_qf_tables.iterrows()]
                sel_qf_ai_table = st.selectbox("Select table", opts_qf_ai, key="qf_ai_desc_table")
                if st.button("\U0001f9e0 Generate & Apply AI Description", key="qf_ai_desc_btn", type="primary"):
                    with st.spinner("AI is generating description..."):
                        try:
                            parts = sel_qf_ai_table.split(".")
                            df_qf_ai = run_query(conn, f"""
                                WITH col_info AS (
                                    SELECT CONCAT_WS(', ', COLLECT_LIST(CONCAT(column_name, ':', full_data_type))) AS cols
                                    FROM {FULL_SCHEMA}.bronze_columns
                                    WHERE table_catalog = '{parts[0]}' AND table_schema = '{parts[1]}' AND table_name = '{parts[2]}'
                                )
                                SELECT ai_query(
                                    'databricks-meta-llama-3-3-70b-instruct',
                                    CONCAT('Generate a concise business-friendly table description (1-2 sentences). Only return the description. Table: {sel_qf_ai_table}. Columns: ', c.cols),
                                    modelParameters => named_struct('max_tokens', 100, 'temperature', 0.2)
                                ) AS desc_text FROM col_info c
                            """.replace("{sel_qf_ai_table}", sel_qf_ai_table))
                            if not df_qf_ai.empty and df_qf_ai.iloc[0]['desc_text']:
                                gen_desc = df_qf_ai.iloc[0]['desc_text'].strip()
                                safe = gen_desc.replace("'", "''")
                                result = run_action(conn, f"COMMENT ON TABLE {sel_qf_ai_table} IS '{safe}'")
                                if result == "OK":
                                    st.markdown(f'<div class="success-box">\u2705 Applied: "{gen_desc}"</div>', unsafe_allow_html=True)
                                    st.cache_data.clear()
                                else:
                                    st.markdown(f'<div class="error-box">Error: {result[:200]}</div>', unsafe_allow_html=True)
                            else:
                                st.warning("AI did not return a description.")
                        except Exception as e:
                            st.error(f"AI generation failed: {str(e)[:200]}")

        with ai_qf2:
            st.markdown(
                '<div class="action-card" style="border-left-color:#8b5cf6">'
                '<h4>\U0001f916 AI Tag Suggestion</h4>'
                '<p>Let AI suggest appropriate governance tags based on table name, schema, and column analysis.</p>'
                '</div>', unsafe_allow_html=True)

            df_ai_qf_notags = run_query(conn,
                f"SELECT table_catalog, table_schema, table_name "
                f"FROM {FULL_SCHEMA}.silver_governance_assessment "
                f"WHERE has_tags = 0 {FILTER_AND} "
                f"ORDER BY table_catalog, table_schema, table_name LIMIT 50")
            if df_ai_qf_notags.empty:
                st.success("All tables have tags!")
            else:
                opts_qf_tag = [f"{r.table_catalog}.{r.table_schema}.{r.table_name}" for _, r in df_ai_qf_notags.iterrows()]
                sel_qf_tag_table = st.selectbox("Select table", opts_qf_tag, key="qf_ai_tag_table")
                if st.button("\U0001f916 Suggest & Apply Tags", key="qf_ai_tag_btn", type="primary"):
                    with st.spinner("AI is analyzing table for tags..."):
                        try:
                            parts = sel_qf_tag_table.split(".")
                            df_qf_tag = run_query(conn, f"""
                                WITH col_info AS (
                                    SELECT CONCAT_WS(', ', COLLECT_LIST(column_name)) AS cols
                                    FROM {FULL_SCHEMA}.bronze_columns
                                    WHERE table_catalog = '{parts[0]}' AND table_schema = '{parts[1]}' AND table_name = '{parts[2]}'
                                )
                                SELECT ai_query(
                                    'databricks-meta-llama-3-3-70b-instruct',
                                    CONCAT(
                                        'Suggest exactly ONE governance tag for this table as key=value. ',
                                        'Choose from: sensitivity=high/medium/low, domain=finance/sales/engineering/hr/marketing/operations, ',
                                        'layer=bronze/silver/gold, pii=true/false. ',
                                        'Only return the tag in format key=value, nothing else. ',
                                        'Table: {sel_qf_tag_table}. Columns: ', c.cols
                                    ),
                                    modelParameters => named_struct('max_tokens', 20, 'temperature', 0.1)
                                ) AS tag_suggestion FROM col_info c
                            """.replace("{sel_qf_tag_table}", sel_qf_tag_table))
                            if not df_qf_tag.empty and df_qf_tag.iloc[0]['tag_suggestion']:
                                tag_text = df_qf_tag.iloc[0]['tag_suggestion'].strip()
                                if '=' in tag_text:
                                    tag_key, tag_val = tag_text.split('=', 1)
                                    tag_key = tag_key.strip().replace("'", "''")
                                    tag_val = tag_val.strip().replace("'", "''")
                                    result = run_action(conn, f"ALTER TABLE {sel_qf_tag_table} SET TAGS ('{tag_key}' = '{tag_val}')")
                                    if result == "OK":
                                        st.markdown(f'<div class="success-box">\u2705 Applied tag: {tag_key}={tag_val}</div>', unsafe_allow_html=True)
                                        st.cache_data.clear()
                                    else:
                                        st.markdown(f'<div class="error-box">Error: {result[:200]}</div>', unsafe_allow_html=True)
                                else:
                                    st.warning(f"AI returned unexpected format: {tag_text}")
                            else:
                                st.warning("AI did not return a tag suggestion.")
                        except Exception as e:
                            st.error(f"AI generation failed: {str(e)[:200]}")

    # -------------------------------------------------------------------
    # SUB-VIEW 2: Export & Scripts
    # -------------------------------------------------------------------
    elif action_mode == "\U0001f4e5 Export & Scripts":
        st.markdown(
            '<div class="tip-box">'
            'Export assessment data or generate SQL scripts for bulk remediation.'
            '</div>', unsafe_allow_html=True)

        # ---- Export Recommendations CSV ----
        st.subheader("\U0001f4e5 Export Recommendations")
        df_recs_export = run_query(conn,
            f"SELECT table_catalog, table_schema, table_name, category, severity, "
            f"recommendation, current_value, target_value "
            f"FROM {FULL_SCHEMA}.gold_recommendations {FILTER_WHERE} "
            f"ORDER BY severity, category")
        if not df_recs_export.empty:
            csv_data = df_recs_export.to_csv(index=False)
            ec1, ec2, ec3 = st.columns([2, 1, 1])
            with ec1:
                st.markdown(f"**{len(df_recs_export):,}** recommendations ready for export"
                            f" ({len(df_recs_export[df_recs_export['severity']=='HIGH']):,} HIGH)")
            with ec2:
                st.download_button("\U0001f4e5 Download CSV", csv_data,
                                   file_name=f"uc_recommendations_{datetime.now().strftime('%Y%m%d')}.csv",
                                   mime="text/csv", type="primary")
            with ec3:
                pass
        else:
            st.info("No recommendations to export for the current filter.")

        # ---- Export UC Functions, ML Models & Volumes CSV ----
        if SHOW_FUNCTIONS or SHOW_ML_MODELS or SHOW_VOLUMES:
            st.markdown("---")
            st.subheader("\U0001f9e9 Export UC Functions, ML Models & Volumes")

        if SHOW_FUNCTIONS:
            _fn_cat_ex = f"WHERE routine_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _fn_sch_ex = (
                f" AND routine_schema = '{selected_schema}'" if selected_schema != "All" and _fn_cat_ex
                else f"WHERE routine_schema = '{selected_schema}'" if selected_schema != "All"
                else ""
            )
            df_fn_export = run_query(conn,
                f"SELECT routine_catalog, routine_schema, routine_name, routine_type, "
                f"data_type AS return_type, comment AS description, created AS created_at, "
                f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 'Yes' ELSE 'No' END AS documented, "
                f"CASE WHEN routine_name RLIKE '^[a-z][a-z0-9_]*$' THEN 'Yes' ELSE 'No' END AS naming_compliant "
                f"FROM system.information_schema.routines "
                f"{_fn_cat_ex}{_fn_sch_ex} "
                f"ORDER BY routine_catalog, routine_schema, routine_name")
            if not df_fn_export.empty:
                fn_csv = df_fn_export.to_csv(index=False)
                fex1, fex2 = st.columns([3, 1])
                with fex1:
                    st.markdown(f"**{len(df_fn_export):,}** UC Functions available for export")
                with fex2:
                    st.download_button("\U0001f4e5 Functions CSV", fn_csv,
                                       file_name=f"uc_functions_{datetime.now().strftime('%Y%m%d')}.csv",
                                       mime="text/csv", key="dl_fn_csv")
            else:
                st.info("No UC Functions to export.")

        if SHOW_ML_MODELS:
            _ml_cat_ex = f"AND model_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _ml_sch_ex = f"AND model_schema = '{selected_schema}'" if selected_schema != "All" else ""
            df_ml_export = run_query(conn,
                f"SELECT model_catalog, model_schema, model_name, "
                f"CASE WHEN has_description = 1 THEN 'Yes' ELSE 'No' END AS documented, "
                f"CASE WHEN naming_compliant = 1 THEN 'Yes' ELSE 'No' END AS naming_compliant, "
                f"model_readiness_score, rag_status "
                f"FROM {FULL_SCHEMA}.gold_models_summary "
                f"WHERE 1=1 {_ml_cat_ex} {_ml_sch_ex} "
                f"ORDER BY model_catalog, model_schema, model_name")
            if not df_ml_export.empty:
                ml_csv = df_ml_export.to_csv(index=False)
                mex1, mex2 = st.columns([3, 1])
                with mex1:
                    st.markdown(f"**{len(df_ml_export):,}** ML Models available for export")
                with mex2:
                    st.download_button("\U0001f4e5 ML Models CSV", ml_csv,
                                       file_name=f"ml_models_{datetime.now().strftime('%Y%m%d')}.csv",
                                       mime="text/csv", key="dl_ml_csv")
            else:
                st.info("No ML Models to export.")

        if SHOW_VOLUMES:
            _vol_cat_ex = f"WHERE volume_catalog = '{selected_catalog}'" if selected_catalog != "All" else ""
            _vol_sch_ex = (
                f" AND volume_schema = '{selected_schema}'" if selected_schema != "All" and _vol_cat_ex
                else f"WHERE volume_schema = '{selected_schema}'" if selected_schema != "All"
                else ""
            )
            vol_regex = "^[a-z][a-z0-9_]*$"
            df_vol_export = run_query(conn,
                f"SELECT volume_catalog, volume_schema, volume_name, volume_type, "
                f"comment AS description, created AS created_at, "
                f"CASE WHEN comment IS NOT NULL AND comment != '' THEN 'Yes' ELSE 'No' END AS documented, "
                f"CASE WHEN volume_name RLIKE '{vol_regex}' THEN 'Yes' ELSE 'No' END AS naming_compliant "
                f"FROM system.information_schema.volumes "
                f"{_vol_cat_ex}{_vol_sch_ex} "
                f"ORDER BY volume_catalog, volume_schema, volume_name")
            if not df_vol_export.empty:
                vol_csv = df_vol_export.to_csv(index=False)
                vex1, vex2 = st.columns([3, 1])
                with vex1:
                    st.markdown(f"**{len(df_vol_export):,}** UC Volumes available for export")
                with vex2:
                    st.download_button("\U0001f4e5 Volumes CSV", vol_csv,
                                       file_name=f"uc_volumes_{datetime.now().strftime('%Y%m%d')}.csv",
                                       mime="text/csv", key="dl_vol_csv")
            else:
                st.info("No Volumes to export.")

        # ---- Generate Fix SQL Script ----
        st.subheader("\U0001f4dc Generate Fix SQL Script")
        st.markdown(
            '<div class="tip-box">'
            'Generate a SQL script with COMMENT ON and ALTER TABLE statements to bulk-fix '
            'the most common assessment gaps. Copy and run in a notebook or SQL editor.'
            '</div>', unsafe_allow_html=True)

        fix_types = st.multiselect("Select fix types to include",
                                    ["Missing Table Descriptions", "Missing Tags", "Non-Delta Tables"],
                                    default=["Missing Table Descriptions"],
                                    key="act_fix_types")
        if st.button("\U0001f4dc Generate Script", key="act_gen_btn"):
            script_lines = ["-- UC Readiness Fix Script", f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            f"-- Filter: Catalog={selected_catalog}, Schema={selected_schema}", ""]
            if "Missing Table Descriptions" in fix_types:
                df_nd = run_query(conn,
                    f"SELECT table_catalog, table_schema, table_name "
                    f"FROM {FULL_SCHEMA}.silver_metadata_assessment "
                    f"WHERE has_table_description = 0 {FILTER_AND}")
                script_lines.append("-- === Missing Table Descriptions ===")
                for _, r in df_nd.iterrows():
                    fqn = f"{r.table_catalog}.{r.table_schema}.{r.table_name}"
                    script_lines.append(f"COMMENT ON TABLE {fqn} IS 'TODO: Add description for {r.table_name}';")
                script_lines.append("")

            if "Missing Tags" in fix_types:
                df_nt = run_query(conn,
                    f"SELECT table_catalog, table_schema, table_name "
                    f"FROM {FULL_SCHEMA}.silver_governance_assessment "
                    f"WHERE has_tags = 0 {FILTER_AND}")
                script_lines.append("-- === Missing Tags ===")
                for _, r in df_nt.iterrows():
                    fqn = f"{r.table_catalog}.{r.table_schema}.{r.table_name}"
                    script_lines.append(f"ALTER TABLE {fqn} SET TAGS ('classification' = 'unclassified');")
                script_lines.append("")

            if "Non-Delta Tables" in fix_types:
                script_lines.append("-- === Non-Delta Tables (manual conversion needed) ===")
                df_nondelta = run_query(conn,
                    f"SELECT table_catalog, table_schema, table_name, data_source_format "
                    f"FROM {FULL_SCHEMA}.silver_quality_assessment "
                    f"WHERE is_delta = 0 {FILTER_AND}")
                for _, r in df_nondelta.iterrows():
                    fqn = f"{r.table_catalog}.{r.table_schema}.{r.table_name}"
                    script_lines.append(f"-- {fqn} (current format: {r.data_source_format})")
                    script_lines.append(f"-- CREATE TABLE {fqn}_delta AS SELECT * FROM {fqn};")
                script_lines.append("")

            script_text = "\n".join(script_lines)
            st.code(script_text, language="sql")
            st.download_button("\U0001f4e5 Download SQL Script", script_text,
                               file_name=f"uc_fix_script_{datetime.now().strftime('%Y%m%d')}.sql",
                               mime="text/plain", key="act_dl_sql")

        st.markdown("---")

        # ---- Export Excel Scorecard ----
        st.subheader("\U0001f4ca Export Excel Scorecard")
        st.markdown(
            '<div class="tip-box">'
            'Generate a professional Excel workbook with 7 sheets matching the enterprise '
            'Data Governance Readiness Framework format: Instructions, Scorecard, Dashboard, Recommendations, Asset Details, Functions & Models, and Compute.'
            '</div>', unsafe_allow_html=True)

        st.markdown("""
        **Included sheets:**
        * **Instructions** \u2014 How to use the scorecard with rating guide (1\u20134 scale)
        * **Scorecard** \u2014 Assessment criteria by dimension with scores and observations
        * **Dashboard** \u2014 Executive summary with overall maturity and dimension scores
        * **Recommendations** \u2014 Remediation action plan with priority, effort, owner, and status
        * **Asset Details** \u2014 Per-asset rule breakdown with current values and what needs improvement
        * **Functions, Models & Volumes** \u2014 Extended asset assessment (UC Functions, ML Models, Volumes)
        * **Compute** \u2014 Clusters and SQL Warehouses readiness scores
        """)

        if st.button("\U0001f4ca Generate Excel Scorecard", key="gen_excel_btn", type="primary"):
            with st.spinner("Generating Excel scorecard..."):
                try:
                    excel_data = generate_excel_scorecard(conn, FILTER_WHERE, FILTER_AND, FULL_SCHEMA)
                    st.download_button(
                        "\U0001f4e5 Download Excel Scorecard",
                        excel_data,
                        file_name=f"UC_Assessment_Scorecard_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_excel_scorecard")
                    st.markdown(
                        '<div class="success-box">Excel scorecard generated! Click the download button above.</div>',
                        unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="error-box">Error generating scorecard: {str(e)[:200]}</div>',
                                unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # SUB-VIEW 3: Bulk Import
    # -------------------------------------------------------------------
    elif action_mode == "\U0001f4e4 Bulk Import":
        st.markdown(
            '<div class="tip-box">'
            'Upload CSV files to apply table descriptions, column descriptions, or metric views in bulk. '
            'Download a template, fill it in, then upload to preview and execute.'
            '</div>', unsafe_allow_html=True)

        bulk1, bulk2 = st.columns(2)

        with bulk1:
            st.markdown(
                '<div class="bulk-section">'
                '<h4>\U0001f4dd Bulk Table Descriptions</h4>'
                '<p>Upload a CSV to set COMMENT ON TABLE for multiple tables at once.</p>'
                '</div>', unsafe_allow_html=True)

            tpl_tbl = pd.DataFrame({
                "catalog": ["my_catalog", "my_catalog"],
                "schema": ["my_schema", "my_schema"],
                "table_name": ["customers", "orders"],
                "description": ["Customer master data with demographics", "Sales order transactions"],
            })
            st.download_button(
                "\U0001f4cb Download Template",
                tpl_tbl.to_csv(index=False),
                file_name="bulk_table_descriptions_template.csv",
                mime="text/csv", key="tpl_tbl_dl")

            uploaded_tbl = st.file_uploader("Upload table descriptions CSV", type=["csv"], key="bulk_tbl_upload")
            if uploaded_tbl is not None:
                df_up_tbl = pd.read_csv(uploaded_tbl)
                required_cols = {"catalog", "schema", "table_name", "description"}
                if not required_cols.issubset(set(df_up_tbl.columns)):
                    st.error(f"CSV must contain columns: {', '.join(sorted(required_cols))}")
                else:
                    df_up_tbl = df_up_tbl.dropna(subset=["catalog", "schema", "table_name", "description"])
                    st.markdown(f"**{len(df_up_tbl)} rows** ready to apply:")
                    st.dataframe(df_up_tbl.head(20), use_container_width=True, height=200)

                    with st.expander("Preview SQL (dry run)"):
                        preview_lines = []
                        for _, r in df_up_tbl.head(10).iterrows():
                            fqn = f"{r['catalog']}.{r['schema']}.{r['table_name']}"
                            safe = str(r["description"]).replace("'", "''")
                            preview_lines.append(f"COMMENT ON TABLE {fqn} IS '{safe}';")
                        if len(df_up_tbl) > 10:
                            preview_lines.append(f"-- ... and {len(df_up_tbl) - 10} more statements")
                        st.code("\n".join(preview_lines), language="sql")

                    if st.button("\U0001f680 Apply All Table Descriptions", key="bulk_tbl_apply", type="primary"):
                        success_count = 0
                        errors = []
                        progress = st.progress(0)
                        for idx, (_, r) in enumerate(df_up_tbl.iterrows()):
                            fqn = f"{r['catalog']}.{r['schema']}.{r['table_name']}"
                            safe = str(r["description"]).replace("'", "''")
                            result = run_action(conn, f"COMMENT ON TABLE {fqn} IS '{safe}'")
                            if result == "OK":
                                success_count += 1
                            else:
                                errors.append(f"{fqn}: {result[:100]}")
                            progress.progress((idx + 1) / len(df_up_tbl))
                        progress.empty()
                        st.markdown(
                            f'<div class="success-box">\u2705 Applied {success_count}/{len(df_up_tbl)} '
                            f'table descriptions successfully.</div>', unsafe_allow_html=True)
                        if errors:
                            with st.expander(f"\u26a0\ufe0f {len(errors)} errors"):
                                for e in errors:
                                    st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)
                        st.cache_data.clear()

        with bulk2:
            st.markdown(
                '<div class="bulk-section">'
                '<h4>\U0001f4cb Bulk Column Descriptions</h4>'
                '<p>Upload a CSV to set column comments for multiple columns across tables.</p>'
                '</div>', unsafe_allow_html=True)

            tpl_col = pd.DataFrame({
                "catalog": ["my_catalog", "my_catalog", "my_catalog"],
                "schema": ["my_schema", "my_schema", "my_schema"],
                "table_name": ["customers", "customers", "orders"],
                "column_name": ["customer_id", "email", "order_date"],
                "description": ["Unique customer identifier", "Primary email address", "Date order was placed"],
            })
            st.download_button(
                "\U0001f4cb Download Template",
                tpl_col.to_csv(index=False),
                file_name="bulk_column_descriptions_template.csv",
                mime="text/csv", key="tpl_col_dl")

            uploaded_col = st.file_uploader("Upload column descriptions CSV", type=["csv"], key="bulk_col_upload")
            if uploaded_col is not None:
                df_up_col = pd.read_csv(uploaded_col)
                required_cols_c = {"catalog", "schema", "table_name", "column_name", "description"}
                if not required_cols_c.issubset(set(df_up_col.columns)):
                    st.error(f"CSV must contain columns: {', '.join(sorted(required_cols_c))}")
                else:
                    df_up_col = df_up_col.dropna(subset=["catalog", "schema", "table_name", "column_name", "description"])
                    st.markdown(f"**{len(df_up_col)} rows** ready to apply:")
                    st.dataframe(df_up_col.head(20), use_container_width=True, height=200)

                    with st.expander("Preview SQL (dry run)"):
                        preview_lines_c = []
                        for _, r in df_up_col.head(10).iterrows():
                            fqn = f"{r['catalog']}.{r['schema']}.{r['table_name']}"
                            safe = str(r["description"]).replace("'", "''")
                            preview_lines_c.append(
                                f"ALTER TABLE {fqn} ALTER COLUMN {r['column_name']} COMMENT '{safe}';")
                        if len(df_up_col) > 10:
                            preview_lines_c.append(f"-- ... and {len(df_up_col) - 10} more statements")
                        st.code("\n".join(preview_lines_c), language="sql")

                    if st.button("\U0001f680 Apply All Column Descriptions", key="bulk_col_apply", type="primary"):
                        success_count_c = 0
                        errors_c = []
                        progress_c = st.progress(0)
                        for idx, (_, r) in enumerate(df_up_col.iterrows()):
                            fqn = f"{r['catalog']}.{r['schema']}.{r['table_name']}"
                            safe = str(r["description"]).replace("'", "''")
                            result = run_action(conn,
                                f"ALTER TABLE {fqn} ALTER COLUMN {r['column_name']} COMMENT '{safe}'")
                            if result == "OK":
                                success_count_c += 1
                            else:
                                errors_c.append(f"{fqn}.{r['column_name']}: {result[:100]}")
                            progress_c.progress((idx + 1) / len(df_up_col))
                        progress_c.empty()
                        st.markdown(
                            f'<div class="success-box">\u2705 Applied {success_count_c}/{len(df_up_col)} '
                            f'column descriptions successfully.</div>', unsafe_allow_html=True)
                        if errors_c:
                            with st.expander(f"\u26a0\ufe0f {len(errors_c)} errors"):
                                for e in errors_c:
                                    st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)
                        st.cache_data.clear()

        st.markdown("---")

        st.markdown(
            '<div class="bulk-section">'
            '<h4>\U0001f4c8 Upload Metric Views</h4>'
            '<p>Define business metric views as SQL. Each row creates a VIEW with a description, '
            'making metrics Genie-ready and discoverable across the organization.</p>'
            '</div>', unsafe_allow_html=True)

        tpl_metric = pd.DataFrame({
            "target_catalog": ["my_catalog", "my_catalog"],
            "target_schema": ["metrics", "metrics"],
            "view_name": ["monthly_revenue", "active_customers"],
            "source_table": ["my_catalog.sales.orders", "my_catalog.core.customers"],
            "sql_expression": [
                "SELECT DATE_TRUNC('month', order_date) AS month, SUM(amount) AS revenue FROM my_catalog.sales.orders GROUP BY 1",
                "SELECT COUNT(DISTINCT customer_id) AS active_count, DATE_TRUNC('month', last_activity) AS month FROM my_catalog.core.customers WHERE last_activity >= DATEADD(DAY, -30, CURRENT_DATE()) GROUP BY 2",
            ],
            "description": [
                "Monthly revenue aggregated from sales orders",
                "Count of customers active in the last 30 days",
            ],
        })
        mc1, mc2 = st.columns([1, 3])
        with mc1:
            st.download_button(
                "\U0001f4cb Download Template",
                tpl_metric.to_csv(index=False),
                file_name="bulk_metric_views_template.csv",
                mime="text/csv", key="tpl_metric_dl")

        uploaded_metric = st.file_uploader("Upload metric views CSV", type=["csv"], key="bulk_metric_upload")
        if uploaded_metric is not None:
            df_up_metric = pd.read_csv(uploaded_metric)
            required_cols_m = {"target_catalog", "target_schema", "view_name", "sql_expression", "description"}
            if not required_cols_m.issubset(set(df_up_metric.columns)):
                st.error(f"CSV must contain columns: {', '.join(sorted(required_cols_m))}")
            else:
                df_up_metric = df_up_metric.dropna(subset=["target_catalog", "target_schema", "view_name", "sql_expression"])
                st.markdown(f"**{len(df_up_metric)} metric view(s)** to create:")
                st.dataframe(df_up_metric[["target_catalog", "target_schema", "view_name", "description"]],
                             use_container_width=True, height=200)

                with st.expander("Preview SQL (dry run)"):
                    preview_lines_m = []
                    for _, r in df_up_metric.iterrows():
                        fqn = f"{r['target_catalog']}.{r['target_schema']}.{r['view_name']}"
                        preview_lines_m.append(f"CREATE OR REPLACE VIEW {fqn} AS")
                        preview_lines_m.append(f"  {r['sql_expression']};")
                        if pd.notna(r.get("description")):
                            safe = str(r["description"]).replace("'", "''")
                            preview_lines_m.append(f"COMMENT ON VIEW {fqn} IS '{safe}';")
                        preview_lines_m.append("")
                    st.code("\n".join(preview_lines_m), language="sql")

                if st.button("\U0001f680 Create Metric Views", key="bulk_metric_apply", type="primary"):
                    success_count_m = 0
                    errors_m = []
                    progress_m = st.progress(0)
                    for idx, (_, r) in enumerate(df_up_metric.iterrows()):
                        fqn = f"{r['target_catalog']}.{r['target_schema']}.{r['view_name']}"
                        create_sql = f"CREATE OR REPLACE VIEW {fqn} AS {r['sql_expression']}"
                        result = run_action(conn, create_sql)
                        if result == "OK":
                            success_count_m += 1
                            if pd.notna(r.get("description")) and str(r["description"]).strip():
                                safe = str(r["description"]).replace("'", "''")
                                run_action(conn, f"COMMENT ON VIEW {fqn} IS '{safe}'")
                        else:
                            errors_m.append(f"{fqn}: {result[:150]}")
                        progress_m.progress((idx + 1) / len(df_up_metric))
                    progress_m.empty()
                    st.markdown(
                        f'<div class="success-box">\u2705 Created {success_count_m}/{len(df_up_metric)} '
                        f'metric views successfully.</div>', unsafe_allow_html=True)
                    if errors_m:
                        with st.expander(f"\u26a0\ufe0f {len(errors_m)} errors"):
                            for e in errors_m:
                                st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)
                    st.cache_data.clear()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

    # -------------------------------------------------------------------
    # SUB-VIEW 4: Refresh Pipeline
    # -------------------------------------------------------------------
    elif action_mode == "\U0001f504 Refresh Pipeline":
        st.markdown(
            '<div class="tip-box">'
            'Re-run the full assessment pipeline to refresh all scores with the latest metadata. '
            'This executes Bronze \u2192 Silver \u2192 Gold layer transformations using your connected SQL Warehouse.</div>',
            unsafe_allow_html=True)

        st.markdown("**Pipeline Steps:**")
        steps = [
            ("1\ufe0f\u20e3", "Bronze Layer", "Ingest from system.information_schema, billing, query history, lineage"),
            ("2\ufe0f\u20e3", "Silver Layer", "Assess metadata, governance, quality, performance, Genie readiness"),
            ("3\ufe0f\u20e3", "Gold Layer", "Aggregate scores, generate recommendations, build executive summary"),
        ]
        for icon, title, desc in steps:
            st.markdown(f"&emsp;{icon} **{title}** \u2014 {desc}")

        st.markdown("")
        st.warning("\u26a0\ufe0f This will recreate all assessment tables. Existing scores will be replaced with fresh calculations.")

        col_run, col_status = st.columns([1, 2])
        with col_run:
            run_pipeline = st.button("\U0001f680 Run Full Pipeline", type="primary", key="run_pipeline_btn")

        if run_pipeline:
            progress = st.progress(0, text="Starting pipeline...")
            status_container = st.container()

            try:
                total_steps = 12
                step_counter = [0]

                def run_step(sql, label):
                    step_counter[0] += 1
                    progress.progress(step_counter[0] / total_steps, text=f"Step {step_counter[0]}/{total_steps}: {label}...")
                    run_query(conn, sql)
                    status_container.markdown(f"\u2705 {label}")

                # === BRONZE LAYER ===
                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_tables AS "
                    f"SELECT * FROM system.information_schema.tables WHERE table_schema != 'information_schema'",
                    "Bronze: Tables ingested")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_columns AS "
                    f"SELECT * FROM system.information_schema.columns WHERE table_schema != 'information_schema'",
                    "Bronze: Columns ingested")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_privileges AS "
                    f"SELECT * FROM system.information_schema.table_privileges",
                    "Bronze: Privileges ingested")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_tags AS "
                    f"SELECT * FROM system.information_schema.table_tags",
                    "Bronze: Tags ingested")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_lineage AS "
                    f"SELECT * FROM system.access.table_lineage WHERE event_time >= current_date() - INTERVAL 30 DAYS",
                    "Bronze: Lineage ingested")

                # === SILVER LAYER ===
                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_metadata_assessment AS "
                    f"WITH col_stats AS ("
                    f"  SELECT table_catalog, table_schema, table_name, COUNT(*) AS total_columns, "
                    f"  SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END) AS documented_columns "
                    f"  FROM {FULL_SCHEMA}.bronze_columns GROUP BY table_catalog, table_schema, table_name) "
                    f"SELECT t.table_catalog, t.table_schema, t.table_name, t.table_type, "
                    f"  CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 1 ELSE 0 END AS has_table_description, "
                    f"  COALESCE(c.total_columns, 0) AS total_columns, COALESCE(c.documented_columns, 0) AS documented_columns, "
                    f"  ROUND(COALESCE(c.documented_columns, 0) * 100.0 / NULLIF(c.total_columns, 0), 1) AS column_doc_pct, "
                    f"  CASE WHEN t.table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END AS naming_score, "
                    f"  ROUND((CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 2.0 ELSE 0 END) + "
                    f"  (COALESCE(c.documented_columns, 0) * 2.0 / NULLIF(c.total_columns, 0)) + "
                    f"  (CASE WHEN t.table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1.0 ELSE 0 END), 2) AS metadata_score "
                    f"FROM {FULL_SCHEMA}.bronze_tables t "
                    f"LEFT JOIN col_stats c ON t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema AND t.table_name = c.table_name",
                    "Silver: Metadata assessed")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_governance_assessment AS "
                    f"WITH tag_stats AS ("
                    f"  SELECT catalog_name AS table_catalog, schema_name AS table_schema, table_name, COUNT(*) AS tag_count "
                    f"  FROM {FULL_SCHEMA}.bronze_table_tags GROUP BY catalog_name, schema_name, table_name), "
                    f"priv_stats AS ("
                    f"  SELECT table_catalog, table_schema, table_name, COUNT(*) AS grant_count, "
                    f"  SUM(CASE WHEN privilege_type = 'ALL PRIVILEGES' THEN 1 ELSE 0 END) AS over_permissioned_grants "
                    f"  FROM {FULL_SCHEMA}.bronze_table_privileges GROUP BY table_catalog, table_schema, table_name) "
                    f"SELECT t.table_catalog, t.table_schema, t.table_name, "
                    f"  CASE WHEN tg.tag_count > 0 THEN 1 ELSE 0 END AS has_tags, "
                    f"  CASE WHEN p.grant_count > 0 THEN 1 ELSE 0 END AS has_explicit_grants, "
                    f"  CASE WHEN COALESCE(p.over_permissioned_grants, 0) > 0 THEN 0 ELSE 1 END AS no_over_permission, "
                    f"  CASE WHEN t.table_type = 'MANAGED' THEN 1 ELSE 0 END AS is_managed, "
                    f"  ROUND((CASE WHEN tg.tag_count > 0 THEN 1.5 ELSE 0 END) + "
                    f"  (CASE WHEN p.grant_count > 0 THEN 1.5 ELSE 0 END) + "
                    f"  (CASE WHEN COALESCE(p.over_permissioned_grants, 0) = 0 THEN 1.0 ELSE 0 END) + "
                    f"  (CASE WHEN t.table_type = 'MANAGED' THEN 1.0 ELSE 0 END), 2) AS governance_score "
                    f"FROM {FULL_SCHEMA}.bronze_tables t "
                    f"LEFT JOIN tag_stats tg ON t.table_catalog = tg.table_catalog AND t.table_schema = tg.table_schema AND t.table_name = tg.table_name "
                    f"LEFT JOIN priv_stats p ON t.table_catalog = p.table_catalog AND t.table_schema = p.table_schema AND t.table_name = p.table_name",
                    "Silver: Governance assessed")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_quality_assessment AS "
                    f"SELECT table_catalog, table_schema, table_name, "
                    f"  CASE WHEN data_source_format = 'DELTA' THEN 1 ELSE 0 END AS is_delta, "
                    f"  CASE WHEN last_altered >= current_date() - INTERVAL 30 DAYS THEN 1 ELSE 0 END AS is_fresh, "
                    f"  ROUND((CASE WHEN data_source_format = 'DELTA' THEN 2.5 ELSE 0 END) + "
                    f"  (CASE WHEN last_altered >= current_date() - INTERVAL 30 DAYS THEN 2.5 ELSE 0 END), 2) AS quality_score "
                    f"FROM {FULL_SCHEMA}.bronze_tables",
                    "Silver: Quality assessed")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_genie_readiness AS "
                    f"WITH lineage_stats AS ("
                    f"  SELECT target_table_catalog AS table_catalog, target_table_schema AS table_schema, "
                    f"  target_table_name AS table_name, COUNT(*) AS lineage_connection_count "
                    f"  FROM {FULL_SCHEMA}.bronze_table_lineage GROUP BY target_table_catalog, target_table_schema, target_table_name) "
                    f"SELECT m.table_catalog, m.table_schema, m.table_name, "
                    f"  m.has_table_description AS has_description, m.column_doc_pct, m.naming_score AS naming_compliant, "
                    f"  CASE WHEN l.lineage_connection_count > 0 THEN 1 ELSE 0 END AS has_lineage, "
                    f"  COALESCE(l.lineage_connection_count, 0) AS lineage_connection_count, "
                    f"  CASE WHEN LOWER(m.table_schema) RLIKE '(gold|curated|mart)' OR LOWER(m.table_name) RLIKE '^(fact|dim)_' THEN 1 ELSE 0 END AS is_gold_layer_candidate, "
                    f"  ROUND((m.has_table_description * 20.0) + (LEAST(COALESCE(m.column_doc_pct, 0), 100) / 100.0 * 30.0) + "
                    f"  (m.naming_score * 15.0) + (CASE WHEN l.lineage_connection_count > 0 THEN 15.0 ELSE 0 END) + "
                    f"  (CASE WHEN LOWER(m.table_schema) RLIKE '(gold|curated|mart)' OR LOWER(m.table_name) RLIKE '^(fact|dim)_' THEN 20.0 ELSE 0 END), 1) AS genie_readiness_score "
                    f"FROM {FULL_SCHEMA}.silver_metadata_assessment m "
                    f"LEFT JOIN lineage_stats l ON m.table_catalog = l.table_catalog AND m.table_schema = l.table_schema AND m.table_name = l.table_name",
                    "Silver: Genie readiness assessed")

                # === GOLD LAYER ===
                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_table_scores AS "
                    f"SELECT m.table_catalog, m.table_schema, m.table_name, "
                    f"  ROUND(m.metadata_score, 2) AS metadata_score, "
                    f"  ROUND(COALESCE(g.governance_score, 0), 2) AS governance_score, "
                    f"  ROUND(COALESCE(q.quality_score, 0), 2) AS quality_score, "
                    f"  ROUND(COALESCE(gr.genie_readiness_score, 0), 2) AS genie_score, "
                    f"  ROUND((COALESCE(m.metadata_score, 0)/5.0*25) + (COALESCE(g.governance_score, 0)/5.0*25) + "
                    f"  (COALESCE(q.quality_score, 0)/5.0*25) + (COALESCE(gr.genie_readiness_score, 0)/100.0*25), 2) AS overall_score, "
                    f"  CASE WHEN ((COALESCE(m.metadata_score,0)/5.0*25)+(COALESCE(g.governance_score,0)/5.0*25)+"
                    f"  (COALESCE(q.quality_score,0)/5.0*25)+(COALESCE(gr.genie_readiness_score,0)/100.0*25)) >= 70 THEN 'GREEN' "
                    f"  WHEN ((COALESCE(m.metadata_score,0)/5.0*25)+(COALESCE(g.governance_score,0)/5.0*25)+"
                    f"  (COALESCE(q.quality_score,0)/5.0*25)+(COALESCE(gr.genie_readiness_score,0)/100.0*25)) >= 40 THEN 'AMBER' "
                    f"  ELSE 'RED' END AS rag_status "
                    f"FROM {FULL_SCHEMA}.silver_metadata_assessment m "
                    f"LEFT JOIN {FULL_SCHEMA}.silver_governance_assessment g ON m.table_catalog=g.table_catalog AND m.table_schema=g.table_schema AND m.table_name=g.table_name "
                    f"LEFT JOIN {FULL_SCHEMA}.silver_quality_assessment q ON m.table_catalog=q.table_catalog AND m.table_schema=q.table_schema AND m.table_name=q.table_name "
                    f"LEFT JOIN {FULL_SCHEMA}.silver_genie_readiness gr ON m.table_catalog=gr.table_catalog AND m.table_schema=gr.table_schema AND m.table_name=gr.table_name",
                    "Gold: Table scores computed")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_category_scores AS "
                    f"WITH metadata_cat AS (SELECT table_catalog AS catalog_name, 'Metadata Readiness' AS category, ROUND(AVG(metadata_score)/5.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_metadata_assessment GROUP BY table_catalog), "
                    f"governance_cat AS (SELECT table_catalog AS catalog_name, 'Governance' AS category, ROUND(AVG(governance_score)/5.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_governance_assessment GROUP BY table_catalog), "
                    f"quality_cat AS (SELECT table_catalog AS catalog_name, 'Data Quality' AS category, ROUND(AVG(quality_score)/5.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_quality_assessment GROUP BY table_catalog), "
                    f"genie_cat AS (SELECT table_catalog AS catalog_name, 'Genie Readiness' AS category, ROUND(AVG(genie_readiness_score)/100.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_genie_readiness GROUP BY table_catalog), "
                    f"metadata_all AS (SELECT 'ALL' AS catalog_name, 'Metadata Readiness' AS category, ROUND(AVG(metadata_score)/5.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_metadata_assessment), "
                    f"governance_all AS (SELECT 'ALL' AS catalog_name, 'Governance' AS category, ROUND(AVG(governance_score)/5.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_governance_assessment), "
                    f"quality_all AS (SELECT 'ALL' AS catalog_name, 'Data Quality' AS category, ROUND(AVG(quality_score)/5.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_quality_assessment), "
                    f"genie_all AS (SELECT 'ALL' AS catalog_name, 'Genie Readiness' AS category, ROUND(AVG(genie_readiness_score)/100.0*5.0,2) AS score, 5.0 AS max_score, COUNT(*) AS assessed_tables FROM {FULL_SCHEMA}.silver_genie_readiness), "
                    f"all_scores AS ("
                    f"  SELECT * FROM metadata_cat UNION ALL SELECT * FROM governance_cat UNION ALL "
                    f"  SELECT * FROM quality_cat UNION ALL SELECT * FROM genie_cat UNION ALL "
                    f"  SELECT * FROM metadata_all UNION ALL SELECT * FROM governance_all UNION ALL "
                    f"  SELECT * FROM quality_all UNION ALL SELECT * FROM genie_all) "
                    f"SELECT catalog_name, category, score, max_score, ROUND(score/max_score*100,1) AS pct, "
                    f"  CASE WHEN score/max_score*100 < 40 THEN 'RED' WHEN score/max_score*100 < 70 THEN 'AMBER' ELSE 'GREEN' END AS rag_status, "
                    f"  assessed_tables, current_timestamp() AS last_updated FROM all_scores",
                    "Gold: Category scores aggregated")

                run_step(
                    f"CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_recommendations AS "
                    f"SELECT table_catalog, table_schema, table_name, 'Metadata Readiness' AS category, 'META_001' AS rule_id, 'HIGH' AS severity, "
                    f"  'Add table description for discoverability and Genie readiness' AS recommendation, 'No description' AS current_value, 'Description present' AS target_value "
                    f"FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE has_table_description = 0 "
                    f"UNION ALL "
                    f"SELECT table_catalog, table_schema, table_name, 'Metadata Readiness', 'META_002', 'HIGH', "
                    f"  'Document columns - critical for Genie and data governance', CONCAT(CAST(ROUND(column_doc_pct,0) AS STRING), '% documented'), '>=80% documented' "
                    f"FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE COALESCE(column_doc_pct, 0) < 80 "
                    f"UNION ALL "
                    f"SELECT table_catalog, table_schema, table_name, 'Governance', 'GOV_001', 'MEDIUM', "
                    f"  'Add governance tags for classification and access control', 'No tags', 'At least 1 tag' "
                    f"FROM {FULL_SCHEMA}.silver_governance_assessment WHERE has_tags = 0 "
                    f"UNION ALL "
                    f"SELECT table_catalog, table_schema, table_name, 'Data Quality', 'DQ_001', 'LOW', "
                    f"  'Table appears stale - no modifications in 30+ days', 'Stale', 'Fresh (modified within 30 days)' "
                    f"FROM {FULL_SCHEMA}.silver_quality_assessment WHERE is_fresh = 0 "
                    f"UNION ALL "
                    f"SELECT table_catalog, table_schema, table_name, 'Data Quality', 'DQ_002', 'MEDIUM', "
                    f"  'Migrate to Delta format for performance and governance features', 'Non-Delta', 'Delta format' "
                    f"FROM {FULL_SCHEMA}.silver_quality_assessment WHERE is_delta = 0 "
                    f"UNION ALL "
                    f"SELECT table_catalog, table_schema, table_name, 'Genie Readiness', 'GENIE_001', 'HIGH', "
                    f"  'Table needs documentation and lineage for Genie compatibility', CONCAT(CAST(ROUND(genie_readiness_score,0) AS STRING), '%%'), '>=70%%' "
                    f"FROM {FULL_SCHEMA}.silver_genie_readiness WHERE genie_readiness_score < 70",
                    "Gold: Recommendations generated")

                progress.progress(1.0, text="\u2705 Pipeline complete!")
                st.success(f"\U0001f389 Assessment pipeline refreshed successfully! All scores updated at {datetime.now().strftime('%H:%M:%S')}. Reload the page to see new data.")
                st.balloons()

            except Exception as e:
                st.error(f"\u274c Pipeline failed at step {step_counter[0]}: {str(e)}")
                st.markdown("**Troubleshooting:** Ensure your SQL Warehouse has access to `system.information_schema`, `system.access`, and `system.billing` tables.")


st.markdown(
    f'<div style="text-align:center;padding:20px 0;color:#94a3b8;font-size:12px;'
    f'border-top:1px solid #e2e8f0;margin-top:30px">'
    f'GovernIQ v1.0 | Schema: {FULL_SCHEMA} '
    f'| Last Assessment: {_refresh_str if _last_refresh is not None else "Not run"}</div>',
    unsafe_allow_html=True)

