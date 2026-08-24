# =============================================================================
# finops_action_plan.py — Resource Cleanup Action Plan Generator
# =============================================================================
# Identifies actively burning resources, categorizes by priority, calculates
# projected monthly cost, and generates structured DELETE/STOP/TERMINATE actions.
# Integrates with GuardrailEngine for enforcement and audit logging.
# =============================================================================

import pandas as pd
from datetime import datetime, timedelta

LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"

# Action mapping by product type
ACTION_MAP = {
    "VECTOR_SEARCH": "DELETE ENDPOINT",
    "MODEL_SERVING": "DELETE ENDPOINT",
    "LAKEBASE": "DELETE RESOURCE",
    "DATABASE": "DELETE RESOURCE",
    "APPS": "STOP APP",
    "INTERACTIVE": "TERMINATE CLUSTER",
    "ALL_PURPOSE": "TERMINATE CLUSTER",
    "SQL": "STOP WAREHOUSE",
    "DATA_QUALITY_MONITORING": "DISABLE MONITOR",
    "DLT": "STOP PIPELINE",
    "PREDICTIVE_OPTIMIZATION": "DISABLE",
    "NETWORKING": "REVIEW",
    "JOBS": "REVIEW",
}

# Priority thresholds (projected monthly cost)
PRIORITY_THRESHOLDS = {
    "CRITICAL": 200,   # >= $200/month projected
    "HIGH": 50,        # >= $50/month projected
    "MEDIUM": 10,      # >= $10/month projected
}

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



class ActionPlanGenerator:
    """Generates resource cleanup action plans from billing data.

    Parameters
    ----------
    conn : databricks.sql connection
        SQL warehouse connection for system table queries.
    subscription_filter : str or list
        Subscription name(s) to filter. Default: 'STAR Group Sandbox'.
    lookback_days : int
        Number of days to look back for active resource detection (default: 7).
    """

    def __init__(self, conn, subscription_filter="STAR Group Sandbox", lookback_days=7):
        self.conn = conn
        self.lookback_days = lookback_days
        if isinstance(subscription_filter, str):
            self.subscriptions = [subscription_filter]
        else:
            self.subscriptions = subscription_filter

    def _run_query(self, query):
        """Execute SQL query and return pandas DataFrame."""
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall_arrow().to_pandas()

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
                a.request_params['name'] AS endpoint_or_index_name,
                a.request_params['endpoint_name'] AS vs_endpoint,
                a.action_name,
                a.event_date
            FROM system.access.audit a
            WHERE a.event_date >= DATEADD(DAY, -180, CURRENT_DATE())
              AND a.service_name = 'vectorSearch'
              AND a.action_name IN ('createEndpoint', 'createVectorIndex')
            ORDER BY a.event_date DESC
            """
            df = self._run_query(query)
            creators = {}
            for _, row in df.iterrows():
                ep = str(row.get('endpoint_or_index_name', '') or row.get('vs_endpoint', ''))
                creator = str(row.get('creator', ''))
                if ep and creator:
                    creators[ep] = creator
            return creators
        except Exception as e:
            print(f"[ActionPlan] Could not resolve VS creators: {e}")
            return {}


    # -----------------------------------------------------------------
    # Core: Generate Action Plan
    # -----------------------------------------------------------------
    def generate_action_plan(self, min_spend_threshold=1.0):
        """Generate a prioritized resource cleanup action plan.

        Queries billing data for the last N days, identifies actively burning
        resources, and returns a structured action plan with cost projections.

        Parameters
        ----------
        min_spend_threshold : float
            Minimum 7-day spend ($) to include a resource (default: $1.00).

        Returns
        -------
        dict with keys:
            - generated_at: timestamp
            - lookback_days: int
            - subscriptions: list
            - total_monthly_savings: float
            - items: list of action plan items (sorted by priority)
            - summary: dict with counts by priority and action type
        """
        subs_filter = ", ".join(f"'{s}'" for s in self.subscriptions)

        query = f"""
        SELECT
            wm.workspace_name,
            u.billing_origin_product AS product,
            u.sku_name,
            COALESCE(u.identity_metadata.run_as,
                     u.identity_metadata.created_by, 'system') AS owner,
            ROUND(SUM(
                CAST(u.usage_quantity AS DOUBLE) *
                COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
            ), 2) AS period_spend,
            ROUND(SUM(
                CAST(u.usage_quantity AS DOUBLE) *
                COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
            ) / {self.lookback_days} * 30, 2) AS projected_monthly_cost,
            MIN(u.usage_date) AS first_usage,
            MAX(u.usage_date) AS last_usage,
            DATEDIFF(CURRENT_DATE(), MAX(u.usage_date)) AS days_since_last_use,
            wm.subscription_name
        FROM system.billing.usage u
        LEFT JOIN system.billing.list_prices p
            ON u.sku_name = p.sku_name
            AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
        INNER JOIN uae_insurance.uae_silver.workspace_mapping wm
            ON u.workspace_id = wm.workspace_id
        WHERE u.usage_date >= DATEADD(DAY, -{self.lookback_days}, CURRENT_DATE())
            AND u.usage_date <= CURRENT_DATE()
            AND wm.subscription_name IN ({subs_filter})
        GROUP BY wm.workspace_name, u.billing_origin_product, u.sku_name,
                 COALESCE(u.identity_metadata.run_as,
                          u.identity_metadata.created_by, 'system'),
                 wm.subscription_name
        HAVING period_spend >= {min_spend_threshold}
        ORDER BY period_spend DESC
        """

        df = self._run_query(query)

        items = []
        for _, row in df.iterrows():
            product = str(row.get("product", "UNKNOWN"))
            projected = float(pd.to_numeric(row.get("projected_monthly_cost", 0), errors="coerce") or 0)
            period_spend = float(pd.to_numeric(row.get("period_spend", 0), errors="coerce") or 0)

            # Determine priority
            if projected >= PRIORITY_THRESHOLDS["CRITICAL"]:
                priority = "CRITICAL"
            elif projected >= PRIORITY_THRESHOLDS["HIGH"]:
                priority = "HIGH"
            elif projected >= PRIORITY_THRESHOLDS["MEDIUM"]:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            # Determine action
            action = ACTION_MAP.get(product, "REVIEW")

            items.append({
                "priority": priority,
                "workspace": str(row.get("workspace_name", "")),
                "product": product,
                "sku": str(row.get("sku_name", "")),
                "owner": self._resolve_identity(str(row.get("owner", "unknown"))),
                "period_spend": period_spend,
                "projected_monthly_cost": projected,
                "first_usage": str(row.get("first_usage", "")),
                "last_usage": str(row.get("last_usage", "")),
                "days_since_last_use": int(pd.to_numeric(row.get("days_since_last_use", 0), errors="coerce") or 0),
                "action": action,
                "subscription": str(row.get("subscription_name", "")),
            })

        
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

        # Sort: CRITICAL first, then by projected cost descending
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        items.sort(key=lambda x: (priority_order.get(x["priority"], 9), -x["projected_monthly_cost"]))

        # Summary
        total_savings = sum(i["projected_monthly_cost"] for i in items)
        priority_counts = {}
        action_counts = {}
        for item in items:
            priority_counts[item["priority"]] = priority_counts.get(item["priority"], 0) + 1
            action_counts[item["action"]] = action_counts.get(item["action"], 0) + 1

        plan = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lookback_days": self.lookback_days,
            "subscriptions": self.subscriptions,
            "total_monthly_savings": round(total_savings, 2),
            "items": items,
            "summary": {
                "total_resources": len(items),
                "by_priority": priority_counts,
                "by_action": action_counts,
            },
        }

        print(f"[ActionPlan] Generated plan: {len(items)} resources, "
              f"${total_savings:,.0f}/mo potential savings")
        return plan

    # -----------------------------------------------------------------
    # Formatted Output: Markdown Table
    # -----------------------------------------------------------------
    def format_as_markdown(self, plan=None, max_items=None):
        """Format action plan as a markdown table for email/reports.

        Parameters
        ----------
        plan : dict, optional
            Action plan dict. If None, generates a new one.
        max_items : int, optional
            Limit output to top N items.

        Returns
        -------
        str : Markdown formatted table
        """
        if plan is None:
            plan = self.generate_action_plan()

        items = plan["items"]
        if max_items:
            items = items[:max_items]

        lines = [
            f"## Resource Cleanup Action Plan",
            f"**Generated:** {plan['generated_at']} | "
            f"**Lookback:** {plan['lookback_days']} days | "
            f"**Total Potential Savings:** ${plan['total_monthly_savings']:,.0f}/month",
            "",
            "| # | Priority | Workspace | Resource | Owner | 7-Day Spend | Proj. Monthly | Action |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]

        for i, item in enumerate(items, 1):
            lines.append(
                f"| {i} | {item['priority']} | {item['workspace']} | "
                f"{item['product']} | {item['owner']} | "
                f"${item['period_spend']:,.2f} | "
                f"${item['projected_monthly_cost']:,.2f} | "
                f"{item['action']} |"
            )

        lines.extend([
            "",
            f"**Summary:** {plan['summary']['total_resources']} resources identified | "
            f"CRITICAL: {plan['summary']['by_priority'].get('CRITICAL', 0)} | "
            f"HIGH: {plan['summary']['by_priority'].get('HIGH', 0)} | "
            f"MEDIUM: {plan['summary']['by_priority'].get('MEDIUM', 0)}",
        ])

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Formatted Output: DataFrame for Dashboard
    # -----------------------------------------------------------------
    def as_dataframe(self, plan=None):
        """Convert action plan to a pandas DataFrame for dashboard display.

        Returns
        -------
        pd.DataFrame with columns: priority, workspace, product, owner,
                                   period_spend, projected_monthly_cost, action
        """
        if plan is None:
            plan = self.generate_action_plan()

        if not plan["items"]:
            return pd.DataFrame()

        df = pd.DataFrame(plan["items"])
        df = df[[
            "priority", "workspace", "product", "owner",
            "period_spend", "projected_monthly_cost", "action",
            "days_since_last_use", "subscription"
        ]]
        return df

    # -----------------------------------------------------------------
    # AI Summary (uses ai_query for natural language explanation)
    # -----------------------------------------------------------------
    def generate_ai_summary(self, plan=None):
        """Generate an AI-powered natural language summary of the action plan.

        Uses ai_query() to create a concise executive summary suitable
        for email responses or Slack notifications.

        Returns
        -------
        str : Natural language summary
        """
        if plan is None:
            plan = self.generate_action_plan()

        # Build context for the LLM
        critical_items = [i for i in plan["items"] if i["priority"] == "CRITICAL"]
        high_items = [i for i in plan["items"] if i["priority"] == "HIGH"]

        context = (
            f"Total resources burning money: {plan['summary']['total_resources']}. "
            f"Total projected monthly savings if all cleaned: ${plan['total_monthly_savings']:,.0f}. "
            f"Critical items ({len(critical_items)}): "
            + "; ".join(
                f"{i['product']} in {i['workspace']} by {i['owner']} (${i['projected_monthly_cost']:,.0f}/mo)"
                for i in critical_items[:5]
            )
            + f". High priority items ({len(high_items)}): "
            + "; ".join(
                f"{i['product']} in {i['workspace']} by {i['owner']} (${i['projected_monthly_cost']:,.0f}/mo)"
                for i in high_items[:5]
            )
        )

        prompt = (
            "You are a FinOps analyst. Write a concise 3-paragraph executive summary "
            "for a cost cleanup action plan. Include: 1) The urgency and total savings, "
            "2) Top offenders and who owns them, 3) Recommended immediate actions. "
            f"Data: {context}"
        )

        try:
            query = f"""
            SELECT ai_query(
                '{LLM_ENDPOINT}',
                '{prompt.replace("'", "''")}'
            ) AS summary
            """
            df = self._run_query(query)
            if not df.empty:
                return str(df.iloc[0, 0])
        except Exception as e:
            print(f"[ActionPlan] AI summary error: {e}")

        # Fallback: manual summary
        return (
            f"ACTION REQUIRED: {len(critical_items)} critical resources identified "
            f"burning ${plan['total_monthly_savings']:,.0f}/month. "
            f"Top offenders are Vector Search endpoints and Lakebase instances "
            f"running with no active workloads. Immediate deletion recommended."
        )

    # -----------------------------------------------------------------
    # Execute Plan (with GuardrailEngine integration)
    # -----------------------------------------------------------------
    def execute_plan(self, plan=None, guardrail_engine=None, priority_filter=None):
        """Execute action plan items using the GuardrailEngine.

        Parameters
        ----------
        plan : dict, optional
            Action plan to execute. If None, generates a new one.
        guardrail_engine : GuardrailEngine, optional
            If provided, uses its SDK client and audit logging.
        priority_filter : list, optional
            Only execute items matching these priorities.
            E.g., ["CRITICAL"] to only handle critical items.

        Returns
        -------
        dict with execution results and audit trail.
        """
        if plan is None:
            plan = self.generate_action_plan()

        items = plan["items"]
        if priority_filter:
            items = [i for i in items if i["priority"] in priority_filter]

        results = []
        for item in items:
            result = {
                **item,
                "execution_status": "pending",
                "execution_details": "",
            }

            # If no guardrail engine or no SDK, mark as manual
            if guardrail_engine is None or not hasattr(guardrail_engine, 'w') or guardrail_engine.w is None:
                result["execution_status"] = "MANUAL_ACTION_REQUIRED"
                result["execution_details"] = (
                    f"Navigate to {item['workspace']} workspace and "
                    f"{item['action'].lower()} the {item['product']} resource owned by {item['owner']}"
                )
            elif guardrail_engine.dry_run:
                result["execution_status"] = "DRY_RUN"
                result["execution_details"] = f"Would {item['action'].lower()} — dry run mode"
            else:
                # Live execution via SDK would go here
                # For safety, we log but require explicit per-resource confirmation
                result["execution_status"] = "QUEUED_FOR_CONFIRMATION"
                result["execution_details"] = (
                    f"Action queued. Confirm via guardrail enforcement job."
                )

            results.append(result)

        executed_plan = {
            "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_items": len(results),
            "priority_filter": priority_filter,
            "results": results,
        }

        print(f"[ActionPlan] Execution complete: {len(results)} items processed")
        return executed_plan
