
# =============================================================================
# finops_remediation.py — Auto-Remediation Engine for FinOps
# =============================================================================
# Features: Scan idle clusters, runaway jobs, oversized warehouses
#           Execute actions via Databricks SDK, audit logging, AI explanations
# =============================================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from databricks.sdk import WorkspaceClient
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"


class RemediationEngine:
    """AI-powered auto-remediation engine for Databricks cost control."""

    def __init__(self, conn, dry_run=True):
        self.conn = conn
        self.dry_run = dry_run
        self._audit_log = []
        self.w = None
        if SDK_AVAILABLE:
            try:
                self.w = WorkspaceClient()
            except Exception:
                pass

    def _run_query(self, query):
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall_arrow().to_pandas()

    # -------------------------------------------------------------------
    # Scan: Idle Clusters
    # -------------------------------------------------------------------
    def scan_idle_clusters(self, cpu_threshold=15, mem_threshold=30,
                           hours_idle=2, start_date=None, end_date=None):
        """
        Find clusters with avg CPU < threshold and avg mem < threshold.
        Returns list of dicts with cluster info and recommended actions.
        """
        sd = start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        ed = end_date or datetime.now().strftime("%Y-%m-%d")

        query = f"""
        WITH cluster_metrics AS (
            SELECT
                n.cluster_id,
                c.cluster_name,
                c.owned_by,
                c.worker_node_type,
                c.worker_count,
                c.auto_termination_minutes,
                c.cluster_source,
                AVG(n.cpu_user_percent + n.cpu_system_percent) AS avg_cpu,
                AVG(n.mem_used_percent) AS avg_mem,
                COUNT(DISTINCT DATE(n.start_time)) AS active_days,
                ROUND(TIMESTAMPDIFF(HOUR,
                    MIN(n.start_time), MAX(n.end_time)), 1) AS total_hours,
                COUNT(DISTINCT n.instance_id) AS node_count
            FROM system.compute.node_timeline n
            LEFT JOIN (
                SELECT cluster_id, cluster_name, owned_by,
                       worker_node_type, worker_count,
                       auto_termination_minutes, cluster_source,
                       ROW_NUMBER() OVER (
                           PARTITION BY cluster_id ORDER BY create_time DESC
                       ) rn
                FROM system.compute.clusters
            ) c ON n.cluster_id = c.cluster_id AND c.rn = 1
            WHERE n.start_time >= '{sd}'
              AND n.end_time <= '{ed}T23:59:59'
            GROUP BY n.cluster_id, c.cluster_name, c.owned_by,
                     c.worker_node_type, c.worker_count,
                     c.auto_termination_minutes, c.cluster_source
            HAVING AVG(n.cpu_user_percent + n.cpu_system_percent) < {cpu_threshold}
               AND AVG(n.mem_used_percent) < {mem_threshold}
        )
        SELECT * FROM cluster_metrics
        ORDER BY avg_cpu ASC
        """
        df = self._run_query(query)
        results = []
        for _, row in df.iterrows():
            cpu = float(pd.to_numeric(row.get("avg_cpu", 0), errors="coerce") or 0)
            mem = float(pd.to_numeric(row.get("avg_mem", 0), errors="coerce") or 0)
            hours = float(pd.to_numeric(row.get("total_hours", 0), errors="coerce") or 0)
            workers = int(pd.to_numeric(row.get("worker_count", 0), errors="coerce") or 0)

            # Estimate waste: hours * workers * rough cost per worker-hour
            est_waste = round(hours * max(workers, 1) * 0.50, 2)

            if cpu < 5:
                action = "terminate_cluster"
                reason = f"Nearly zero CPU ({cpu:.0f}%) — likely abandoned"
            elif cpu < cpu_threshold:
                action = "resize_cluster"
                reason = f"Low utilization (CPU: {cpu:.0f}%, Mem: {mem:.0f}%) — oversized"
            else:
                action = "monitor"
                reason = "Borderline utilization"

            results.append({
                "cluster_id": str(row.get("cluster_id", "")),
                "cluster_name": str(row.get("cluster_name", "Unknown")),
                "owned_by": str(row.get("owned_by", "")),
                "worker_type": str(row.get("worker_node_type", "")),
                "workers": workers,
                "cpu_avg": round(cpu, 1),
                "mem_avg": round(mem, 1),
                "hours_active": round(hours, 1),
                "estimated_waste_cost": est_waste,
                "recommended_action": action,
                "reason": reason,
            })
        return results

    # -------------------------------------------------------------------
    # Scan: Runaway Jobs
    # -------------------------------------------------------------------
    def scan_runaway_jobs(self, cost_threshold_daily=None,
                          duration_threshold_min=None,
                          start_date=None, end_date=None):
        """
        Find jobs with abnormally high cost or excessive duration.
        """
        sd = start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        ed = end_date or datetime.now().strftime("%Y-%m-%d")

        cost_filter = ""
        if cost_threshold_daily:
            cost_filter = f"HAVING daily_cost > {cost_threshold_daily}"

        duration_filter = ""
        if duration_threshold_min:
            duration_filter = (
                f"{' AND ' if cost_filter else ' HAVING '}"
                f"MAX(r.run_duration_seconds) / 60 > {duration_threshold_min}"
            )

        query = f"""
        WITH job_costs AS (
            SELECT
                r.job_id,
                j.name AS job_name,
                DATE(r.period_start_time) AS run_date,
                r.run_id,
                r.result_state,
                MAX(r.run_duration_seconds) AS duration_sec,
                MAX(r.execution_duration_seconds) AS exec_sec,
                COUNT(*) AS run_count
            FROM system.lakeflow.job_run_timeline r
            LEFT JOIN (
                SELECT workspace_id, job_id, name,
                       ROW_NUMBER() OVER (
                           PARTITION BY workspace_id, job_id
                           ORDER BY change_time DESC
                       ) rn
                FROM system.lakeflow.jobs
            ) j ON r.workspace_id = j.workspace_id
                AND r.job_id = j.job_id AND j.rn = 1
            WHERE r.period_start_time >= '{sd}'
              AND r.period_end_time <= '{ed}T23:59:59'
              AND r.result_state IS NOT NULL
            GROUP BY r.job_id, j.name, DATE(r.period_start_time),
                     r.run_id, r.result_state
        ),
        job_billing AS (
            SELECT
                u.usage_metadata.job_id AS job_id,
                u.usage_date,
                SUM(CAST(u.usage_quantity AS DOUBLE) *
                    COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                ) AS daily_cost
            FROM system.billing.usage u
            LEFT JOIN system.billing.list_prices p
                ON u.sku_name = p.sku_name
                AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
            WHERE u.usage_date >= '{sd}' AND u.usage_date <= '{ed}'
              AND u.usage_metadata.job_id IS NOT NULL
            GROUP BY u.usage_metadata.job_id, u.usage_date
        )
        SELECT
            jc.job_id, jc.job_name, jc.run_date,
            jc.run_id, jc.result_state,
            jc.duration_sec, jc.exec_sec, jc.run_count,
            COALESCE(jb.daily_cost, 0) AS daily_cost
        FROM job_costs jc
        LEFT JOIN job_billing jb
            ON CAST(jc.job_id AS STRING) = jb.job_id
            AND jc.run_date = jb.usage_date
        ORDER BY daily_cost DESC
        LIMIT 50
        """
        df = self._run_query(query)
        results = []
        for _, row in df.iterrows():
            cost = float(pd.to_numeric(row.get("daily_cost", 0), errors="coerce") or 0)
            dur_min = float(pd.to_numeric(row.get("duration_sec", 0), errors="coerce") or 0) / 60
            state = str(row.get("result_state", ""))

            issues = []
            if cost_threshold_daily and cost > cost_threshold_daily:
                issues.append(f"Cost ${cost:,.0f} exceeds ${cost_threshold_daily:,.0f} threshold")
            if duration_threshold_min and dur_min > duration_threshold_min:
                issues.append(f"Duration {dur_min:.0f}min exceeds {duration_threshold_min}min limit")
            if state == "FAILED":
                issues.append("Job FAILED — wasted compute")

            if not issues and cost > 0:
                issues.append(f"High daily cost: ${cost:,.0f}")

            action = "stop_job_run" if (state == "FAILED" or dur_min > 180) else "monitor"

            results.append({
                "job_id": str(row.get("job_id", "")),
                "job_name": str(row.get("job_name", "Unknown")),
                "run_id": str(row.get("run_id", "")),
                "run_date": str(row.get("run_date", "")),
                "result_state": state,
                "duration_min": round(dur_min, 1),
                "daily_cost": round(cost, 2),
                "issues": "; ".join(issues) if issues else "No issues",
                "recommended_action": action,
            })
        return results

    # -------------------------------------------------------------------
    # Scan: Oversized Warehouses
    # -------------------------------------------------------------------
    def scan_oversized_warehouses(self, start_date=None, end_date=None):
        """
        Find SQL warehouses with disproportionate cost vs query volume.
        """
        sd = start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        ed = end_date or datetime.now().strftime("%Y-%m-%d")

        query = f"""
        SELECT
            u.usage_metadata.warehouse_id AS warehouse_id,
            u.sku_name,
            SUM(CAST(u.usage_quantity AS DOUBLE)) AS total_dbus,
            SUM(CAST(u.usage_quantity AS DOUBLE) *
                COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
            ) AS total_cost,
            COUNT(DISTINCT u.usage_date) AS active_days,
            SUM(CAST(u.usage_quantity AS DOUBLE)) /
                NULLIF(COUNT(DISTINCT u.usage_date), 0) AS avg_daily_dbus
        FROM system.billing.usage u
        LEFT JOIN system.billing.list_prices p
            ON u.sku_name = p.sku_name
            AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
        WHERE u.usage_date >= '{sd}' AND u.usage_date <= '{ed}'
          AND u.usage_metadata.warehouse_id IS NOT NULL
        GROUP BY u.usage_metadata.warehouse_id, u.sku_name
        ORDER BY total_cost DESC
        """
        df = self._run_query(query)
        results = []
        for _, row in df.iterrows():
            cost = float(pd.to_numeric(row.get("total_cost", 0), errors="coerce") or 0)
            dbus = float(pd.to_numeric(row.get("total_dbus", 0), errors="coerce") or 0)
            days = int(pd.to_numeric(row.get("active_days", 0), errors="coerce") or 0)
            avg_daily = float(pd.to_numeric(row.get("avg_daily_dbus", 0), errors="coerce") or 0)

            action = "resize_warehouse" if cost > 100 else "monitor"
            reason = f"Total cost: ${cost:,.0f}, Avg daily DBUs: {avg_daily:,.0f}"

            results.append({
                "warehouse_id": str(row.get("warehouse_id", "")),
                "sku_name": str(row.get("sku_name", "")),
                "total_dbus": round(dbus, 1),
                "total_cost": round(cost, 2),
                "active_days": days,
                "avg_daily_dbus": round(avg_daily, 1),
                "recommended_action": action,
                "reason": reason,
            })
        return results

    # -------------------------------------------------------------------
    # Execute remediation action
    # -------------------------------------------------------------------
    def execute_action(self, action_type, resource_id, params=None):
        """
        Execute a remediation action via Databricks SDK.
        Respects dry_run mode. Returns result dict.
        """
        params = params or {}
        result = {
            "action": action_type,
            "resource_id": resource_id,
            "dry_run": self.dry_run,
            "status": "pending",
            "message": "",
        }

        if self.dry_run:
            result["status"] = "dry_run"
            result["message"] = (
                f"[DRY RUN] Would execute {action_type} on {resource_id}"
            )
            return result

        if not self.w:
            result["status"] = "error"
            result["message"] = "Databricks SDK not available or not authenticated"
            return result

        try:
            if action_type == "terminate_cluster":
                self.w.clusters.delete(cluster_id=resource_id)
                result["status"] = "success"
                result["message"] = f"Cluster {resource_id} terminated"

            elif action_type == "resize_cluster":
                new_workers = params.get("num_workers", 1)
                self.w.clusters.edit(
                    cluster_id=resource_id,
                    num_workers=new_workers,
                )
                result["status"] = "success"
                result["message"] = (
                    f"Cluster {resource_id} resized to {new_workers} workers"
                )

            elif action_type == "stop_job_run":
                self.w.jobs.cancel_run(run_id=int(resource_id))
                result["status"] = "success"
                result["message"] = f"Job run {resource_id} cancelled"

            elif action_type == "resize_warehouse":
                new_size = params.get("warehouse_size", "Small")
                # Warehouse edit requires getting current config first
                wh = self.w.warehouses.get(id=resource_id)
                self.w.warehouses.edit(
                    id=resource_id,
                    name=wh.name,
                    cluster_size=new_size,
                    warehouse_type=wh.warehouse_type,
                )
                result["status"] = "success"
                result["message"] = (
                    f"Warehouse {resource_id} resized to {new_size}"
                )
            else:
                result["status"] = "error"
                result["message"] = f"Unknown action type: {action_type}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Action failed: {str(e)[:200]}"

        return result

    # -------------------------------------------------------------------
    # Remediation plan from anomalies
    # -------------------------------------------------------------------
    def get_remediation_plan(self, anomaly_df, confidence_threshold=0.9):
        """
        Generate prioritized remediation actions from anomaly results.
        Returns list of action dicts sorted by priority.
        """
        if anomaly_df.empty or "anomaly_score" not in anomaly_df.columns:
            return []

        high_confidence = anomaly_df[
            anomaly_df["anomaly_score"] >= confidence_threshold
        ].copy()

        if high_confidence.empty:
            return []

        actions = []
        for _, row in high_confidence.iterrows():
            resource = str(row.get("resource_name", "Unknown"))
            score = float(row.get("anomaly_score", 0))
            cost = float(row.get("daily_cost", 0))
            expected = float(row.get("expected_value", 0))
            excess = max(cost - expected, 0)

            # Determine action based on severity
            if score >= 3.0:
                priority = "critical"
                action = "investigate_and_terminate"
            elif score >= 2.0:
                priority = "high"
                action = "investigate_and_resize"
            else:
                priority = "medium"
                action = "monitor_closely"

            actions.append({
                "resource": resource,
                "anomaly_score": round(score, 2),
                "daily_cost": round(cost, 2),
                "expected_cost": round(expected, 2),
                "excess_cost": round(excess, 2),
                "priority": priority,
                "recommended_action": action,
                "date": str(row.get("usage_date", "")),
            })

        # Sort by priority (critical > high > medium) then by excess cost
        priority_order = {"critical": 0, "high": 1, "medium": 2}
        actions.sort(key=lambda x: (priority_order.get(x["priority"], 3), -x["excess_cost"]))
        return actions

    # -------------------------------------------------------------------
    # Audit logging
    # -------------------------------------------------------------------
    def log_action(self, action_type, resource_id, resource_name,
                   reason, result, cost_impact):
        """
        Log a remediation action to the internal audit log.
        """
        self._audit_log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action_type": action_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "reason": reason,
            "result": result,
            "cost_impact": cost_impact,
            "dry_run": self.dry_run,
        })

    def get_audit_log(self):
        """Returns audit log as DataFrame."""
        if not self._audit_log:
            return pd.DataFrame(columns=[
                "timestamp", "action_type", "resource_id", "resource_name",
                "reason", "result", "cost_impact", "dry_run"
            ])
        return pd.DataFrame(self._audit_log)

    # -------------------------------------------------------------------
    # AI Explanation
    # -------------------------------------------------------------------
    def get_ai_explanation_query(self, action_dict):
        """
        Generate SQL for ai_query() to explain a remediation recommendation.
        Returns the SQL string (caller executes).
        """
        resource = action_dict.get("resource", "Unknown")
        action = action_dict.get("recommended_action", "N/A")
        score = action_dict.get("anomaly_score", 0)
        daily_cost = action_dict.get("daily_cost", 0)
        expected_cost = action_dict.get("expected_cost", 0)
        excess_cost = action_dict.get("excess_cost", 0)
        priority = action_dict.get("priority", "unknown")
        context = (
            "Resource: {}\n"
            "Action: {}\n"
            "Anomaly Score: {}\n"
            "Daily Cost: ${:,.0f}\n"
            "Expected Cost: ${:,.0f}\n"
            "Excess Cost: ${:,.0f}\n"
            "Priority: {}"
        ).format(resource, action, score, daily_cost,
                 expected_cost, excess_cost, priority)
        prompt = (
            "You are a Databricks FinOps remediation expert. Explain this "
            "recommended action in plain language. Include: why this action "
            "is recommended, expected impact, potential risks, and "
            "alternatives. Be concise (under 100 words).\n\n" + context
        )
        safe_prompt = prompt.replace("'", "''")
        return (
            "SELECT ai_query('{}', ".format(LLM_ENDPOINT)
            + "'{}') AS explanation".format(safe_prompt)
        )
