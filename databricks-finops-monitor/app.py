# =============================================================================
# Databricks Monitoring & FinOps Dashboard — AI-Enhanced Edition
# =============================================================================
# Features: Job Monitoring, Cost FinOps, Performance Insights,
#           AI Cost Forecasting, Budget Management, Auto-Remediation,
#           AI FinOps Agent (chat)
# =============================================================================

import os
import math
import json
from datetime import datetime, timedelta, date

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from databricks import sql
from databricks.sdk.core import Config

# Import AI FinOps modules
try:
    from finops_anomaly import (
        detect_anomalies_zscore, detect_anomalies_iqr,
        detect_anomalies_isolation_forest, get_cost_anomalies_by_resource,
        get_anomaly_summary, SKLEARN_AVAILABLE
    )
    ANOMALY_MODULE_AVAILABLE = True
except ImportError:
    ANOMALY_MODULE_AVAILABLE = False
    SKLEARN_AVAILABLE = False

try:
    from finops_budget import BudgetManager
    BUDGET_MODULE_AVAILABLE = True
except ImportError:
    BUDGET_MODULE_AVAILABLE = False

try:
    from finops_remediation import RemediationEngine
    REMEDIATION_MODULE_AVAILABLE = True
except ImportError:
    REMEDIATION_MODULE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Page config & styles
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Databricks FinOps Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px; padding: 20px; text-align: center;
        border: 1px solid #0f3460; margin: 4px 0;
    }
    .metric-card h2 { color: #e94560; margin: 0; font-size: 28px; }
    .metric-card p  { color: #a0a0b0; margin: 4px 0 0 0; font-size: 13px; }
    .alert-box {
        background: #2d1b1b; border-left: 4px solid #e94560;
        padding: 12px 16px; border-radius: 6px; margin: 6px 0;
    }
    .recommend-box {
        background: #1b2d1b; border-left: 4px solid #4caf50;
        padding: 12px 16px; border-radius: 6px; margin: 6px 0;
    }
    .ai-box {
        background: #1b1b2d; border-left: 4px solid #7c4dff;
        padding: 12px 16px; border-radius: 6px; margin: 6px 0;
    }
    .warning-box {
        background: #2d2a1b; border-left: 4px solid #ff9800;
        padding: 12px 16px; border-radius: 6px; margin: 6px 0;
    }
    .success-box {
        background: #1b2d1b; border-left: 4px solid #4caf50;
        padding: 12px 16px; border-radius: 6px; margin: 6px 0;
    }
    div[data-testid="stMetric"] {
        background-color: #0e1117; border: 1px solid #262730;
        border-radius: 8px; padding: 12px;
    }
    .chat-msg-user { background: #1e293b; border-radius: 12px;
        padding: 12px 16px; margin: 8px 0; border-left: 3px solid #00b4d8; }
    .chat-msg-ai   { background: #1a1a2e; border-radius: 12px;
        padding: 12px 16px; margin: 8px 0; border-left: 3px solid #7c4dff; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
cfg = Config()
LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"


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


def run_query_nocache(conn, query: str) -> pd.DataFrame:
    """Non-cached query for AI-generated dynamic SQL."""
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall_arrow().to_pandas()


def metric_card(label: str, value, prefix="", suffix=""):
    st.markdown(
        f'<div class="metric-card"><h2>{prefix}{value}{suffix}</h2>'
        f'<p>{label}</p></div>', unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Workspace & Subscription Helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def load_workspace_mapping(_conn):
    """Load workspace → name/subscription mapping from Unity Catalog table."""
    try:
        df_ws = run_query(_conn,
            "SELECT CAST(workspace_id AS STRING) AS workspace_id, "
            "workspace_name, subscription_name, resource_group, location "
            "FROM salama_insurance.salama_silver.workspace_mapping "
            "WHERE workspace_name IS NOT NULL"
        )
        ws_name_map = dict(zip(
            df_ws["workspace_id"].astype(str).str.strip(),
            df_ws["workspace_name"].astype(str).str.strip()
        ))
        ws_sub_map = dict(zip(
            df_ws["workspace_id"].astype(str).str.strip(),
            df_ws["subscription_name"].astype(str).str.strip()
        ))
        all_subs = sorted(df_ws["subscription_name"].dropna().unique().tolist())
        return ws_name_map, ws_sub_map, all_subs
    except Exception as e:
        st.sidebar.warning(f"Workspace mapping unavailable: {e}")
        return {}, {}, []


def get_ws_ids_for_subscriptions(ws_sub_map, all_subs, selected_subs):
    """Return workspace IDs belonging to the selected subscriptions."""
    if not selected_subs or set(selected_subs) == set(all_subs):
        return None  # No filter needed — all selected
    return [wid for wid, sub in ws_sub_map.items() if sub in selected_subs]


def ws_sql_filter(col="u.workspace_id", ws_ids=None):
    """Return a SQL AND clause to filter by workspace IDs, or empty string if no filter."""
    if ws_ids is None:
        return ""
    ids_str = ", ".join(f"'{wid}'" for wid in ws_ids)
    return f" AND {col} IN ({ids_str})"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.databricks.com/wp-content/uploads/2022/06/db-nav-logo.svg", width=160)
    st.title("FinOps Monitor")
    st.caption("AI-Enhanced Edition v2.0")
    st.divider()
    warehouse_id = st.text_input(
        "SQL Warehouse ID",
        value=os.environ.get("DATABRICKS_WAREHOUSE_ID", ""),
        help="Found in the warehouse HTTP path: /sql/1.0/warehouses/<ID>",
    )

conn = None
if warehouse_id:
    try:
        conn = get_connection(warehouse_id)
    except Exception as e:
        st.error(f"Connection failed: {e}")
if not conn:
    st.title("📊 Databricks Monitoring & FinOps Dashboard")
    st.info("Enter a **SQL Warehouse ID** in the sidebar to connect.")
    st.stop()

st.sidebar.success("Connected")

# Load workspace mappings dynamically from Unity Catalog
WS_NAME_MAP, WS_SUBSCRIPTION_MAP, ALL_SUBSCRIPTIONS = load_workspace_mapping(conn)

with st.sidebar:
    selected_subscriptions = st.multiselect(
        "🔗 Subscription",
        options=ALL_SUBSCRIPTIONS,
        default=ALL_SUBSCRIPTIONS,
        help="Filter all metrics to workspaces in the selected Azure subscriptions.",
    )
    sub_ws_ids = get_ws_ids_for_subscriptions(WS_SUBSCRIPTION_MAP, ALL_SUBSCRIPTIONS, selected_subscriptions)
    st.subheader("Filters")
    date_range = st.date_input(
        "Date range",
        value=(date.today() - timedelta(days=30), date.today()),
        max_value=date.today(),
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date.today() - timedelta(days=30), date.today()

    sla_threshold_min = st.number_input(
        "SLA threshold (minutes)", min_value=1, value=60, step=5,
        help="Job runs exceeding this are flagged as SLA breaches.",
    )
    st.divider()
    search_term = st.text_input("Search jobs / clusters", placeholder="e.g. ETL, nightly")
    st.divider()
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Data range: {start_date} → {end_date}")

SD = start_date.isoformat()
ED = end_date.isoformat()


# ===========================================================================
# TAB LAYOUT — 7 tabs including AI features, Budget & Remediation
# ===========================================================================
tab_jobs, tab_cost, tab_forecast, tab_perf, tab_budget, tab_remediation, tab_agent = st.tabs([
    "🔧 Job Monitoring",
    "💰 Cost & FinOps",
    "🔮 AI Cost Forecast",
    "⚡ Performance",
    "🎯 Budget & Anomaly",
    "🛡️ Auto-Remediation",
    "🤖 AI FinOps Agent",
])


# ===========================================================================
# TAB 1 — JOB MONITORING (with AI Root Cause Analysis)
# ===========================================================================
with tab_jobs:
    st.header("Job Monitoring Dashboard")

    job_runs_query = f"""
    SELECT
        r.workspace_id, r.job_id, r.run_id,
        j.name AS job_name,
        r.result_state, r.run_type, r.trigger_type, r.termination_code, r.run_name,
        MIN(r.period_start_time) AS run_start,
        MAX(r.period_end_time)   AS run_end,
        MAX(r.run_duration_seconds)       AS duration_sec,
        MAX(r.execution_duration_seconds) AS exec_duration_sec,
        MAX(r.setup_duration_seconds)     AS setup_sec,
        MAX(r.queue_duration_seconds)     AS queue_sec
    FROM system.lakeflow.job_run_timeline r
    LEFT JOIN (
        SELECT workspace_id, job_id, name,
               ROW_NUMBER() OVER (PARTITION BY workspace_id, job_id ORDER BY change_time DESC) rn
        FROM system.lakeflow.jobs
    ) j ON r.workspace_id = j.workspace_id AND r.job_id = j.job_id AND j.rn = 1
    WHERE r.period_start_time >= '{SD}'
      AND r.period_end_time   <= '{ED}T23:59:59'
      AND r.result_state IS NOT NULL
    GROUP BY r.workspace_id, r.job_id, r.run_id, j.name,
             r.result_state, r.run_type, r.trigger_type, r.termination_code, r.run_name
    ORDER BY run_start DESC
    """
    with st.spinner("Loading job runs…"):
        df_runs = run_query(conn, job_runs_query)

    if df_runs.empty:
        st.warning("No job run data found for the selected date range.")
    else:
        # Apply subscription filter
        if sub_ws_ids is not None:
            df_runs = df_runs[df_runs["workspace_id"].astype(str).str.strip().isin(sub_ws_ids)]

        if search_term:
            mask = (
                df_runs["job_name"].fillna("").str.contains(search_term, case=False)
                | df_runs["run_name"].fillna("").str.contains(search_term, case=False)
            )
            df_runs = df_runs[mask]

        df_runs["duration_min"] = pd.to_numeric(df_runs["duration_sec"], errors="coerce").fillna(0) / 60
        df_runs["run_date"] = pd.to_datetime(df_runs["run_start"]).dt.date
        df_runs["sla_breach"] = df_runs["duration_min"] > sla_threshold_min

        total_runs   = len(df_runs)
        failed_runs  = int((df_runs["result_state"] == "FAILED").sum())
        success_rate = round((1 - failed_runs / max(total_runs, 1)) * 100, 1)
        avg_duration = round(df_runs["duration_min"].mean(), 1)
        sla_breaches = int(df_runs["sla_breach"].sum())

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1: metric_card("Total Runs", f"{total_runs:,}")
        with k2: metric_card("Failed Runs", f"{failed_runs:,}")
        with k3: metric_card("Success Rate", f"{success_rate}%")
        with k4: metric_card("Avg Duration", f"{avg_duration} min")
        with k5: metric_card("SLA Breaches", f"{sla_breaches:,}")
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Run Outcomes Over Time")
            daily = df_runs.groupby(["run_date", "result_state"]).size().reset_index(name="count")
            color_map = {"SUCCESS": "#4caf50", "FAILED": "#e94560",
                         "CANCELED": "#ff9800", "TIMED_OUT": "#9c27b0", "SKIPPED": "#607d8b"}
            fig = px.bar(daily, x="run_date", y="count", color="result_state",
                         color_discrete_map=color_map,
                         labels={"run_date": "Date", "count": "Runs", "result_state": "Status"})
            fig.update_layout(barmode="stack", height=350,
                              margin=dict(l=20, r=20, t=30, b=20),
                              legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Duration Distribution (min)")
            fig2 = px.histogram(df_runs, x="duration_min", nbins=40,
                                color_discrete_sequence=["#00b4d8"],
                                labels={"duration_min": "Duration (minutes)"})
            fig2.add_vline(x=sla_threshold_min, line_dash="dash",
                           line_color="#e94560", annotation_text=f"SLA: {sla_threshold_min}m")
            fig2.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # ---- Alerts + Failure Trend ----
        alert_col, trend_col = st.columns(2)
        with alert_col:
            st.subheader("🚨 Alerts")
            df_failed = df_runs[df_runs["result_state"] == "FAILED"].head(10)
            if not df_failed.empty:
                for _, row in df_failed.iterrows():
                    st.markdown(
                        f'<div class="alert-box"><strong>{row.get("job_name", "Unknown")}</strong> '
                        f'(run {row["run_id"]}) — FAILED<br><small>Termination: '
                        f'{row.get("termination_code", "N/A")} | {row.get("run_start", "")}'
                        f'</small></div>', unsafe_allow_html=True)
            else:
                st.success("No failed jobs in this period.")
            df_sla = df_runs[df_runs["sla_breach"]].head(5)
            if not df_sla.empty:
                for _, row in df_sla.iterrows():
                    st.markdown(
                        f'<div class="alert-box"><strong>SLA Breach:</strong> '
                        f'{row.get("job_name", "Unknown")} — '
                        f'{round(row["duration_min"], 1)} min (limit: {sla_threshold_min} min)'
                        f'</div>', unsafe_allow_html=True)

        with trend_col:
            st.subheader("Failure Trend (7-day rolling)")
            daily_fail = df_runs[df_runs["result_state"] == "FAILED"] \
                .groupby("run_date").size().reset_index(name="failures")
            all_dates = pd.DataFrame({"run_date": pd.date_range(start_date, end_date).date})
            daily_fail = all_dates.merge(daily_fail, on="run_date", how="left").fillna(0)
            daily_fail["rolling_7d"] = daily_fail["failures"].rolling(7, min_periods=1).mean()
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=daily_fail["run_date"], y=daily_fail["failures"],
                                  name="Daily Failures", marker_color="#e94560", opacity=0.5))
            fig3.add_trace(go.Scatter(x=daily_fail["run_date"], y=daily_fail["rolling_7d"],
                                      name="7d Avg", line=dict(color="#ff6b6b", width=2)))
            fig3.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20),
                               legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig3, use_container_width=True)

        # ================================================================
        # AI ROOT CAUSE ANALYSIS for failed jobs
        # ================================================================
        st.markdown("---")
        st.subheader("🧠 AI Root Cause Analysis")
        st.caption("Select a failed job to get an AI-powered diagnosis using `ai_query()`")

        failed_jobs_list = df_runs[df_runs["result_state"] == "FAILED"][
            ["job_name", "run_id", "termination_code", "duration_min", "run_start",
             "trigger_type", "setup_sec", "queue_sec", "exec_duration_sec"]
        ].head(20)

        if failed_jobs_list.empty:
            st.info("No failed jobs to analyze.")
        else:
            rca_options = [
                f"{r['job_name']} (run {r['run_id']})" for _, r in failed_jobs_list.iterrows()
            ]
            selected_rca = st.selectbox("Select a failed run:", rca_options, key="rca_select")
            if st.button("🔍 Analyze Root Cause", key="rca_btn"):
                idx = rca_options.index(selected_rca)
                row = failed_jobs_list.iloc[idx]
                rca_prompt = (
                    f"You are a Databricks FinOps expert. Analyze this failed job run and provide "
                    f"a root cause analysis with actionable recommendations.\n\n"
                    f"Job: {row['job_name']}\n"
                    f"Run ID: {row['run_id']}\n"
                    f"Termination Code: {row['termination_code']}\n"
                    f"Duration: {row['duration_min']:.1f} minutes\n"
                    f"Setup Time: {row['setup_sec']}s\n"
                    f"Queue Time: {row['queue_sec']}s\n"
                    f"Execution Time: {row['exec_duration_sec']}s\n"
                    f"Trigger: {row['trigger_type']}\n"
                    f"Start: {row['run_start']}\n\n"
                    f"Provide: 1) Likely root cause 2) Impact assessment "
                    f"3) Recommended fix 4) Prevention steps. Be concise."
                )
                rca_query = f"""
                SELECT ai_query(
                    '{LLM_ENDPOINT}',
                    '{rca_prompt.replace("'", "''")}')
                AS analysis
                """
                with st.spinner("AI analyzing root cause…"):
                    try:
                        rca_result = run_query_nocache(conn, rca_query)
                        analysis = rca_result.iloc[0]["analysis"]
                        st.markdown(f'<div class="ai-box">🧠 <strong>AI Analysis</strong><br><br>'
                                    f'{analysis}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"AI analysis failed: {e}")

        # ---- Drill-down table ----
        st.subheader("Job Runs Detail")
        job_filter = st.selectbox(
            "Filter by job",
            options=["All Jobs"] + sorted(df_runs["job_name"].dropna().unique().tolist()),
        )
        df_display = df_runs if job_filter == "All Jobs" else df_runs[df_runs["job_name"] == job_filter]
        display_cols = ["job_name", "run_id", "result_state", "trigger_type",
                        "run_start", "run_end", "duration_min", "exec_duration_sec",
                        "setup_sec", "queue_sec", "sla_breach"]
        available = [c for c in display_cols if c in df_display.columns]
        st.dataframe(df_display[available].head(200), use_container_width=True, hide_index=True,
                     column_config={
                         "sla_breach": st.column_config.CheckboxColumn("SLA Breach"),
                         "duration_min": st.column_config.NumberColumn("Duration (min)", format="%.1f"),
                     })
        csv = df_display[available].to_csv(index=False)
        st.download_button("📥 Export Job Runs CSV", csv, "job_runs.csv", "text/csv")


# ===========================================================================
# TAB 2 — COST & FINOPS
# ===========================================================================
with tab_cost:
    st.header("Cost & FinOps Dashboard")

    cost_query = f"""
    WITH usage_data AS (
        SELECT
            u.workspace_id, u.sku_name, u.usage_date, u.usage_quantity,
            u.billing_origin_product,
            u.usage_metadata.cluster_id   AS cluster_id,
            u.usage_metadata.job_id       AS job_id,
            u.usage_metadata.job_name     AS job_name,
            u.usage_metadata.warehouse_id AS warehouse_id,
            u.usage_metadata.app_name     AS app_name,
            u.usage_metadata.app_id       AS app_id,
            u.usage_metadata.endpoint_name AS endpoint_name,
            u.usage_metadata.endpoint_id  AS endpoint_id,
            u.usage_metadata.notebook_path AS notebook_path,
            u.usage_metadata.dlt_pipeline_id AS pipeline_id,
            COALESCE(u.identity_metadata.run_as,
                     u.identity_metadata.created_by,
                     u.identity_metadata.owned_by, 'unknown') AS user_identity,
            u.identity_metadata.created_by AS created_by
        FROM system.billing.usage u
        WHERE u.usage_date >= '{SD}' AND u.usage_date <= '{ED}'
    ),
    prices AS (
        SELECT sku_name, pricing.effective_list.default AS price_per_dbu,
               price_start_time, price_end_time
        FROM system.billing.list_prices
        WHERE price_end_time IS NULL OR price_end_time > '{SD}'
    ),
    warehouses AS (
        SELECT warehouse_id, warehouse_name, created_by AS wh_created_by,
               ROW_NUMBER() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) AS rn
        FROM system.compute.warehouses
    )
    SELECT ud.workspace_id, ud.sku_name, ud.usage_date,
           CAST(ud.usage_quantity AS DOUBLE) AS dbus,
           ud.billing_origin_product, ud.cluster_id, ud.job_id,
           ud.job_name, ud.warehouse_id, ud.user_identity, ud.created_by,
           ud.app_name, ud.app_id, ud.endpoint_name, ud.endpoint_id,
           ud.notebook_path, ud.pipeline_id,
           wh.warehouse_name,
           CAST(ud.usage_quantity AS DOUBLE) * COALESCE(CAST(p.price_per_dbu AS DOUBLE), 0) AS estimated_cost
    FROM usage_data ud
    LEFT JOIN prices p ON ud.sku_name = p.sku_name
        AND (p.price_end_time IS NULL OR ud.usage_date < p.price_end_time)
    LEFT JOIN warehouses wh ON ud.warehouse_id = wh.warehouse_id AND wh.rn = 1
    ORDER BY ud.usage_date DESC
    """
    with st.spinner("Loading billing data…"):
        df_cost = run_query(conn, cost_query)

    if df_cost.empty:
        st.warning("No billing data found for the selected date range.")
    else:
        # Apply subscription filter
        if sub_ws_ids is not None:
            df_cost = df_cost[df_cost["workspace_id"].astype(str).str.strip().isin(sub_ws_ids)]

        if search_term:
            mask = (df_cost["job_name"].fillna("").str.contains(search_term, case=False)
                    | df_cost["cluster_id"].fillna("").str.contains(search_term, case=False))
            df_cost_filtered = df_cost[mask]
        else:
            df_cost_filtered = df_cost

        for col in ["dbus", "estimated_cost"]:
            df_cost_filtered[col] = pd.to_numeric(df_cost_filtered[col], errors="coerce").fillna(0)

        total_cost  = df_cost_filtered["estimated_cost"].sum()
        total_dbus  = df_cost_filtered["dbus"].sum()
        unique_jobs = df_cost_filtered["job_id"].dropna().nunique()
        daily_avg   = total_cost / max((end_date - start_date).days, 1)

        k1, k2, k3, k4 = st.columns(4)
        with k1: metric_card("Total Estimated Cost", f"${total_cost:,.0f}")
        with k2: metric_card("Total DBUs", f"{total_dbus:,.0f}")
        with k3: metric_card("Active Jobs", f"{unique_jobs:,}")
        with k4: metric_card("Daily Avg Cost", f"${daily_avg:,.0f}")
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Daily Cost Trend")
            daily_cost = df_cost_filtered.groupby("usage_date").agg(
                cost=("estimated_cost", "sum"), dbus=("dbus", "sum")).reset_index()
            daily_cost["rolling_7d"] = daily_cost["cost"].rolling(7, min_periods=1).mean()
            cost_mean = daily_cost["cost"].mean()
            cost_std  = daily_cost["cost"].std()
            daily_cost["is_spike"] = daily_cost["cost"] > (cost_mean + 2 * cost_std)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=daily_cost["usage_date"], y=daily_cost["cost"],
                                 name="Daily Cost", marker_color="#00b4d8", opacity=0.6))
            fig.add_trace(go.Scatter(x=daily_cost["usage_date"], y=daily_cost["rolling_7d"],
                                     name="7-day Avg", line=dict(color="#e94560", width=2)))
            spikes = daily_cost[daily_cost["is_spike"]]
            if not spikes.empty:
                fig.add_trace(go.Scatter(x=spikes["usage_date"], y=spikes["cost"],
                                         mode="markers", name="Cost Spike",
                                         marker=dict(color="#ff0000", size=12, symbol="triangle-up")))
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20),
                              yaxis_title="Estimated Cost ($)",
                              legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Cost by Product")
            product_cost = df_cost_filtered.groupby("billing_origin_product") \
                .agg(cost=("estimated_cost", "sum")).reset_index().sort_values("cost", ascending=False)
            fig2 = px.pie(product_cost.head(10), names="billing_origin_product",
                          values="cost", hole=0.45,
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig2.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        b1, b2 = st.columns(2)
        with b1:
            st.subheader("Top 15 Jobs by Cost")
            job_cost = df_cost_filtered.groupby("job_name").agg(
                cost=("estimated_cost", "sum"), dbus=("dbus", "sum")
            ).reset_index().sort_values("cost", ascending=True).tail(15)
            fig3 = px.bar(job_cost, y="job_name", x="cost", orientation="h",
                          color="cost", color_continuous_scale="Reds",
                          labels={"cost": "Cost ($)", "job_name": ""})
            fig3.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                               showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)
        with b2:
            st.subheader("Top 15 Users by Cost")
            user_cost = df_cost_filtered.groupby("user_identity").agg(
                cost=("estimated_cost", "sum"), dbus=("dbus", "sum")
            ).reset_index().sort_values("cost", ascending=True).tail(15)
            fig4 = px.bar(user_cost, y="user_identity", x="cost", orientation="h",
                          color="cost", color_continuous_scale="Blues",
                          labels={"cost": "Cost ($)", "user_identity": ""})
            fig4.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                               showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig4, use_container_width=True)

        # ---- Service / App Cost Drivers ----
        st.markdown("---")
        st.subheader("⚙️ Cost by Service / App")
        st.caption("Which Databricks services and apps are consuming the most — with per-service user drill-down")

        # Build service-level summary from the cost data
        svc_summary = df_cost_filtered.groupby("billing_origin_product").agg(
            total_cost=("estimated_cost", "sum"),
            total_dbus=("dbus", "sum"),
            active_users=("user_identity", "nunique"),
            active_workspaces=("workspace_id", "nunique"),
        ).reset_index().sort_values("total_cost", ascending=False)
        svc_summary["cost_pct"] = (svc_summary["total_cost"] / svc_summary["total_cost"].sum() * 100).round(1)

        # Side-by-side: Treemap + Service table
        svc_c1, svc_c2 = st.columns([3, 2])
        with svc_c1:
            st.markdown("**Service Cost Treemap**")
            fig_svc_tree = px.treemap(
                svc_summary[svc_summary["total_cost"] > 0],
                path=["billing_origin_product"],
                values="total_cost",
                color="total_cost",
                color_continuous_scale="RdYlGn_r",
                labels={"billing_origin_product": "Service", "total_cost": "Cost ($)"},
            )
            fig_svc_tree.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10),
                                        coloraxis_showscale=False)
            fig_svc_tree.update_traces(
                texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
                textfont_size=12
            )
            st.plotly_chart(fig_svc_tree, use_container_width=True)

        with svc_c2:
            st.markdown("**Service Summary**")
            svc_display = svc_summary[["billing_origin_product", "total_cost", "cost_pct",
                                        "total_dbus", "active_users", "active_workspaces"]].copy()
            svc_display.columns = ["Service", "Cost ($)", "Share %", "DBUs", "Users", "Workspaces"]
            svc_display["Cost ($)"] = svc_display["Cost ($)"].apply(lambda x: f"${x:,.2f}")
            svc_display["DBUs"] = svc_display["DBUs"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(svc_display, use_container_width=True, hide_index=True, height=400)

        # Service drill-down expander
        with st.expander("🔍 Service Drill-Down — Top Users & Workspaces per Service"):
            selected_svc = st.selectbox(
                "Select a service",
                svc_summary["billing_origin_product"].tolist(),
                key="svc_drilldown_select"
            )
            svc_data = df_cost_filtered[df_cost_filtered["billing_origin_product"] == selected_svc]

            svc_total = svc_data["estimated_cost"].sum()
            svc_dbus = svc_data["dbus"].sum()
            svc_users = svc_data["user_identity"].nunique()

            sk1, sk2, sk3 = st.columns(3)
            with sk1: metric_card(f"{selected_svc} — Total Cost", f"${svc_total:,.0f}")
            with sk2: metric_card(f"{selected_svc} — DBUs", f"{svc_dbus:,.0f}")
            with sk3: metric_card(f"{selected_svc} — Users", f"{svc_users:,}")

            svc_dd1, svc_dd2 = st.columns(2)
            with svc_dd1:
                st.markdown(f"**Top Users — {selected_svc}**")
                svc_users_df = svc_data.groupby("user_identity").agg(
                    cost=("estimated_cost", "sum"), dbus=("dbus", "sum")
                ).reset_index().sort_values("cost", ascending=True).tail(10)
                fig_svc_u = px.bar(svc_users_df, y="user_identity", x="cost", orientation="h",
                                   color="cost", color_continuous_scale="Oranges",
                                   labels={"cost": "Cost ($)", "user_identity": ""})
                fig_svc_u.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20),
                                         showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_svc_u, use_container_width=True)

            with svc_dd2:
                st.markdown(f"**Top SKUs — {selected_svc}**")
                svc_skus = svc_data.groupby("sku_name").agg(
                    cost=("estimated_cost", "sum"), dbus=("dbus", "sum")
                ).reset_index().sort_values("cost", ascending=True).tail(10)
                fig_svc_s = px.bar(svc_skus, y="sku_name", x="cost", orientation="h",
                                   color="cost", color_continuous_scale="Purples",
                                   labels={"cost": "Cost ($)", "sku_name": ""})
                fig_svc_s.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20),
                                         showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_svc_s, use_container_width=True)

            # Daily trend for selected service
            st.markdown(f"**Daily Cost Trend — {selected_svc}**")
            svc_daily = svc_data.groupby("usage_date").agg(
                cost=("estimated_cost", "sum")).reset_index()
            fig_svc_daily = px.area(svc_daily, x="usage_date", y="cost",
                                     color_discrete_sequence=["#00b4d8"],
                                     labels={"cost": "Cost ($)", "usage_date": "Date"})
            fig_svc_daily.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_svc_daily, use_container_width=True)

        # ---- Asset Cost Drivers ----
        st.markdown("---")
        st.subheader("🏷️ Asset Cost Drivers")
        st.caption("Cost by named assets — Apps, SQL Warehouses, Serving Endpoints, Jobs, and Notebooks")

        # Derive a unified asset name column
        def get_asset_name(row):
            if pd.notna(row.get("app_name")) and row["app_name"]:
                return f"App: {row['app_name']}"
            elif pd.notna(row.get("warehouse_name")) and row["warehouse_name"]:
                return f"Warehouse: {row['warehouse_name']}"
            elif pd.notna(row.get("endpoint_name")) and row["endpoint_name"]:
                return f"Endpoint: {row['endpoint_name']}"
            elif pd.notna(row.get("job_name")) and row["job_name"]:
                return f"Job: {row['job_name']}"
            elif pd.notna(row.get("notebook_path")) and row["notebook_path"]:
                nb = str(row["notebook_path"]).split("/")[-1]
                return f"Notebook: {nb}"
            elif pd.notna(row.get("pipeline_id")) and row["pipeline_id"]:
                return f"Pipeline: {row['pipeline_id'][:12]}..."
            elif pd.notna(row.get("cluster_id")) and row["cluster_id"]:
                return f"Cluster: {row['cluster_id']}"
            else:
                return "Other / Platform"

        def get_asset_type(row):
            if pd.notna(row.get("app_name")) and row["app_name"]:
                return "App"
            elif pd.notna(row.get("warehouse_name")) and row["warehouse_name"]:
                return "SQL Warehouse"
            elif pd.notna(row.get("endpoint_name")) and row["endpoint_name"]:
                return "Serving Endpoint"
            elif pd.notna(row.get("job_name")) and row["job_name"]:
                return "Job"
            elif pd.notna(row.get("notebook_path")) and row["notebook_path"]:
                return "Notebook"
            elif pd.notna(row.get("pipeline_id")) and row["pipeline_id"]:
                return "Pipeline"
            elif pd.notna(row.get("cluster_id")) and row["cluster_id"]:
                return "Cluster"
            else:
                return "Other"

        df_cost_filtered["asset_name"] = df_cost_filtered.apply(get_asset_name, axis=1)
        df_cost_filtered["asset_type"] = df_cost_filtered.apply(get_asset_type, axis=1)
        df_cost_filtered["asset_owner"] = df_cost_filtered["created_by"].fillna(
            df_cost_filtered["user_identity"]
        )

        # Top assets by cost
        asset_summary = df_cost_filtered.groupby(["asset_name", "asset_type", "billing_origin_product"]).agg(
            total_cost=("estimated_cost", "sum"),
            total_dbus=("dbus", "sum"),
            owner=("asset_owner", "first"),
        ).reset_index().sort_values("total_cost", ascending=False)

        # Side-by-side: Top assets bar + asset type pie
        ast_c1, ast_c2 = st.columns([3, 2])
        with ast_c1:
            st.markdown("**Top 15 Assets by Cost**")
            top_assets = asset_summary.head(15).sort_values("total_cost", ascending=True)
            fig_ast = px.bar(
                top_assets, y="asset_name", x="total_cost", orientation="h",
                color="asset_type",
                color_discrete_map={
                    "App": "#e94560", "SQL Warehouse": "#00b4d8",
                    "Serving Endpoint": "#7c4dff", "Job": "#4caf50",
                    "Notebook": "#ff9800", "Pipeline": "#9c27b0",
                    "Cluster": "#607d8b", "Other": "#aaaaaa"
                },
                labels={"total_cost": "Cost ($)", "asset_name": "", "asset_type": "Type"},
                text=top_assets["total_cost"].apply(lambda x: f"${x:,.0f}")
            )
            fig_ast.update_traces(textposition="outside")
            fig_ast.update_layout(
                height=500, margin=dict(l=20, r=80, t=30, b=20),
                legend=dict(orientation="h", y=-0.15)
            )
            st.plotly_chart(fig_ast, use_container_width=True)

        with ast_c2:
            st.markdown("**Cost by Asset Type**")
            type_summary = df_cost_filtered.groupby("asset_type").agg(
                cost=("estimated_cost", "sum")).reset_index().sort_values("cost", ascending=False)
            fig_type = px.pie(
                type_summary, names="asset_type", values="cost", hole=0.4,
                color="asset_type",
                color_discrete_map={
                    "App": "#e94560", "SQL Warehouse": "#00b4d8",
                    "Serving Endpoint": "#7c4dff", "Job": "#4caf50",
                    "Notebook": "#ff9800", "Pipeline": "#9c27b0",
                    "Cluster": "#607d8b", "Other": "#aaaaaa"
                },
            )
            fig_type.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_type, use_container_width=True)

            # Asset count metrics
            st.markdown("**Asset Counts**")
            n_apps = asset_summary[asset_summary["asset_type"] == "App"]["asset_name"].nunique()
            n_wh = asset_summary[asset_summary["asset_type"] == "SQL Warehouse"]["asset_name"].nunique()
            n_ep = asset_summary[asset_summary["asset_type"] == "Serving Endpoint"]["asset_name"].nunique()
            ac1, ac2, ac3 = st.columns(3)
            with ac1: metric_card("Apps", f"{n_apps}")
            with ac2: metric_card("Warehouses", f"{n_wh}")
            with ac3: metric_card("Endpoints", f"{n_ep}")

        # Detailed asset table
        st.markdown("**Asset Cost Detail**")
        asset_display = asset_summary.head(30).copy()
        asset_display["total_cost"] = asset_display["total_cost"].apply(lambda x: f"${x:,.2f}")
        asset_display["total_dbus"] = asset_display["total_dbus"].apply(lambda x: f"{x:,.0f}")
        asset_display.columns = ["Asset", "Type", "Service", "Cost", "DBUs", "Owner"]
        st.dataframe(asset_display, use_container_width=True, hide_index=True)

        # ---- Workspace Cost Drivers ----
        st.markdown("---")
        st.subheader("🏢 Workspace Cost Drivers")
        st.caption("Cost breakdown by workspace — ID, name, products, jobs, and daily trends")

        ws_name_map = WS_NAME_MAP

        # Build workspace summary
        df_cost_filtered["workspace_id_str"] = df_cost_filtered["workspace_id"].astype(str).str.strip()
        df_cost_filtered["workspace_label"] = df_cost_filtered["workspace_id_str"].apply(
            lambda wid: f"{ws_name_map[wid]} ({wid})" if wid in ws_name_map else f"Workspace {wid}"
        )

        ws_summary = df_cost_filtered.groupby(["workspace_id_str", "workspace_label"]).agg(
            total_cost=("estimated_cost", "sum"),
            total_dbus=("dbus", "sum"),
            active_jobs=("job_id", "nunique"),
            active_users=("user_identity", "nunique"),
            top_product=("billing_origin_product", lambda x: x.value_counts().index[0] if len(x.value_counts()) > 0 else "N/A"),
        ).reset_index().sort_values("total_cost", ascending=False)

        num_days = max((end_date - start_date).days, 1)
        ws_summary["daily_avg"] = ws_summary["total_cost"] / num_days
        ws_summary["cost_pct"] = (ws_summary["total_cost"] / ws_summary["total_cost"].sum() * 100).round(1)

        # KPI row for top workspaces
        top_ws = ws_summary.head(4)
        ws_kpi_cols = st.columns(min(len(top_ws), 4))
        for i, (_, row) in enumerate(top_ws.iterrows()):
            if i < len(ws_kpi_cols):
                with ws_kpi_cols[i]:
                    metric_card(row["workspace_label"], f"${row['total_cost']:,.0f}")

        st.markdown("")

        # Side-by-side: Workspace cost comparison bar + cost share pie
        ws_c1, ws_c2 = st.columns(2)
        with ws_c1:
            st.markdown("**Cost by Workspace**")
            fig_ws_bar = px.bar(
                ws_summary, y="workspace_label", x="total_cost", orientation="h",
                color="total_cost", color_continuous_scale="Teal",
                labels={"total_cost": "Total Cost ($)", "workspace_label": ""},
                text=ws_summary["total_cost"].apply(lambda x: f"${x:,.0f}")
            )
            fig_ws_bar.update_traces(textposition="outside")
            fig_ws_bar.update_layout(
                height=max(250, len(ws_summary) * 55),
                margin=dict(l=20, r=80, t=30, b=20),
                showlegend=False, coloraxis_showscale=False
            )
            st.plotly_chart(fig_ws_bar, use_container_width=True)

        with ws_c2:
            st.markdown("**Cost Share (%)**")
            fig_ws_pie = px.pie(
                ws_summary, names="workspace_label", values="total_cost",
                hole=0.45, color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_ws_pie.update_layout(height=max(250, len(ws_summary) * 55),
                                      margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_ws_pie, use_container_width=True)

        # Daily trend by workspace (stacked area)
        st.markdown("**Daily Cost Trend by Workspace**")
        ws_daily = df_cost_filtered.groupby(["workspace_label", "usage_date"]).agg(
            cost=("estimated_cost", "sum")).reset_index()
        fig_ws_area = px.area(
            ws_daily, x="usage_date", y="cost", color="workspace_label",
            labels={"cost": "Cost ($)", "usage_date": "Date", "workspace_label": "Workspace"}
        )
        fig_ws_area.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20),
                                   legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_ws_area, use_container_width=True)

        # Per-workspace cost drivers table
        st.markdown("**Workspace Summary**")
        ws_display = ws_summary[["workspace_label", "total_cost", "daily_avg", "cost_pct",
                                  "total_dbus", "active_jobs", "active_users", "top_product"]].copy()
        ws_display.columns = ["Workspace", "Total Cost ($)", "Daily Avg ($)", "Cost Share %",
                               "Total DBUs", "Active Jobs", "Active Users", "Top Product"]
        ws_display["Total Cost ($)"] = ws_display["Total Cost ($)"].apply(lambda x: f"${x:,.2f}")
        ws_display["Daily Avg ($)"] = ws_display["Daily Avg ($)"].apply(lambda x: f"${x:,.2f}")
        ws_display["Total DBUs"] = ws_display["Total DBUs"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(ws_display, use_container_width=True, hide_index=True)

        # Per-workspace drill-down
        with st.expander("🔍 Workspace Cost Drill-Down"):
            selected_ws = st.selectbox(
                "Select a workspace",
                ws_summary["workspace_label"].tolist(),
                key="ws_drilldown_select"
            )
            selected_ws_id = ws_summary[ws_summary["workspace_label"] == selected_ws]["workspace_id_str"].iloc[0]
            ws_data = df_cost_filtered[df_cost_filtered["workspace_id_str"] == selected_ws_id]

            dd1, dd2 = st.columns(2)
            with dd1:
                st.markdown(f"**Top Products — {selected_ws}**")
                ws_products = ws_data.groupby("billing_origin_product").agg(
                    cost=("estimated_cost", "sum")).reset_index().sort_values("cost", ascending=False).head(10)
                fig_dd1 = px.bar(ws_products, x="billing_origin_product", y="cost",
                                 color="cost", color_continuous_scale="Reds",
                                 labels={"cost": "Cost ($)", "billing_origin_product": ""})
                fig_dd1.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20),
                                       showlegend=False, coloraxis_showscale=False,
                                       xaxis_tickangle=-45)
                st.plotly_chart(fig_dd1, use_container_width=True)

            with dd2:
                st.markdown(f"**Top Jobs — {selected_ws}**")
                ws_jobs = ws_data.groupby("job_name").agg(
                    cost=("estimated_cost", "sum")).reset_index().sort_values("cost", ascending=True).tail(10)
                fig_dd2 = px.bar(ws_jobs, y="job_name", x="cost", orientation="h",
                                 color="cost", color_continuous_scale="Blues",
                                 labels={"cost": "Cost ($)", "job_name": ""})
                fig_dd2.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20),
                                       showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_dd2, use_container_width=True)

            st.markdown(f"**Top Users — {selected_ws}**")
            ws_users = ws_data.groupby("user_identity").agg(
                cost=("estimated_cost", "sum"), dbus=("dbus", "sum")
            ).reset_index().sort_values("cost", ascending=False).head(10)
            ws_users["cost"] = ws_users["cost"].apply(lambda x: f"${x:,.2f}")
            ws_users["dbus"] = ws_users["dbus"].apply(lambda x: f"{x:,.0f}")
            ws_users.columns = ["User", "Cost ($)", "DBUs"]
            st.dataframe(ws_users, use_container_width=True, hide_index=True)

        # ---- AI Cost Spike Analysis ----
        st.subheader("🧠 AI Cost Anomaly Analysis")
        if not spikes.empty:
            spike_summary = "; ".join([
                f"{r['usage_date']}: ${r['cost']:,.0f}" for _, r in spikes.iterrows()
            ])
            avg_str = f"${cost_mean:,.0f}"
            spike_prompt = (
                f"You are a Databricks FinOps analyst. These are cost spike days "
                f"(>2 std devs above the {avg_str} daily average): {spike_summary}. "
                f"The date range is {SD} to {ED}. "
                f"Provide: 1) Likely causes of the spikes 2) Whether this is a pattern "
                f"3) Specific actions to reduce costs. Be concise and actionable."
            )
            spike_ai_query = f"""
            SELECT ai_query('{LLM_ENDPOINT}',
                            '{spike_prompt.replace("'", "''")}')
            AS analysis
            """
            if st.button("🔍 AI Analyze Cost Spikes", key="cost_spike_ai"):
                with st.spinner("AI analyzing cost patterns…"):
                    try:
                        result = run_query_nocache(conn, spike_ai_query)
                        st.markdown(f'<div class="ai-box">🧠 <strong>AI Analysis</strong><br><br>'
                                    f'{result.iloc[0]["analysis"]}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"AI analysis failed: {e}")
        else:
            st.success("No cost anomalies detected (threshold: 2σ above mean).")

        with st.expander("📋 Detailed Cost Data"):
            cost_cols = ["usage_date", "workspace_id", "billing_origin_product", "asset_name",
                         "asset_type", "app_name", "warehouse_name", "endpoint_name",
                         "job_name", "notebook_path", "sku_name",
                         "user_identity", "created_by", "dbus", "estimated_cost"]
            avail = [c for c in cost_cols if c in df_cost_filtered.columns]
            st.dataframe(df_cost_filtered[avail].head(500), use_container_width=True, hide_index=True)
            st.download_button("📥 Export Cost CSV",
                               df_cost_filtered[avail].to_csv(index=False),
                               "cost_data.csv", "text/csv")


# ===========================================================================
# TAB 3 — AI COST FORECAST (using ai_forecast)
# ===========================================================================
with tab_forecast:
    st.header("🔮 AI Cost Forecasting")
    st.caption("Powered by Databricks `ai_forecast()` — predicts future costs using historical billing data")

    fc1, fc2 = st.columns([1, 1])
    with fc1:
        forecast_days = st.slider("Forecast horizon (days)", min_value=7, max_value=90, value=30, step=7)
    with fc2:
        forecast_group = st.selectbox(
            "Forecast granularity",
            ["Total (all workloads)", "By Product", "By Workspace"],
        )

    horizon_date = (end_date + timedelta(days=forecast_days)).isoformat()
    ws_filter = ws_sql_filter("u.workspace_id", sub_ws_ids)

    if forecast_group == "Total (all workloads)":
        forecast_query = f"""
        WITH daily_cost AS (
            SELECT
                u.usage_date AS ds,
                SUM(CAST(u.usage_quantity AS DOUBLE) *
                    COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                ) AS cost
            FROM system.billing.usage u
            LEFT JOIN system.billing.list_prices p
                ON u.sku_name = p.sku_name
                AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
            WHERE u.usage_date >= DATE_SUB('{SD}', 60)
              AND u.usage_date <= '{ED}'
              {ws_filter}
            GROUP BY u.usage_date
        ),
        forecast AS (
            SELECT * FROM ai_forecast(
                TABLE(daily_cost),
                horizon => '{horizon_date}',
                time_col => 'ds',
                value_col => 'cost',
                frequency => 'day',
                prediction_interval_width => 0.9,
                parameters => '{{"global_floor": 0}}'
            )
        )
        SELECT
            h.ds, h.cost_forecast, h.cost_upper, h.cost_lower
        FROM forecast h
        ORDER BY h.ds
        """
    elif forecast_group == "By Product":
        forecast_query = f"""
        WITH daily_cost AS (
            SELECT
                u.usage_date AS ds,
                u.billing_origin_product AS product,
                SUM(CAST(u.usage_quantity AS DOUBLE) *
                    COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                ) AS cost
            FROM system.billing.usage u
            LEFT JOIN system.billing.list_prices p
                ON u.sku_name = p.sku_name
                AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
            WHERE u.usage_date >= DATE_SUB('{SD}', 60)
              AND u.usage_date <= '{ED}'
              AND u.billing_origin_product IS NOT NULL
              {ws_filter}
            GROUP BY u.usage_date, u.billing_origin_product
        ),
        forecast AS (
            SELECT * FROM ai_forecast(
                TABLE(daily_cost),
                horizon => '{horizon_date}',
                time_col => 'ds',
                value_col => 'cost',
                group_col => 'product',
                frequency => 'day',
                prediction_interval_width => 0.9,
                parameters => '{{"global_floor": 0}}'
            )
        )
        SELECT h.ds, h.product, h.cost_forecast, h.cost_upper, h.cost_lower
        FROM forecast h
        ORDER BY h.product, h.ds
        """
    else:  # By Workspace
        forecast_query = f"""
        WITH daily_cost AS (
            SELECT
                u.usage_date AS ds,
                u.workspace_id,
                SUM(CAST(u.usage_quantity AS DOUBLE) *
                    COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                ) AS cost
            FROM system.billing.usage u
            LEFT JOIN system.billing.list_prices p
                ON u.sku_name = p.sku_name
                AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
            WHERE u.usage_date >= DATE_SUB('{SD}', 60)
              AND u.usage_date <= '{ED}'
              {ws_filter}
            GROUP BY u.usage_date, u.workspace_id
        ),
        forecast AS (
            SELECT * FROM ai_forecast(
                TABLE(daily_cost),
                horizon => '{horizon_date}',
                time_col => 'ds',
                value_col => 'cost',
                group_col => 'workspace_id',
                frequency => 'day',
                prediction_interval_width => 0.9,
                parameters => '{{"global_floor": 0}}'
            )
        )
        SELECT h.ds, h.workspace_id, h.cost_forecast, h.cost_upper, h.cost_lower
        FROM forecast h
        ORDER BY h.workspace_id, h.ds
        """

    if st.button("🚀 Run Forecast", type="primary", key="run_forecast"):
        with st.spinner(f"Running ai_forecast for {forecast_days}-day horizon…"):
            try:
                df_forecast = run_query_nocache(conn, forecast_query)

                if df_forecast.empty:
                    st.warning("Forecast returned no results. Ensure there is sufficient historical data.")
                else:
                    for col in ["cost_forecast", "cost_upper", "cost_lower"]:
                        if col in df_forecast.columns:
                            df_forecast[col] = pd.to_numeric(df_forecast[col], errors="coerce")

                    # ---- Also get actuals for overlay ----
                    actuals_query = f"""
                    SELECT u.usage_date AS ds,
                           SUM(CAST(u.usage_quantity AS DOUBLE) *
                               COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                           ) AS cost
                    FROM system.billing.usage u
                    LEFT JOIN system.billing.list_prices p
                        ON u.sku_name = p.sku_name
                        AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
                    WHERE u.usage_date >= '{SD}' AND u.usage_date <= '{ED}'
                    {ws_filter}
                    GROUP BY u.usage_date ORDER BY u.usage_date
                    """
                    df_actuals = run_query(conn, actuals_query)
                    df_actuals["cost"] = pd.to_numeric(df_actuals["cost"], errors="coerce")

                    # ---- KPIs ----
                    total_forecast = df_forecast["cost_forecast"].sum()
                    daily_forecast_avg = df_forecast["cost_forecast"].mean()
                    monthly_estimate = daily_forecast_avg * 30
                    max_day = df_forecast.loc[df_forecast["cost_forecast"].idxmax()]

                    fk1, fk2, fk3, fk4 = st.columns(4)
                    with fk1: metric_card(f"Forecasted {forecast_days}d Total", f"${total_forecast:,.0f}")
                    with fk2: metric_card("Daily Avg Forecast", f"${daily_forecast_avg:,.0f}")
                    with fk3: metric_card("Monthly Estimate", f"${monthly_estimate:,.0f}")
                    with fk4: metric_card("Peak Day Cost", f"${max_day['cost_forecast']:,.0f}")

                    st.markdown("---")

                    if forecast_group == "Total (all workloads)":
                        fig = go.Figure()
                        # Actuals
                        fig.add_trace(go.Scatter(
                            x=df_actuals["ds"], y=df_actuals["cost"],
                            name="Actual Cost", line=dict(color="#00b4d8", width=2)))
                        # Forecast
                        fig.add_trace(go.Scatter(
                            x=df_forecast["ds"], y=df_forecast["cost_forecast"],
                            name="Forecast", line=dict(color="#7c4dff", width=2, dash="dash")))
                        # Confidence band
                        fig.add_trace(go.Scatter(
                            x=pd.concat([df_forecast["ds"], df_forecast["ds"][::-1]]),
                            y=pd.concat([df_forecast["cost_upper"], df_forecast["cost_lower"][::-1]]),
                            fill="toself", fillcolor="rgba(124,77,255,0.15)",
                            line=dict(color="rgba(255,255,255,0)"), name="90% CI"))
                        fig.update_layout(
                            title="Cost Forecast with Confidence Interval",
                            height=450, margin=dict(l=20, r=20, t=50, b=20),
                            yaxis_title="Estimated Cost ($)",
                            legend=dict(orientation="h", y=-0.15))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        group_col = "product" if "product" in df_forecast.columns else "workspace_id"
                        fig = px.line(
                            df_forecast, x="ds", y="cost_forecast", color=group_col,
                            labels={"cost_forecast": "Forecasted Cost ($)", "ds": "Date"})
                        fig.update_layout(height=450, margin=dict(l=20, r=20, t=50, b=20),
                                          legend=dict(orientation="h", y=-0.15))
                        st.plotly_chart(fig, use_container_width=True)

                    # ---- AI interpretation ----
                    st.subheader("🧠 AI Forecast Interpretation")
                    actual_avg = df_actuals["cost"].mean()
                    trend_pct = ((daily_forecast_avg - actual_avg) / max(actual_avg, 0.01)) * 100
                    interp_prompt = (
                        f"You are a Databricks FinOps analyst. Interpret this cost forecast:\n"
                        f"- Historical daily avg: ${actual_avg:,.0f}\n"
                        f"- Forecasted daily avg: ${daily_forecast_avg:,.0f} ({trend_pct:+.1f}%)\n"
                        f"- {forecast_days}-day total forecast: ${total_forecast:,.0f}\n"
                        f"- Peak day: {max_day['ds']} at ${max_day['cost_forecast']:,.0f}\n"
                        f"Provide: 1) Trend summary 2) Budget implications "
                        f"3) Cost optimization actions. Be concise."
                    )
                    interp_query = f"""
                    SELECT ai_query('{LLM_ENDPOINT}',
                                    '{interp_prompt.replace("'", "''")}')
                    AS interpretation
                    """
                    with st.spinner("AI interpreting forecast…"):
                        try:
                            interp = run_query_nocache(conn, interp_query)
                            st.markdown(
                                f'<div class="ai-box">🔮 <strong>AI Interpretation</strong><br><br>'
                                f'{interp.iloc[0]["interpretation"]}</div>',
                                unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"AI interpretation unavailable: {e}")

                    # Forecast data table
                    with st.expander("📋 Forecast Data"):
                        st.dataframe(df_forecast, use_container_width=True, hide_index=True)
                        st.download_button("📥 Export Forecast CSV",
                                           df_forecast.to_csv(index=False),
                                           "cost_forecast.csv", "text/csv")
            except Exception as e:
                st.error(f"Forecast failed: {e}")
                st.info("Ensure your SQL warehouse supports `ai_forecast()` (requires serverless or Pro warehouse).")


# ===========================================================================
# TAB 4 — PERFORMANCE INSIGHTS (with AI Recommendations)
# ===========================================================================
with tab_perf:
    st.header("Performance & Cluster Insights")

    node_query = f"""
    SELECT
        n.cluster_id, c.cluster_name, c.workspace_id, c.owned_by,
        c.worker_node_type, c.worker_count, c.min_autoscale_workers,
        c.max_autoscale_workers, c.auto_termination_minutes, c.cluster_source,
        DATE(n.start_time) AS metric_date,
        AVG(n.cpu_user_percent + n.cpu_system_percent) AS avg_cpu_pct,
        MAX(n.cpu_user_percent + n.cpu_system_percent) AS max_cpu_pct,
        AVG(n.mem_used_percent) AS avg_mem_pct,
        MAX(n.mem_used_percent) AS max_mem_pct,
        COUNT(DISTINCT n.instance_id) AS node_count,
        SUM(CAST(n.network_sent_bytes AS DOUBLE)) AS total_net_sent,
        SUM(CAST(n.network_received_bytes AS DOUBLE)) AS total_net_recv,
        COUNT(*) AS sample_count
    FROM system.compute.node_timeline n
    LEFT JOIN (
        SELECT cluster_id, workspace_id, cluster_name, owned_by,
               worker_node_type, worker_count, min_autoscale_workers,
               max_autoscale_workers, auto_termination_minutes, cluster_source,
               ROW_NUMBER() OVER (PARTITION BY cluster_id ORDER BY create_time DESC) rn
        FROM system.compute.clusters
    ) c ON n.cluster_id = c.cluster_id AND c.rn = 1
    WHERE n.start_time >= '{SD}' AND n.end_time <= '{ED}T23:59:59'
    GROUP BY n.cluster_id, c.cluster_name, c.workspace_id, c.owned_by,
             c.worker_node_type, c.worker_count, c.min_autoscale_workers,
             c.max_autoscale_workers, c.auto_termination_minutes,
             c.cluster_source, DATE(n.start_time)
    ORDER BY metric_date DESC, avg_cpu_pct ASC
    """
    with st.spinner("Loading cluster utilization…"):
        df_nodes = run_query(conn, node_query)

    if df_nodes.empty:
        st.warning("No cluster utilization data found for the selected date range.")
    else:
        # Apply subscription filter
        if sub_ws_ids is not None:
            df_nodes = df_nodes[df_nodes["workspace_id"].astype(str).str.strip().isin(sub_ws_ids)]

        if search_term:
            df_nodes = df_nodes[df_nodes["cluster_name"].fillna("").str.contains(search_term, case=False)]

        for col in ["avg_cpu_pct", "max_cpu_pct", "avg_mem_pct", "max_mem_pct"]:
            df_nodes[col] = pd.to_numeric(df_nodes[col], errors="coerce").fillna(0)

        cluster_summary = df_nodes.groupby(
            ["cluster_id", "cluster_name", "owned_by", "worker_node_type",
             "worker_count", "auto_termination_minutes", "cluster_source"]
        ).agg(avg_cpu=("avg_cpu_pct", "mean"), max_cpu=("max_cpu_pct", "max"),
               avg_mem=("avg_mem_pct", "mean"), max_mem=("max_mem_pct", "max"),
               days_active=("metric_date", "nunique"), total_samples=("sample_count", "sum"),
               avg_nodes=("node_count", "mean")).reset_index()

        def classify_cluster(row):
            if row["avg_cpu"] < 15 and row["avg_mem"] < 30: return "Idle / Underutilized"
            elif row["avg_cpu"] < 30: return "Underutilized"
            elif row["avg_cpu"] > 85 or row["avg_mem"] > 90: return "Over-loaded"
            else: return "Well-utilized"
        cluster_summary["utilization_class"] = cluster_summary.apply(classify_cluster, axis=1)

        total_clusters = cluster_summary["cluster_id"].nunique()
        idle_clusters = (cluster_summary["utilization_class"].isin(["Idle / Underutilized", "Underutilized"])).sum()
        overloaded = (cluster_summary["utilization_class"] == "Over-loaded").sum()
        avg_cpu_all = round(cluster_summary["avg_cpu"].mean(), 1)

        k1, k2, k3, k4 = st.columns(4)
        with k1: metric_card("Active Clusters", f"{total_clusters:,}")
        with k2: metric_card("Underutilized", f"{idle_clusters:,}")
        with k3: metric_card("Over-loaded", f"{overloaded:,}")
        with k4: metric_card("Avg CPU Usage", f"{avg_cpu_all}%")
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Cluster Utilization Scatter")
            cmap = {"Idle / Underutilized": "#e94560", "Underutilized": "#ff9800",
                    "Well-utilized": "#4caf50", "Over-loaded": "#9c27b0"}
            fig = px.scatter(cluster_summary, x="avg_cpu", y="avg_mem",
                             color="utilization_class", color_discrete_map=cmap,
                             size="days_active", hover_name="cluster_name",
                             labels={"avg_cpu": "Avg CPU %", "avg_mem": "Avg Memory %"})
            fig.add_vrect(x0=0, x1=15, fillcolor="#e94560", opacity=0.05)
            fig.add_hrect(y0=0, y1=30, fillcolor="#e94560", opacity=0.05)
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("CPU Utilization Over Time")
            daily_cpu = df_nodes.groupby("metric_date").agg(
                avg_cpu=("avg_cpu_pct", "mean"),
                p90_cpu=("avg_cpu_pct", lambda x: x.quantile(0.9))).reset_index()
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=daily_cpu["metric_date"], y=daily_cpu["avg_cpu"],
                                      name="Avg CPU", fill="tozeroy", line=dict(color="#00b4d8")))
            fig2.add_trace(go.Scatter(x=daily_cpu["metric_date"], y=daily_cpu["p90_cpu"],
                                      name="P90 CPU", line=dict(color="#e94560", dash="dash")))
            fig2.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20),
                               yaxis_title="CPU %", legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig2, use_container_width=True)

        # ---- Heatmap ----
        st.subheader("Cluster CPU Heatmap (Top 20)")
        top20 = cluster_summary.nlargest(20, "days_active")["cluster_id"].tolist()
        hm = df_nodes[df_nodes["cluster_id"].isin(top20)].pivot_table(
            index="cluster_name", columns="metric_date", values="avg_cpu_pct", aggfunc="mean").fillna(0)
        if not hm.empty:
            fig_hm = px.imshow(hm, aspect="auto", color_continuous_scale="RdYlGn_r",
                               labels={"color": "Avg CPU %"})
            fig_hm.update_layout(height=max(250, len(hm) * 28), margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_hm, use_container_width=True)

        # ================================================================
        # AI-POWERED OPTIMIZATION RECOMMENDATIONS
        # ================================================================
        st.markdown("---")
        st.subheader("🧠 AI Optimization Recommendations")
        st.caption("Powered by `ai_query()` — context-aware recommendations from real cluster data")

        idle_df = cluster_summary[cluster_summary["utilization_class"].isin(
            ["Idle / Underutilized", "Underutilized"])].sort_values("avg_cpu").head(10)
        overloaded_df = cluster_summary[cluster_summary["utilization_class"] == "Over-loaded"].head(5)

        if not idle_df.empty or not overloaded_df.empty:
            cluster_context_parts = []
            for _, r in idle_df.iterrows():
                cluster_context_parts.append(
                    f"- {r.get('cluster_name', r['cluster_id'])}: CPU={r['avg_cpu']:.0f}%, "
                    f"Mem={r['avg_mem']:.0f}%, Workers={r.get('worker_count', 'N/A')}, "
                    f"Type={r.get('worker_node_type', 'N/A')}, "
                    f"AutoTerm={r.get('auto_termination_minutes', 'N/A')}min, "
                    f"Source={r.get('cluster_source', 'N/A')}, "
                    f"DaysActive={r['days_active']}, Class={r['utilization_class']}")
            for _, r in overloaded_df.iterrows():
                cluster_context_parts.append(
                    f"- {r.get('cluster_name', r['cluster_id'])}: CPU={r['avg_cpu']:.0f}%, "
                    f"Mem={r['avg_mem']:.0f}%, Workers={r.get('worker_count', 'N/A')}, "
                    f"Type={r.get('worker_node_type', 'N/A')}, Class=OVERLOADED")

            cluster_context = "\n".join(cluster_context_parts)
            ai_rec_prompt = (
                f"You are a senior Databricks platform engineer and FinOps specialist. "
                f"Analyze these clusters and provide specific, actionable optimization recommendations. "
                f"Consider instance types, worker counts, auto-termination settings, autoscaling, "
                f"and cluster source (JOB vs all-purpose).\n\n"
                f"CLUSTER DATA:\n{cluster_context}\n\n"
                f"For each problematic cluster, provide:\n"
                f"1. Specific issue\n"
                f"2. Estimated monthly savings or performance gain\n"
                f"3. Exact action to take (instance type change, worker count, settings)\n"
                f"4. Risk level of the change (low/medium/high)\n\n"
                f"Format as a structured report. Be specific with numbers."
            )
            ai_rec_query = f"""
            SELECT ai_query('{LLM_ENDPOINT}',
                            '{ai_rec_prompt.replace("'", "''")}') AS recommendations
            """

            if st.button("🔍 Generate AI Recommendations", key="ai_recs"):
                with st.spinner("AI generating optimization plan…"):
                    try:
                        recs = run_query_nocache(conn, ai_rec_query)
                        st.markdown(
                            f'<div class="ai-box">🧠 <strong>AI Optimization Report</strong>'
                            f'<br><br>{recs.iloc[0]["recommendations"]}</div>',
                            unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"AI recommendations failed: {e}")
        else:
            st.success("All clusters are well-utilized. No optimization needed.")

        # ---- Rule-based recommendations (always shown) ----
        with st.expander("📋 Rule-Based Recommendations"):
            for _, row in idle_df.iterrows():
                cname = row.get("cluster_name") or row["cluster_id"]
                recs = []
                if row["avg_cpu"] < 15:
                    recs.append("Consider **terminating** — CPU near zero.")
                elif row["avg_cpu"] < 30:
                    recs.append("Consider **downsizing** instance type.")
                at = row.get("auto_termination_minutes")
                if pd.notna(at) and at > 60:
                    recs.append(f"Reduce auto-termination from **{int(at)} min** to **20–30 min**.")
                elif pd.isna(at) or at == 0:
                    recs.append("Enable **auto-termination** (20–30 min).")
                wc = row.get("worker_count")
                if pd.notna(wc) and wc > 4 and row["avg_cpu"] < 25:
                    recs.append(f"Reduce workers from {int(wc)} to **{max(1, int(wc // 2))}**.")
                if row.get("cluster_source") not in ("JOB", "PIPELINE"):
                    recs.append("Switch from all-purpose to **job clusters** for scheduled work.")
                for rec in recs:
                    st.markdown(f'<div class="recommend-box">🔧 <strong>{cname}</strong> '
                                f'(CPU: {row["avg_cpu"]:.0f}%): {rec}</div>', unsafe_allow_html=True)

        with st.expander("📋 Cluster Details"):
            detail_cols = ["cluster_name", "cluster_id", "owned_by", "worker_node_type",
                           "worker_count", "auto_termination_minutes", "cluster_source",
                           "avg_cpu", "max_cpu", "avg_mem", "days_active", "utilization_class"]
            avail = [c for c in detail_cols if c in cluster_summary.columns]
            st.dataframe(cluster_summary[avail], use_container_width=True, hide_index=True,
                         column_config={
                             "avg_cpu": st.column_config.ProgressColumn("Avg CPU %", min_value=0, max_value=100, format="%.0f%%"),
                             "avg_mem": st.column_config.ProgressColumn("Avg Mem %", min_value=0, max_value=100, format="%.0f%%"),
                         })
            st.download_button("📥 Export Cluster CSV",
                               cluster_summary[avail].to_csv(index=False),
                               "cluster_perf.csv", "text/csv")


# ===========================================================================
# TAB 5 — BUDGET & ENHANCED ANOMALY DETECTION (NEW!)
# ===========================================================================
with tab_budget:
    st.header("🎯 Budget Management & Enhanced Anomaly Detection")

    if not BUDGET_MODULE_AVAILABLE or not ANOMALY_MODULE_AVAILABLE:
        st.warning(
            "Budget or Anomaly modules not available. Ensure finops_budget.py and "
            "finops_anomaly.py are in the same directory as app.py."
        )
    else:
        # ---- Budget Configuration ----
        st.subheader("💰 Budget Configuration")
        budget_col1, budget_col2, budget_col3 = st.columns(3)
        with budget_col1:
            monthly_budget = st.number_input(
                "Monthly Budget ($)",
                min_value=100,
                max_value=10000000,
                value=st.session_state.get("monthly_budget", 50000),
                step=1000,
                help="Set your monthly Databricks spend budget"
            )
            st.session_state["monthly_budget"] = monthly_budget
        with budget_col2:
            alert_thresholds = st.multiselect(
                "Alert Thresholds (%)",
                options=[25, 50, 75, 80, 90, 95, 100, 110],
                default=[50, 75, 90, 100],
                help="Trigger alerts when budget utilization reaches these levels"
            )
        with budget_col3:
            st.metric("Budget Period", f"{start_date} to {end_date}")

        # Initialize BudgetManager
        budget_mgr = BudgetManager(conn, start_date, end_date)

        # ---- Budget KPIs ----
        st.markdown("---")
        prediction = budget_mgr.predict_budget_breach(monthly_budget)

        bk1, bk2, bk3, bk4, bk5 = st.columns(5)
        with bk1:
            metric_card("Current Spend", f"${prediction['current_spend']:,.0f}")
        with bk2:
            util_color = "#4caf50" if prediction['budget_utilization_pct'] < 75 else (
                "#ff9800" if prediction['budget_utilization_pct'] < 90 else "#e94560")
            st.markdown(
                f'<div class="metric-card"><h2 style="color:{util_color};">'
                f'{prediction["budget_utilization_pct"]:.1f}%</h2>'
                f'<p>Budget Used</p></div>', unsafe_allow_html=True)
        with bk3:
            metric_card("Daily Burn Rate", f"${prediction['daily_burn_rate']:,.0f}")
        with bk4:
            if prediction["will_breach"]:
                st.markdown(
                    f'<div class="metric-card"><h2 style="color:#e94560;">'
                    f'{prediction["days_until_breach"]} days</h2>'
                    f'<p>Until Breach</p></div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="metric-card"><h2 style="color:#4caf50;">Safe</h2>'
                    f'<p>No Breach Expected</p></div>', unsafe_allow_html=True)
        with bk5:
            if prediction["will_breach"]:
                st.markdown(
                    f'<div class="metric-card"><h2 style="color:#e94560;">'
                    f'+{prediction["projected_overshoot_pct"]:.1f}%</h2>'
                    f'<p>Projected Overshoot</p></div>', unsafe_allow_html=True)
            else:
                metric_card("Projected Total", f"${prediction['projected_monthly_total']:,.0f}")

        # ---- Budget Alerts ----
        alerts = budget_mgr.get_budget_alerts(monthly_budget, alert_thresholds)
        if alerts:
            st.subheader("🚨 Budget Alerts")
            for alert in alerts:
                severity_colors = {
                    "critical": "#e94560", "high": "#ff5722",
                    "warning": "#ff9800", "info": "#2196f3"
                }
                color = severity_colors.get(alert["severity"], "#607d8b")
                st.markdown(
                    f'<div class="alert-box" style="border-left-color: {color};">'
                    f'<strong>{alert["severity"].upper()}</strong>: {alert["message"]}</div>',
                    unsafe_allow_html=True)

        # ---- Budget Burndown Chart ----
        st.markdown("---")
        st.subheader("📉 Budget Burndown")
        burndown_df = budget_mgr.get_budget_burndown(monthly_budget)
        if not burndown_df.empty:
            fig_burn = go.Figure()
            # Cumulative spend area
            fig_burn.add_trace(go.Scatter(
                x=burndown_df["usage_date"], y=burndown_df["cumulative_cost"],
                name="Actual Spend", fill="tozeroy",
                line=dict(color="#00b4d8", width=2), fillcolor="rgba(0,180,216,0.3)"))
            # Budget line
            fig_burn.add_trace(go.Scatter(
                x=burndown_df["usage_date"], y=burndown_df["budget_line"],
                name="Budget", line=dict(color="#e94560", width=2, dash="dash")))
            # Expected pace
            fig_burn.add_trace(go.Scatter(
                x=burndown_df["usage_date"], y=burndown_df["expected_pace"],
                name="Expected Pace", line=dict(color="#4caf50", width=1, dash="dot")))
            fig_burn.update_layout(
                height=400, margin=dict(l=20, r=20, t=30, b=20),
                yaxis_title="Cumulative Cost ($)",
                legend=dict(orientation="h", y=-0.15),
                hovermode="x unified")
            st.plotly_chart(fig_burn, use_container_width=True)

            # Ahead/behind indicator
            latest = burndown_df.iloc[-1]
            if latest["ahead_behind"] > 0:
                st.markdown(
                    f'<div class="warning-box">📈 <strong>Ahead of pace</strong> by '
                    f'${latest["ahead_behind"]:,.0f} — spending faster than expected.</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="success-box">✅ <strong>On track</strong> — '
                    f'${abs(latest["ahead_behind"]):,.0f} under expected pace.</div>',
                    unsafe_allow_html=True)

        # ---- AI Budget Insight ----
        if st.button("🧠 Get AI Budget Analysis", key="ai_budget"):
            insight_query = budget_mgr.get_ai_budget_insight(monthly_budget)
            with st.spinner("AI analyzing budget…"):
                try:
                    insight_result = run_query_nocache(conn, insight_query)
                    st.markdown(
                        f'<div class="ai-box">💰 <strong>AI Budget Analysis</strong><br><br>'
                        f'{insight_result.iloc[0]["insight"]}</div>',
                        unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"AI analysis failed: {e}")

        # ================================================================
        # ENHANCED ANOMALY DETECTION SECTION
        # ================================================================
        st.markdown("---")
        st.subheader("🔍 Enhanced Cost Anomaly Detection")
        st.caption("Multi-method anomaly detection with per-resource granularity")

        anom_col1, anom_col2, anom_col3 = st.columns(3)
        with anom_col1:
            anomaly_granularity = st.selectbox(
                "Granularity",
                ["job", "cluster", "user", "product", "workspace"],
                index=0,
                help="Analyze anomalies per resource type"
            )
        with anom_col2:
            anomaly_methods = ["Z-Score (Rolling)"]
            if SKLEARN_AVAILABLE:
                anomaly_methods.extend(["IQR (Interquartile)", "Isolation Forest (ML)"])
            else:
                anomaly_methods.append("IQR (Interquartile)")
            anomaly_method = st.selectbox(
                "Detection Method",
                anomaly_methods,
                help="Z-Score: rolling window; IQR: quartile bounds; Isolation Forest: ML-based"
            )
        with anom_col3:
            anomaly_threshold = st.slider(
                "Sensitivity",
                min_value=1.5, max_value=4.0, value=2.5, step=0.25,
                help="Lower = more sensitive (more anomalies detected)"
            )

        if st.button("🚀 Run Anomaly Detection", key="run_anomaly"):
            with st.spinner(f"Running {anomaly_method} anomaly detection on {anomaly_granularity} level…"):
                try:
                    # Get cost data by resource
                    df_resource_cost = get_cost_anomalies_by_resource(
                        conn, start_date, end_date,
                        granularity=anomaly_granularity,
                        run_query_fn=run_query_nocache
                    )

                    if df_resource_cost.empty:
                        st.warning("No cost data found for anomaly detection.")
                    else:
                        # Apply selected method
                        if "Z-Score" in anomaly_method:
                            df_anomalies = detect_anomalies_zscore(
                                df_resource_cost, "daily_cost",
                                group_col="resource_name",
                                threshold=anomaly_threshold
                            )
                        elif "IQR" in anomaly_method:
                            df_anomalies = detect_anomalies_iqr(
                                df_resource_cost, "daily_cost",
                                group_col="resource_name",
                                multiplier=anomaly_threshold
                            )
                        else:  # Isolation Forest
                            df_anomalies = detect_anomalies_isolation_forest(
                                df_resource_cost, "daily_cost",
                                group_col="resource_name",
                                contamination=0.05
                            )

                        # Get summary
                        summary = get_anomaly_summary(df_anomalies)

                        # Display KPIs
                        ak1, ak2, ak3, ak4 = st.columns(4)
                        with ak1:
                            metric_card("Total Anomalies", f"{summary['total_anomalies']:,}")
                        with ak2:
                            metric_card("Excess Cost", f"${summary['estimated_excess_cost']:,.0f}")
                        with ak3:
                            metric_card("Critical", f"{summary['severity_distribution']['critical']}")
                        with ak4:
                            metric_card("High Severity", f"{summary['severity_distribution']['high']}")

                        # Top offenders
                        if summary["top_offenders"]:
                            st.subheader("🚨 Top Cost Anomaly Offenders")
                            offender_df = pd.DataFrame(summary["top_offenders"])
                            st.dataframe(
                                offender_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "total_cost": st.column_config.NumberColumn(
                                        "Total Cost", format="$%.0f"),
                                    "max_deviation_pct": st.column_config.NumberColumn(
                                        "Max Deviation %", format="%.1f%%"),
                                }
                            )

                            # Bar chart of top offenders
                            fig_offend = px.bar(
                                offender_df.head(10),
                                x="resource", y="total_cost",
                                color="avg_score",
                                color_continuous_scale="Reds",
                                labels={"total_cost": "Cost ($)", "resource": "", "avg_score": "Anomaly Score"}
                            )
                            fig_offend.update_layout(
                                height=350, margin=dict(l=20, r=20, t=30, b=20),
                                xaxis_tickangle=-45)
                            st.plotly_chart(fig_offend, use_container_width=True)

                        # Anomaly timeline
                        st.subheader("📅 Anomaly Timeline")
                        anomaly_only = df_anomalies[df_anomalies["is_anomaly"]].copy()
                        if not anomaly_only.empty:
                            fig_timeline = px.scatter(
                                anomaly_only,
                                x="usage_date", y="daily_cost",
                                color="anomaly_score",
                                size="anomaly_score",
                                hover_data=["resource_name", "deviation_pct"],
                                color_continuous_scale="Reds",
                                labels={"daily_cost": "Cost ($)", "usage_date": "Date"}
                            )
                            fig_timeline.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
                            st.plotly_chart(fig_timeline, use_container_width=True)
                        else:
                            st.success("No anomalies detected with current settings.")

                        # Store for remediation tab
                        st.session_state["df_anomalies"] = df_anomalies
                        st.session_state["anomaly_summary"] = summary

                        with st.expander("📋 Full Anomaly Data"):
                            st.dataframe(df_anomalies, use_container_width=True, hide_index=True)
                            st.download_button(
                                "📥 Export Anomalies CSV",
                                df_anomalies.to_csv(index=False),
                                "cost_anomalies.csv", "text/csv"
                            )

                except Exception as e:
                    st.error(f"Anomaly detection failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())


# ===========================================================================
# TAB 6 — AUTO-REMEDIATION DASHBOARD (NEW!)
# ===========================================================================
with tab_remediation:
    st.header("🛡️ Auto-Remediation Engine")
    st.caption("AI-powered cost control with automated remediation actions")

    if not REMEDIATION_MODULE_AVAILABLE:
        st.warning(
            "Remediation module not available. Ensure finops_remediation.py "
            "is in the same directory as app.py."
        )
    else:
        # Initialize session state for audit log
        if "remediation_audit_log" not in st.session_state:
            st.session_state["remediation_audit_log"] = []

        # ---- Policy Configuration ----
        st.subheader("⚙️ Remediation Policies")
        pol_col1, pol_col2, pol_col3, pol_col4 = st.columns(4)
        with pol_col1:
            confidence_threshold = st.slider(
                "Anomaly Confidence Threshold",
                min_value=0.5, max_value=1.0, value=0.9, step=0.05,
                help="Only take action on anomalies with score >= this threshold"
            )
        with pol_col2:
            idle_cpu_threshold = st.slider(
                "Idle Cluster CPU %",
                min_value=5, max_value=30, value=15,
                help="Clusters with avg CPU below this are candidates for termination"
            )
        with pol_col3:
            max_daily_job_cost = st.number_input(
                "Max Daily Job Cost ($)",
                min_value=0, value=500, step=50,
                help="Flag jobs exceeding this daily cost"
            )
        with pol_col4:
            dry_run_mode = st.toggle(
                "🛡️ Dry Run Mode",
                value=True,
                help="When ON, actions are simulated but not executed"
            )

        if dry_run_mode:
            st.info("🛡️ **Dry Run Mode is ON** — All actions will be simulated. No changes will be made.")
        else:
            st.warning("⚠️ **LIVE MODE** — Actions will be executed! Use with caution.")

        # Initialize RemediationEngine
        remediation_engine = RemediationEngine(conn, dry_run=dry_run_mode)

        st.markdown("---")

        # ---- Three-column scan results ----
        st.subheader("🔍 Resource Scans")
        scan_col1, scan_col2, scan_col3 = st.columns(3)

        # ---- Idle Clusters ----
        with scan_col1:
            st.markdown("##### 💤 Idle Clusters")
            if st.button("🔄 Scan Idle Clusters", key="scan_idle"):
                with st.spinner("Scanning for idle clusters..."):
                    idle_clusters = remediation_engine.scan_idle_clusters(
                        cpu_threshold=idle_cpu_threshold,
                        start_date=str(start_date),
                        end_date=str(end_date)
                    )
                    st.session_state["idle_clusters"] = idle_clusters

            if "idle_clusters" in st.session_state:
                clusters = st.session_state["idle_clusters"]
                if clusters:
                    st.metric("Found", len(clusters))
                    for i, c in enumerate(clusters[:5]):
                        with st.container():
                            st.markdown(
                                f'<div class="warning-box">'
                                f'<strong>{c["cluster_name"]}</strong><br>'
                                f'CPU: {c["cpu_avg"]}% | Workers: {c["workers"]}<br>'
                                f'Est. Waste: ${c["estimated_waste_cost"]:,.0f}<br>'
                                f'<em>{c["reason"]}</em></div>',
                                unsafe_allow_html=True)
                            if c["recommended_action"] != "monitor":
                                if st.button(
                                    f"{'[DRY] ' if dry_run_mode else ''}"
                                    f"{c['recommended_action'].replace('_', ' ').title()}",
                                    key=f"cluster_action_{i}"
                                ):
                                    result = remediation_engine.execute_action(
                                        c["recommended_action"], c["cluster_id"]
                                    )
                                    st.session_state["remediation_audit_log"].append({
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "action": c["recommended_action"],
                                        "resource": c["cluster_name"],
                                        "resource_id": c["cluster_id"],
                                        "status": result["status"],
                                        "message": result["message"],
                                        "dry_run": dry_run_mode,
                                    })
                                    st.toast(result["message"])
                else:
                    st.success("No idle clusters found.")

        # ---- Runaway Jobs ----
        with scan_col2:
            st.markdown("##### 🚀 Runaway Jobs")
            if st.button("🔄 Scan Runaway Jobs", key="scan_jobs"):
                with st.spinner("Scanning for runaway jobs..."):
                    runaway_jobs = remediation_engine.scan_runaway_jobs(
                        cost_threshold_daily=max_daily_job_cost if max_daily_job_cost > 0 else None,
                        start_date=str(start_date),
                        end_date=str(end_date)
                    )
                    st.session_state["runaway_jobs"] = runaway_jobs

            if "runaway_jobs" in st.session_state:
                jobs = st.session_state["runaway_jobs"]
                if jobs:
                    st.metric("Found", len(jobs))
                    for i, j in enumerate(jobs[:5]):
                        with st.container():
                            st.markdown(
                                f'<div class="alert-box">'
                                f'<strong>{j["job_name"]}</strong><br>'
                                f'Cost: ${j["daily_cost"]:,.0f} | Duration: {j["duration_min"]}min<br>'
                                f'State: {j["result_state"]}<br>'
                                f'<em>{j["issues"]}</em></div>',
                                unsafe_allow_html=True)
                            if j["result_state"] == "FAILED" or j["recommended_action"] == "stop_job_run":
                                if st.button(
                                    f"{'[DRY] ' if dry_run_mode else ''}"
                                    f"Stop Run {j['run_id']}",
                                    key=f"job_action_{i}"
                                ):
                                    result = remediation_engine.execute_action(
                                        "stop_job_run", j["run_id"]
                                    )
                                    st.session_state["remediation_audit_log"].append({
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "action": "stop_job_run",
                                        "resource": j["job_name"],
                                        "resource_id": j["run_id"],
                                        "status": result["status"],
                                        "message": result["message"],
                                        "dry_run": dry_run_mode,
                                    })
                                    st.toast(result["message"])
                else:
                    st.success("No runaway jobs found.")

        # ---- Oversized Warehouses ----
        with scan_col3:
            st.markdown("##### 🏭 SQL Warehouses")
            if st.button("🔄 Scan Warehouses", key="scan_wh"):
                with st.spinner("Scanning warehouses..."):
                    warehouses = remediation_engine.scan_oversized_warehouses(
                        start_date=str(start_date),
                        end_date=str(end_date)
                    )
                    st.session_state["oversized_warehouses"] = warehouses

            if "oversized_warehouses" in st.session_state:
                whs = st.session_state["oversized_warehouses"]
                if whs:
                    st.metric("Found", len(whs))
                    for i, w in enumerate(whs[:5]):
                        with st.container():
                            st.markdown(
                                f'<div class="recommend-box">'
                                f'<strong>{w["warehouse_id"]}</strong><br>'
                                f'Cost: ${w["total_cost"]:,.0f} | DBUs: {w["total_dbus"]:,.0f}<br>'
                                f'Days Active: {w["active_days"]}<br>'
                                f'<em>{w["reason"]}</em></div>',
                                unsafe_allow_html=True)
                else:
                    st.success("No warehouse issues found.")

        # ---- Anomaly-Based Remediation ----
        st.markdown("---")
        st.subheader("🎯 Anomaly-Based Remediation Plan")
        if "df_anomalies" in st.session_state and not st.session_state["df_anomalies"].empty:
            remediation_plan = remediation_engine.get_remediation_plan(
                st.session_state["df_anomalies"],
                confidence_threshold=confidence_threshold
            )
            if remediation_plan:
                st.info(f"Found {len(remediation_plan)} actionable anomalies (score >= {confidence_threshold})")
                plan_df = pd.DataFrame(remediation_plan)
                st.dataframe(
                    plan_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "daily_cost": st.column_config.NumberColumn("Daily Cost", format="$%.0f"),
                        "expected_cost": st.column_config.NumberColumn("Expected", format="$%.0f"),
                        "excess_cost": st.column_config.NumberColumn("Excess", format="$%.0f"),
                        "anomaly_score": st.column_config.NumberColumn("Score", format="%.2f"),
                    }
                )

                # AI explanation for top action
                if st.button("🧠 Get AI Explanation for Top Action", key="ai_explain"):
                    top_action = remediation_plan[0]
                    explain_query = remediation_engine.get_ai_explanation_query(top_action)
                    with st.spinner("AI generating explanation..."):
                        try:
                            explain_result = run_query_nocache(conn, explain_query)
                            st.markdown(
                                f'<div class="ai-box">🧠 <strong>AI Recommendation</strong><br><br>'
                                f'{explain_result.iloc[0]["explanation"]}</div>',
                                unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"AI explanation failed: {e}")
            else:
                st.success("No anomalies meet the confidence threshold for remediation.")
        else:
            st.info("👈 Run anomaly detection in the **Budget & Anomaly** tab first to generate a remediation plan.")

        # ---- Audit Log ----
        st.markdown("---")
        st.subheader("📝 Remediation Audit Log")
        if st.session_state["remediation_audit_log"]:
            audit_df = pd.DataFrame(st.session_state["remediation_audit_log"])
            st.dataframe(audit_df, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Export Audit Log",
                audit_df.to_csv(index=False),
                "remediation_audit_log.csv", "text/csv"
            )
            if st.button("🗑️ Clear Audit Log", key="clear_audit"):
                st.session_state["remediation_audit_log"] = []
                st.rerun()
        else:
            st.info("No remediation actions have been taken yet.")


# ===========================================================================
# TAB 7 — AI FINOPS AGENT (Conversational Chat)
# ===========================================================================
with tab_agent:
    st.header("🤖 AI FinOps Agent")
    st.caption(
        "Ask natural-language questions about your Databricks costs, jobs, and clusters. "
        "The agent uses `ai_query()` to interpret your question and generates SQL against system tables."
    )

    # System table schema context for the LLM
    SCHEMA_CONTEXT = """
Available Databricks system tables:

1. system.billing.usage — Billable usage records
   Key columns: workspace_id, sku_name, usage_date, usage_quantity (DBUs),
   billing_origin_product, usage_metadata (struct with cluster_id, job_id, job_name,
   warehouse_id, notebook_id), identity_metadata (struct with run_as, created_by, owned_by),
   product_features (struct with jobs_tier, sql_tier, is_serverless, is_photon)

2. system.billing.list_prices — SKU pricing
   Key columns: sku_name, pricing.effective_list.default (price per DBU), cloud, currency_code

3. system.compute.clusters — Cluster configurations (SCD2)
   Key columns: cluster_id, cluster_name, workspace_id, owned_by, driver_node_type,
   worker_node_type, worker_count, min_autoscale_workers, max_autoscale_workers,
   auto_termination_minutes, cluster_source, create_time, delete_time

4. system.compute.node_timeline — Node-level metrics (per minute)
   Key columns: cluster_id, instance_id, start_time, end_time, driver (boolean),
   cpu_user_percent, cpu_system_percent, cpu_wait_percent, mem_used_percent,
   network_sent_bytes, network_received_bytes, node_type

5. system.lakeflow.jobs — Job definitions (SCD2)
   Key columns: workspace_id, job_id, name, creator_id, run_as, change_time, trigger_type

6. system.lakeflow.job_run_timeline — Job run facts (time slices)
   Key columns: workspace_id, job_id, run_id, period_start_time, period_end_time,
   result_state, run_type, trigger_type, termination_code, run_duration_seconds,
   execution_duration_seconds, setup_duration_seconds, queue_duration_seconds

Cost formula: estimated_cost = usage_quantity * list_prices.pricing.effective_list.default
(JOIN billing.usage.sku_name = billing.list_prices.sku_name)
""".strip()

    # Initialize chat history
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    # Render chat history
    for msg in st.session_state.agent_messages:
        css_class = "chat-msg-user" if msg["role"] == "user" else "chat-msg-ai"
        icon = "👤" if msg["role"] == "user" else "🤖"
        st.markdown(f'<div class="{css_class}">{icon} {msg["content"]}</div>',
                    unsafe_allow_html=True)

    # Suggested questions
    if not st.session_state.agent_messages:
        st.markdown("**Try asking:**")
        suggestions = [
            "What are the top 5 most expensive jobs this month?",
            "Show me clusters with CPU usage below 20%",
            "How much did we spend on serverless compute last week?",
            "Which users are consuming the most DBUs?",
            "List all failed jobs in the last 7 days with their error codes",
            "What is the daily cost trend by product category?",
            "Find over-provisioned clusters with more than 8 workers but low CPU",
        ]
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(f"💡 {s}", key=f"suggest_{i}"):
                    st.session_state.agent_input = s
                    st.rerun()

    # Chat input
    default_input = st.session_state.pop("agent_input", "")
    user_input = st.chat_input("Ask about your Databricks costs, jobs, or clusters…")
    if default_input and not user_input:
        user_input = default_input

    if user_input:
        st.session_state.agent_messages.append({"role": "user", "content": user_input})

        # Step 1: Use ai_query to generate SQL from the question
        sql_gen_prompt = (
            f"You are a Databricks SQL expert. Given the user question, generate a single "
            f"Databricks SQL query that answers it using ONLY the system tables described below. "
            f"Return ONLY the SQL query, no explanation, no markdown formatting.\n\n"
            f"SCHEMA:\n{SCHEMA_CONTEXT}\n\n"
            f"RULES:\n"
            f"- Use date range: '{SD}' to '{ED}'\n"
            f"- For cost, JOIN usage with list_prices on sku_name\n"
            f"- For job names, JOIN job_run_timeline with jobs (latest record via ROW_NUMBER)\n"
            f"- For clusters, use latest config via ROW_NUMBER on create_time\n"
            f"- LIMIT results to 50 rows max\n"
            f"- Use CAST for decimal/numeric operations\n\n"
            f"USER QUESTION: {user_input}"
        )

        sql_gen_query = f"""
        SELECT ai_query('{LLM_ENDPOINT}',
                        '{sql_gen_prompt.replace("'", "''")}')
        AS generated_sql
        """

        with st.spinner("🤖 Agent thinking…"):
            try:
                # Generate SQL
                gen_result = run_query_nocache(conn, sql_gen_query)
                generated_sql = gen_result.iloc[0]["generated_sql"].strip()

                # Clean up: remove markdown code fences if present
                if generated_sql.startswith("```"):
                    lines = generated_sql.split("\n")
                    generated_sql = "\n".join(
                        l for l in lines if not l.strip().startswith("```")
                    ).strip()

                # Execute the generated SQL
                try:
                    df_result = run_query_nocache(conn, generated_sql)

                    # Step 2: Use ai_query to interpret the results
                    result_preview = df_result.head(20).to_string(index=False, max_colwidth=50)
                    interpret_prompt = (
                        f"You are a helpful FinOps analyst. The user asked: '{user_input}'\n\n"
                        f"Here are the SQL results:\n{result_preview}\n\n"
                        f"Provide a clear, concise summary of the findings. "
                        f"Highlight key numbers, trends, and actionable insights. "
                        f"Use bullet points where appropriate. Keep it under 200 words."
                    )
                    interpret_query = f"""
                    SELECT ai_query('{LLM_ENDPOINT}',
                                    '{interpret_prompt.replace("'", "''")}')
                    AS interpretation
                    """
                    interp_result = run_query_nocache(conn, interpret_query)
                    interpretation = interp_result.iloc[0]["interpretation"]

                    # Build response
                    response = f"{interpretation}"
                    st.session_state.agent_messages.append({"role": "assistant", "content": response})

                    # Show current response
                    st.markdown(f'<div class="chat-msg-ai">🤖 {response}</div>',
                                unsafe_allow_html=True)

                    # Show data and SQL in expanders
                    with st.expander("📊 Query Results"):
                        st.dataframe(df_result, use_container_width=True, hide_index=True)
                    with st.expander("🔍 Generated SQL"):
                        st.code(generated_sql, language="sql")

                except Exception as exec_err:
                    error_msg = (
                        f"I generated a query but it failed to execute: `{str(exec_err)[:200]}`. "
                        f"Let me show you the SQL I attempted so you can refine the question."
                    )
                    st.session_state.agent_messages.append({"role": "assistant", "content": error_msg})
                    st.markdown(f'<div class="chat-msg-ai">🤖 {error_msg}</div>',
                                unsafe_allow_html=True)
                    with st.expander("🔍 Generated SQL (failed)"):
                        st.code(generated_sql, language="sql")

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)[:300]}"
                st.session_state.agent_messages.append({"role": "assistant", "content": error_msg})
                st.markdown(f'<div class="chat-msg-ai">🤖 {error_msg}</div>',
                            unsafe_allow_html=True)

    # Clear chat button
    if st.session_state.agent_messages:
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.agent_messages = []
            st.rerun()


# ===========================================================================
# Footer
# ===========================================================================
st.markdown("---")
st.caption(
    f"Databricks FinOps Monitor — AI-Enhanced Edition v2.0 • "
    f"Powered by system tables + ai_query() + ai_forecast() • "
    f"Range: {start_date} to {end_date}"
)
