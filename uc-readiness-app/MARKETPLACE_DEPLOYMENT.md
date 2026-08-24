# 🏪 Databricks Marketplace Deployment Guide
## UC Readiness Accelerator (GovernIQ) — Marketplace Listing Strategy

---

## OVERVIEW

To make GovernIQ available as a deployable asset on the **Databricks Marketplace**, the recommended approach is a **Solution Accelerator** listing. This allows customers to clone the repository, run a setup notebook, and have the app deployed in their workspace within minutes.

---

## LISTING TYPE: Solution Accelerator

### Why Solution Accelerator (vs. other listing types)

| Listing Type | What's Shared | Consumer Experience | Fit for GovernIQ |
| --- | --- | --- | --- |
| **Dataset** | Tables via Delta Sharing | Read-only catalog | No — app needs write access |
| **Notebook** | .ipynb files | Import to workspace | Partial — misses app deploy |
| **Model** | ML model artifacts | Model serving | Not applicable |
| **Solution Accelerator** | Git repo (cloned) | Full project with setup | Best fit |
| **MCP Server** | Agent tools | AI agent integration | Not applicable |

**Solution Accelerators** are shared as Git repositories that consumers clone into their workspace as a Git folder. This is ideal because GovernIQ requires:
- Application code (`app.py`, `app.yaml`, `requirements.txt`)
- Pipeline notebook (creates assessment tables)
- Configuration files (`.streamlit/config.toml`)
- Setup/deployment automation

---

## REPOSITORY STRUCTURE (For Marketplace)

Restructure the project into a self-contained, parameterized Git repository:

```
uc-readiness-accelerator/
├── README.md                          # Overview, screenshots, prerequisites
├── SETUP.md                           # Step-by-step deployment instructions
├── LICENSE                            # Apache 2.0 or your preferred license
│
├── app/                               # Databricks App source
│   ├── app.py                         # Main Streamlit app
│   ├── app.yaml                       # App configuration (parameterized)
│   ├── requirements.txt               # Python dependencies
│   └── .streamlit/
│       └── config.toml                # Streamlit theme config
│
├── pipeline/                          # Assessment pipeline
│   ├── 01_setup_schema.sql            # CREATE SCHEMA + assessment_rules seed
│   ├── 02_bronze_ingestion.sql        # Bronze layer DDL
│   ├── 03_silver_assessment.sql       # Silver layer transformations
│   ├── 04_gold_aggregation.sql        # Gold layer scoring + recommendations
│   └── full_pipeline.py               # All-in-one notebook (current pipeline)
│
├── deployment/                        # Automated deployment
│   ├── deploy_app.py                  # Notebook: creates + deploys the app
│   ├── schedule_pipeline.py           # Notebook: creates a recurring job
│   └── validate_permissions.py        # Checks required privileges
│
├── config/                            # Configuration templates
│   ├── config.yaml.template           # User fills: catalog, schema, warehouse ID
│   └── assessment_rules.csv           # Default rule definitions (seedable)
│
├── docs/                              # Documentation
│   ├── architecture.png               # Pipeline architecture diagram
│   ├── screenshots/                   # App screenshots for README
│   └── VIDEO_PRESENTATION_SCRIPT.md   # Demo video script
│
└── tests/                             # Validation
    └── validate_deployment.py         # Post-deploy health check notebook
```

---

## PREREQUISITES FOR CONSUMERS

Document these clearly in `README.md`:

### Required
1. **Azure Databricks workspace** with Unity Catalog enabled
2. **SQL Warehouse** (Serverless or Pro) with access to:
   - `system.information_schema` (tables, columns, table_privileges, table_tags)
   - `system.access.table_lineage`
   - `system.billing.usage` (optional — for FinOps tab)
   - `system.query.history` (optional — for Performance tab)
3. **CREATE SCHEMA** privilege on a target catalog
4. **Databricks Apps** enabled on the workspace
5. **Premium or Enterprise** tier (for system tables access)

### Optional (for full functionality)
- `system.billing.usage` access (FinOps Insights)
- `system.query.history` access (Performance tab)
- ML Models registered in Unity Catalog (ML Models tab)
- UC Volumes created (Volumes tab)

---

## PARAMETERIZATION (Make it Customer-Agnostic)

### Current hardcoded values to parameterize:

| Current Value | Parameterize As | Where |
| --- | --- | --- |
| `democatalog.uc_assessment` | `{TARGET_CATALOG}.{TARGET_SCHEMA}` | `app.py` line \~130 |
| `6fcaa843626846e7` | `{WAREHOUSE_ID}` | `app.yaml` env var |
| Hardcoded assessment rules | Seedable from `assessment_rules.csv` | Pipeline notebook |

### Implementation: `config.yaml.template`

```yaml
# UC Readiness Accelerator — Configuration
# Copy this file to config.yaml and fill in your values

target_catalog: "my_catalog"           # Catalog where assessment tables will be created
target_schema: "uc_assessment"         # Schema name (will be created if not exists)
warehouse_id: ""                       # Your SQL Warehouse ID
app_name: "uc-readiness-accelerator"   # Databricks App name (must be unique in workspace)

# Optional: Scope the assessment to specific catalogs (empty = all accessible)
include_catalogs: []                   # e.g., ["production", "analytics"]
exclude_catalogs:                      # Always excluded
  - "system"
  - "information_schema"

# Optional: Schedule
pipeline_schedule: "0 6 * * 1"        # Cron: every Monday at 6 AM
```

### Implementation: Modify `app.py` to read config

```python
import os

# Support both direct config and environment variable override
FULL_SCHEMA = os.getenv("UC_ASSESSMENT_SCHEMA", "catalog.uc_assessment")
```

### Implementation: Modify `app.yaml`

```yaml
command: ["streamlit", "run", "app.py"]

env:
  - name: DATABRICKS_WAREHOUSE_ID
    description: "SQL Warehouse ID for querying assessment data"
  - name: UC_ASSESSMENT_SCHEMA
    description: "Fully qualified schema (catalog.schema) for assessment tables"
    value: "my_catalog.uc_assessment"
```

---

## DEPLOYMENT NOTEBOOK (`deployment/deploy_app.py`)

This is the one-click setup experience consumers run after cloning:

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # UC Readiness Accelerator — Deployment
# MAGIC
# MAGIC Run this notebook to:
# MAGIC 1. Validate permissions
# MAGIC 2. Create the assessment schema
# MAGIC 3. Seed assessment rules
# MAGIC 4. Run the initial pipeline
# MAGIC 5. Deploy the Databricks App

# COMMAND ----------
# MAGIC %pip install databricks-sdk pyyaml

# COMMAND ----------
# Configuration — UPDATE THESE VALUES
TARGET_CATALOG = "my_catalog"          # Your catalog
TARGET_SCHEMA = "uc_assessment"        # Schema name
WAREHOUSE_ID = "your_warehouse_id"     # Your SQL Warehouse ID
APP_NAME = "uc-readiness-accelerator"  # App name (unique per workspace)

# COMMAND ----------
# Step 1: Validate permissions
spark.sql(f"USE CATALOG {TARGET_CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"Schema {TARGET_CATALOG}.{TARGET_SCHEMA} ready")

# COMMAND ----------
# Step 2: Seed assessment rules
# ... (INSERT INTO assessment_rules from CSV)

# COMMAND ----------
# Step 3: Run full pipeline (Bronze - Silver - Gold)
# ... (execute all pipeline SQL)

# COMMAND ----------
# Step 4: Deploy the Databricks App
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode
from datetime import timedelta

w = WorkspaceClient()

# Get the path to the app/ folder relative to this notebook
notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
base_path = "/Workspace" + notebook_path.rsplit("/", 2)[0] + "/app"

# Create the app
try:
    app = w.apps.create_and_wait(
        name=APP_NAME,
        description="UC Readiness Accelerator - Automated Unity Catalog governance assessment"
    )
except Exception as e:
    if "already exists" in str(e):
        print(f"App '{APP_NAME}' already exists, deploying update...")
    else:
        raise

# Deploy
deployment = w.apps.deploy(
    app_name=APP_NAME,
    app_deployment=AppDeployment(
        source_code_path=base_path,
        mode=AppDeploymentMode.SNAPSHOT
    )
)
result = deployment.result(timeout=timedelta(minutes=5))
print(f"App deployed! URL: https://{APP_NAME}-{w.config.host.split('//')[1]}")
```

---

## MARKETPLACE LISTING DETAILS

### Provider Registration

1. Navigate to **Marketplace** → **Provider Console**
2. Click **Create Listing**
3. Select listing type: **Solution Accelerator**

### Listing Fields

| Field | Value |
| --- | --- |
| **Title** | UC Readiness Accelerator (GovernIQ) |
| **Subtitle** | Automated Unity Catalog Governance Assessment and Remediation |
| **Category** | Data Governance / Data Management |
| **Git Repository URL** | `https://github.com/your-org/uc-readiness-accelerator` |
| **Provider** | SystechUSA |
| **Pricing** | Free / Open Source |
| **Tags** | Unity Catalog, Governance, Assessment, Genie Readiness, Data Quality |

### Listing Description

```
## UC Readiness Accelerator (GovernIQ)

Automated assessment dashboard that scores every table in your Unity Catalog
against enterprise governance standards across 5 dimensions:

- **Metadata Readiness** — Documentation, naming conventions, column descriptions
- **Governance** — Tags, access controls, managed table adoption
- **Data Quality** — Delta format, freshness, staleness detection
- **Performance** — Query patterns, DBU consumption, expensive queries
- **Genie Readiness** — AI-readiness scoring for Databricks Genie

### Features
- Executive Summary with RAG scoring (RED/AMBER/GREEN)
- Per-table detailed assessment with drill-down
- Prioritized recommendations with one-click remediation
- Excel Scorecard export (enterprise governance framework format)
- In-app pipeline refresh (no notebook switching required)
- ML Models, UC Functions, Volumes, and Compute assessment
- FinOps Insights with DBU consumption analysis

### Deployment
1. Clone this repository into your workspace
2. Run the `deployment/deploy_app.py` notebook
3. Enter your catalog, schema, and warehouse ID
4. App deploys automatically with initial assessment

### Requirements
- Azure Databricks Premium/Enterprise with Unity Catalog
- SQL Warehouse (Serverless or Pro)
- Access to system.information_schema tables
```

### Sample Notebook

Include a **sample notebook** in the listing that shows:
- Sample output from the assessment pipeline
- Screenshot of the app dashboard
- Key metrics explanation

---

## GIT REPOSITORY SETUP

### Step 1: Create GitHub Repository

```bash
gh repo create systechusa/uc-readiness-accelerator --public \
  --description "Automated Unity Catalog Governance Assessment Dashboard"
```

### Step 2: Sanitize Code Before Publishing

Remove from `app.py` before publishing:
- Hardcoded warehouse IDs
- Workspace-specific paths
- Any credential references
- Internal catalog/schema names

Replace with environment variable reads:
```python
FULL_SCHEMA = os.getenv("UC_ASSESSMENT_SCHEMA", "catalog.uc_assessment")
```

### Step 3: Add CI/CD (Optional)

```yaml
# .github/workflows/validate.yml
name: Validate
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install ruff
      - run: ruff check app/app.py
```

---

## CONSUMER EXPERIENCE (End-to-End)

```
┌─────────────────────────────────────────────────────────┐
│  1. Consumer finds "UC Readiness Accelerator" on        │
│     Databricks Marketplace                              │
│                         |                               │
│  2. Clicks "Get" - Clones Git repo into workspace       │
│     as a Git folder                                     │
│                         |                               │
│  3. Opens deployment/deploy_app.py notebook             │
│     - Enters: catalog, schema, warehouse ID             │
│     - Clicks "Run All"                                  │
│                         |                               │
│  4. Notebook:                                           │
│     a) Creates schema                                   │
│     b) Seeds assessment rules                           │
│     c) Runs Bronze - Silver - Gold pipeline             │
│     d) Creates and deploys Databricks App               │
│                         |                               │
│  5. Consumer opens app URL - sees full assessment       │
│     dashboard with their own catalog data               │
│                         |                               │
│  6. (Optional) Schedule pipeline for recurring refresh  │
└─────────────────────────────────────────────────────────┘
```

---

## ALTERNATIVE: Private Exchange

If you want to share with specific customers (not public):

1. Create a **Private Exchange** in Provider Console
2. Invite specific organizations by Databricks account email
3. Listing visible only to exchange members
4. Useful for: internal team distribution, partner-only access, beta testing

---

## VERSIONING STRATEGY

| Version | Content | Marketplace Action |
| --- | --- | --- |
| v1.0 | Core 9 tabs, 5 dimensions, Excel export | Initial listing |
| v1.1 | In-app pipeline refresh, first-run setup | Update Git repo |
| v2.0 | Custom rules UI, multi-workspace support | New listing version |

Consumers who cloned the repo can `git pull` to get updates. The Marketplace listing itself links to the repo's main branch.

---

## CHECKLIST BEFORE PUBLISHING

- [ ] Remove all hardcoded workspace-specific values
- [ ] Parameterize catalog/schema/warehouse via environment variables
- [ ] Create `deployment/deploy_app.py` one-click setup notebook
- [ ] Add `README.md` with screenshots, prerequisites, architecture diagram
- [ ] Add `LICENSE` file (Apache 2.0 recommended)
- [ ] Test end-to-end deployment in a clean workspace
- [ ] Create Provider account on Databricks Marketplace
- [ ] Create Provider Profile (logo, description, website)
- [ ] Create listing with Git repository URL
- [ ] Add sample notebook with output previews
- [ ] Submit for Marketplace review (public listings require approval)
- [ ] Add thumbnail/icon for listing card

---

## TIMELINE ESTIMATE

| Task | Effort |
| --- | --- |
| Parameterize app.py (remove hardcoding) | 2-3 hours |
| Create deployment notebook | 2-3 hours |
| Structure Git repository | 1-2 hours |
| Write README + SETUP docs | 2-3 hours |
| Test clean-room deployment | 2-3 hours |
| Marketplace Provider signup + profile | 1 hour |
| Create listing + submit for review | 1 hour |
| **Total** | **\~2 days** |

---

## REFERENCES

- [Databricks Marketplace Overview](https://learn.microsoft.com/en-us/azure/databricks/marketplace/)
- [Become a Marketplace Provider](https://learn.microsoft.com/en-us/azure/databricks/marketplace/become-a-provider/)
- [Create a Marketplace Listing](https://learn.microsoft.com/en-us/azure/databricks/marketplace/create-listing/)
- [Solution Accelerators on Marketplace](https://learn.microsoft.com/en-us/azure/databricks/marketplace/get-started-consumer/)
- [Databricks Apps Documentation](https://learn.microsoft.com/en-us/azure/databricks/apps/)
