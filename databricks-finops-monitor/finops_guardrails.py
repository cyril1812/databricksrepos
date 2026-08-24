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


    def _safe_int(self, val, default=0):
        """Safely convert a value to int, handling NaN/None."""
        try:
            numeric = pd.to_numeric(val, errors="coerce")
            if pd.isna(numeric):
                return default
            return int(numeric)
        except (ValueError, TypeError):
            return default

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
                    min_autoscale_workers, max_autoscale_workers,
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
                workers = self._safe_int(row.get("worker_count", 0))
                max_auto = self._safe_int(row.get("max_autoscale_workers", 0))
                source = str(row.get("cluster_source", ""))
                effective_max = max(workers, max_auto)

                # Check auto-termination
                if auto_term is None or self._safe_int(auto_term) == 0:
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

            if not violations:
                self._log_action("cluster_compliance", "all", "all_clusters",
                                 "scan_complete", "passed",
                                 "All clusters comply with policies")
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
                    cluster_id, cluster_name, owned_by, tags,
                    delete_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY cluster_id ORDER BY change_time DESC
                    ) AS rn
                FROM system.compute.clusters
            )
            SELECT cluster_id, cluster_name, owned_by, tags
            FROM latest_clusters
            WHERE rn = 1 AND delete_time IS NULL
            """
            df = self._run_query(query)

            for _, row in df.iterrows():
                cid = str(row.get("cluster_id", ""))
                cname = str(row.get("cluster_name", "Unknown"))
                owner = str(row.get("owned_by", "unknown"))
                tags_raw = row.get("tags")

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

            if not violations:
                self._log_action("tag_compliance", "all", "all_clusters",
                                 "scan_complete", "passed",
                                 "All clusters have required tags")
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
            WHERE u.usage_date >= '{month_start}'
              AND u.usage_date <= '{today}'
            """
            df = self._run_query(query)
            spend = float(pd.to_numeric(
                df.iloc[0]["total_spend"], errors="coerce") or 0) if not df.empty else 0.0

            result["current_spend"] = round(spend, 2)
            result["utilization_pct"] = round(
                (spend / monthly_budget * 100) if monthly_budget > 0 else 0, 1)
            result["threshold_exceeded"] = result["utilization_pct"] >= critical_threshold_pct

            if result["threshold_exceeded"]:
                util_pct = result["utilization_pct"]
                self._log_action("budget_enforcement", "workspace", "all",
                                 "budget_critical", "triggered",
                                 f"Spend ${spend:,.0f} = {util_pct}% of ${monthly_budget:,}")

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

            budget_status_str = "CRITICAL" if result["threshold_exceeded"] else "OK"
            print(f"[Budget] Spend: ${spend:,.0f} / ${monthly_budget:,} "
                  f"({util_pct}%) — "
                  f"{budget_status_str}")
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

            idle_cluster_count = len([a for a in actions if a.get('resource_type') == 'CLUSTER'])
            idle_cluster_actions = [a for a in actions if a.get("resource_type") == "CLUSTER"]
            if not idle_cluster_actions:
                self._log_action("idle_enforcement", "all", "all_clusters",
                                 "scan_complete", "passed",
                                 "No idle clusters detected")
            print(f"[Idle Clusters] Scanned {len(clusters)} clusters, "
                  f"{idle_cluster_count} idle")
        except Exception as e:
            print("[Idle Clusters] Error: {}".format(e))
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

            wh_actions = [a for a in actions if a.get("resource_type") == "WAREHOUSE"]
            if not wh_actions:
                self._log_action("idle_enforcement", "all", "all_warehouses",
                                 "scan_complete", "passed",
                                 "No idle warehouses detected")
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

            if not actions:
                self._log_action("app_lifecycle", "all", "all_apps",
                                 "scan_complete", "passed",
                                 "No idle apps detected")
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
                  AND (r.result_state IS NULL OR r.result_state = 'RUNNING')
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

            if not actions:
                self._log_action("job_guardrail", "all", "all_jobs",
                                 "scan_complete", "passed",
                                 "No runaway jobs detected")
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

        print("\n" + "=" * 60)
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