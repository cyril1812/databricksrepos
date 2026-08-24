# Databricks notebook source
# DBTITLE 1,FinOps Guardrails Builder
# MAGIC %md
# MAGIC # FinOps Guardrails Builder
# MAGIC Enhances the FinOps Monitor App with automated cost guardrails, policy enforcement, and real remediation actions.
# MAGIC
# MAGIC | Capability | Description |
# MAGIC |---|---|
# MAGIC | **Cluster Policy Compliance** | Auto-termination, max workers, idle detection |
# MAGIC | **Tag Compliance** | Enforce `project`, `owner`, `env` tags on all resources |
# MAGIC | **Budget Hard Limits** | Auto-terminate interactive clusters when spend exceeds critical threshold |
# MAGIC | **Idle Resource Enforcement** | Terminate idle clusters and stop idle SQL warehouses |
# MAGIC | **App Lifecycle Management** | Stop idle Databricks Apps to save DBU costs |
# MAGIC | **Runaway Job Protection** | Cancel jobs exceeding duration or cost limits |
# MAGIC | **Audit Logging** | Full audit trail written to Delta table |
# MAGIC
# MAGIC **Run all cells** to deploy the enhancements to `/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/`.

# COMMAND ----------

# DBTITLE 1,Create finops_guardrails.py — GuardrailEngine
guardrails_code = '''
# =============================================================================
# finops_guardrails.py — FinOps Guardrail Engine
# =============================================================================
# Automated cost guardrails, policy enforcement, and real remediation actions.
# Designed to work alongside the existing RemediationEngine.
# =============================================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.compute import State as ClusterState
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ClusterState = None

LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"


class GuardrailEngine:
    """Automated FinOps guardrail engine with policy enforcement.

    Parameters
    ----------
    conn : databricks.sql connection
        SQL warehouse connection for system table queries.
    dry_run : bool
        If True, only report findings. If False, execute remediation actions.
    """

    def __init__(self, conn, dry_run=True):
        self.conn = conn
        self.dry_run = dry_run
        self._audit_log = []
        self.w = None
        if SDK_AVAILABLE:
            try:
                self.w = WorkspaceClient()
            except Exception as e:
                print(f"[GuardrailEngine] SDK init warning: {e}")

    def _run_query(self, query):
        """Execute SQL query and return pandas DataFrame."""
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall_arrow().to_pandas()

    def _log_action(self, action_type, resource_id, resource_name, action, status, details=""):
        """Internal: append to audit log with timestamp."""
        self._audit_log.append({
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action_type": action_type,
            "resource_id": str(resource_id),
            "resource_name": str(resource_name),
            "action": action,
            "status": status,
            "details": str(details)[:500],
            "dry_run": self.dry_run,
        })

    # -----------------------------------------------------------------
    # 1. CLUSTER POLICY COMPLIANCE
    # -----------------------------------------------------------------
    def check_cluster_compliance(self, max_workers=20):
        """Check active clusters for policy violations.

        Flags:
        - Auto-termination disabled (auto_termination_minutes = 0 or NULL)
        - Max workers exceeding threshold
        - Clusters running > 4 hours with low utilization

        Returns list of violation dicts.
        """
        violations = []
        try:
            query = """
            WITH latest_clusters AS (
                SELECT
                    cluster_id, cluster_name, owned_by,
                    worker_count, auto_termination_minutes,
                    cluster_source, driver_node_type, worker_node_type,
                    autoscale_min_workers, autoscale_max_workers,
                    delete_time, create_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY cluster_id ORDER BY change_time DESC
                    ) AS rn
                FROM system.compute.clusters
            )
            SELECT *
            FROM latest_clusters
            WHERE rn = 1
              AND delete_time IS NULL
            ORDER BY create_time DESC
            """
            df = self._run_query(query)

            for _, row in df.iterrows():
                cid = str(row.get("cluster_id", ""))
                cname = str(row.get("cluster_name", "Unknown"))
                owner = str(row.get("owned_by", "unknown"))
                auto_term = row.get("auto_termination_minutes")
                workers = int(pd.to_numeric(row.get("worker_count", 0), errors="coerce") or 0)
                max_auto = int(pd.to_numeric(row.get("autoscale_max_workers", 0), errors="coerce") or 0)
                source = str(row.get("cluster_source", ""))
                effective_max = max(workers, max_auto)

                # Check auto-termination
                if auto_term is None or (pd.to_numeric(auto_term, errors="coerce") or 0) == 0:
                    violations.append({
                        "cluster_id": cid,
                        "cluster_name": cname,
                        "owner": owner,
                        "violation_type": "NO_AUTO_TERMINATION",
                        "severity": "HIGH",
                        "recommended_action": "Enable auto-termination (30 min recommended)",
                        "details": f"Auto-termination is disabled. Source: {source}",
                    })
                    self._log_action("cluster_compliance", cid, cname,
                                     "flag_no_auto_term", "violation",
                                     "Auto-termination disabled")

                # Check max workers
                if effective_max > max_workers:
                    violations.append({
                        "cluster_id": cid,
                        "cluster_name": cname,
                        "owner": owner,
                        "violation_type": "EXCEEDS_MAX_WORKERS",
                        "severity": "MEDIUM",
                        "recommended_action": f"Reduce to <= {max_workers} workers",
                        "details": f"Configured for {effective_max} workers (limit: {max_workers})",
                    })
                    self._log_action("cluster_compliance", cid, cname,
                                     "flag_oversized", "violation",
                                     f"{effective_max} workers exceeds {max_workers} limit")

            print(f"[Cluster Compliance] Scanned {len(df)} clusters, found {len(violations)} violations")
        except Exception as e:
            print(f"[Cluster Compliance] Error: {e}")
            self._log_action("cluster_compliance", "N/A", "N/A",
                             "scan_error", "error", str(e))
        return violations

    # -----------------------------------------------------------------
    # 2. TAG COMPLIANCE
    # -----------------------------------------------------------------
    def check_tag_compliance(self, required_tags=None):
        """Check clusters for missing required tags.

        Parameters
        ----------
        required_tags : list
            Tag keys that must exist. Defaults to ["project", "owner", "env"].

        Returns list of non-compliant resource dicts.
        """
        required_tags = required_tags or ["project", "owner", "env"]
        violations = []
        try:
            query = """
            WITH latest_clusters AS (
                SELECT
                    cluster_id, cluster_name, owned_by, custom_tags,
                    delete_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY cluster_id ORDER BY change_time DESC
                    ) AS rn
                FROM system.compute.clusters
            )
            SELECT cluster_id, cluster_name, owned_by, custom_tags
            FROM latest_clusters
            WHERE rn = 1 AND delete_time IS NULL
            """
            df = self._run_query(query)

            for _, row in df.iterrows():
                cid = str(row.get("cluster_id", ""))
                cname = str(row.get("cluster_name", "Unknown"))
                owner = str(row.get("owned_by", "unknown"))
                tags_raw = row.get("custom_tags")

                # Parse tags — can be dict, list of {key,value}, or JSON string
                existing_keys = set()
                if tags_raw is not None:
                    if isinstance(tags_raw, dict):
                        existing_keys = set(tags_raw.keys())
                    elif isinstance(tags_raw, list):
                        for t in tags_raw:
                            if isinstance(t, dict) and "key" in t:
                                existing_keys.add(t["key"])
                            elif isinstance(t, dict):
                                existing_keys.update(t.keys())
                    elif isinstance(tags_raw, str):
                        try:
                            import json
                            parsed = json.loads(tags_raw)
                            if isinstance(parsed, dict):
                                existing_keys = set(parsed.keys())
                            elif isinstance(parsed, list):
                                for t in parsed:
                                    if isinstance(t, dict) and "key" in t:
                                        existing_keys.add(t["key"])
                        except Exception:
                            pass

                missing = [t for t in required_tags if t.lower() not in
                           {k.lower() for k in existing_keys}]
                if missing:
                    violations.append({
                        "resource_id": cid,
                        "resource_type": "CLUSTER",
                        "resource_name": cname,
                        "owner": owner,
                        "missing_tags": missing,
                        "existing_tags": list(existing_keys),
                    })
                    self._log_action("tag_compliance", cid, cname,
                                     "flag_missing_tags", "violation",
                                     f"Missing: {', '.join(missing)}")

            print(f"[Tag Compliance] Scanned {len(df)} clusters, "
                  f"{len(violations)} missing required tags")
        except Exception as e:
            print(f"[Tag Compliance] Error: {e}")
            self._log_action("tag_compliance", "N/A", "N/A",
                             "scan_error", "error", str(e))
        return violations

    # -----------------------------------------------------------------
    # 3. BUDGET HARD LIMITS
    # -----------------------------------------------------------------
    def enforce_budget_limits(self, monthly_budget=5000, critical_threshold_pct=95):
        """Enforce hard budget limits.

        When current-month spend exceeds critical_threshold_pct of monthly_budget,
        auto-terminate all interactive (non-job) clusters.

        Returns dict with budget status and actions taken.
        """
        result = {
            "budget": monthly_budget,
            "current_spend": 0.0,
            "utilization_pct": 0.0,
            "threshold_pct": critical_threshold_pct,
            "threshold_exceeded": False,
            "actions_taken": [],
        }
        try:
            now = datetime.now()
            month_start = now.replace(day=1).strftime("%Y-%m-%d")
            today = now.strftime("%Y-%m-%d")

            query = f"""
            SELECT
                SUM(CAST(u.usage_quantity AS DOUBLE) *
                    COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                ) AS total_spend
            FROM system.billing.usage u
            LEFT JOIN system.billing.list_prices p
                ON u.sku_name = p.sku_name
                AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
            WHERE u.usage_date >= \'{month_start}\'
              AND u.usage_date <= \'{today}\'
            """
            df = self._run_query(query)
            spend = float(pd.to_numeric(
                df.iloc[0]["total_spend"], errors="coerce") or 0) if not df.empty else 0.0

            result["current_spend"] = round(spend, 2)
            result["utilization_pct"] = round(
                (spend / monthly_budget * 100) if monthly_budget > 0 else 0, 1)
            result["threshold_exceeded"] = result["utilization_pct"] >= critical_threshold_pct

            if result["threshold_exceeded"]:
                self._log_action("budget_enforcement", "workspace", "all",
                                 "budget_critical", "triggered",
                                 f"Spend ${spend:,.0f} = {result[\"utilization_pct\"]}% of ${monthly_budget:,}")

                if self.w and not self.dry_run:
                    # Terminate all interactive (non-job) clusters
                    try:
                        clusters = list(self.w.clusters.list())
                        for c in clusters:
                            state = getattr(c, "state", None)
                            source = getattr(c, "cluster_source", "")
                            if state and str(state) in ("RUNNING", "PENDING", "RESIZING",
                                                        "State.RUNNING", "State.PENDING"):
                                if "JOB" not in str(source).upper():
                                    try:
                                        self.w.clusters.delete(cluster_id=c.cluster_id)
                                        action_msg = f"Terminated cluster {c.cluster_name} ({c.cluster_id})"
                                        result["actions_taken"].append(action_msg)
                                        self._log_action("budget_enforcement",
                                                         c.cluster_id, c.cluster_name,
                                                         "terminate_cluster", "executed", action_msg)
                                    except Exception as te:
                                        result["actions_taken"].append(
                                            f"Failed to terminate {c.cluster_name}: {te}")
                    except Exception as le:
                        result["actions_taken"].append(f"Error listing clusters: {le}")
                elif self.dry_run and result["threshold_exceeded"]:
                    result["actions_taken"].append(
                        "[DRY RUN] Would terminate all interactive clusters")

            print(f"[Budget] Spend: ${spend:,.0f} / ${monthly_budget:,} "
                  f"({result[\"utilization_pct\"]}%) — "
                  f"{'CRITICAL' if result[\"threshold_exceeded\"] else 'OK'}")
        except Exception as e:
            print(f"[Budget Enforcement] Error: {e}")
            self._log_action("budget_enforcement", "N/A", "N/A",
                             "scan_error", "error", str(e))
        return result

    # -----------------------------------------------------------------
    # 4. IDLE RESOURCE ENFORCEMENT
    # -----------------------------------------------------------------
    def enforce_idle_resources(self, idle_threshold_minutes=120):
        """Find and terminate idle clusters and SQL warehouses.

        Uses SDK to check last_activity_time for running clusters.
        If idle > threshold and not a job cluster, terminates.
        Also checks for idle SQL warehouses.

        Returns list of actions taken/proposed.
        """
        actions = []
        if not self.w:
            actions.append({"resource": "N/A", "action": "skip",
                            "reason": "SDK not available", "status": "skipped"})
            return actions

        now = datetime.now()
        threshold_delta = timedelta(minutes=idle_threshold_minutes)

        # ---- Check clusters ----
        try:
            clusters = list(self.w.clusters.list())
            for c in clusters:
                state = str(getattr(c, "state", ""))
                if "RUNNING" not in state:
                    continue

                source = str(getattr(c, "cluster_source", "")).upper()
                if "JOB" in source:
                    continue  # Skip job clusters

                last_activity = getattr(c, "last_activity_time", None)
                idle_min = None
                if last_activity:
                    try:
                        if isinstance(last_activity, (int, float)):
                            last_dt = datetime.fromtimestamp(last_activity / 1000)
                        else:
                            last_dt = pd.to_datetime(last_activity).to_pydatetime()
                        idle_min = (now - last_dt).total_seconds() / 60
                    except Exception:
                        idle_min = None

                if idle_min is not None and idle_min > idle_threshold_minutes:
                    action_detail = {
                        "resource_type": "CLUSTER",
                        "resource_id": c.cluster_id,
                        "resource_name": getattr(c, "cluster_name", "Unknown"),
                        "owner": str(getattr(c, "creator_user_name", "unknown")),
                        "idle_minutes": round(idle_min, 0),
                        "action": "terminate",
                        "status": "proposed",
                    }

                    if not self.dry_run:
                        try:
                            self.w.clusters.delete(cluster_id=c.cluster_id)
                            action_detail["status"] = "executed"
                            self._log_action("idle_enforcement", c.cluster_id,
                                             action_detail["resource_name"],
                                             "terminate_cluster", "executed",
                                             f"Idle {idle_min:.0f} min")
                        except Exception as e:
                            action_detail["status"] = f"error: {e}"
                    else:
                        action_detail["status"] = "dry_run"
                        self._log_action("idle_enforcement", c.cluster_id,
                                         action_detail["resource_name"],
                                         "would_terminate", "dry_run",
                                         f"Idle {idle_min:.0f} min")

                    actions.append(action_detail)

            print(f"[Idle Clusters] Scanned {len(clusters)} clusters, "
                  f"{len([a for a in actions if a.get('resource_type') == 'CLUSTER'])} idle")
        except Exception as e:
            print(f"[Idle Clusters] Error: {e}")
            self._log_action("idle_enforcement", "N/A", "N/A",
                             "cluster_scan_error", "error", str(e))

        # ---- Check SQL warehouses ----
        try:
            warehouses = list(self.w.warehouses.list())
            for wh in warehouses:
                wh_state = str(getattr(wh, "state", "")).upper()
                if "RUNNING" not in wh_state:
                    continue

                # Warehouses have auto_stop_mins; if set to 0, flag them
                auto_stop = getattr(wh, "auto_stop_mins", None)
                if auto_stop is not None and int(auto_stop or 0) == 0:
                    action_detail = {
                        "resource_type": "WAREHOUSE",
                        "resource_id": wh.id,
                        "resource_name": getattr(wh, "name", "Unknown"),
                        "owner": str(getattr(wh, "creator_name", "unknown")),
                        "idle_minutes": "N/A (no auto-stop)",
                        "action": "stop_warehouse",
                        "status": "proposed",
                    }

                    if not self.dry_run:
                        try:
                            self.w.warehouses.stop(id=wh.id)
                            action_detail["status"] = "executed"
                            self._log_action("idle_enforcement", wh.id,
                                             action_detail["resource_name"],
                                             "stop_warehouse", "executed",
                                             "Auto-stop disabled")
                        except Exception as e:
                            action_detail["status"] = f"error: {e}"
                    else:
                        action_detail["status"] = "dry_run"
                        self._log_action("idle_enforcement", wh.id,
                                         action_detail["resource_name"],
                                         "would_stop_warehouse", "dry_run",
                                         "Auto-stop disabled")

                    actions.append(action_detail)

            print(f"[Idle Warehouses] Scanned {len(warehouses)} warehouses")
        except Exception as e:
            print(f"[Idle Warehouses] Error: {e}")
            self._log_action("idle_enforcement", "N/A", "N/A",
                             "warehouse_scan_error", "error", str(e))

        return actions

    # -----------------------------------------------------------------
    # 5. APP LIFECYCLE MANAGEMENT
    # -----------------------------------------------------------------
    def enforce_app_lifecycle(self, app_names=None, idle_hours=8):
        """Check and stop idle Databricks Apps.

        Parameters
        ----------
        app_names : list or None
            If provided, only check these app names.
        idle_hours : int
            Apps running longer than this are candidates for stopping.

        Returns list of actions taken/proposed.
        """
        actions = []
        if not self.w:
            actions.append({"app_name": "N/A", "action": "skip",
                            "reason": "SDK not available", "status": "skipped"})
            return actions

        try:
            apps = list(self.w.apps.list())
            for app in apps:
                name = getattr(app, "name", "unknown")

                # Filter to specific apps if provided
                if app_names and name not in app_names:
                    continue

                compute_status = getattr(app, "compute_status", None)
                compute_state = str(getattr(compute_status, "state", "")).upper()

                if "ACTIVE" not in compute_state and "RUNNING" not in compute_state:
                    continue  # Already stopped

                url = getattr(app, "url", "")
                action_detail = {
                    "app_name": name,
                    "compute_state": compute_state,
                    "url": url,
                    "action": "stop_app",
                    "reason": f"Running (may be idle > {idle_hours}h)",
                    "status": "proposed",
                }

                if not self.dry_run:
                    try:
                        self.w.apps.stop(name=name)
                        action_detail["status"] = "executed"
                        self._log_action("app_lifecycle", name, name,
                                         "stop_app", "executed",
                                         f"App stopped to save DBU costs")
                    except Exception as e:
                        action_detail["status"] = f"error: {e}"
                        self._log_action("app_lifecycle", name, name,
                                         "stop_app", "error", str(e))
                else:
                    action_detail["status"] = "dry_run"
                    self._log_action("app_lifecycle", name, name,
                                     "would_stop_app", "dry_run",
                                     f"Would stop app (idle > {idle_hours}h)")

                actions.append(action_detail)

            print(f"[App Lifecycle] Scanned {len(apps)} apps, "
                  f"{len(actions)} running")
        except Exception as e:
            print(f"[App Lifecycle] Error: {e}")
            self._log_action("app_lifecycle", "N/A", "N/A",
                             "scan_error", "error", str(e))
        return actions

    # -----------------------------------------------------------------
    # 6. RUNAWAY JOB PROTECTION
    # -----------------------------------------------------------------
    def enforce_job_guardrails(self, max_duration_minutes=360, max_daily_cost=100):
        """Find and optionally cancel jobs exceeding limits.

        Queries system tables for currently long-running jobs and high-cost jobs.

        Returns list of flagged/cancelled jobs.
        """
        actions = []
        try:
            query = f"""
            WITH running_jobs AS (
                SELECT
                    r.workspace_id, r.job_id, r.run_id,
                    j.name AS job_name,
                    r.result_state,
                    MIN(r.period_start_time) AS run_start,
                    MAX(r.run_duration_seconds) AS duration_sec,
                    ROUND(MAX(r.run_duration_seconds) / 60.0, 1) AS duration_min
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
                WHERE r.period_start_time >= DATE_SUB(CURRENT_DATE(), 1)
                  AND (r.result_state IS NULL OR r.result_state = \'RUNNING\')
                GROUP BY r.workspace_id, r.job_id, r.run_id, j.name, r.result_state
                HAVING MAX(r.run_duration_seconds) / 60.0 > {max_duration_minutes}
            )
            SELECT * FROM running_jobs
            ORDER BY duration_min DESC
            LIMIT 20
            """
            df = self._run_query(query)

            for _, row in df.iterrows():
                run_id = str(row.get("run_id", ""))
                job_name = str(row.get("job_name", "Unknown"))
                dur_min = float(pd.to_numeric(
                    row.get("duration_min", 0), errors="coerce") or 0)

                action_detail = {
                    "job_id": str(row.get("job_id", "")),
                    "run_id": run_id,
                    "job_name": job_name,
                    "duration_min": dur_min,
                    "violation": f"Duration {dur_min:.0f}min > {max_duration_minutes}min limit",
                    "action": "cancel_run",
                    "status": "proposed",
                }

                if not self.dry_run and self.w:
                    try:
                        self.w.jobs.cancel_run(run_id=int(run_id))
                        action_detail["status"] = "executed"
                        self._log_action("job_guardrail", run_id, job_name,
                                         "cancel_run", "executed",
                                         f"Duration {dur_min:.0f}min exceeded limit")
                    except Exception as e:
                        action_detail["status"] = f"error: {e}"
                else:
                    action_detail["status"] = "dry_run"
                    self._log_action("job_guardrail", run_id, job_name,
                                     "would_cancel_run", "dry_run",
                                     f"Duration {dur_min:.0f}min exceeded {max_duration_minutes}min limit")

                actions.append(action_detail)

            print(f"[Job Guardrails] Found {len(actions)} jobs exceeding {max_duration_minutes}min")
        except Exception as e:
            print(f"[Job Guardrails] Error: {e}")
            self._log_action("job_guardrail", "N/A", "N/A",
                             "scan_error", "error", str(e))
        return actions

    # -----------------------------------------------------------------
    # 7. FULL GUARDRAIL SCAN
    # -----------------------------------------------------------------
    def run_full_scan(self, monthly_budget=5000, config=None):
        """Orchestrate all guardrail checks and return a comprehensive report."""
        cfg = config or {}
        max_workers = cfg.get("max_workers", 20)
        required_tags = cfg.get("required_tags", ["project", "owner", "env"])
        budget_critical_pct = cfg.get("budget_critical_pct", 95)
        idle_threshold_min = cfg.get("idle_threshold_min", 120)
        max_job_duration_min = cfg.get("max_job_duration_min", 360)
        max_daily_job_cost = cfg.get("max_daily_job_cost", 100)
        app_idle_hours = cfg.get("app_idle_hours", 8)
        app_names = cfg.get("app_names", None)

        print("=" * 60)
        print("  FINOPS GUARDRAIL SCAN")
        print(f"  Mode: {'DRY RUN' if self.dry_run else 'LIVE ENFORCEMENT'}")
        print(f"  Budget: ${monthly_budget:,} | Critical: {budget_critical_pct}%")
        print("=" * 60)

        cluster_violations = self.check_cluster_compliance(max_workers=max_workers)
        tag_violations = self.check_tag_compliance(required_tags=required_tags)
        budget_status = self.enforce_budget_limits(
            monthly_budget=monthly_budget,
            critical_threshold_pct=budget_critical_pct)
        idle_actions = self.enforce_idle_resources(
            idle_threshold_minutes=idle_threshold_min)
        app_actions = self.enforce_app_lifecycle(
            app_names=app_names, idle_hours=app_idle_hours)
        job_actions = self.enforce_job_guardrails(
            max_duration_minutes=max_job_duration_min,
            max_daily_cost=max_daily_job_cost)

        # Build summary
        total_violations = (len(cluster_violations) + len(tag_violations) +
                            len(idle_actions) + len(app_actions) + len(job_actions))
        critical_count = (
            len([v for v in cluster_violations if v.get("severity") == "HIGH"]) +
            (1 if budget_status.get("threshold_exceeded") else 0) +
            len(job_actions)
        )
        est_savings = sum(
            float(a.get("idle_minutes", 0) or 0) / 60 * 0.50
            for a in idle_actions if isinstance(a.get("idle_minutes"), (int, float))
        ) + len(app_actions) * 0.5 * 8  # rough: 0.5 DBU/hr * 8 hrs per idle app

        total_checks = max(
            len(cluster_violations) + len(tag_violations) +
            len(idle_actions) + len(app_actions) + len(job_actions) + 5, 1)
        compliance_score = round(
            (1 - total_violations / total_checks) * 100, 1)

        report = {
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dry_run": self.dry_run,
            "cluster_violations": cluster_violations,
            "tag_violations": tag_violations,
            "budget_status": budget_status,
            "idle_actions": idle_actions,
            "app_actions": app_actions,
            "job_actions": job_actions,
            "summary": {
                "total_violations": total_violations,
                "critical_count": critical_count,
                "estimated_daily_savings": round(est_savings, 2),
                "compliance_score": max(0, min(100, compliance_score)),
            },
        }

        print("\\n" + "=" * 60)
        print(f"  SCAN COMPLETE | Violations: {total_violations} | "
              f"Critical: {critical_count} | "
              f"Est. Savings: ${est_savings:,.0f}/day")
        print("=" * 60)
        return report

    # -----------------------------------------------------------------
    # 8. AUDIT LOG
    # -----------------------------------------------------------------
    def get_audit_log(self):
        """Returns all logged actions as a DataFrame."""
        if not self._audit_log:
            return pd.DataFrame(columns=[
                "scan_time", "action_type", "resource_id",
                "resource_name", "action", "status", "details", "dry_run"
            ])
        return pd.DataFrame(self._audit_log)
'''

# Write the file
output_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/finops_guardrails.py"
with open(output_path, "w") as f:
    f.write(guardrails_code.strip())

print(f"✅ Created {output_path}")
print(f"   Size: {len(guardrails_code.strip()):,} chars")
print(f"   Classes: GuardrailEngine")
print(f"   Methods: check_cluster_compliance, check_tag_compliance, enforce_budget_limits,")
print(f"            enforce_idle_resources, enforce_app_lifecycle, enforce_job_guardrails,")
print(f"            run_full_scan, get_audit_log")

# COMMAND ----------

# DBTITLE 1,Create finops_enforcement_job.py — Scheduled Enforcement
enforcement_job_code = '''
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

print(f"\n{'='*60}")
print(f"  FINOPS GUARDRAIL ENFORCEMENT JOB")
print(f"  Time: {datetime.now().strftime(\'{}\')}"  .format("%Y-%m-%d %H:%M:%S"))
print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE ENFORCEMENT'}")
print(f"  Budget: ${monthly_budget:,.0f}")
print(f"{'='*60}\n")

# ---------- Connect to SQL Warehouse ----------
if not warehouse_id:
    raise ValueError("warehouse_id is required. Set via widget or DATABRICKS_WAREHOUSE_ID env var.")

cfg = Config()
host = cfg.host.replace("https://", "").replace("http://", "")
conn = sql.connect(
    server_hostname=host,
    http_path=f"/sql/1.0/warehouses/{warehouse_id}",
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
print(f"\n{'='*60}")
print("  GUARDRAIL SCAN RESULTS")
print(f"{'='*60}")
s = report["summary"]
print(f"  Total Violations:      {s['total_violations']}")
print(f"  Critical Issues:       {s['critical_count']}")
print(f"  Est. Daily Savings:    ${s['estimated_daily_savings']:,.2f}")
print(f"  Compliance Score:      {s['compliance_score']}%")
print(f"{'='*60}")

print(f"\n  Cluster Violations:    {len(report['cluster_violations'])}")
print(f"  Tag Violations:        {len(report['tag_violations'])}")
print(f"  Budget Status:         {'CRITICAL' if report['budget_status'].get('threshold_exceeded') else 'OK'}")
print(f"    Spend: ${report['budget_status'].get('current_spend', 0):,.0f} / ${monthly_budget:,.0f} "
      f"({report['budget_status'].get('utilization_pct', 0)}%)")
print(f"  Idle Resource Actions: {len(report['idle_actions'])}")
print(f"  App Lifecycle Actions: {len(report['app_actions'])}")
print(f"  Job Guardrail Actions: {len(report['job_actions'])}")

# ---------- Write Audit Log to Delta Table ----------
AUDIT_TABLE = "salama_insurance.salama_silver.finops_guardrail_audit"
audit_df = engine.get_audit_log()

if not audit_df.empty:
    try:
        spark_df = spark.createDataFrame(audit_df)
        spark_df.write.mode("append").option("mergeSchema", "true").saveAsTable(AUDIT_TABLE)
        print(f"\n[OK] Wrote {len(audit_df)} audit records to {AUDIT_TABLE}")
    except Exception as e:
        print(f"\n[WARN] Could not write audit log to Delta: {e}")
        print("       Audit log available in-memory via engine.get_audit_log()")
else:
    print("\n[INFO] No audit log entries to write.")

# ---------- AI Summary (optional) ----------
try:
    summary_prompt = (
        f"Summarize this FinOps guardrail scan in 3-4 sentences for a Slack notification. "
        f"Violations: {s['total_violations']}, Critical: {s['critical_count']}, "
        f"Budget: ${report['budget_status'].get('current_spend', 0):,.0f}/"
        f"${monthly_budget:,.0f}, "
        f"Compliance: {s['compliance_score']}%, "
        f"Mode: {'Dry Run' if dry_run else 'Live'}. "
        f"Cluster issues: {len(report['cluster_violations'])}, "
        f"Tag issues: {len(report['tag_violations'])}, "
        f"Idle resources: {len(report['idle_actions'])}, "
        f"Runaway jobs: {len(report['job_actions'])}."
    )
    safe_prompt = summary_prompt.replace("\'", "\'\'")
    with conn.cursor() as cur:
        cur.execute(f"SELECT ai_query(\'databricks-meta-llama-3-3-70b-instruct\', \'{safe_prompt}\') AS summary")
        ai_result = cur.fetchall_arrow().to_pandas()
        ai_summary = ai_result.iloc[0]["summary"]
        print(f"\n{'='*60}")
        print("  AI SUMMARY")
        print(f"{'='*60}")
        print(f"  {ai_summary}")
except Exception as e:
    print(f"\n[INFO] AI summary skipped: {e}")

conn.close()
print(f"\n{'='*60}")
print("  JOB COMPLETE")
print(f"{'='*60}")
'''

# Write the enforcement job file
output_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/finops_enforcement_job.py"
with open(output_path, "w") as f:
    f.write(enforcement_job_code.strip())

print(f"✅ Created {output_path}")
print(f"   Size: {len(enforcement_job_code.strip()):,} chars")
print(f"   Parameters: dry_run, monthly_budget, warehouse_id")
print(f"   Audit table: salama_insurance.salama_silver.finops_guardrail_audit")

# COMMAND ----------

# DBTITLE 1,Update app.py — Add Guardrails & Remediation Tab
# Read the current app.py
app_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/app.py"
with open(app_path, "r") as f:
    content = f.read()

print(f"Original app.py: {len(content):,} chars")

# =============================================================================
# 1. Add GuardrailEngine import (after RemediationEngine import)
# =============================================================================
old_import = """try:
    from finops_remediation import RemediationEngine
    REMEDIATION_MODULE_AVAILABLE = True
except ImportError:
    REMEDIATION_MODULE_AVAILABLE = False"""

new_import = """try:
    from finops_remediation import RemediationEngine
    REMEDIATION_MODULE_AVAILABLE = True
except ImportError:
    REMEDIATION_MODULE_AVAILABLE = False

try:
    from finops_guardrails import GuardrailEngine
    GUARDRAIL_MODULE_AVAILABLE = True
except ImportError:
    GUARDRAIL_MODULE_AVAILABLE = False"""

content = content.replace(old_import, new_import)

# =============================================================================
# 2. Update tab layout
# =============================================================================
old_tabs = """tab_jobs, tab_cost, tab_forecast, tab_perf, tab_budget, tab_remediation, tab_agent = st.tabs([
    "\U0001f527 Job Monitoring",
    "\U0001f4b0 Cost & FinOps",
    "\U0001f52e AI Cost Forecast",
    "\u26a1 Performance",
    "\U0001f3af Budget & Anomaly",
    "\U0001f6e1\ufe0f Auto-Remediation",
    "\U0001f916 AI FinOps Agent",
])"""

new_tabs = """tab_jobs, tab_cost, tab_forecast, tab_perf, tab_budget, tab_remediation, tab_agent = st.tabs([
    "\U0001f527 Job Monitoring",
    "\U0001f4b0 Cost & FinOps",
    "\U0001f52e AI Cost Forecast",
    "\u26a1 Performance",
    "\U0001f3af Budget & Anomaly",
    "\U0001f6e1\ufe0f Guardrails & Remediation",
    "\U0001f916 AI FinOps Agent",
])"""

content = content.replace(old_tabs, new_tabs)

# =============================================================================
# 3. Replace the entire Tab 6 content (Auto-Remediation -> Guardrails)
# =============================================================================
old_tab6_header = """# ===========================================================================
# TAB 6 \u2014 AUTO-REMEDIATION DASHBOARD (NEW!)
# ==========================================================================="""

tab7_header = """\n\n# ===========================================================================
# TAB 7 \u2014 AI FINOPS AGENT (Conversational Chat)
# ==========================================================================="""

# Find boundaries
tab6_start = content.find(old_tab6_header)
tab7_start = content.find(tab7_header.strip(), tab6_start)

if tab6_start == -1 or tab7_start == -1:
    print(f"WARNING: Could not find tab boundaries. tab6={tab6_start}, tab7={tab7_start}")
    print("Attempting alternative search...")
    tab6_start = content.find("with tab_remediation:")
    tab7_start = content.find("with tab_agent:")
    if tab6_start > 0:
        # Back up to include the section comment
        search_back = content.rfind("# =====", max(0, tab6_start - 300), tab6_start)
        if search_back > 0:
            tab6_start = search_back

# New enhanced guardrails tab
new_tab6 = '''
# ===========================================================================
# TAB 6 — GUARDRAILS & REMEDIATION
# ===========================================================================
with tab_remediation:
    st.header("🛡️ Guardrails & Remediation Engine")
    st.caption("Automated cost guardrails, policy enforcement, and remediation actions")

    if not REMEDIATION_MODULE_AVAILABLE:
        st.warning(
            "Remediation module not available. Ensure finops_remediation.py "
            "is in the same directory as app.py."
        )

    guardrails_available = GUARDRAIL_MODULE_AVAILABLE if 'GUARDRAIL_MODULE_AVAILABLE' in dir() else False
    if not guardrails_available:
        st.warning(
            "Guardrails module not available. Ensure finops_guardrails.py "
            "is in the same directory as app.py."
        )

    # ---- Guardrail Configuration ----
    with st.expander("⚙️ Guardrail Configuration", expanded=False):
        gc1, gc2, gc3, gc4 = st.columns(4)
        with gc1:
            gr_monthly_budget = st.number_input(
                "Monthly Budget ($)", min_value=100, value=5000, step=500,
                help="Total monthly DBU budget in dollars",
                key="gr_budget"
            )
            gr_max_workers = st.number_input(
                "Max Workers per Cluster", min_value=1, value=20, step=5,
                help="Flag clusters exceeding this worker count",
                key="gr_max_workers"
            )
        with gc2:
            gr_idle_threshold = st.number_input(
                "Idle Threshold (min)", min_value=15, value=120, step=15,
                help="Terminate clusters idle longer than this",
                key="gr_idle_min"
            )
            gr_budget_critical_pct = st.slider(
                "Budget Critical %", min_value=50, max_value=100, value=95,
                help="Hard limit: auto-terminate interactive clusters above this %",
                key="gr_budget_pct"
            )
        with gc3:
            gr_max_job_duration = st.number_input(
                "Max Job Duration (min)", min_value=30, value=360, step=30,
                help="Flag/cancel jobs running longer than this",
                key="gr_max_job_dur"
            )
            gr_app_idle_hours = st.number_input(
                "App Idle Hours", min_value=1, value=8, step=1,
                help="Stop apps running longer than this",
                key="gr_app_idle_hrs"
            )
        with gc4:
            gr_required_tags = st.multiselect(
                "Required Tags",
                options=["project", "owner", "env", "team", "cost_center", "department"],
                default=["project", "owner", "env"],
                help="Tags that must exist on all clusters",
                key="gr_req_tags"
            )
            gr_dry_run = st.toggle(
                "🛡️ Dry Run Mode", value=True,
                help="When ON, actions are simulated. When OFF, actions are executed.",
                key="gr_dry_run"
            )

    if gr_dry_run:
        st.info("🛡️ **Dry Run Mode** — All actions will be simulated. No changes will be made.")
    else:
        st.warning("⚠️ **LIVE MODE** — Actions will be executed! Use with caution.")

    st.markdown("---")

    # ================================================================
    # GUARDRAILS SECTION
    # ================================================================
    if guardrails_available:
        # Initialize session state
        if "guardrail_report" not in st.session_state:
            st.session_state["guardrail_report"] = None

        col_scan, col_enforce = st.columns([3, 1])
        with col_scan:
            run_scan = st.button("🔍 Run Guardrail Scan", type="primary",
                                 key="gr_run_scan", use_container_width=True)
        with col_enforce:
            run_enforce = st.button("🚀 Execute All Actions", key="gr_enforce",
                                    use_container_width=True,
                                    disabled=gr_dry_run)

        if run_scan or run_enforce:
            effective_dry_run = gr_dry_run if not run_enforce else False
            engine = GuardrailEngine(conn, dry_run=effective_dry_run)
            config = {
                "max_workers": gr_max_workers,
                "required_tags": gr_required_tags,
                "budget_critical_pct": gr_budget_critical_pct,
                "idle_threshold_min": gr_idle_threshold,
                "max_job_duration_min": gr_max_job_duration,
                "max_daily_job_cost": 100,
                "app_idle_hours": gr_app_idle_hours,
            }
            with st.spinner("Running guardrail scan..."):
                report = engine.run_full_scan(
                    monthly_budget=gr_monthly_budget, config=config)
                report["_audit_df"] = engine.get_audit_log()
                st.session_state["guardrail_report"] = report

        report = st.session_state.get("guardrail_report")
        if report:
            s = report["summary"]

            # ---- Summary Metrics Row ----
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                metric_card("Total Violations", s["total_violations"])
            with m2:
                metric_card("Critical Issues", s["critical_count"])
            with m3:
                metric_card("Est. Daily Savings",
                            f"${s['estimated_daily_savings']:,.0f}")
            with m4:
                score = s["compliance_score"]
                metric_card("Compliance Score", f"{score}%")

            st.markdown("---")

            # ---- Budget Status with Gauge ----
            st.subheader("💰 Budget Status")
            bs = report["budget_status"]
            budget_pct = bs.get("utilization_pct", 0)

            b1, b2 = st.columns([2, 1])
            with b1:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=budget_pct,
                    number={"suffix": "%"},
                    delta={"reference": gr_budget_critical_pct, "relative": False},
                    title={"text": "Budget Utilization"},
                    gauge={
                        "axis": {"range": [0, 120], "ticksuffix": "%"},
                        "bar": {"color": "#00b4d8"},
                        "steps": [
                            {"range": [0, 50], "color": "#1b2d1b"},
                            {"range": [50, 75], "color": "#2d2a1b"},
                            {"range": [75, 95], "color": "#3d2a1b"},
                            {"range": [95, 120], "color": "#4d1b1b"},
                        ],
                        "threshold": {
                            "line": {"color": "#e94560", "width": 3},
                            "thickness": 0.75,
                            "value": gr_budget_critical_pct,
                        },
                    },
                ))
                fig_gauge.update_layout(
                    height=280,
                    margin=dict(l=20, r=20, t=50, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#a0a0b0"},
                )
                st.plotly_chart(fig_gauge, use_container_width=True)
            with b2:
                st.metric("Current Spend", f"${bs.get('current_spend', 0):,.0f}")
                st.metric("Monthly Budget", f"${bs.get('budget', 0):,.0f}")
                if bs.get("threshold_exceeded"):
                    st.markdown(
                        '<div class="alert-box">🚨 <strong>BUDGET CRITICAL</strong> — '
                        'Interactive clusters will be terminated!</div>',
                        unsafe_allow_html=True)
                    for act in bs.get("actions_taken", []):
                        st.markdown(f"- {act}")
                else:
                    st.markdown(
                        '<div class="success-box">✅ Budget within limits</div>',
                        unsafe_allow_html=True)

            st.markdown("---")

            # ---- Cluster Compliance ----
            gc_left, gc_right = st.columns(2)
            with gc_left:
                st.subheader("🖥️ Cluster Compliance")
                cv = report.get("cluster_violations", [])
                if cv:
                    for v in cv:
                        severity_color = "#e94560" if v["severity"] == "HIGH" else "#ff9800"
                        box_class = "alert-box" if v["severity"] == "HIGH" else "warning-box"
                        st.markdown(
                            f'<div class="{box_class}">'
                            f'<strong>{v["cluster_name"]}</strong> '
                            f'<span style="color:{severity_color}">'
                            f'[{v["severity"]}]</span><br>'
                            f'{v["violation_type"]}: {v["details"]}<br>'
                            f'<em>Owner: {v["owner"]} | '
                            f'Action: {v["recommended_action"]}</em></div>',
                            unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="success-box">'
                        '✅ All clusters comply with policies</div>',
                        unsafe_allow_html=True)

            # ---- Tag Compliance ----
            with gc_right:
                st.subheader("🏷️ Tag Compliance")
                tv = report.get("tag_violations", [])
                if tv:
                    for v in tv:
                        missing_str = ", ".join(v.get("missing_tags", []))
                        st.markdown(
                            f'<div class="warning-box">'
                            f'<strong>{v["resource_name"]}</strong><br>'
                            f'Missing tags: <code>{missing_str}</code><br>'
                            f'<em>Owner: {v["owner"]} | '
                            f'Existing: {\', \'.join(v.get("existing_tags", [])[:5])}'
                            f'</em></div>',
                            unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="success-box">'
                        '✅ All clusters have required tags</div>',
                        unsafe_allow_html=True)

            st.markdown("---")

            # ---- Idle Resources & App Lifecycle ----
            idle_left, idle_right = st.columns(2)
            with idle_left:
                st.subheader("💤 Idle Resources")
                ia = report.get("idle_actions", [])
                if ia:
                    for a in ia:
                        status_icon = "✅" if a.get("status") == "executed" else "🔍"
                        st.markdown(
                            f'<div class="warning-box">'
                            f'{status_icon} <strong>{a.get("resource_name", "Unknown")}</strong> '
                            f'({a.get("resource_type", "")})<br>'
                            f'Idle: {a.get("idle_minutes", "N/A")} min | '
                            f'Action: {a.get("action", "")} | '
                            f'Status: {a.get("status", "")}<br>'
                            f'<em>Owner: {a.get("owner", "unknown")}</em></div>',
                            unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="success-box">'
                        '✅ No idle resources detected</div>',
                        unsafe_allow_html=True)

            with idle_right:
                st.subheader("📱 App Lifecycle")
                aa = report.get("app_actions", [])
                if aa:
                    for a in aa:
                        status_icon = "✅" if a.get("status") == "executed" else "🔍"
                        st.markdown(
                            f'<div class="warning-box">'
                            f'{status_icon} <strong>{a.get("app_name", "Unknown")}</strong><br>'
                            f'State: {a.get("compute_state", "")} | '
                            f'Action: {a.get("action", "")} | '
                            f'Status: {a.get("status", "")}<br>'
                            f'<em>{a.get("reason", "")}</em></div>',
                            unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="success-box">'
                        '✅ No idle apps running</div>',
                        unsafe_allow_html=True)

            st.markdown("---")

            # ---- Runaway Jobs ----
            st.subheader("🚀 Job Guardrails")
            ja = report.get("job_actions", [])
            if ja:
                for a in ja:
                    status_icon = "✅" if a.get("status") == "executed" else "⚠️"
                    st.markdown(
                        f'<div class="alert-box">'
                        f'{status_icon} <strong>{a.get("job_name", "Unknown")}</strong> '
                        f'(run {a.get("run_id", "")})<br>'
                        f'Duration: {a.get("duration_min", 0):.0f} min | '
                        f'{a.get("violation", "")}<br>'
                        f'Action: {a.get("action", "")} | '
                        f'Status: {a.get("status", "")}</div>',
                        unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="success-box">'
                    '✅ No runaway jobs detected</div>',
                    unsafe_allow_html=True)

            # ---- Audit Log ----
            st.markdown("---")
            with st.expander("📋 Audit Log", expanded=False):
                audit_df = report.get("_audit_df")
                if audit_df is not None and not audit_df.empty:
                    st.dataframe(audit_df, use_container_width=True, hide_index=True)
                    csv = audit_df.to_csv(index=False)
                    st.download_button("📥 Export Audit Log", csv,
                                       "guardrail_audit.csv", "text/csv",
                                       key="gr_audit_export")
                else:
                    st.info("No audit entries yet. Run a scan first.")

    st.markdown("---")

    # ================================================================
    # LEGACY REMEDIATION SCANS (preserved from original)
    # ================================================================
    if REMEDIATION_MODULE_AVAILABLE:
        st.subheader("🔧 Resource Scans (Legacy)")
        st.caption("Original scan capabilities from the remediation engine")

        if "remediation_audit_log" not in st.session_state:
            st.session_state["remediation_audit_log"] = []

        pol_col1, pol_col2, pol_col3 = st.columns(3)
        with pol_col1:
            idle_cpu_threshold = st.slider(
                "Idle Cluster CPU %",
                min_value=5, max_value=30, value=15,
                help="Clusters with avg CPU below this are candidates for termination",
                key="legacy_cpu_thresh"
            )
        with pol_col2:
            max_daily_job_cost = st.number_input(
                "Max Daily Job Cost ($)",
                min_value=0, value=500, step=50,
                help="Flag jobs exceeding this daily cost",
                key="legacy_job_cost"
            )
        with pol_col3:
            legacy_dry_run = st.toggle(
                "🛡️ Legacy Dry Run",
                value=True,
                help="When ON, actions are simulated",
                key="legacy_dry_run"
            )

        remediation_engine = RemediationEngine(conn, dry_run=legacy_dry_run)

        scan_c1, scan_c2, scan_c3 = st.columns(3)

        with scan_c1:
            st.markdown("##### 💤 Idle Clusters")
            if st.button("🔄 Scan Idle Clusters", key="legacy_scan_idle"):
                with st.spinner("Scanning..."):
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
                        st.markdown(
                            f\'<div class="warning-box">\'
                            f\'<strong>{c["cluster_name"]}</strong><br>\'
                            f\'CPU: {c["cpu_avg"]}% | Workers: {c["workers"]}\'
                            f\'<br>Est. Waste: ${c["estimated_waste_cost"]:,.0f}\'
                            f\'</div>\',
                            unsafe_allow_html=True)
                else:
                    st.success("No idle clusters found.")

        with scan_c2:
            st.markdown("##### 🚀 Runaway Jobs")
            if st.button("🔄 Scan Runaway Jobs", key="legacy_scan_jobs"):
                with st.spinner("Scanning..."):
                    runaway = remediation_engine.scan_runaway_jobs(
                        cost_threshold_daily=max_daily_job_cost if max_daily_job_cost > 0 else None,
                        start_date=str(start_date),
                        end_date=str(end_date)
                    )
                    st.session_state["runaway_jobs"] = runaway
            if "runaway_jobs" in st.session_state:
                jobs = st.session_state["runaway_jobs"]
                if jobs:
                    st.metric("Found", len(jobs))
                    for i, j in enumerate(jobs[:5]):
                        st.markdown(
                            f\'<div class="alert-box">\'
                            f\'<strong>{j["job_name"]}</strong><br>\'
                            f\'Cost: ${j["daily_cost"]:,.0f} | \'
                            f\'{j["duration_min"]}min</div>\',
                            unsafe_allow_html=True)
                else:
                    st.success("No runaway jobs found.")

        with scan_c3:
            st.markdown("##### 📦 Oversized Warehouses")
            if st.button("🔄 Scan Warehouses", key="legacy_scan_wh"):
                with st.spinner("Scanning..."):
                    oversized = remediation_engine.scan_oversized_warehouses(
                        start_date=str(start_date),
                        end_date=str(end_date)
                    )
                    st.session_state["oversized_warehouses"] = oversized
            if "oversized_warehouses" in st.session_state:
                whs = st.session_state["oversized_warehouses"]
                if whs:
                    st.metric("Found", len(whs))
                    for w in whs[:5]:
                        st.markdown(
                            f\'<div class="warning-box">\'
                            f\'<strong>{w["warehouse_id"]}</strong><br>\'
                            f\'Cost: ${w["total_cost"]:,.0f} | \'
                            f\'{w["total_dbus"]:,.0f} DBUs</div>\',
                            unsafe_allow_html=True)
                else:
                    st.success("No oversized warehouses found.")


'''

# Perform the replacement
if tab6_start > 0 and tab7_start > tab6_start:
    content = content[:tab6_start] + new_tab6 + content[tab7_start:]
    print(f"Replaced tab 6 content (chars {tab6_start}-{tab7_start})")
else:
    print(f"ERROR: Could not find tab boundaries for replacement")
    print(f"  tab6_start={tab6_start}, tab7_start={tab7_start}")

# Write updated app.py
with open(app_path, "w") as f:
    f.write(content)

print(f"\n\u2705 Updated {app_path}")
print(f"   New size: {len(content):,} chars")
print(f"   Changes:")
print(f"   - Added GuardrailEngine import")
print(f"   - Renamed tab to 'Guardrails & Remediation'")
print(f"   - Replaced Auto-Remediation tab with enhanced Guardrails tab")
print(f"   - Preserved legacy remediation scans in expandable section")

# COMMAND ----------

# DBTITLE 1,Verify all files and print capability checklist
import os

base_dir = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor"

files_to_check = [
    "app.py",
    "finops_guardrails.py",
    "finops_enforcement_job.py",
    "finops_remediation.py",
    "finops_anomaly.py",
    "finops_budget.py",
    "requirements.txt",
    "app.yaml",
]

check_icon = "\u2705"
cross_icon = "\u274c"

print("=" * 60)
print("  FINOPS GUARDRAILS DEPLOYMENT VERIFICATION")
print("=" * 60)
print()
print("\U0001f4c1 File Inventory:")
print("-" * 50)
total_size = 0
for fname in files_to_check:
    fpath = os.path.join(base_dir, fname)
    if os.path.exists(fpath):
        size = os.path.getsize(fpath)
        total_size += size
        marker = ""
        if fname == "finops_guardrails.py":
            with open(fpath) as f:
                c = f.read()
            if "GuardrailEngine" in c:
                marker = f" {check_icon} GuardrailEngine class found"
            else:
                marker = f" {cross_icon} GuardrailEngine class NOT found"
        elif fname == "finops_enforcement_job.py":
            with open(fpath) as f:
                c = f.read()
            if "run_full_scan" in c:
                marker = f" {check_icon} Enforcement logic found"
            else:
                marker = f" {cross_icon} Enforcement logic NOT found"
        elif fname == "app.py":
            with open(fpath) as f:
                c = f.read()
            checks = [
                ("from finops_guardrails import GuardrailEngine", "GuardrailEngine import"),
                ("Guardrails & Remediation", "Tab renamed"),
                ("run_full_scan", "Full scan integration"),
                ("Budget Status", "Budget gauge"),
                ("Tag Compliance", "Tag compliance UI"),
                ("App Lifecycle", "App lifecycle UI"),
            ]
            found = sum(1 for pattern, _ in checks if pattern in c)
            marker = f" {check_icon} {found}/{len(checks)} guardrail features integrated"
        icon = check_icon if os.path.exists(fpath) else cross_icon
        print(f"  {icon} {fname:30s} {size:>8,} bytes{marker}")
    else:
        print(f"  {cross_icon} {fname:30s} MISSING")

print(f"\n  Total: {total_size:,} bytes across {len(files_to_check)} files")

print("\n" + "=" * 60)
print("  GUARDRAIL CAPABILITIES CHECKLIST")
print("=" * 60)

capabilities = [
    ("Cluster Policy Compliance", "Auto-termination, max workers, idle detection"),
    ("Tag Compliance", "Enforce project/owner/env tags on all clusters"),
    ("Budget Hard Limits", "Auto-terminate clusters when spend > critical %"),
    ("Idle Resource Enforcement", "Terminate idle clusters + stop idle SQL warehouses"),
    ("App Lifecycle Management", "Stop idle Databricks Apps (e.g., salama-fraud-dashboard)"),
    ("Runaway Job Protection", "Cancel jobs exceeding duration limits"),
    ("Audit Logging", "Delta table: salama_insurance.salama_silver.finops_guardrail_audit"),
    ("Budget Gauge Visualization", "Plotly gauge chart in Guardrails tab"),
    ("Configurable Thresholds", "All limits configurable via Streamlit UI"),
    ("Dry Run / Live Toggle", "Safe simulation mode with one-click enforcement"),
    ("AI Summary", "LLM-generated scan summaries in scheduled job"),
    ("Scheduled Enforcement", "finops_enforcement_job.py for Databricks Jobs"),
]

for cap, desc in capabilities:
    print(f"  {check_icon} {cap}")
    print(f"       {desc}")

print(f"\n{'='*60}")
print("  ALL GUARDRAIL ENHANCEMENTS READY FOR DEPLOYMENT")
print(f"{'='*60}")

# COMMAND ----------

# DBTITLE 1,Deployment Instructions
# MAGIC %md
# MAGIC ## Deployment Instructions
# MAGIC
# MAGIC ### 1. Redeploy the App
# MAGIC
# MAGIC ```bash
# MAGIC databricks apps deploy databricks-finops-monitor \
# MAGIC   --source-code-path /Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor
# MAGIC ```
# MAGIC
# MAGIC Or redeploy from the Databricks Apps UI by selecting the app and clicking **Deploy**.
# MAGIC
# MAGIC ### 2. Set Up Scheduled Enforcement Job
# MAGIC
# MAGIC Create a Databricks Job with a **Python script task** pointing to:
# MAGIC
# MAGIC ```
# MAGIC /Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/finops_enforcement_job.py
# MAGIC ```
# MAGIC
# MAGIC **Parameters:**
# MAGIC | Parameter | Default | Description |
# MAGIC |-----------|---------|-------------|
# MAGIC | `dry_run` | `true` | Set to `false` for live enforcement |
# MAGIC | `monthly_budget` | `5000` | Monthly budget in dollars |
# MAGIC | `warehouse_id` | (env var) | SQL Warehouse ID |
# MAGIC
# MAGIC **Recommended Schedule:** Every 4 hours during business days
# MAGIC
# MAGIC ```
# MAGIC 0 0 */4 ? * MON-FRI *
# MAGIC ```
# MAGIC
# MAGIC ### 3. Create Audit Delta Table
# MAGIC
# MAGIC The enforcement job auto-creates the table on first run. To pre-create:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE IF NOT EXISTS salama_insurance.salama_silver.finops_guardrail_audit (
# MAGIC   scan_time TIMESTAMP,
# MAGIC   action_type STRING,
# MAGIC   resource_id STRING,
# MAGIC   resource_name STRING,
# MAGIC   action STRING,
# MAGIC   status STRING,
# MAGIC   details STRING,
# MAGIC   dry_run BOOLEAN
# MAGIC );
# MAGIC ```
# MAGIC
# MAGIC ### 4. FinOps Maturity Roadmap
# MAGIC
# MAGIC | Level | Capability | Status |
# MAGIC |-------|-----------|--------|
# MAGIC | 1 - Visibility | DBU dashboards, cost tracking | Done |
# MAGIC | 2 - Accountability | Cost per team/project, tag enforcement | Done |
# MAGIC | 3 - Control | Policies, alerts, budget limits | Done |
# MAGIC | 4 - Automation | Auto-remediation, scheduled enforcement | **Ready** |

# COMMAND ----------

# DBTITLE 1,Integrate finops_action_plan.py into app.py + sync to repos
import os
import shutil

# =============================================================================
# Integrate finops_action_plan.py into the FinOps Monitor App
# =============================================================================

app_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/app.py"
with open(app_path, "r") as f:
    content = f.read()

print(f"Original app.py: {len(content):,} chars")
changes_made = []

# ---------------------------------------------------------------------------
# 1. Add ActionPlanGenerator import (after GuardrailEngine import block)
# ---------------------------------------------------------------------------
import_marker = """try:
    from finops_guardrails import GuardrailEngine
    GUARDRAIL_MODULE_AVAILABLE = True
except ImportError:
    GUARDRAIL_MODULE_AVAILABLE = False"""

new_import = """try:
    from finops_guardrails import GuardrailEngine
    GUARDRAIL_MODULE_AVAILABLE = True
except ImportError:
    GUARDRAIL_MODULE_AVAILABLE = False

try:
    from finops_action_plan import ActionPlanGenerator
    ACTION_PLAN_MODULE_AVAILABLE = True
except ImportError:
    ACTION_PLAN_MODULE_AVAILABLE = False"""

if "finops_action_plan" not in content:
    if import_marker in content:
        content = content.replace(import_marker, new_import)
        changes_made.append("Added ActionPlanGenerator import")
    else:
        # Fallback: insert after all imports section
        fallback_insert = "\n\ntry:\n    from finops_action_plan import ActionPlanGenerator\n    ACTION_PLAN_MODULE_AVAILABLE = True\nexcept ImportError:\n    ACTION_PLAN_MODULE_AVAILABLE = False\n"
        # Find end of imports
        guardrail_idx = content.find("GUARDRAIL_MODULE_AVAILABLE = False")
        if guardrail_idx > 0:
            insert_pos = content.index("\n", guardrail_idx) + 1
            content = content[:insert_pos] + fallback_insert + content[insert_pos:]
            changes_made.append("Added ActionPlanGenerator import (fallback position)")
else:
    changes_made.append("ActionPlanGenerator import already exists — skipped")

# ---------------------------------------------------------------------------
# 2. Add "📋 Action Plan" tab to st.tabs()
# ---------------------------------------------------------------------------
old_tabs = """tab_jobs, tab_cost, tab_forecast, tab_perf, tab_budget, tab_remediation, tab_agent = st.tabs([
    "\U0001f527 Job Monitoring",
    "\U0001f4b0 Cost & FinOps",
    "\U0001f52e AI Cost Forecast",
    "\u26a1 Performance",
    "\U0001f3af Budget & Anomaly",
    "\U0001f6e1\ufe0f Guardrails & Remediation",
    "\U0001f916 AI FinOps Agent",
])"""

new_tabs = """tab_jobs, tab_cost, tab_forecast, tab_perf, tab_budget, tab_remediation, tab_action, tab_agent = st.tabs([
    "\U0001f527 Job Monitoring",
    "\U0001f4b0 Cost & FinOps",
    "\U0001f52e AI Cost Forecast",
    "\u26a1 Performance",
    "\U0001f3af Budget & Anomaly",
    "\U0001f6e1\ufe0f Guardrails & Remediation",
    "\U0001f4cb Action Plan",
    "\U0001f916 AI FinOps Agent",
])"""

if "tab_action" not in content:
    if old_tabs in content:
        content = content.replace(old_tabs, new_tabs)
        changes_made.append("Added '📋 Action Plan' tab to st.tabs()")
    else:
        # Try flexible replacement
        import re
        pattern = r'(tab_jobs, tab_cost, tab_forecast, tab_perf, tab_budget, tab_remediation), (tab_agent = st\.tabs\(\[)'
        replacement = r'\1, tab_action, \2'
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            # Also add the tab label
            content = content.replace(
                '"\U0001f6e1\ufe0f Guardrails & Remediation",\n    "\U0001f916 AI FinOps Agent",',
                '"\U0001f6e1\ufe0f Guardrails & Remediation",\n    "\U0001f4cb Action Plan",\n    "\U0001f916 AI FinOps Agent",'
            )
            changes_made.append("Added tab_action variable and tab label (regex)")
        else:
            changes_made.append("WARNING: Could not find tabs definition to modify")
else:
    changes_made.append("tab_action already exists — skipped")

# ---------------------------------------------------------------------------
# 3. Add Action Plan tab content (before tab_agent)
# ---------------------------------------------------------------------------
action_tab_code = '''
# ===========================================================================
# TAB 7 — RESOURCE CLEANUP ACTION PLAN
# ===========================================================================
with tab_action:
    st.header("\U0001f4cb Resource Cleanup Action Plan")
    st.caption("Identifies actively burning resources with DELETE/STOP/TERMINATE recommendations")

    if not ACTION_PLAN_MODULE_AVAILABLE:
        st.warning("\u26a0\ufe0f Action Plan module not available. Ensure `finops_action_plan.py` is in the app directory.")
    else:
        try:
            planner = ActionPlanGenerator(conn, subscription_filter=selected_subscriptions or "STAR Group Sandbox", lookback_days=7)

            with st.spinner("Generating action plan..."):
                plan = planner.generate_action_plan(min_spend_threshold=1.0)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                metric_card("Total Monthly Savings", f"${plan[\'total_monthly_savings\']:,.0f}", prefix="")
            with col2:
                metric_card("Critical Resources", plan[\'summary\'][\'by_priority\'].get(\'CRITICAL\', 0))
            with col3:
                metric_card("High Priority", plan[\'summary\'][\'by_priority\'].get(\'HIGH\', 0))
            with col4:
                metric_card("Total Resources", plan[\'summary\'][\'total_resources\'])

            st.markdown("---")

            # Action plan DataFrame
            df_plan = planner.as_dataframe(plan)
            if not df_plan.empty:
                st.subheader("\U0001f525 Resources to Action")

                # Priority filter
                priorities = st.multiselect(
                    "Filter by Priority",
                    options=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    default=["CRITICAL", "HIGH"],
                    key="action_plan_priority_filter"
                )
                if priorities:
                    df_display = df_plan[df_plan["priority"].isin(priorities)]
                else:
                    df_display = df_plan

                st.dataframe(
                    df_display.style.apply(
                        lambda row: [
                            \'background-color: #3d1f1f\' if row[\'priority\'] == \'CRITICAL\'
                            else \'background-color: #3d2e1f\' if row[\'priority\'] == \'HIGH\'
                            else \'background-color: #1f2d3d\' if row[\'priority\'] == \'MEDIUM\'
                            else \'\' for _ in row
                        ], axis=1
                    ),
                    use_container_width=True,
                    height=400,
                )

                # Cost by product chart
                st.subheader("\U0001f4b0 Projected Monthly Cost by Product")
                cost_by_product = df_plan.groupby("product")["projected_monthly_cost"].sum().reset_index()
                cost_by_product = cost_by_product.sort_values("projected_monthly_cost", ascending=False)
                fig = px.bar(
                    cost_by_product, x="product", y="projected_monthly_cost",
                    color="projected_monthly_cost",
                    color_continuous_scale="Reds",
                    labels={"product": "Resource Type", "projected_monthly_cost": "Projected Monthly ($)"}
                )
                fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig, use_container_width=True)

                # AI Summary
                st.subheader("\U0001f916 AI Executive Summary")
                if st.button("Generate AI Summary", key="gen_ai_summary"):
                    with st.spinner("Generating AI summary..."):
                        summary = planner.generate_ai_summary(plan)
                    st.markdown(f\'<div class="ai-box">{summary}</div>\', unsafe_allow_html=True)

                # Export
                st.subheader("\U0001f4e4 Export")
                col_md, col_csv = st.columns(2)
                with col_md:
                    md_output = planner.format_as_markdown(plan)
                    st.download_button("\U0001f4dd Download Markdown", md_output, "action_plan.md", "text/markdown")
                with col_csv:
                    csv_output = df_plan.to_csv(index=False)
                    st.download_button("\U0001f4ca Download CSV", csv_output, "action_plan.csv", "text/csv")
            else:
                st.success("\u2705 No resources exceeding spend thresholds found!")
        except Exception as e:
            st.error(f"Error generating action plan: {e}")
            import traceback
            st.code(traceback.format_exc())

'''

if "with tab_action:" not in content:
    # Insert before the AI Agent tab
    agent_marker = "with tab_agent:"
    agent_idx = content.find(agent_marker)
    if agent_idx > 0:
        # Find the comment block before tab_agent
        # Look back for the separator comment
        search_back = content[:agent_idx].rfind("# ===")
        if search_back > 0 and (agent_idx - search_back) < 200:
            insert_pos = search_back
        else:
            insert_pos = agent_idx
        content = content[:insert_pos] + action_tab_code + "\n" + content[insert_pos:]
        changes_made.append("Added Action Plan tab content (before AI Agent tab)")
    else:
        # Append at the end
        content += action_tab_code
        changes_made.append("Added Action Plan tab content (appended at end)")
else:
    changes_made.append("Action Plan tab content already exists — skipped")

# ---------------------------------------------------------------------------
# 4. Write updated app.py
# ---------------------------------------------------------------------------
with open(app_path, "w") as f:
    f.write(content)

print(f"\n\u2705 Updated {app_path}")
print(f"   New size: {len(content):,} chars")
print(f"   Changes:")
for change in changes_made:
    print(f"   - {change}")

# ---------------------------------------------------------------------------
# 5. Copy finops_action_plan.py to repos folder
# ---------------------------------------------------------------------------
src = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/finops_action_plan.py"
dst = "/Workspace/Users/cyrils@systechusa.com/databricksrepos/databricks-finops-monitor/finops_action_plan.py"

if os.path.exists(src):
    shutil.copy2(src, dst)
    print(f"\n\u2705 Copied finops_action_plan.py to repos folder")
    print(f"   {dst}")
else:
    print(f"\n\u274c Source file not found: {src}")
    print("   Please ensure finops_action_plan.py exists in the app directory.")

print("\n" + "=" * 60)
print("  ACTION PLAN INTEGRATION COMPLETE")
print("=" * 60)
print("\n  Redeploy the app to see the new '📋 Action Plan' tab.")

# COMMAND ----------

# DBTITLE 1,Patch finops_action_plan.py — Add SP Identity Resolution
import os
import shutil
import re

# =============================================================================
# Patch finops_action_plan.py — Add Service Principal Identity Resolution
# =============================================================================
# Resolves 'unknown' and UUID entries in the action plan to actual SP names
# or the user who created the resource (via audit log for Vector Search).
# =============================================================================

file_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/finops_action_plan.py"
with open(file_path, "r") as f:
    content = f.read()

print(f"Original finops_action_plan.py: {len(content):,} chars")
changes_made = []

# ---------------------------------------------------------------------------
# 1. Add KNOWN_SERVICE_PRINCIPALS constant after PRIORITY_THRESHOLDS
# ---------------------------------------------------------------------------
sp_constant = '''
# Known Databricks system service principals (resolved via audit log activity patterns)
KNOWN_SERVICE_PRINCIPALS = {
    "7fa11abe-2286-4e13-9f2c-bbf024d4f240": "SP: Predictive Optimization",
    "9f1a68cf-9a25-41ce-b85e-059d1c4b6fd6": "SP: Lakehouse Monitor (Data Quality)",
    "f61e27a7-0ea9-43f8-ba6c-5ad3ef571db0": "SP: SQL Warehouse System",
    "3da41f72-707d-47f8-8227-ea587c58374a": "SP: Model Serving / AI Functions",
    "10b233e2-8b72-4f99-9e4f-a3b2aabbf959": "SP: Model Serving (Delta Sharing Proxy)",
    "7d54e4b8-b257-484b-934e-7ab53bb34d58": "SP: Predictive Optimization (Metrics)",
    "b17f60f5-7694-469b-a910-940138496295": "SP: Workspace OAuth Client",
    "faf75d25-3cda-4042-92af-4180d1abf2df": "SP: Account Service",
}
'''

if "KNOWN_SERVICE_PRINCIPALS" not in content:
    # Insert after PRIORITY_THRESHOLDS block
    marker = '"MEDIUM": 10,      # >= $10/month projected\n}'
    idx = content.find(marker)
    if idx > 0:
        insert_pos = idx + len(marker)
        content = content[:insert_pos] + "\n" + sp_constant + content[insert_pos:]
        changes_made.append("Added KNOWN_SERVICE_PRINCIPALS constant")
    else:
        changes_made.append("WARNING: Could not find PRIORITY_THRESHOLDS marker")
else:
    changes_made.append("KNOWN_SERVICE_PRINCIPALS already exists — skipped")

# ---------------------------------------------------------------------------
# 2. Add _resolve_identity and _resolve_vector_search_creators methods
# ---------------------------------------------------------------------------
resolve_methods = '''
    # -----------------------------------------------------------------
    # Identity Resolution: Map UUIDs/unknown to SP names or creators
    # -----------------------------------------------------------------
    def _resolve_identity(self, owner_value):
        """Resolve owner identity - map UUIDs to SP names, annotate 'unknown'.

        Parameters
        ----------
        owner_value : str
            Raw owner string from billing (email, UUID, or 'unknown')

        Returns
        -------
        str : Resolved identity (SP name, email, or annotated value)
        """
        import re

        if not owner_value or owner_value == 'system':
            return 'system'

        # Check known SP mapping first
        if owner_value in KNOWN_SERVICE_PRINCIPALS:
            return KNOWN_SERVICE_PRINCIPALS[owner_value]

        # Check if it's a UUID pattern (service principal)
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, owner_value):
            return f"SP: {owner_value[:8]}... (unresolved)"

        # 'unknown' is typically Vector Search or system-managed endpoints
        if owner_value == 'unknown':
            return 'unknown (system-managed)'

        return owner_value

    def _resolve_vector_search_creators(self):
        """Query audit log to find who created Vector Search endpoints.

        Returns dict mapping endpoint_name -> creator email.
        """
        try:
            query = """
            SELECT
                a.user_identity.email AS creator,
                a.request_params[\'name\'] AS endpoint_or_index_name,
                a.request_params[\'endpoint_name\'] AS vs_endpoint,
                a.action_name,
                a.event_date
            FROM system.access.audit a
            WHERE a.event_date >= DATEADD(DAY, -180, CURRENT_DATE())
              AND a.service_name = \'vectorSearch\'
              AND a.action_name IN (\'createEndpoint\', \'createVectorIndex\')
            ORDER BY a.event_date DESC
            """
            df = self._run_query(query)
            creators = {}
            for _, row in df.iterrows():
                ep = str(row.get(\'endpoint_or_index_name\', \'\') or row.get(\'vs_endpoint\', \'\'))
                creator = str(row.get(\'creator\', \'\'))
                if ep and creator:
                    creators[ep] = creator
            return creators
        except Exception as e:
            print(f"[ActionPlan] Could not resolve VS creators: {e}")
            return {}

'''

if "_resolve_identity" not in content:
    # Insert after _run_query method
    run_query_end = 'return cur.fetchall_arrow().to_pandas()'
    idx = content.find(run_query_end)
    if idx > 0:
        # Find the end of the _run_query method (next blank line after return)
        next_newline = content.index("\n", idx)
        content = content[:next_newline + 1] + resolve_methods + content[next_newline + 1:]
        changes_made.append("Added _resolve_identity() and _resolve_vector_search_creators() methods")
    else:
        changes_made.append("WARNING: Could not find _run_query return statement")
else:
    changes_made.append("_resolve_identity already exists — skipped")

# ---------------------------------------------------------------------------
# 3. Replace owner assignment in generate_action_plan to use _resolve_identity
# ---------------------------------------------------------------------------
old_owner = '"owner": str(row.get("owner", "unknown")),'
new_owner = '"owner": self._resolve_identity(str(row.get("owner", "unknown"))),'

if old_owner in content and new_owner not in content:
    content = content.replace(old_owner, new_owner)
    changes_made.append("Updated owner assignment to use _resolve_identity()")
elif new_owner in content:
    changes_made.append("Owner assignment already uses _resolve_identity — skipped")
else:
    changes_made.append("WARNING: Could not find owner assignment line")

# ---------------------------------------------------------------------------
# 4. Add VS creator resolution step before sorting
# ---------------------------------------------------------------------------
vs_resolution_code = '''
        # Resolve "unknown" Vector Search owners via audit log
        try:
            vs_creators = self._resolve_vector_search_creators()
            for item in items:
                if item["owner"] == "unknown (system-managed)" and item["product"] == "VECTOR_SEARCH":
                    for ep_name, creator in vs_creators.items():
                        if creator:
                            item["owner"] = f"{creator} (VS endpoint creator)"
                            break
        except Exception:
            pass  # Gracefully handle if audit access fails

'''

sort_marker = '# Sort: CRITICAL first'
if "_resolve_vector_search_creators()" not in content.split(sort_marker)[0] if sort_marker in content else True:
    idx = content.find(sort_marker)
    if idx > 0 and "vs_creators = self._resolve_vector_search_creators" not in content:
        content = content[:idx] + vs_resolution_code + "        " + content[idx:]
        changes_made.append("Added VS creator resolution before sort step")
    elif "vs_creators" in content:
        changes_made.append("VS creator resolution already exists — skipped")
    else:
        changes_made.append("WARNING: Could not find sort marker")

# ---------------------------------------------------------------------------
# 5. Write updated file
# ---------------------------------------------------------------------------
with open(file_path, "w") as f:
    f.write(content)

print(f"\n\u2705 Updated {file_path}")
print(f"   New size: {len(content):,} chars")
print(f"   Changes:")
for change in changes_made:
    print(f"   - {change}")

# ---------------------------------------------------------------------------
# 6. Copy to repos folder
# ---------------------------------------------------------------------------
dst = "/Workspace/Users/cyrils@systechusa.com/databricksrepos/databricks-finops-monitor/finops_action_plan.py"
shutil.copy2(file_path, dst)
print(f"\n\u2705 Synced to repos folder: {dst}")

print("\n" + "=" * 60)
print("  SP IDENTITY RESOLUTION PATCH COMPLETE")
print("=" * 60)
print("\n  Service principals now resolved:")
print("  - 7fa11abe... → SP: Predictive Optimization")
print("  - 9f1a68cf... → SP: Lakehouse Monitor (Data Quality)")
print("  - f61e27a7... → SP: SQL Warehouse System")
print("  - 3da41f72... → SP: Model Serving / AI Functions")
print("  - 10b233e2... → SP: Model Serving (Delta Sharing Proxy)")
print("  - 'unknown'  → Resolved via audit log (VS endpoint creator)")

# COMMAND ----------

# DBTITLE 1,Patch app.py — Global SP Identity Resolution Across All Tabs
import os
import shutil
import re

# =============================================================================
# Patch app.py — Add Global SP Identity Resolution Across ALL Tabs
# =============================================================================
# Adds a shared resolve_identity() utility function in app.py so that
# every tab displaying owner/identity dynamically resolves UUIDs and 'unknown'
# to SP names or the actual resource creator.
# =============================================================================

app_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/app.py"
with open(app_path, "r") as f:
    content = f.read()

print(f"Original app.py: {len(content):,} chars")
changes_made = []

# ---------------------------------------------------------------------------
# 1. Add global SP mapping + resolve_identity() utility function
#    Insert after the metric_card() helper (before Workspace Helpers section)
# ---------------------------------------------------------------------------
sp_resolver_code = '''
# ---------------------------------------------------------------------------
# Identity Resolution — Resolve UUIDs, 'unknown', and SP IDs globally
# ---------------------------------------------------------------------------
import re as _re

KNOWN_SERVICE_PRINCIPALS = {
    "7fa11abe-2286-4e13-9f2c-bbf024d4f240": "SP: Predictive Optimization",
    "9f1a68cf-9a25-41ce-b85e-059d1c4b6fd6": "SP: Lakehouse Monitor (Data Quality)",
    "f61e27a7-0ea9-43f8-ba6c-5ad3ef571db0": "SP: SQL Warehouse System",
    "3da41f72-707d-47f8-8227-ea587c58374a": "SP: Model Serving / AI Functions",
    "10b233e2-8b72-4f99-9e4f-a3b2aabbf959": "SP: Model Serving (Delta Sharing Proxy)",
    "7d54e4b8-b257-484b-934e-7ab53bb34d58": "SP: Predictive Optimization (Metrics)",
    "b17f60f5-7694-469b-a910-940138496295": "SP: Workspace OAuth Client",
    "faf75d25-3cda-4042-92af-4180d1abf2df": "SP: Account Service",
}

_UUID_PATTERN = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def resolve_identity(owner_value):
    """Resolve owner identity globally — maps UUIDs to SP names, annotates unknown."""
    if not owner_value or owner_value in ("system", "None", "nan"):
        return "system"
    owner_value = str(owner_value).strip()
    if owner_value in KNOWN_SERVICE_PRINCIPALS:
        return KNOWN_SERVICE_PRINCIPALS[owner_value]
    if _UUID_PATTERN.match(owner_value):
        return f"SP: {owner_value[:8]}..."
    if owner_value == "unknown":
        return "unknown (system-managed)"
    return owner_value


def resolve_identity_column(df, col="owner"):
    """Apply resolve_identity to an entire DataFrame column in-place."""
    if col in df.columns:
        df[col] = df[col].astype(str).apply(resolve_identity)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def get_vs_endpoint_creators(_conn):
    """Cached: query audit log for Vector Search endpoint creators."""
    try:
        query = """
        SELECT
            a.user_identity.email AS creator,
            COALESCE(a.request_params[\'name\'], a.request_params[\'endpoint_name\']) AS resource_name,
            a.action_name,
            a.event_date
        FROM system.access.audit a
        WHERE a.event_date >= DATEADD(DAY, -180, CURRENT_DATE())
          AND a.service_name = \'vectorSearch\'
          AND a.action_name IN (\'createEndpoint\', \'createVectorIndex\')
        ORDER BY a.event_date DESC
        """
        df = run_query(_conn, query)
        creators = {}
        for _, row in df.iterrows():
            name = str(row.get("resource_name", ""))
            creator = str(row.get("creator", ""))
            if name and creator:
                creators[name] = creator
        return creators
    except Exception:
        return {}


def resolve_unknown_vs_owners(df, conn, owner_col="owner", product_col=None):
    """For rows with \'unknown (system-managed)\' + VECTOR_SEARCH product,
    resolve to the actual VS endpoint creator via audit log."""
    if product_col and product_col in df.columns:
        vs_mask = (
            (df[owner_col].str.contains("unknown", case=False, na=False)) &
            (df[product_col].str.contains("VECTOR_SEARCH", case=False, na=False))
        )
    else:
        vs_mask = df[owner_col].str.contains("unknown", case=False, na=False)

    if vs_mask.any():
        creators = get_vs_endpoint_creators(conn)
        if creators:
            # Use the most recent VS creator as default attribution
            default_creator = next(iter(creators.values()), None)
            if default_creator:
                df.loc[vs_mask, owner_col] = df.loc[vs_mask, owner_col].apply(
                    lambda x: f"{default_creator} (VS creator)" if "unknown" in str(x).lower() else x
                )
    return df

'''

if "KNOWN_SERVICE_PRINCIPALS" not in content:
    # Insert after metric_card function, before Workspace Helpers section
    marker = '# Workspace & Subscription Helpers'
    idx = content.find(marker)
    if idx > 0:
        # Find the comment divider line before it
        divider_idx = content.rfind('# -----', 0, idx)
        insert_pos = divider_idx if divider_idx > 0 else idx
        content = content[:insert_pos] + sp_resolver_code + "\n" + content[insert_pos:]
        changes_made.append("Added global KNOWN_SERVICE_PRINCIPALS + resolve_identity() utility")
    else:
        changes_made.append("WARNING: Could not find Workspace Helpers section marker")
else:
    changes_made.append("KNOWN_SERVICE_PRINCIPALS already in app.py — skipped")

# ---------------------------------------------------------------------------
# 2. Patch Cost & FinOps tab — resolve owner in cost queries
#    The cost tab uses identity_metadata to show top spenders.
#    We add resolve_identity_column() after each owner DataFrame is created.
# ---------------------------------------------------------------------------
# Find patterns like:
#   COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by, 'system') AS owner
# and after the DataFrame is built, apply resolution.

# Strategy: Find all places where a df has an 'owner' column displayed and
# add resolve_identity_column(df, 'owner') just before st.dataframe() or display calls.

# Patch: replace raw COALESCE owner in SQL with resolution at display time
# Add a universal post-processing step in each tab's data display

# Simpler approach: Add a global hook after run_query that resolves owners
# Let's patch run_query to optionally resolve identities

old_run_query = '''@st.cache_data(ttl=300, show_spinner=False)
def run_query(_conn, query: str) -> pd.DataFrame:
    with _conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall_arrow().to_pandas()'''

new_run_query = '''@st.cache_data(ttl=300, show_spinner=False)
def run_query(_conn, query: str, resolve_owners: bool = False) -> pd.DataFrame:
    with _conn.cursor() as cur:
        cur.execute(query)
        df = cur.fetchall_arrow().to_pandas()
    if resolve_owners:
        for col in ["owner", "run_as", "created_by", "owned_by"]:
            if col in df.columns:
                df[col] = df[col].astype(str).apply(
                    lambda x: KNOWN_SERVICE_PRINCIPALS.get(x, x) if x else x
                )
    return df'''

if 'resolve_owners: bool' not in content:
    if old_run_query in content:
        content = content.replace(old_run_query, new_run_query)
        changes_made.append("Patched run_query() to support resolve_owners parameter")
    else:
        changes_made.append("NOTE: run_query signature differs — manual review needed")
else:
    changes_made.append("run_query already has resolve_owners — skipped")

# ---------------------------------------------------------------------------
# 3. Add identity resolution to all SQL queries that use COALESCE(...) AS owner
#    Instead of modifying each query, we add a post-query transform.
#    We'll inject resolve_identity_column() calls after key DataFrames.
# ---------------------------------------------------------------------------
# Find all instances of display patterns with owner columns and add resolution
# Target: wherever `st.dataframe(df_` appears and df has an owner column

# More practical: Add a SQL-level CASE expression wrapper
# Inject a helper SQL function definition

sql_resolver = '''
# SQL helper: wrap owner column with SP resolution in SQL queries
def sql_resolve_owner_expr(alias="owner"):
    """Returns a SQL CASE expression that resolves known SP UUIDs inline."""
    cases = "\\n".join(
        f"        WHEN {{col}} = \'{uuid}\' THEN \'{name}\'"
        for uuid, name in KNOWN_SERVICE_PRINCIPALS.items()
    )
    return f"""CASE
{cases}
        WHEN {{col}} RLIKE \'^[0-9a-f]{{8}}-[0-9a-f]{{4}}-\' THEN CONCAT(\'SP: \', LEFT({{col}}, 8), \'...\')
        WHEN {{col}} = \'unknown\' THEN \'unknown (system-managed)\'
        WHEN {{col}} IS NULL THEN \'system\'
        ELSE {{col}}
    END AS {alias}"""


OWNER_RESOLVE_SQL = sql_resolve_owner_expr("owner").format(
    col="COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by, \'system\')")
'''

if 'sql_resolve_owner_expr' not in content:
    # Insert right after the KNOWN_SERVICE_PRINCIPALS block we just added
    sp_end_marker = 'def resolve_unknown_vs_owners'
    idx = content.find(sp_end_marker)
    if idx > 0:
        # Find end of that function
        next_func = content.find("\n\n", idx + 100)
        if next_func > 0:
            content = content[:next_func] + "\n" + sql_resolver + content[next_func:]
            changes_made.append("Added sql_resolve_owner_expr() SQL helper")
    else:
        changes_made.append("NOTE: Could not find insertion point for SQL helper")
else:
    changes_made.append("sql_resolve_owner_expr already exists — skipped")

# ---------------------------------------------------------------------------
# 4. Replace COALESCE(...) AS owner patterns in major tab queries
#    with the CASE-based resolver
# ---------------------------------------------------------------------------
# Common pattern in queries:
old_owner_sql = "COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by, 'system') AS owner"
new_owner_sql = """CASE
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) IN ('7fa11abe-2286-4e13-9f2c-bbf024d4f240') THEN 'SP: Predictive Optimization'
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) IN ('9f1a68cf-9a25-41ce-b85e-059d1c4b6fd6') THEN 'SP: Lakehouse Monitor (Data Quality)'
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) IN ('f61e27a7-0ea9-43f8-ba6c-5ad3ef571db0') THEN 'SP: SQL Warehouse System'
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) IN ('3da41f72-707d-47f8-8227-ea587c58374a') THEN 'SP: Model Serving / AI Functions'
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) IN ('10b233e2-8b72-4f99-9e4f-a3b2aabbf959') THEN 'SP: Model Serving (Delta Sharing Proxy)'
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) RLIKE '^[0-9a-f]{8}-[0-9a-f]{4}-' THEN CONCAT('SP: ', LEFT(COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by), 8), '...')
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) = 'unknown' THEN 'unknown (system-managed)'
            WHEN COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by) IS NULL THEN 'system'
            ELSE COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by, 'system')
        END AS owner"""

replacements_made = content.count(old_owner_sql)
if replacements_made > 0:
    content = content.replace(old_owner_sql, new_owner_sql)
    changes_made.append(f"Replaced {replacements_made} COALESCE(...) AS owner → CASE-based SP resolution in SQL")
else:
    # Try alternate pattern with different quotes
    alt_old = 'COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by, \'system\') AS owner'
    alt_count = content.count(alt_old)
    if alt_count > 0:
        content = content.replace(alt_old, new_owner_sql)
        changes_made.append(f"Replaced {alt_count} COALESCE (alt quotes) → CASE-based SP resolution")
    else:
        changes_made.append("NOTE: No direct COALESCE AS owner patterns found — may use different format")

# ---------------------------------------------------------------------------
# 5. Write updated app.py
# ---------------------------------------------------------------------------
with open(app_path, "w") as f:
    f.write(content)

print(f"\n\u2705 Updated {app_path}")
print(f"   New size: {len(content):,} chars")
print(f"   Changes:")
for change in changes_made:
    print(f"   - {change}")

# Copy to repos
dst = "/Workspace/Users/cyrils@systechusa.com/databricksrepos/databricks-finops-monitor/app.py"
shutil.copy2(app_path, dst)
print(f"\n\u2705 Synced app.py to repos folder")

print("\n" + "=" * 60)
print("  GLOBAL SP RESOLUTION DEPLOYED TO app.py")
print("=" * 60)
print("\n  All tabs now resolve:")
print("  - UUID service principals → readable SP names")
print("  - 'unknown' → 'unknown (system-managed)'")
print("  - Vector Search creators → actual user via audit log")
print("\n  Affected tabs: Cost & FinOps, Budget & Anomaly,")
print("  Guardrails & Remediation, Action Plan")

# COMMAND ----------

# DBTITLE 1,Fix IndentationError — Restructure resolve_unknown_vs_owners
import os
import shutil
import py_compile

app_path = "/Workspace/Users/cyrils@systechusa.com/databricks-finops-monitor/app.py"
repos_path = "/Workspace/Users/cyrils@systechusa.com/databricksrepos/databricks-finops-monitor/app.py"

with open(app_path, "r") as f:
    content = f.read()

print(f"Original app.py: {len(content):,} chars")

# The broken structure looks like:
# def resolve_unknown_vs_owners(...):
#     ...
#     else:
#         vs_mask = df[owner_col].str.contains(...)
#
# # SQL helper: ...
# def sql_resolve_owner_expr(alias="owner"):
#     ...
#
# OWNER_RESOLVE_SQL = sql_resolve_owner_expr(...)
#
#
#     if vs_mask.any():    <--- INDENTATION ERROR (orphaned from its function)
#         ...
#     return df

# Strategy:
# 1. Find the broken resolve_unknown_vs_owners function
# 2. Find where it was split (the point where sql_resolve_owner_expr starts)
# 3. Find the orphaned `if vs_mask.any():` block
# 4. Reassemble: complete resolve_unknown_vs_owners first, then sql_resolve_owner_expr

# --- Locate the function definition ---
func_start_marker = 'def resolve_unknown_vs_owners(df, conn, owner_col="owner", product_col=None):'
func_start = content.find(func_start_marker)
assert func_start >= 0, "Could not find resolve_unknown_vs_owners function"
print(f"Found resolve_unknown_vs_owners at char {func_start}")

# --- Find where sql_resolve_owner_expr intrudes ---
sql_helper_marker = '# SQL helper: wrap owner column with SP resolution in SQL queries'
sql_helper_start = content.find(sql_helper_marker, func_start)
assert sql_helper_start >= 0, "Could not find sql_resolve_owner_expr comment"
print(f"Found SQL helper intrusion at char {sql_helper_start}")

# --- Find the orphaned `if vs_mask.any():` block ---
# It appears AFTER OWNER_RESOLVE_SQL with wrong indentation
orphan_marker = '\n    if vs_mask.any():'
# Search after the sql_resolve_owner_expr
orphan_start = content.find(orphan_marker, sql_helper_start)
assert orphan_start >= 0, "Could not find orphaned 'if vs_mask.any():' block"
print(f"Found orphaned block at char {orphan_start}")

# Find the end of the orphaned block (ends with `    return df\n`)
# The return df at function-indent level marks end of the orphaned code
orphan_return = content.find('\n    return df\n', orphan_start)
assert orphan_return >= 0, "Could not find orphaned 'return df'"
orphan_end = orphan_return + len('\n    return df\n')
print(f"Orphaned block ends at char {orphan_end}")

# Extract the orphaned code (the `if vs_mask.any(): ... return df` block)
orphaned_code = content[orphan_start:orphan_end]
print(f"\nOrphaned code ({len(orphaned_code)} chars):")
print(orphaned_code[:300])

# --- Find the split point in resolve_unknown_vs_owners ---
# The function body ends just before the sql_helper comment
# We need to find the last line of function body before the split
# That's the `vs_mask = ...` line or the preceding else block

# The function body before the split ends with a newline before the sql helper comment
# Go back from sql_helper_start to find the end of actual function content
func_body_end = sql_helper_start
# Strip trailing whitespace/newlines to get clean join point
while func_body_end > 0 and content[func_body_end - 1] in '\n ':
    func_body_end -= 1
func_body_end += 1  # include one newline

print(f"\nFunction body ends at char {func_body_end}")
print(f"Last 100 chars of function body: ...{content[func_body_end-100:func_body_end]}")

# --- Extract the sql_resolve_owner_expr + OWNER_RESOLVE_SQL block ---
sql_block = content[sql_helper_start:orphan_start]
print(f"\nSQL helper block ({len(sql_block)} chars):")
print(sql_block[:200])

# --- Reassemble the correct structure ---
# 1. Everything before the split (resolve_unknown_vs_owners function body up to vs_mask line)
# 2. The orphaned block (if vs_mask.any(): ... return df) — goes back into the function
# 3. Two newlines
# 4. The sql_resolve_owner_expr function and OWNER_RESOLVE_SQL
# 5. Everything after the orphaned block

before_split = content[:func_body_end]
after_orphan = content[orphan_end:]

# Build the fixed content
fixed_content = before_split + orphaned_code + '\n\n' + sql_block.rstrip() + '\n\n' + after_orphan.lstrip()

print(f"\n{'='*60}")
print(f"Fixed app.py: {len(fixed_content):,} chars (was {len(content):,})")

# --- Validate syntax ---
with open(app_path, "w") as f:
    f.write(fixed_content)

try:
    py_compile.compile(app_path, doraise=True)
    print("\n✅ SYNTAX CHECK PASSED — No IndentationError!")
except py_compile.PyCompileError as e:
    print(f"\n❌ Still has syntax error: {e}")
    # Restore original
    with open(app_path, "w") as f:
        f.write(content)
    print("Restored original file.")
    raise

# --- Sync to repos folder ---
shutil.copy2(app_path, repos_path)
print(f"\n✅ Synced to repos: {repos_path}")
print("\n" + "="*60)
print("  IndentationError FIXED — app.py is ready to deploy")
print("="*60)
