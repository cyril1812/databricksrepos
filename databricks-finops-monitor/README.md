# Databricks FinOps Monitor — AI-Enhanced Edition

An AI-powered FinOps command center deployed as a native Databricks App. It monitors costs, predicts budget breaches, detects anomalies, enforces guardrails, and auto-remediates waste across your Databricks workspaces.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Deployment](#installation--deployment)
7. [Configuration](#configuration)
8. [Modules](#modules)
9. [Scheduled Enforcement](#scheduled-enforcement)
10. [Data Sources](#data-sources)
11. [AI Capabilities](#ai-capabilities)
12. [PDF Export](#pdf-export)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The Databricks FinOps Monitor is a Streamlit-based dashboard that provides real-time visibility into Databricks cloud spend, resource utilization, and cost optimization opportunities. It queries Databricks **system tables** directly and layers AI/ML capabilities for proactive cost management.

**Key Value Propositions:**
- Proactive budget breach prediction (not just reactive alerts)
- Multi-method anomaly detection (Z-Score, IQR, Isolation Forest)
- Automated remediation of idle/oversized resources via Databricks SDK
- Natural language FinOps agent powered by Meta Llama 3.3 70B
- Identity resolution for service principals and system-managed resources
- Multi-workspace support with subscription-level filtering

---

## Architecture

```
+----------------------------------------------------------+
|                  Databricks App (Streamlit)               |
|                                                          |
|  +---------+  +----------+  +-----------+  +--------+   |
|  |  Cost   |  | Anomaly  |  | Guardrail |  |   AI   |   |
|  | Monitor |  | Detector |  |  Engine   |  | Agent  |   |
|  +---------+  +----------+  +-----------+  +--------+   |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|              Databricks SQL Warehouse                     |
+----------------------------------------------------------+
                            |
        +-------------------+-------------------+
        v                   v                   v
+--------------+  +----------------+  +------------------+
|system.billing|  |system.compute  |  |system.lakeflow   |
|  .usage      |  |  .clusters     |  |  .job_run_timeline|
|  .list_prices|  |  .node_timeline|  |  .jobs           |
+--------------+  +----------------+  +------------------+
```

**Components:**
- **Frontend**: Streamlit app with dark-themed UI, deployed as a Databricks App
- **Data Layer**: Databricks system tables via SQL Warehouse connection
- **AI/ML Layer**: LLM (Meta Llama 3.3 70B) for chat + scikit-learn for anomaly detection
- **Automation Layer**: Databricks SDK for remediation actions (terminate, resize, stop)
- **Export Layer**: PDF reports per tab via fpdf2 + kaleido

---

## Features

| Feature | Description |
| --- | --- |
| Job Monitoring | Track job runs, failures, SLA compliance, duration trends |
| Cost FinOps | Spend breakdown by product, workspace, user, SKU |
| Performance Insights | Cluster utilization, warehouse efficiency metrics |
| AI Cost Forecasting | Predict future spend and budget breach dates |
| Budget Management | Cumulative burn tracking, burndown charts, threshold alerts |
| Anomaly Detection | Multi-algorithm detection (Z-Score, IQR, Isolation Forest) |
| Auto-Remediation | Scan and fix idle clusters, runaway jobs, oversized warehouses |
| Guardrails | Policy compliance checks, tag enforcement, auto-termination rules |
| Action Plans | Prioritized resource cleanup recommendations |
| AI FinOps Agent | Natural language chat for cost queries and insights |
| PDF Export | Per-tab downloadable PDF reports with charts and tables |
| Identity Resolution | Maps service principal UUIDs to human-readable names |

---

## Project Structure

```
databricks-finops-monitor/
├── app.py                      # Main Streamlit application
├── app.yaml                    # Databricks App deployment config
├── requirements.txt            # Python dependencies
├── finops_anomaly.py           # Anomaly detection (Z-Score, IQR, Isolation Forest)
├── finops_budget.py            # Budget management (cumulative spend, breach prediction)
├── finops_remediation.py       # Auto-remediation engine (idle clusters, runaway jobs)
├── finops_guardrails.py        # Policy compliance & guardrail enforcement
├── finops_action_plan.py       # Resource cleanup action plan generator
├── finops_enforcement_job.py   # Scheduled job for guardrail enforcement
├── pdf_export.py               # PDF report generation per dashboard tab
├── FinOps Guardrails Builder   # Notebook: guardrails setup & testing
├── AI FinOps Enhancement Builder # Notebook: AI feature development
├── VIDEO_PRESENTATION_SCRIPT.md # Demo video script
└── README.md                   # This file
```

---

## Prerequisites

- **Databricks Workspace** with access to system tables
- **SQL Warehouse** (Serverless or Pro recommended)
- **Unity Catalog** enabled (for system table access)
- **System table access** granted:
  - `system.billing.usage`
  - `system.billing.list_prices`
  - `system.compute.clusters`
  - `system.compute.node_timeline`
  - `system.lakeflow.jobs`
  - `system.lakeflow.job_run_timeline`
  - `system.access.audit` (optional, for identity resolution)
- **Workspace mapping table** (optional): `uae_insurance.uae_silver.workspace_mapping`
- **Model Serving Endpoint**: `databricks-meta-llama-3-3-70b-instruct` (for AI Agent)

---

## Installation & Deployment

### 1. Deploy as Databricks App

The app is configured to run as a native Databricks App using the `app.yaml`:

```yaml
command: ['streamlit', 'run', 'app.py', '--server.maxUploadSize=50']
env:
  - name: 'STREAMLIT_GATHER_USAGE_STATS'
    value: 'false'
  - name: 'STREAMLIT_THEME_BASE'
    value: 'dark'
```

### 2. Install Dependencies

Dependencies are auto-installed from `requirements.txt` during app deployment:

```
databricks-sdk
databricks-sql-connector
streamlit
pandas
numpy
plotly
scikit-learn
fpdf2
kaleido
```

### 3. Access the App

Once deployed, navigate to the Databricks Apps page and launch the app. Enter your SQL Warehouse ID in the sidebar to connect.

---

## Configuration

### Sidebar Parameters

| Parameter | Description | Default |
| --- | --- | --- |
| SQL Warehouse ID | Warehouse for system table queries | Required |
| Date Range | Start/end dates for data filtering | Last 30 days |
| Azure Subscription | Filter by subscription (multi-workspace) | All |
| Workspace | Filter by workspace name | All |
| SLA Threshold | Job SLA target for compliance tracking | Configurable |
| Monthly Budget | Budget target for breach prediction | $5,000 |

### Environment Variables

The app uses `databricks.sdk.core.Config()` for authentication — no manual API keys required when running as a Databricks App.

---

## Modules

### `finops_anomaly.py`

Multi-algorithm anomaly detection engine:

- **Z-Score**: Rolling window (14-day default) with configurable threshold (2.5 sigma)
- **IQR**: Interquartile range with configurable multiplier (1.5x)
- **Isolation Forest**: ML-based detection via scikit-learn (5% contamination default)

Granularity options: per-job, per-cluster, per-user, per-workspace, per-product.

### `finops_budget.py`

Budget lifecycle management:

- Cumulative daily spend tracking (grouped by product/workspace/user)
- Budget breach prediction with projected dates
- Burndown charts with pace lines
- Threshold-based alerting (50%, 75%, 90%, 100%)
- AI-powered budget insights via `ai_query()`

### `finops_remediation.py`

Automated cost remediation with dry-run support:

- **Idle Cluster Detection**: Flags clusters with low CPU (<15%) and memory (<30%)
- **Runaway Job Detection**: Identifies jobs exceeding cost or duration thresholds
- **Oversized Warehouse Detection**: Finds underutilized SQL warehouses
- **Actions**: Terminate, resize, stop — executed via Databricks SDK
- **Audit Logging**: All actions logged with timestamps and justification

### `finops_guardrails.py`

Policy compliance enforcement:

- **Cluster Compliance**: Auto-termination enabled, max worker limits
- **Tag Compliance**: Required tags (project, owner, env) enforcement
- **Real-time Scanning**: Checks all active clusters against policies
- **Severity Levels**: HIGH, MEDIUM, LOW with recommended actions

### `finops_action_plan.py`

Structured resource cleanup recommendations:

- Identifies actively burning resources by product type
- Categorizes by priority (CRITICAL >= $200/mo, HIGH >= $50/mo, MEDIUM >= $10/mo)
- Generates specific actions: DELETE ENDPOINT, TERMINATE CLUSTER, STOP WAREHOUSE, etc.
- Integrates with GuardrailEngine for enforcement

### `pdf_export.py`

Per-tab PDF report generation:

- Landscape A4 format with branded headers
- Embeds Plotly charts as images (via kaleido)
- Includes metric summaries and data tables
- Download buttons within each dashboard tab

---

## Scheduled Enforcement

The `finops_enforcement_job.py` script is designed to run as a scheduled Databricks Job:

### Parameters (via `dbutils.widgets`):

| Parameter | Description | Default |
| --- | --- | --- |
| `dry_run` | `true` = report only, `false` = execute actions | `true` |
| `monthly_budget` | Budget threshold for alerts | `5000` |
| `warehouse_id` | SQL Warehouse ID for system table queries | env var |

### Recommended Schedule

- **Frequency**: Every 4 hours
- **Mode**: Start with `dry_run=true`, switch to `false` after validating findings

---

## Data Sources

The app queries the following Databricks system tables:

| Table | Purpose |
| --- | --- |
| `system.billing.usage` | DBU consumption, cost calculation |
| `system.billing.list_prices` | SKU pricing for cost estimation |
| `system.compute.clusters` | Cluster metadata, configuration |
| `system.compute.node_timeline` | Node-level CPU/memory utilization |
| `system.lakeflow.jobs` | Job definitions and metadata |
| `system.lakeflow.job_run_timeline` | Job run history, durations, results |
| `system.access.audit` | Audit logs for identity resolution |

---

## AI Capabilities

### AI FinOps Agent (Chat)

- Powered by **Meta Llama 3.3 70B Instruct** via Databricks Model Serving
- Accepts natural language cost queries (e.g., "What's my most expensive job this week?")
- Generates and executes dynamic SQL against system tables
- Provides cost optimization recommendations

### Anomaly Detection

- Three detection methods for different data characteristics
- Auto-fallback: Isolation Forest falls back to Z-Score if scikit-learn unavailable
- Per-resource granularity with deviation percentages

### Identity Resolution

- Maps known Databricks service principal UUIDs to human-readable names
- Resolves Vector Search endpoint creators via audit log queries
- Handles `unknown` and `system` owners gracefully

---

## PDF Export

Each dashboard tab includes a **Download PDF** button that generates a report containing:

- Header with tab name, date range, and generation timestamp
- Key metrics summary
- Plotly charts rendered as images
- Data tables with the most relevant rows

Requires `fpdf2` and `kaleido` packages.

---

## Troubleshooting

| Issue | Solution |
| --- | --- |
| Connection failed | Verify SQL Warehouse ID is correct and warehouse is running |
| No data displayed | Ensure system table access is granted to your account |
| Anomaly module unavailable | Install `scikit-learn` (falls back to Z-Score) |
| PDF export missing | Ensure `fpdf2` and `kaleido` are in requirements.txt |
| AI Agent not responding | Verify `databricks-meta-llama-3-3-70b-instruct` endpoint is active |
| Remediation actions fail | Check Databricks SDK permissions; use `dry_run=true` first |
| Workspace names not loading | Verify workspace mapping table exists in Unity Catalog |

---

## License

Internal use — Databricks workspace deployment.

---

## Author

Built with Databricks Apps, Streamlit, and AI/ML for proactive cloud cost management.
