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
    page_title="UC Readiness Accelerator",
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
FULL_SCHEMA = "democatalog.uc_assessment"
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

    ws['A4'] = ("Enterprise Data Governance Readiness Framework | Version 1.0 | "
                + datetime.now().strftime("%B %Y"))
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

    ws2['A3'] = "Rate each item 1 (Initial) \u2192 4 (Optimized)  |  Enter score in column E"
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
        f"FROM {full_schema}.assessment_rules ORDER BY category, rule_id")

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
    overall = float(df_exec.iloc[0].get('overall_readiness_score', 0)) if not df_exec.empty else 0

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
        ("6. Operational Maturity & Sharing", "Genie Readiness"),
    ]
    r = 10
    for dim_name, cat_key in dims:
        cat_row = df_cat[df_cat['category'] == cat_key]
        pct = float(cat_row['pct'].iloc[0]) if not cat_row.empty else 0
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
        pct = float(cat_row['pct'].iloc[0]) if not cat_row.empty else 0
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
        f"ORDER BY CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END "
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

        # Add a section separator row when the table changes
        if fqn != current_table:
            if current_table is not None:
                r5 += 1  # blank separator row
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
        '<p style="color:#334155;font-size:22px;font-weight:700;margin:0">UC Readiness</p>'
        '<p style="color:#64748b;font-size:13px;margin:0">Accelerator v1.0</p>',
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
    st.title("\U0001f3db\ufe0f UC Readiness Accelerator")
    st.info("Enter a **SQL Warehouse ID** in the sidebar to connect.")
    st.stop()

st.sidebar.success("Connected")

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
FILTER_COND  = " AND ".join(_fp)
FILTER_WHERE = f"WHERE {FILTER_COND}" if FILTER_COND else ""
FILTER_AND   = f"AND {FILTER_COND}" if FILTER_COND else ""

_cp = []
if selected_catalog != "All":
    _cp.append(f"catalog_name = '{selected_catalog}'")
CAT_FILTER_WHERE = f"WHERE {' AND '.join(_cp)}" if _cp else ""
CAT_FILTER_AND   = f"AND {' AND '.join(_cp)}" if _cp else ""

IS_FILTERED = bool(FILTER_COND)

# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------
st.markdown(
    '<div style="background:linear-gradient(135deg,#1e40af 0%,#3b82f6 100%);'
    'padding:24px 32px;border-radius:12px;margin-bottom:20px">'
    '<h1 style="color:white !important;margin:0;font-size:28px;font-weight:700">'
    'UC Readiness Accelerator</h1>'
    '<p style="color:#bfdbfe;margin:4px 0 0;font-size:14px">'
    'Unity Catalog Assessment Dashboard</p></div>',
    unsafe_allow_html=True)

if IS_FILTERED:
    pills = []
    if selected_catalog != "All":
        pills.append(f'<span class="filter-pill">Catalog: {selected_catalog}</span>')
    if selected_schema != "All":
        pills.append(f'<span class="filter-pill">Schema: {selected_schema}</span>')
    st.markdown(
        f'<div class="tip-box">Showing filtered results: {"".join(pills)}</div>',
        unsafe_allow_html=True)

# ===========================================================================
# TABS
# ===========================================================================
tab_exec, tab_detail, tab_recs, tab_finops, tab_perf, tab_genie, tab_rules, tab_actions = st.tabs([
    "\U0001f4ca Executive Summary",
    "\U0001f50d Detailed Assessment",
    "\U0001f4a1 Recommendations",
    "\U0001f4b0 FinOps Insights",
    "\u26a1 Performance",
    "\U0001f916 Genie Readiness",
    "\U0001f4d6 Assessment Rules",
    "\U0001f527 Actions",
])

# ===========================================================================
# TAB 1 — EXECUTIVE SUMMARY
# ===========================================================================
with tab_exec:
    st.header("Executive Summary")

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

        rag_class = f"rag-{rag.lower()}"
        st.markdown(
            f'<div class="{rag_class}"><strong>Overall Readiness Score: '
            f'{overall}%</strong> {rag_badge(rag)}</div>', unsafe_allow_html=True)
        st.markdown("")

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: metric_card("Catalogs", int(row.get("total_catalogs") or 0), CLR_BLUE)
        with k2: metric_card("Tables", f"{int(row.get('total_tables') or 0):,}", CLR_BLUE)
        with k3: metric_card("Columns", f"{int(row.get('total_columns') or 0):,}", CLR_BLUE)
        with k4: metric_card("Recommendations", f"{int(row.get('total_recommendations') or 0):,}", CLR_RED)
        with k5: metric_card("HIGH Priority", f"{int(row.get('high_priority_recommendations') or 0):,}", CLR_RED)
        with k6: metric_card("DBUs (30d)", f"{float(row.get('total_dbus_consumed') or 0):,.0f}", CLR_PURPLE)

        st.markdown("---")
        st.subheader("Category Scores")
        categories = [
            ("Metadata", float(row.get("metadata_score") or 0)),
            ("Governance", float(row.get("governance_score") or 0)),
            ("Data Quality", float(row.get("quality_score") or 0)),
            ("Performance", float(row.get("performance_score") or 0)),
            ("Genie", float(row.get("genie_score") or 0)),
        ]
        cols = st.columns(5)
        for i, (name, score) in enumerate(categories):
            with cols[i]:
                color = CLR_RED if score < 40 else CLR_AMBER if score < 70 else CLR_GREEN
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=score,
                    title={"text": name, "font": {"size": 13, "color": "#334155"}},
                    number={"suffix": "%", "font": {"color": "#1e293b"}},
                    gauge={"axis": {"range": [0, 100], "tickfont": {"color": "#64748b"}},
                           "bar": {"color": color},
                           "steps": [{"range": [0, 40], "color": "#fef2f2"},
                                     {"range": [40, 70], "color": "#fffbeb"},
                                     {"range": [70, 100], "color": "#f0fdf4"}]}))
                fig.update_layout(height=180, margin=dict(t=35, b=0, l=15, r=15), **CHART_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Key Indicators")
        i1, i2, i3, i4, i5 = st.columns(5)
        with i1: st.metric("Tables with Descriptions", f"{row.get('tables_with_descriptions_pct') or 0}%")
        with i2: st.metric("Columns Documented", f"{row.get('columns_documented_pct') or 0}%")
        with i3: st.metric("Delta Format", f"{row.get('delta_format_pct') or 0}%")
        with i4: st.metric("Fresh Tables (30d)", f"{row.get('fresh_tables_pct') or 0}%")
        with i5: st.metric("Genie-Ready", f"{int(row.get('genie_ready_tables') or 0)} ({row.get('genie_ready_pct') or 0}%)")

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

# ===========================================================================
# TAB 3 — RECOMMENDATIONS
# ===========================================================================
with tab_recs:
    st.header("Recommendations")

    df_recs = run_query(conn,
        f"SELECT * FROM {FULL_SCHEMA}.gold_recommendations {FILTER_WHERE} ORDER BY severity, category")
    if df_recs.empty:
        st.warning("No recommendations for the current filter.")
    else:
        r1, r2, r3 = st.columns(3)
        with r1: metric_card("HIGH", len(df_recs[df_recs['severity'] == 'HIGH']), CLR_RED)
        with r2: metric_card("MEDIUM", len(df_recs[df_recs['severity'] == 'MEDIUM']), CLR_AMBER)
        with r3: metric_card("LOW", len(df_recs[df_recs['severity'] == 'LOW']), CLR_BLUE)

        summary = df_recs.groupby(["category", "severity"]).size().reset_index(name="count")
        fig = px.bar(summary, x="category", y="count", color="severity",
                     color_discrete_map={"HIGH": CLR_RED, "MEDIUM": CLR_AMBER, "LOW": CLR_BLUE},
                     title="Recommendations by Category & Severity", barmode="group")
        fig.update_layout(height=400, **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Actionable Recommendations")
        sev_filter = st.selectbox("Severity", ["All", "HIGH", "MEDIUM", "LOW"])
        cat_filter = st.selectbox("Category", ["All"] + sorted(df_recs["category"].unique().tolist()))
        df_rf = df_recs.copy()
        if sev_filter != "All":
            df_rf = df_rf[df_rf["severity"] == sev_filter]
        if cat_filter != "All":
            df_rf = df_rf[df_rf["category"] == cat_filter]
        st.dataframe(df_rf[["table_catalog", "table_schema", "table_name", "category",
                            "severity", "recommendation", "current_value", "target_value"]],
                     use_container_width=True, height=400)

# ===========================================================================
# TAB 4 — FINOPS INSIGHTS  (workspace-level — not filtered)
# ===========================================================================
with tab_finops:
    st.header("FinOps Insights")
    if IS_FILTERED:
        st.markdown('<div class="warn-box">FinOps data is workspace-level and not affected by catalog/schema filters.</div>',
                    unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        df_product = run_query(conn, f"SELECT * FROM {FULL_SCHEMA}.gold_cost_by_product ORDER BY total_dbus DESC")
        if not df_product.empty:
            fig = px.bar(df_product.head(12), x="billing_origin_product", y="total_dbus",
                         title="DBU Consumption by Product (Last 30 Days)",
                         color_discrete_sequence=[CLR_BLUE])
            fig.update_layout(height=400, xaxis_tickangle=-45, **CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        df_sku = run_query(conn,
            f"SELECT sku_name, SUM(total_dbus) as total_dbus FROM {FULL_SCHEMA}.gold_cost_by_sku "
            f"GROUP BY sku_name ORDER BY total_dbus DESC LIMIT 15")
        if not df_sku.empty:
            fig2 = px.bar(df_sku, x="sku_name", y="total_dbus", title="Top 15 SKUs by DBU Usage",
                          color_discrete_sequence=[CLR_PURPLE])
            fig2.update_layout(height=400, xaxis_tickangle=-45, **CHART_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top Expensive Queries")
    df_exp = run_query(conn,
        f"SELECT statement_type, executed_by, total_duration_ms, read_bytes, execution_status "
        f"FROM {FULL_SCHEMA}.gold_expensive_queries LIMIT 25")
    if not df_exp.empty:
        st.dataframe(df_exp, use_container_width=True, height=350)

# ===========================================================================
# TAB 5 — PERFORMANCE  (workspace-level — not filtered)
# ===========================================================================
with tab_perf:
    st.header("Performance Insights")
    if IS_FILTERED:
        st.markdown('<div class="warn-box">Performance data is aggregated at workspace level and not affected by catalog/schema filters.</div>',
                    unsafe_allow_html=True)

    df_perf = run_query(conn, f"SELECT * FROM {FULL_SCHEMA}.silver_performance_assessment ORDER BY query_count DESC")
    if df_perf.empty:
        st.warning("No performance data available.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(df_perf, x="statement_type", y="avg_duration_ms",
                         color="performance_category",
                         color_discrete_map={"GOOD": CLR_GREEN, "MODERATE": CLR_AMBER, "POOR": CLR_RED},
                         title="Avg Duration by Statement Type")
            fig.update_layout(height=400, **CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(df_perf, x="statement_type", y="query_count",
                          title="Query Volume by Statement Type",
                          color_discrete_sequence=[CLR_BLUE])
            fig2.update_layout(height=400, **CHART_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Performance Detail")
        st.dataframe(
            df_perf.style.applymap(
                lambda v: "background-color: #fef2f2; color: #991b1b" if v == "POOR" else
                          "background-color: #fffbeb; color: #92400e" if v == "MODERATE" else
                          "background-color: #f0fdf4; color: #166534" if v == "GOOD" else "",
                subset=["performance_category"]),
            use_container_width=True)

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

# ===========================================================================
# TAB 7 — ASSESSMENT RULES  (reference — not filtered)
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
    st.subheader("Defined Rules")

    df_rules = run_query(conn,
        f"SELECT rule_id, category, rule_name, description, weight, severity "
        f"FROM {FULL_SCHEMA}.assessment_rules ORDER BY category, rule_id")

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
        }
        for cat_name, grp in df_rules.groupby("category", sort=False):
            icon = cat_icons.get(cat_name, "\U0001f4cb")
            st.markdown(f'<div class="section-header">{icon} {cat_name}</div>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            for idx, (_, rule) in enumerate(grp.iterrows()):
                sev = rule["severity"]
                with (col_a if idx % 2 == 0 else col_b):
                    st.markdown(
                        f'<div class="rule-card">'
                        f'<div class="rule-id">{rule["rule_id"]}</div>'
                        f'<div class="rule-name">{rule["rule_name"]}</div>'
                        f'<div class="rule-desc">{rule["description"]}</div>'
                        f'<div class="rule-meta">'
                        f'<span class="{sev_class.get(sev, "")}">Severity: {sev}</span>'
                        f'<span style="color:#64748b">Weight: {rule["weight"]}</span>'
                        f'</div></div>', unsafe_allow_html=True)

# ===========================================================================
# TAB 8 — ACTIONS (with sub-navigation)
# ===========================================================================
with tab_actions:
    st.header("Actions")

    action_mode = st.radio(
        "Select action type",
        ["\U0001f527 Quick Fix", "\U0001f4e5 Export & Scripts", "\U0001f4e4 Bulk Import"],
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

        st.markdown("---")

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
            'Generate a professional Excel workbook with 4 sheets matching the enterprise '
            'Data Governance Readiness Framework format: Instructions, Scorecard, Dashboard, and Recommendations.'
            '</div>', unsafe_allow_html=True)

        st.markdown("""
        **Included sheets:**
        * **Instructions** \u2014 How to use the scorecard with rating guide (1\u20134 scale)
        * **Scorecard** \u2014 Assessment criteria by dimension with scores and observations
        * **Dashboard** \u2014 Executive summary with overall maturity and dimension scores
        * **Recommendations** \u2014 Remediation action plan with priority, effort, owner, and status
        * **Asset Details** \u2014 Per-asset rule breakdown with current values and what needs improvement
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
st.markdown(
    f'<div style="text-align:center;padding:20px 0;color:#94a3b8;font-size:12px;'
    f'border-top:1px solid #e2e8f0;margin-top:30px">'
    f'UC Readiness Accelerator v1.0 | Schema: {FULL_SCHEMA} '
    f'| Refreshed: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
    unsafe_allow_html=True)
