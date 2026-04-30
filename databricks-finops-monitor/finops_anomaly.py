
# =============================================================================
# finops_anomaly.py — Enhanced Anomaly Detection for FinOps
# =============================================================================
# Methods: Z-Score, IQR, Isolation Forest
# Granularity: per-job, per-cluster, per-user, per-workspace, per-product
# =============================================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Z-Score Anomaly Detection
# ---------------------------------------------------------------------------
def detect_anomalies_zscore(df, value_col, group_col=None, window=14, threshold=2.5):
    """
    Detect anomalies using rolling Z-Score method.
    Returns df with: anomaly_score, is_anomaly, expected_value, deviation_pct
    """
    result = df.copy()

    def _zscore_group(grp):
        grp = grp.sort_values(grp.columns[0])  # sort by first col (date)
        vals = pd.to_numeric(grp[value_col], errors="coerce").fillna(0)
        rolling_mean = vals.rolling(window=window, min_periods=max(3, window // 3)).mean()
        rolling_std = vals.rolling(window=window, min_periods=max(3, window // 3)).std()
        rolling_std = rolling_std.replace(0, np.nan).fillna(vals.std() if vals.std() > 0 else 1)
        z_scores = (vals - rolling_mean) / rolling_std
        grp["anomaly_score"] = z_scores.abs().fillna(0)
        grp["is_anomaly"] = grp["anomaly_score"] > threshold
        grp["expected_value"] = rolling_mean.fillna(vals.mean())
        grp["deviation_pct"] = (
            ((vals - grp["expected_value"]) / grp["expected_value"].replace(0, np.nan)) * 100
        ).fillna(0).round(1)
        return grp

    if group_col and group_col in result.columns:
        result = result.groupby(group_col, group_keys=False).apply(_zscore_group)
    else:
        result = _zscore_group(result)

    return result


# ---------------------------------------------------------------------------
# IQR Anomaly Detection
# ---------------------------------------------------------------------------
def detect_anomalies_iqr(df, value_col, group_col=None, multiplier=1.5):
    """
    Detect anomalies using Interquartile Range (IQR) method.
    Returns df with: anomaly_score, is_anomaly, expected_value, deviation_pct
    """
    result = df.copy()

    def _iqr_group(grp):
        vals = pd.to_numeric(grp[value_col], errors="coerce").fillna(0)
        q1 = vals.quantile(0.25)
        q3 = vals.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        median_val = vals.median()

        # Score: how many IQRs away from bounds
        deviation = np.where(
            vals > upper_bound, (vals - upper_bound) / max(iqr, 1e-6),
            np.where(vals < lower_bound, (lower_bound - vals) / max(iqr, 1e-6), 0)
        )
        grp["anomaly_score"] = np.abs(deviation).round(3)
        grp["is_anomaly"] = (vals < lower_bound) | (vals > upper_bound)
        grp["expected_value"] = median_val
        grp["deviation_pct"] = (
            ((vals - median_val) / max(median_val, 1e-6)) * 100
        ).round(1)
        return grp

    if group_col and group_col in result.columns:
        result = result.groupby(group_col, group_keys=False).apply(_iqr_group)
    else:
        result = _iqr_group(result)

    return result


# ---------------------------------------------------------------------------
# Isolation Forest Anomaly Detection
# ---------------------------------------------------------------------------
def detect_anomalies_isolation_forest(df, value_col, group_col=None, contamination=0.05):
    """
    Detect anomalies using Isolation Forest (scikit-learn).
    Returns df with: anomaly_score, is_anomaly, expected_value, deviation_pct
    Falls back to Z-Score if scikit-learn is not installed.
    """
    if not SKLEARN_AVAILABLE:
        import warnings
        warnings.warn("scikit-learn not installed, falling back to Z-Score method")
        return detect_anomalies_zscore(df, value_col, group_col=group_col)

    result = df.copy()

    def _iforest_group(grp):
        vals = pd.to_numeric(grp[value_col], errors="coerce").fillna(0)
        if len(vals) < 10:
            # Not enough data for Isolation Forest
            grp["anomaly_score"] = 0.0
            grp["is_anomaly"] = False
            grp["expected_value"] = vals.mean()
            grp["deviation_pct"] = 0.0
            return grp

        X = vals.values.reshape(-1, 1)
        model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        model.fit(X)
        preds = model.predict(X)          # 1 = normal, -1 = anomaly
        scores = model.decision_function(X)  # lower = more anomalous

        # Normalize scores: invert so higher = more anomalous
        norm_scores = 1 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)

        grp["anomaly_score"] = np.round(norm_scores, 3)
        grp["is_anomaly"] = preds == -1
        grp["expected_value"] = vals.mean()
        grp["deviation_pct"] = (
            ((vals - vals.mean()) / max(vals.mean(), 1e-6)) * 100
        ).round(1)
        return grp

    if group_col and group_col in result.columns:
        result = result.groupby(group_col, group_keys=False).apply(_iforest_group)
    else:
        result = _iforest_group(result)

    return result


# ---------------------------------------------------------------------------
# SQL: Get cost anomalies by resource
# ---------------------------------------------------------------------------
def get_cost_anomalies_by_resource(conn, start_date, end_date, granularity="job",
                                    run_query_fn=None):
    """
    Query system tables for per-resource daily cost, then apply anomaly detection.
    granularity: 'job', 'cluster', 'user', 'workspace', 'product'
    Returns DataFrame with anomaly flags.
    """
    granularity_map = {
        "job": ("COALESCE(u.usage_metadata.job_name, CONCAT('job_', u.usage_metadata.job_id))",
                "resource_name"),
        "cluster": ("COALESCE(u.usage_metadata.cluster_id, 'unknown')", "resource_name"),
        "user": ("COALESCE(u.identity_metadata.run_as, u.identity_metadata.created_by, "
                 "u.identity_metadata.owned_by, 'unknown')", "resource_name"),
        "workspace": ("CAST(u.workspace_id AS STRING)", "resource_name"),
        "product": ("COALESCE(u.billing_origin_product, 'unknown')", "resource_name"),
    }

    sql_expr, alias = granularity_map.get(granularity, granularity_map["job"])
    SD = start_date if isinstance(start_date, str) else start_date.isoformat()
    ED = end_date if isinstance(end_date, str) else end_date.isoformat()

    query = f"""
    SELECT
        u.usage_date,
        {sql_expr} AS {alias},
        SUM(CAST(u.usage_quantity AS DOUBLE)) AS total_dbus,
        SUM(CAST(u.usage_quantity AS DOUBLE) *
            COALESCE(CAST(p.pricing.effective_list.default AS DOUBLE), 0)
        ) AS daily_cost
    FROM system.billing.usage u
    LEFT JOIN system.billing.list_prices p
        ON u.sku_name = p.sku_name
        AND (p.price_end_time IS NULL OR u.usage_date < p.price_end_time)
    WHERE u.usage_date >= '{SD}' AND u.usage_date <= '{ED}'
    GROUP BY u.usage_date, {sql_expr}
    HAVING SUM(CAST(u.usage_quantity AS DOUBLE)) > 0
    ORDER BY u.usage_date, {alias}
    """

    if run_query_fn:
        df = run_query_fn(conn, query)
    else:
        with conn.cursor() as cur:
            cur.execute(query)
            df = cur.fetchall_arrow().to_pandas()

    # Apply numeric conversion
    for col in ["total_dbus", "daily_cost"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# ---------------------------------------------------------------------------
# Anomaly Summary
# ---------------------------------------------------------------------------
def get_anomaly_summary(df_anomalies):
    """
    Summarize anomaly detection results.
    Returns dict with total_anomalies, top_offenders, estimated_excess_cost, severity_distribution.
    """
    if df_anomalies.empty or "is_anomaly" not in df_anomalies.columns:
        return {
            "total_anomalies": 0,
            "top_offenders": [],
            "estimated_excess_cost": 0.0,
            "severity_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
        }

    anomalies = df_anomalies[df_anomalies["is_anomaly"]].copy()
    total = len(anomalies)

    # Top offenders by excess cost
    top_offenders = []
    if "resource_name" in anomalies.columns and "daily_cost" in anomalies.columns:
        top = anomalies.groupby("resource_name").agg(
            anomaly_count=("is_anomaly", "sum"),
            total_cost=("daily_cost", "sum"),
            avg_score=("anomaly_score", "mean"),
            max_deviation=("deviation_pct", "max"),
        ).sort_values("total_cost", ascending=False).head(10)
        for name, row in top.iterrows():
            top_offenders.append({
                "resource": name,
                "anomaly_count": int(row["anomaly_count"]),
                "total_cost": round(float(row["total_cost"]), 2),
                "avg_score": round(float(row["avg_score"]), 2),
                "max_deviation_pct": round(float(row["max_deviation"]), 1),
            })

    # Estimated excess cost
    excess_cost = 0.0
    if "daily_cost" in anomalies.columns and "expected_value" in anomalies.columns:
        excess = anomalies["daily_cost"] - anomalies["expected_value"]
        excess_cost = float(excess[excess > 0].sum())

    # Severity distribution based on anomaly_score
    severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    if "anomaly_score" in anomalies.columns:
        scores = anomalies["anomaly_score"]
        severity["low"] = int((scores < 1.5).sum())
        severity["medium"] = int(((scores >= 1.5) & (scores < 2.5)).sum())
        severity["high"] = int(((scores >= 2.5) & (scores < 4.0)).sum())
        severity["critical"] = int((scores >= 4.0).sum())

    return {
        "total_anomalies": total,
        "top_offenders": top_offenders,
        "estimated_excess_cost": round(excess_cost, 2),
        "severity_distribution": severity,
    }
