
# =============================================================================
# finops_budget.py — Budget Management for FinOps
# =============================================================================
# Features: Cumulative spend, breach prediction, burndown, alerts
# Uses ai_query() for natural language budget insights
# =============================================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"


class BudgetManager:
    """Manages budget tracking, forecasting, and alerts for Databricks FinOps."""

    def __init__(self, conn, start_date, end_date):
        self.conn = conn
        self.start_date = start_date if isinstance(start_date, str) else start_date.isoformat()
        self.end_date = end_date if isinstance(end_date, str) else end_date.isoformat()

    def _run_query(self, query):
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall_arrow().to_pandas()

    # -------------------------------------------------------------------
    # Cumulative daily spend
    # -------------------------------------------------------------------
    def get_cumulative_spend(self, group_by=None):
        """
        Get cumulative daily spend, optionally grouped.
        group_by: None, 'product', 'workspace', 'user'
        """
        group_expr = ""
        group_col = ""
        if group_by == "product":
            group_col = "u.billing_origin_product AS group_name,"
            group_expr = ", u.billing_origin_product"
        elif group_by == "workspace":
            group_col = "CAST(u.workspace_id AS STRING) AS group_name,"
            group_expr = ", CAST(u.workspace_id AS STRING)"
        elif group_by == "user":
            group_col = ("COALESCE(u.identity_metadata.run_as, "
                         "u.identity_metadata.created_by, 'unknown') AS group_name,")
            group_expr = (", COALESCE(u.identity_metadata.run_as, "
                          "u.identity_metadata.created_by, 'unknown')")

        query = f"""
        WITH daily AS (
            SELECT
                u.usage_date,
                {group_col}
                SUM(CAST(u.usage_quantity AS DOUBLE) *
                    COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
                ) AS daily_cost
            FROM system.billing.usage u
            LEFT JOIN system.billing.list_prices p
                ON u.sku_name = p.sku_name
                AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
            WHERE u.usage_date >= '{self.start_date}'
              AND u.usage_date <= '{self.end_date}'
            GROUP BY u.usage_date {group_expr}
        )
        SELECT *,
               SUM(daily_cost) OVER (
                   {"PARTITION BY group_name" if group_by else ""}
                   ORDER BY usage_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS cumulative_cost
        FROM daily
        ORDER BY usage_date
        """
        df = self._run_query(query)
        for col in ["daily_cost", "cumulative_cost"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df

    # -------------------------------------------------------------------
    # Budget breach prediction
    # -------------------------------------------------------------------
    def predict_budget_breach(self, monthly_budget, forecast_df=None):
        """
        Predict if/when the monthly budget will be exceeded.
        Returns dict with: will_breach, breach_date, days_until_breach,
                          projected_monthly_total, projected_overshoot_pct
        """
        df = self.get_cumulative_spend()
        if df.empty:
            return {
                "will_breach": False, "breach_date": None,
                "days_until_breach": None, "projected_monthly_total": 0,
                "projected_overshoot_pct": 0, "current_spend": 0,
                "budget_utilization_pct": 0, "daily_burn_rate": 0,
            }

        current_spend = float(df["cumulative_cost"].iloc[-1])
        days_elapsed = len(df)
        daily_avg = current_spend / max(days_elapsed, 1)

        # Use forecast if available for better projection
        if forecast_df is not None and not forecast_df.empty:
            forecast_col = [c for c in forecast_df.columns if "forecast" in c.lower()]
            if forecast_col:
                projected_remaining = float(
                    pd.to_numeric(forecast_df[forecast_col[0]], errors="coerce").fillna(0).sum()
                )
                projected_total = current_spend + projected_remaining
            else:
                projected_total = daily_avg * 30
        else:
            projected_total = daily_avg * 30

        # Determine breach
        will_breach = projected_total > monthly_budget
        breach_date = None
        days_until_breach = None

        if daily_avg > 0:
            remaining_budget = monthly_budget - current_spend
            if remaining_budget > 0:
                days_until_breach = int(remaining_budget / daily_avg)
                breach_date = (
                    datetime.strptime(self.end_date, "%Y-%m-%d") + timedelta(days=days_until_breach)
                ).strftime("%Y-%m-%d")
            else:
                days_until_breach = 0
                breach_date = self.end_date

        overshoot_pct = round(
            ((projected_total - monthly_budget) / max(monthly_budget, 1)) * 100, 1
        )

        return {
            "will_breach": will_breach,
            "breach_date": breach_date,
            "days_until_breach": days_until_breach,
            "projected_monthly_total": round(projected_total, 2),
            "projected_overshoot_pct": overshoot_pct if will_breach else 0,
            "current_spend": round(current_spend, 2),
            "budget_utilization_pct": round((current_spend / max(monthly_budget, 1)) * 100, 1),
            "daily_burn_rate": round(daily_avg, 2),
        }

    # -------------------------------------------------------------------
    # Budget burndown
    # -------------------------------------------------------------------
    def get_budget_burndown(self, monthly_budget):
        """
        Returns df with: date, cumulative_spend, budget_line, remaining_budget, burn_rate
        """
        df = self.get_cumulative_spend()
        if df.empty:
            return pd.DataFrame()

        df["budget_line"] = monthly_budget
        df["remaining_budget"] = monthly_budget - df["cumulative_cost"]
        df["burn_rate"] = df["daily_cost"].rolling(7, min_periods=1).mean()
        df["budget_pct_used"] = (df["cumulative_cost"] / monthly_budget * 100).round(1)

        # Linear budget pace line (expected even distribution)
        total_days = len(df)
        df["expected_pace"] = [
            monthly_budget * (i + 1) / max(total_days, 1) for i in range(len(df))
        ]
        df["ahead_behind"] = df["cumulative_cost"] - df["expected_pace"]

        return df

    # -------------------------------------------------------------------
    # Budget alerts
    # -------------------------------------------------------------------
    def get_budget_alerts(self, monthly_budget, thresholds=None):
        """
        Returns list of triggered alert dicts based on budget utilization.
        """
        if thresholds is None:
            thresholds = [50, 75, 90, 100]

        prediction = self.predict_budget_breach(monthly_budget)
        alerts = []
        utilization = prediction["budget_utilization_pct"]

        for t in sorted(thresholds):
            if utilization >= t:
                severity = "info"
                if t >= 100:
                    severity = "critical"
                elif t >= 90:
                    severity = "high"
                elif t >= 75:
                    severity = "warning"

                cur_spend_val = prediction["current_spend"]
                msg = (
                    "Budget {}% threshold breached — "
                    "${:,.0f} of ${:,.0f} used ({:.1f}%)"
                ).format(t, cur_spend_val, monthly_budget, utilization)
                alerts.append({
                    "threshold_pct": t,
                    "severity": severity,
                    "message": msg,
                    "utilization_pct": utilization,
                    "current_spend": cur_spend_val,
                })

        # Breach prediction alert
        if prediction["will_breach"] and prediction["days_until_breach"] is not None:
            if prediction["days_until_breach"] <= 7:
                days_left = prediction["days_until_breach"]
                proj_total = prediction["projected_monthly_total"]
                proj_over = prediction["projected_overshoot_pct"]
                msg = (
                    "BUDGET BREACH IMMINENT — projected to exceed "
                    "budget in {} days. "
                    "Projected total: ${:,.0f} "
                    "(+{}%)"
                ).format(days_left, proj_total, proj_over)
                alerts.append({
                    "threshold_pct": None,
                    "severity": "critical",
                    "message": msg,
                    "utilization_pct": utilization,
                    "current_spend": prediction["current_spend"],
                })

        return alerts

    # -------------------------------------------------------------------
    # AI Budget Insight
    # -------------------------------------------------------------------
    def get_ai_budget_insight(self, monthly_budget):
        """
        Use ai_query() to generate a natural language budget analysis.
        Returns the SQL query string (caller executes via their connection).
        """
        prediction = self.predict_budget_breach(monthly_budget)
        p = prediction
        cur_spend_val = p["current_spend"]
        util_pct_val = p["budget_utilization_pct"]
        burn_rate_val = p["daily_burn_rate"]
        proj_total_val = p["projected_monthly_total"]
        will_breach_val = p["will_breach"]
        days_breach_val = p["days_until_breach"]
        overshoot_val = p["projected_overshoot_pct"]
        prompt = (
            "You are a Databricks FinOps budget analyst. Analyze this budget status "
            "and provide actionable insights:\n\n"
            "Monthly Budget: ${:,.0f}\n"
            "Current Spend: ${:,.0f} ({}%)\n"
            "Daily Burn Rate: ${:,.0f}/day\n"
            "Projected Monthly Total: ${:,.0f}\n"
            "Will Breach: {}\n"
            "Days Until Breach: {}\n"
            "Projected Overshoot: {}%\n\n"
            "Provide: 1) Budget health assessment 2) Risk level "
            "3) Top 3 cost reduction actions 4) Forecast confidence. Be concise."
        ).format(
            monthly_budget, cur_spend_val, util_pct_val,
            burn_rate_val, proj_total_val, will_breach_val,
            days_breach_val, overshoot_val
        )
        query = f"""
        SELECT ai_query('{LLM_ENDPOINT}',
                        '{prompt.replace("'", "''")}')
        AS insight
        """
        return query
