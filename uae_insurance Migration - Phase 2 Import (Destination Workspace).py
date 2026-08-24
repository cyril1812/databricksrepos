# Databricks notebook source
# DBTITLE 1,Overview
# MAGIC %md
# MAGIC # uae_insurance Catalog — Phase 2: Import from External Storage
# MAGIC ### Run this notebook on the **Destination Workspace**
# MAGIC
# MAGIC **What it does:**
# MAGIC - Creates the target catalog and schema
# MAGIC - DEEP CLONEs all 66 tables from the shared ADLS export path into the new catalog
# MAGIC - Recreates views using DDLs saved during Phase 1
# MAGIC - Validates row counts between export and destination
# MAGIC
# MAGIC **Pre-requisites:**
# MAGIC - Phase 1 must have completed successfully
# MAGIC - The ADLS export path must be registered as an **External Location** in the destination metastore with read access
# MAGIC - Cluster with Standard or Dedicated access mode (Unity Catalog enabled)

# COMMAND ----------

# DBTITLE 1,Configuration
# ── Configuration ──────────────────────────────────────────────────────────────
TARGET_CATALOG   = "uae_insurance"
TARGET_SCHEMA    = "uae_silver"
IMPORT_BASE_PATH = "abfss://amhfilescontainer@amhaslfiles.dfs.core.windows.net/migration/uae_insurance/uae_silver"

VIEWS = [
    "v_claims_analysis",
    "v_fraud_investigation_detail",
]

ALL_TABLES = [
    "audit", "audit_metrics", "balance_sheet_metrics", "billing_usage_metrics",
    "claim", "claim_document_chunks", "claim_document_chunks_hierarchy",
    "claim_documents_index", "claim_documents_parsed", "claim_payment_metrics",
    "claimpayment", "claims_metrics", "claims_rag_agent_hierarchy_payload",
    "claims_rag_agent_payload", "compute_clusters_metrics", "compute_node_metrics",
    "dim_account", "dim_agent", "dim_claim", "dim_customer", "dim_date",
    "dim_employee", "dim_policy", "dim_product", "endpoint_usage_metrics",
    "fact_balance_sheet", "fact_claim", "fact_claim_payment", "fact_financial",
    "fact_fraud_investigation", "fact_investment", "fact_litigation", "fact_policy",
    "fact_premium", "fact_sales_funnel", "financial_metrics", "fraud_ai_results",
    "fraud_investigation", "fraud_investigation_metrics", "investment_metrics",
    "job_runs_metrics", "jobs_metrics", "list_prices_metrics", "litigation_metrics",
    "lookup_business_line", "lookup_claim_status", "lookup_claim_type",
    "lookup_currency", "lookup_customer_type", "lookup_emirates",
    "lookup_lead_source", "lookup_payment_method", "lookup_policy_status",
    "lookup_regulator", "lookup_risk_rating", "lookup_sales_channel",
    "lookup_time_periods",
    "policy_doc_raw_text", "policy_docs_chunks_table",
    "workspace_mapping",
]

# Metric views (21)
METRIC_VIEWS = [
    "audit_metrics", "balance_sheet_metrics", "billing_usage_metrics",
    "claim_payment_metrics", "claims_metrics", "compute_clusters_metrics",
    "compute_node_metrics", "endpoint_usage_metrics", "financial_metrics",
    "fraud_investigation_metrics", "investment_metrics", "job_runs_metrics",
    "jobs_metrics", "list_prices_metrics", "litigation_metrics",
    "policy_metrics", "premium_metrics", "query_history_metrics",
    "sales_funnel_metrics", "table_lineage_metrics", "warehouse_events_metrics",
]

# UC Functions (2)
FUNCTIONS = [
    "ask_claims_agent",
    "ask_claims_agent_hierarchy",
]

# UC Volumes (2)
VOLUMES = [
    "call_audio",
    "claim_documents",
]

print(f"Target          : {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"Import path     : {IMPORT_BASE_PATH}")
print(f"Tables          : {len(ALL_TABLES)}")
print(f"Views           : {len(VIEWS)}")
print(f"Metric views    : {len(METRIC_VIEWS)}")
print(f"Functions       : {len(FUNCTIONS)}")
print(f"Volumes         : {len(VOLUMES)}")

# COMMAND ----------

# DBTITLE 1,Step 1 - Create Catalog and Schema
# ── Step 1: Create Catalog and Schema ──────────────────────────────────────────
spark.sql(f"CREATE CATALOG IF NOT EXISTS {TARGET_CATALOG}")
print(f"\u2713  Catalog '{TARGET_CATALOG}' ready")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"\u2713  Schema '{TARGET_CATALOG}.{TARGET_SCHEMA}' ready")

# COMMAND ----------

# DBTITLE 1,Step 2 - DEEP CLONE Tables from Export Path
# ── Step 2: DEEP CLONE Tables from Export Path ─────────────────────────────────
succeeded = []
failed    = []

for i, table in enumerate(ALL_TABLES, 1):
    src_path = f"{IMPORT_BASE_PATH}/{table}"
    dest     = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{table}"
    try:
        spark.sql(f"CREATE OR REPLACE TABLE {dest} DEEP CLONE delta.`{src_path}`")
        succeeded.append(table)
        print(f"[{i:02d}/{len(ALL_TABLES)}] \u2713  {table}")
    except Exception as e:
        failed.append({"table": table, "error": str(e)})
        print(f"[{i:02d}/{len(ALL_TABLES)}] \u2717  {table}  \u2192  {e}")

print(f"\n{'\u2500'*60}")
print(f"Succeeded : {len(succeeded)} / {len(ALL_TABLES)}")
print(f"Failed    : {len(failed)}")
if failed:
    print("\nFailed tables:")
    for f in failed:
        print(f"  \u2022 {f['table']}: {f['error']}")

# COMMAND ----------

# DBTITLE 1,Step 3 - Create Volumes and Import Files
# ── Step 3: Create Volumes and Import Files ─────────────────────────────────
# Create managed volumes in the destination, then copy files from the export path
for volume in VOLUMES:
    src_path  = f"{IMPORT_BASE_PATH}/_volumes/{volume}"
    dest_path = f"/Volumes/{TARGET_CATALOG}/{TARGET_SCHEMA}/{volume}"
    try:
        # Create the managed volume
        spark.sql(f"CREATE VOLUME IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}.{volume}")
        print(f"\u2713  Volume created : {volume}")
        # Copy files from export path into the new volume
        dbutils.fs.cp(src_path, dest_path, recurse=True)
        file_count = len(dbutils.fs.ls(dest_path))
        print(f"\u2713  Files imported : {volume} — {file_count} file(s)")
    except Exception as e:
        print(f"\u2717  {volume}  \u2192  {e}")

# COMMAND ----------

# DBTITLE 1,Step 3 - Recreate Views
# ── Step 4: Recreate Views, Metric Views, and Functions ───────────────────────
# Load all DDLs saved during Phase 1
try:
    ddl_rows = spark.read.parquet(f"{IMPORT_BASE_PATH}/_metadata/ddls").collect()
except Exception as e:
    raise Exception(
        f"Could not load DDLs from export path. Ensure Phase 1 completed successfully.\n{e}"
    )

# Recreate in dependency order: views first, then metric views, then functions
for obj_type in ["view", "metric_view", "function"]:
    objects = [r for r in ddl_rows if r.object_type == obj_type]
    if not objects:
        continue
    print(f"\n--- {obj_type.replace('_', ' ').title()}s ({len(objects)}) ---")
    for row in objects:
        # Replace all source catalog/schema references with the target
        # Covers both the CREATE statement header and YAML body references
        ddl = (
            row.ddl
            .replace("uae_insurance.uae_silver", f"{TARGET_CATALOG}.{TARGET_SCHEMA}")
            .replace("salama_insurance.salama_silver", f"{TARGET_CATALOG}.{TARGET_SCHEMA}")
        )
        try:
            spark.sql(ddl)
            print(f"  \u2713  {row.name}")
        except Exception as e:
            print(f"  \u2717  {row.name}  \u2192  {e}")

print("\n" + "\u2500" * 60)
print("\u26a0  Note: Functions ask_claims_agent and ask_claims_agent_hierarchy")
print("   reference serving endpoints 'claims_rag_agent' and 'claims_rag_agent_hierarchy'.")
print("   Ensure those endpoints are deployed in the destination workspace before use.")

# COMMAND ----------

# DBTITLE 1,Step 4 - Validate Row Counts
# ── Step 4: Validate Row Counts ────────────────────────────────────────────────
print("Verifying imported table counts vs export...\n")
mismatches = []

for table in succeeded:
    src_count = spark.read.format("delta").load(f"{IMPORT_BASE_PATH}/{table}").count()
    dst_count = spark.table(f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{table}").count()
    status = "\u2713" if src_count == dst_count else "\u2717 MISMATCH"
    if src_count != dst_count:
        mismatches.append({"table": table, "export": src_count, "imported": dst_count})
    print(f"{status}  {table}: {dst_count:,} rows")

print(f"\n{'\u2500'*60}")
print(f"Checked    : {len(succeeded)} tables")
print(f"Mismatches : {len(mismatches)}")
if mismatches:
    print("\nMismatched tables:")
    for m in mismatches:
        print(f"  \u2022 {m['table']}: export={m['export']:,}  imported={m['imported']:,}")
else:
    print("\nAll row counts match. Import complete \u2713")

# Verify views
print("\nViews:")
for view in VIEWS:
    try:
        count = spark.table(f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{view}").count()
        print(f"\u2713  {view}: {count:,} rows")
    except Exception as e:
        print(f"\u2717  {view}: {e}")
