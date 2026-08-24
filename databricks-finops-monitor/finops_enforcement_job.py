# =============================================================================
# finops_enforcement_job.py — Scheduled FinOps Guardrail Enforcement
# =============================================================================
# Run as a Databricks Job task on schedule (e.g., every 4 hours).
# Performs full guardrail scan, logs results, and optionally takes action.
#
# Parameters (via dbutils.widgets):
#   dry_run       : "true" or "false" (default "true")
#   monthly_budget: budget amount (default "5000")
#   warehouse_id  : SQL Warehouse ID for queries
# =============================================================================

import os
import sys
from datetime import datetime

import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

# ---------- Widget Parameters ----------
try:
    dbutils.widgets.text("dry_run", "true", "Dry Run Mode")
    dbutils.widgets.text("monthly_budget", "5000", "Monthly Budget ($)")
    dbutils.widgets.text("warehouse_id", os.environ.get("DATABRICKS_WAREHOUSE_ID", ""),
                         "SQL Warehouse ID")
except Exception:
    pass  # Handles case where dbutils is not available

try:
    dry_run_str = dbutils.widgets.get("dry_run")
    monthly_budget_str = dbutils.widgets.get("monthly_budget")
    warehouse_id = dbutils.widgets.get("warehouse_id")
except Exception:
    dry_run_str = os.environ.get("DRY_RUN", "true")
    monthly_budget_str = os.environ.get("MONTHLY_BUDGET", "5000")
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")

dry_run = dry_run_str.lower().strip() in ("true", "1", "yes")
monthly_budget = float(monthly_budget_str)

separator = "=" * 60
mode_str = "DRY RUN" if dry_run else "LIVE ENFORCEMENT"
time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print("")
print(separator)
print("  FINOPS GUARDRAIL ENFORCEMENT JOB")
print("  Time: " + time_str)
print("  Mode: " + mode_str)
print("  Budget: ${:,.0f}".format(monthly_budget))
print(separator)
print("")

# ---------- Connect to SQL Warehouse ----------
if not warehouse_id:
    raise ValueError("warehouse_id is required. Set via widget or DATABRICKS_WAREHOUSE_ID env var.")

cfg = Config()
host = cfg.host.replace("https://", "").replace("http://", "")
conn = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/" + warehouse_id,
    credentials_provider=lambda: cfg.authenticate,
    _use_arrow_native_complex_types=False,
)
print("[OK] Connected to SQL Warehouse")

# ---------- Import and Run GuardrailEngine ----------
# Add app directory to path so we can import the guardrails module
app_dir = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor"
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from finops_guardrails import GuardrailEngine

engine = GuardrailEngine(conn, dry_run=dry_run)

# Run full scan with configuration
config = {
    "max_workers": 20,
    "required_tags": ["project", "owner", "env"],
    "budget_critical_pct": 95,
    "idle_threshold_min": 120,
    "max_job_duration_min": 360,
    "max_daily_job_cost": 100,
    "app_idle_hours": 8,
}

report = engine.run_full_scan(monthly_budget=monthly_budget, config=config)

# ---------- Print Summary Report ----------
s = report["summary"]
cluster_violations = report["cluster_violations"]
tag_violations = report["tag_violations"]
budget_status = report["budget_status"]
idle_actions = report["idle_actions"]
app_actions = report["app_actions"]
job_actions = report["job_actions"]

budget_state = "CRITICAL" if budget_status.get("threshold_exceeded") else "OK"
current_spend = budget_status.get("current_spend", 0)
util_pct = budget_status.get("utilization_pct", 0)

print("")
print(separator)
print("  GUARDRAIL SCAN RESULTS")
print(separator)
print("  Total Violations:      {}".format(s["total_violations"]))
print("  Critical Issues:       {}".format(s["critical_count"]))
print("  Est. Daily Savings:    ${:,.2f}".format(s["estimated_daily_savings"]))
print("  Compliance Score:      {}%".format(s["compliance_score"]))
print(separator)

print("")
print("  Cluster Violations:    {}".format(len(cluster_violations)))
print("  Tag Violations:        {}".format(len(tag_violations)))
print("  Budget Status:         " + budget_state)
print("    Spend: ${:,.0f} / ${:,.0f} ({}%)".format(current_spend, monthly_budget, util_pct))
print("  Idle Resource Actions: {}".format(len(idle_actions)))
print("  App Lifecycle Actions: {}".format(len(app_actions)))
print("  Job Guardrail Actions: {}".format(len(job_actions)))

# ---------- Write Audit Log to Delta Table ----------
AUDIT_TABLE = "uae_insurance.uae_silver.finops_guardrail_audit"
audit_df = engine.get_audit_log()

if not audit_df.empty:
    try:
        spark_df = spark.createDataFrame(audit_df)
        spark_df.write.mode("append").option("mergeSchema", "true").saveAsTable(AUDIT_TABLE)
        print("")
        print("[OK] Wrote {} audit records to {}".format(len(audit_df), AUDIT_TABLE))
    except Exception as e:
        print("")
        print("[WARN] Could not write audit log to Delta: {}".format(e))
        print("       Audit log available in-memory via engine.get_audit_log()")
else:
    print("")
    print("[INFO] No audit log entries to write.")

# ---------- AI Summary (optional) ----------
try:
    summary_prompt = (
        "Summarize this FinOps guardrail scan in 3-4 sentences for a Slack notification. "
        "Violations: {}, Critical: {}, "
        "Budget: ${:,.0f}/${:,.0f}, "
        "Compliance: {}%, "
        "Mode: {}. "
        "Cluster issues: {}, "
        "Tag issues: {}, "
        "Idle resources: {}, "
        "Runaway jobs: {}."
    ).format(
        s["total_violations"], s["critical_count"],
        current_spend, monthly_budget,
        s["compliance_score"],
        "Dry Run" if dry_run else "Live",
        len(cluster_violations), len(tag_violations),
        len(idle_actions), len(job_actions)
    )
    safe_prompt = summary_prompt.replace("'", "''")
    ai_sql = "SELECT ai_query('databricks-meta-llama-3-3-70b-instruct', '{}') AS summary".format(safe_prompt)
    with conn.cursor() as cur:
        cur.execute(ai_sql)
        ai_result = cur.fetchall_arrow().to_pandas()
        ai_summary = ai_result.iloc[0]["summary"]
        print("")
        print(separator)
        print("  AI SUMMARY")
        print(separator)
        print("  " + str(ai_summary))
except Exception as e:
    print("")
    print("[INFO] AI summary skipped: {}".format(e))

conn.close()
print("")
print(separator)
print("  JOB COMPLETE")
print(separator)
