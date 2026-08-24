# Databricks notebook source
# DBTITLE 1,Configuration & Parameters
# === UC Readiness Accelerator - Configuration ===
TARGET_CATALOG = "governiq"
TARGET_SCHEMA = "uc_assessment"
FULL_SCHEMA = f"{TARGET_CATALOG}.{TARGET_SCHEMA}"
DATE_RANGE_DAYS = 30

print("=" * 60)
print("UC Readiness Accelerator - Configuration")
print("=" * 60)
print(f"  Target Catalog : {TARGET_CATALOG}")
print(f"  Target Schema  : {TARGET_SCHEMA}")
print(f"  Full Schema    : {FULL_SCHEMA}")
print(f"  Date Range     : Last {DATE_RANGE_DAYS} days")
print("=" * 60)

# Ensure schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FULL_SCHEMA}")
print(f"\n✅ Schema {FULL_SCHEMA} is ready.")

# COMMAND ----------

# DBTITLE 1,Bronze Layer - System Table Ingestion
# === Bronze Layer - Ingest from System Tables ===
bronze_sources = {
    "bronze_tables": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_tables AS
        SELECT * FROM system.information_schema.tables
        WHERE table_schema != 'information_schema'
    """,
    "bronze_columns": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_columns AS
        SELECT * FROM system.information_schema.columns
        WHERE table_schema != 'information_schema'
    """,
    "bronze_table_tags": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_tags AS
        SELECT * FROM system.information_schema.table_tags
    """,
    "bronze_column_tags": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_column_tags AS
        SELECT * FROM system.information_schema.column_tags
    """,
    "bronze_table_privileges": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_privileges AS
        SELECT * FROM system.information_schema.table_privileges
    """,
    "bronze_billing_usage": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_billing_usage AS
        SELECT * FROM system.billing.usage
        WHERE usage_date >= current_date() - INTERVAL {DATE_RANGE_DAYS} DAYS
    """,
    "bronze_query_history": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_query_history AS
        SELECT * FROM system.query.history
        WHERE start_time >= current_date() - INTERVAL {DATE_RANGE_DAYS} DAYS
    """,
    "bronze_table_lineage": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_table_lineage AS
        SELECT * FROM system.access.table_lineage
        WHERE event_date >= current_date() - INTERVAL {DATE_RANGE_DAYS} DAYS
    """
}

print("=" * 60)
print("BRONZE LAYER - System Table Ingestion")
print("=" * 60)

for tbl_name, sql in bronze_sources.items():
    try:
        spark.sql(sql)
        cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.{tbl_name}").collect()[0]["cnt"]
        print(f"  ✅ {tbl_name}: {cnt:,} rows")
    except Exception as e:
        print(f"  ❌ {tbl_name}: FAILED - {str(e)[:150]}")

print("=" * 60)
print("Bronze layer ingestion complete.")

# COMMAND ----------

# DBTITLE 1,Bronze Layer - Functions, Models & Volumes
# === Bronze Layer - UC Functions, ML Models & Volumes ===
from datetime import datetime

print("=" * 60)
print("BRONZE LAYER - Functions, Models & Volumes")
print("=" * 60)

# --- 1. UC Functions (from system.information_schema.routines) ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_routines AS
        SELECT
            routine_catalog,
            routine_schema,
            routine_name,
            routine_type,
            routine_owner,
            data_type,
            full_data_type,
            routine_body,
            routine_definition,
            external_language,
            is_deterministic,
            sql_data_access,
            is_null_call,
            security_type,
            comment,
            created,
            created_by,
            last_altered,
            last_altered_by
        FROM system.information_schema.routines
        WHERE routine_schema != 'information_schema'
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_routines").collect()[0]["cnt"]
    print(f"  ✅ bronze_routines: {cnt:,} UC functions ingested")
except Exception as e:
    print(f"  ❌ bronze_routines: FAILED - {str(e)[:150]}")

# --- 2. Volumes (from system.information_schema.volumes) ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_volumes AS
        SELECT
            volume_catalog,
            volume_schema,
            volume_name,
            volume_type,
            volume_owner,
            comment,
            storage_location,
            created,
            created_by,
            last_altered,
            last_altered_by
        FROM system.information_schema.volumes
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_volumes").collect()[0]["cnt"]
    print(f"  ✅ bronze_volumes: {cnt:,} volumes ingested")
except Exception as e:
    print(f"  ❌ bronze_volumes: FAILED - {str(e)[:150]}")

# --- 3. ML Models (from UC Registry via REST API) ---
try:
    import requests
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    host = ctx.apiUrl().get()
    token = ctx.apiToken().get()
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Get all registered models
    all_models = []
    next_token = None
    while True:
        params = {"max_results": 100}
        if next_token:
            params["page_token"] = next_token
        resp = requests.get(f"{host}/api/2.0/mlflow/unity-catalog/registered-models/search",
                           headers=headers, params=params)
        if resp.status_code != 200:
            raise Exception(f"API returned {resp.status_code}: {resp.text[:100]}")
        data = resp.json()
        all_models.extend(data.get("registered_models", []))
        next_token = data.get("next_page_token")
        if not next_token:
            break

    # Step 2: For each model, get version info via model-versions/search
    models_data = []
    for rm in all_models:
        full_name = rm.get("name", "")
        parts = full_name.split(".")
        model_catalog = parts[0] if len(parts) >= 3 else "default"
        model_schema = parts[1] if len(parts) >= 3 else "default"
        model_name = parts[-1]

        # Get latest version for this model
        latest_version = 0
        latest_status = "UNKNOWN"
        try:
            vresp = requests.get(
                f"{host}/api/2.0/mlflow/unity-catalog/model-versions/search",
                headers=headers,
                params={"filter": f"name='{full_name}'", "max_results": 1, "order_by": "version_number DESC"}
            )
            if vresp.status_code == 200:
                versions = vresp.json().get("model_versions", [])
                if versions:
                    latest_version = int(versions[0].get("version", 0))
                    latest_status = versions[0].get("status", "UNKNOWN")
        except:
            pass

        models_data.append({
            "full_name": full_name,
            "model_catalog": model_catalog,
            "model_schema": model_schema,
            "model_name": model_name,
            "description": rm.get("description", ""),
            "creation_timestamp": rm.get("creation_timestamp", 0),
            "last_updated_timestamp": rm.get("last_updated_timestamp", 0),
            "latest_version": latest_version,
            "latest_status": latest_status,
            "tags": str({t["key"]: t["value"] for t in rm.get("tags", [])})
        })

    next_token = None  # reset

    if models_data:
        df_models = spark.createDataFrame(models_data)
        df_models.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.bronze_registered_models")
        cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_registered_models").collect()[0]["cnt"]
        print(f"  ✅ bronze_registered_models: {cnt:,} models ingested")
    else:
        spark.sql(f"""
            CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_registered_models (
                full_name STRING, model_catalog STRING, model_schema STRING,
                model_name STRING, description STRING, creation_timestamp LONG,
                last_updated_timestamp LONG, latest_version INT,
                latest_status STRING, tags STRING
            )
        """)
        print("  ⚠️ bronze_registered_models: 0 models found (empty table created)")
except Exception as e:
    # Fallback: create empty table so downstream cells don't fail
    try:
        spark.sql(f"""
            CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_registered_models (
                full_name STRING, model_catalog STRING, model_schema STRING,
                model_name STRING, description STRING, creation_timestamp LONG,
                last_updated_timestamp LONG, latest_version INT,
                latest_status STRING, tags STRING
            )
        """)
    except: pass
    print(f"  ❌ bronze_registered_models: FAILED - {str(e)[:150]}")
    print("     (empty table created as fallback)")

print("=" * 60)
print("Bronze extended layer complete.")

# COMMAND ----------

# DBTITLE 1,Bronze Layer - Clusters & SQL Warehouses
# === Bronze Layer - Clusters & SQL Warehouses ===
# Filter to current workspace only (system.compute tables are account-level)
import requests
_ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
WORKSPACE_ID = _ctx.workspaceId().get()
print(f"Current Workspace ID: {WORKSPACE_ID}")

print("=" * 60)
print("BRONZE LAYER - Clusters & SQL Warehouses")
print("=" * 60)

# --- 1. Interactive Clusters (current workspace, excludes ephemeral job/pipeline and soft-deleted clusters) ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_clusters AS
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY cluster_id ORDER BY change_time DESC) AS rn
            FROM system.compute.clusters
            WHERE cluster_source IN ('UI', 'API')
              AND workspace_id = '{WORKSPACE_ID}'
        )
        SELECT
            account_id, workspace_id, cluster_id, cluster_name, owned_by,
            create_time, driver_node_type, worker_node_type,
            worker_count, min_autoscale_workers, max_autoscale_workers,
            auto_termination_minutes, enable_elastic_disk,
            tags, cluster_source, dbr_version,
            data_security_mode, policy_id, change_time
        FROM ranked
        WHERE rn = 1 AND delete_time IS NULL
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_clusters").collect()[0]["cnt"]
    print(f"  \u2705 bronze_clusters: {cnt:,} active interactive clusters ingested")
except Exception as e:
    print(f"  \u274c bronze_clusters: FAILED - {str(e)[:150]}")

# --- 2. SQL Warehouses (current workspace, excludes soft-deleted) ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.bronze_warehouses AS
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) AS rn
            FROM system.compute.warehouses
            WHERE workspace_id = '{WORKSPACE_ID}'
        )
        SELECT
            warehouse_id, workspace_id, account_id, warehouse_name,
            warehouse_type, warehouse_channel, warehouse_size,
            min_clusters, max_clusters, auto_stop_minutes,
            tags, change_time, created_by
        FROM ranked
        WHERE rn = 1 AND delete_time IS NULL
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_warehouses").collect()[0]["cnt"]
    print(f"  \u2705 bronze_warehouses: {cnt:,} active SQL warehouses ingested")
except Exception as e:
    print(f"  \u274c bronze_warehouses: FAILED - {str(e)[:150]}")

print("=" * 60)
print("Bronze compute layer complete.")

# COMMAND ----------

# DBTITLE 1,Bronze Layer - ABAC Policy Inventory
# === Bronze Layer - ABAC Policy Inventory ===
from datetime import datetime, timezone
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

print("=" * 60)
print("BRONZE LAYER - ABAC Policy Inventory")
print("=" * 60)

try:
    def quote_ident(value):
        return "`" + str(value).replace("`", "``") + "`"

    def fq_name(*parts):
        return ".".join(quote_ident(part) for part in parts if part is not None and part != "")

    source_tables = spark.sql(f"""
        SELECT DISTINCT table_catalog, table_schema, table_name
        FROM {FULL_SCHEMA}.bronze_tables
        WHERE table_schema != 'information_schema'
        ORDER BY table_catalog, table_schema, table_name
    """).collect()

    print(f"Scanning effective ABAC policies across {len(source_tables):,} tables...")

    policy_rows = []
    coverage_rows = []
    scan_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    for idx, row in enumerate(source_tables, start=1):
        table_catalog = row["table_catalog"]
        table_schema = row["table_schema"]
        table_name = row["table_name"]

        try:
            effective_rows = spark.sql(
                f"SHOW EFFECTIVE POLICIES ON TABLE {fq_name(table_catalog, table_schema, table_name)}"
            ).collect()

            row_filter_count = sum(1 for policy_row in effective_rows if str(policy_row["Policy Type"]).upper() == "ROW FILTER")
            column_mask_count = sum(1 for policy_row in effective_rows if str(policy_row["Policy Type"]).upper() == "COLUMN MASK")
            abac_policy_count = row_filter_count + column_mask_count

            coverage_rows.append((
                table_catalog,
                table_schema,
                table_name,
                abac_policy_count,
                row_filter_count,
                column_mask_count,
                1 if column_mask_count > 0 else 0,
                1 if row_filter_count > 0 else 0,
                "SCANNED",
                None,
                scan_ts
            ))

            for policy_row in effective_rows:
                policy_dict = policy_row.asDict()
                policy_type = str(policy_dict.get("Policy Type") or "").upper()

                if policy_type in ("ROW FILTER", "COLUMN MASK"):
                    policy_rows.append((
                        table_catalog,
                        table_schema,
                        table_name,
                        policy_dict.get("Policy Name"),
                        policy_type,
                        policy_dict.get("Catalog"),
                        policy_dict.get("Schema"),
                        policy_dict.get("Table"),
                        policy_dict.get("Comment"),
                        scan_ts
                    ))
        except Exception as table_error:
            error_text = str(table_error)[:500]
            inventory_status = "UNSUPPORTED"
            if "SAMPLE_TABLE_PERMISSIONS" not in error_text:
                inventory_status = "ERROR"

            coverage_rows.append((
                table_catalog,
                table_schema,
                table_name,
                None,
                None,
                None,
                0,
                0,
                inventory_status,
                error_text,
                scan_ts
            ))

        if idx % 100 == 0 or idx == len(source_tables):
            print(f"  Processed {idx:,} / {len(source_tables):,} tables")

    coverage_schema = StructType([
        StructField("table_catalog", StringType(), False),
        StructField("table_schema", StringType(), False),
        StructField("table_name", StringType(), False),
        StructField("effective_policy_count", IntegerType(), True),
        StructField("row_filter_policy_count", IntegerType(), True),
        StructField("column_mask_policy_count", IntegerType(), True),
        StructField("abac_mask_policy_present", IntegerType(), False),
        StructField("abac_row_filter_policy_present", IntegerType(), False),
        StructField("inventory_status", StringType(), False),
        StructField("error_message", StringType(), True),
        StructField("inventoried_at", TimestampType(), False)
    ])

    policies_schema = StructType([
        StructField("table_catalog", StringType(), False),
        StructField("table_schema", StringType(), False),
        StructField("table_name", StringType(), False),
        StructField("policy_name", StringType(), True),
        StructField("policy_type", StringType(), True),
        StructField("policy_catalog", StringType(), True),
        StructField("policy_schema", StringType(), True),
        StructField("policy_table", StringType(), True),
        StructField("policy_comment", StringType(), True),
        StructField("inventoried_at", TimestampType(), False)
    ])

    coverage_df = spark.createDataFrame(coverage_rows, coverage_schema)
    coverage_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.bronze_abac_policy_coverage")

    if policy_rows:
        policies_df = spark.createDataFrame(policy_rows, policies_schema)
    else:
        policies_df = spark.createDataFrame([], policies_schema)

    policies_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.bronze_abac_effective_policies")

    coverage_cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_abac_policy_coverage").collect()[0]["cnt"]
    policy_cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.bronze_abac_effective_policies").collect()[0]["cnt"]

    print(f"✅ bronze_abac_policy_coverage: {coverage_cnt:,} tables inventoried")
    print(f"✅ bronze_abac_effective_policies: {policy_cnt:,} ABAC policy associations captured")

    display(spark.sql(f"""
        SELECT
            inventory_status,
            COUNT(*) AS table_count,
            SUM(COALESCE(effective_policy_count, 0)) AS effective_policy_count,
            SUM(COALESCE(row_filter_policy_count, 0)) AS row_filter_policy_count,
            SUM(COALESCE(column_mask_policy_count, 0)) AS column_mask_policy_count
        FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
        GROUP BY inventory_status
        ORDER BY CASE inventory_status WHEN 'SCANNED' THEN 1 WHEN 'UNSUPPORTED' THEN 2 ELSE 3 END, inventory_status
    """))
except Exception as e:
    print(f"❌ ABAC policy inventory: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Governance Assessment
# === ABAC Inventory Diagnostics ===
try:
    print("=" * 60)
    print("ABAC INVENTORY DIAGNOSTICS")
    print("=" * 60)

    error_summary = spark.sql(f"""
        SELECT
            inventory_status,
            COUNT(*) AS table_count,
            SUM(CASE WHEN error_message IS NOT NULL AND error_message != '' THEN 1 ELSE 0 END) AS tables_with_errors
        FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
        GROUP BY inventory_status
        ORDER BY inventory_status
    """)
    display(error_summary)

    error_samples = spark.sql(f"""
        SELECT
            table_catalog,
            table_schema,
            table_name,
            SUBSTRING(error_message, 1, 250) AS error_message
        FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
        WHERE inventory_status = 'ERROR'
        ORDER BY table_catalog, table_schema, table_name
        LIMIT 20
    """)
    display(error_samples)
except Exception as e:
    print(f"❌ ABAC diagnostics: FAILED - {e}")


# COMMAND ----------

# DBTITLE 1,Assessment Rules Engine
# === Assessment Rules Engine ===
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.assessment_rules (
            rule_id STRING,
            category STRING,
            rule_name STRING,
            description STRING,
            weight INT,
            severity STRING,
            enabled BOOLEAN,
            formula STRING,
            threshold STRING
        )
    """)

    spark.sql(f"""
        INSERT OVERWRITE {FULL_SCHEMA}.assessment_rules VALUES
        ('META_001', 'Metadata Readiness', 'Table Description Present', 'Check if table has a description/comment', 10, 'HIGH', TRUE, 'CASE WHEN has_table_description = 1 THEN 1 ELSE 0 END', NULL),
        ('META_002', 'Metadata Readiness', 'Column Descriptions Present', 'Check percentage of columns with descriptions', 15, 'HIGH', TRUE, 'CASE WHEN column_doc_pct >= 80 THEN 1 ELSE 0 END', '80'),
        ('META_003', 'Metadata Readiness', 'Naming Convention Compliance', 'Check if table follows lowercase snake_case naming', 5, 'MEDIUM', TRUE, "CASE WHEN table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END", NULL),
        ('GOV_001', 'Governance', 'Table Has Tags', 'Check if table has governance tags applied', 10, 'MEDIUM', TRUE, 'CASE WHEN tag_count > 0 THEN 1 ELSE 0 END', NULL),
        ('GOV_002', 'Governance', 'Access Controls Defined', 'Check if explicit privileges are granted', 15, 'HIGH', TRUE, 'CASE WHEN grant_count > 0 THEN 1 ELSE 0 END', NULL),
        ('GOV_003', 'Governance', 'Over-Permissioning Check', 'Flag tables with ALL PRIVILEGES granted', 10, 'HIGH', TRUE, 'CASE WHEN over_permissioned_grants = 0 THEN 1 ELSE 0 END', NULL),
        ('GOV_004', 'Governance', 'Managed vs External Tables', 'Check if tables are Unity Catalog managed rather than external or foreign. Managed tables provide better governance, lineage tracking, and lifecycle management.', 10, 'MEDIUM', TRUE, "CASE WHEN table_type = 'MANAGED' THEN 1 ELSE 0 END", NULL),
        ('DQ_001', 'Data Quality', 'Freshness Check', 'Check if table was modified within 30 days', 10, 'MEDIUM', TRUE, 'CASE WHEN DATEDIFF(current_date(), last_altered) <= 30 THEN 1 ELSE 0 END', '30'),
        ('DQ_002', 'Data Quality', 'Delta Format', 'Check if table uses Delta format', 5, 'LOW', TRUE, "CASE WHEN data_source_format = 'DELTA' THEN 1 ELSE 0 END", NULL),
        ('PERF_001', 'Performance', 'Table Format is Delta', 'Delta enables OPTIMIZE and Z-ORDER', 10, 'MEDIUM', TRUE, "CASE WHEN data_source_format = 'DELTA' THEN 1 ELSE 0 END", NULL),
        ('PERF_002', 'Performance', 'Query Performance', 'Assess avg query duration by statement type', 10, 'MEDIUM', TRUE, 'CASE WHEN avg_duration_ms < 5000 THEN 1 ELSE 0 END', '5000'),
        ('GENIE_001', 'Genie Readiness', 'Business-Friendly Naming', 'No numeric suffixes or cryptic abbreviations', 10, 'MEDIUM', TRUE, 'CASE WHEN naming_compliant = 1 THEN 1 ELSE 0 END', NULL),
        ('GENIE_002', 'Genie Readiness', 'Has Relationships', 'Table has lineage connections', 10, 'MEDIUM', TRUE, 'CASE WHEN lineage_count > 0 THEN 1 ELSE 0 END', NULL),
        ('GENIE_003', 'Genie Readiness', 'Column Documentation >=80pct', 'At least 80 pct of columns documented', 15, 'HIGH', TRUE, 'CASE WHEN column_doc_pct >= 80 THEN 1 ELSE 0 END', '80'),
        ('COMP_001', 'Compliance', 'Regulated Data Tagged', 'Starter control for HIPAA, PCI DSS, GDPR, CCPA/CPRA, FERPA, and GLBA. Check that regulated assets have at least one governance or sensitivity tag.', 15, 'HIGH', TRUE, 'CASE WHEN tag_count > 0 THEN 1 ELSE 0 END', 'frameworks=HIPAA|HITECH|PCI DSS|GDPR|CCPA|CPRA|FERPA|GLBA'),
        ('COMP_002', 'Compliance', 'Least Privilege Access', 'Starter control for HIPAA, PCI DSS, SOX, GLBA, FedRAMP, FISMA, NIST, and FERPA. Check that explicit access is defined for the asset.', 15, 'HIGH', TRUE, 'CASE WHEN grant_count > 0 THEN 1 ELSE 0 END', 'frameworks=HIPAA|PCI DSS|SOX|GLBA|FedRAMP|FISMA|NIST|FERPA'),
        ('COMP_003', 'Compliance', 'No Broad Grants', 'Starter control for PCI DSS, HIPAA, GLBA, SOX, FedRAMP, and NIST. Fail assets with broad or ALL PRIVILEGES grants.', 15, 'HIGH', TRUE, 'CASE WHEN over_permissioned_grants = 0 THEN 1 ELSE 0 END', 'frameworks=PCI DSS|HIPAA|GLBA|SOX|FedRAMP|NIST'),
        ('COMP_004', 'Compliance', 'Regulated Data Documentation', 'Starter control for GDPR, HIPAA, FERPA, and FISMA. Require documented tables and strong column documentation for regulated assets.', 10, 'MEDIUM', TRUE, 'CASE WHEN has_table_description = 1 AND column_doc_pct >= 80 THEN 1 ELSE 0 END', 'min_doc_pct=80;frameworks=GDPR|HIPAA|FERPA|FISMA'),
        ('COMP_005', 'Compliance', 'Lineage Traceability', 'Starter control for GDPR, SOX, FedRAMP, FISMA, and NIST. Require upstream or downstream lineage for auditable data movement.', 10, 'MEDIUM', TRUE, 'CASE WHEN lineage_count > 0 THEN 1 ELSE 0 END', 'frameworks=GDPR|SOX|FedRAMP|FISMA|NIST'),
        ('COMP_006', 'Compliance', 'Controlled Data Zone Naming', 'Starter control for HIPAA, PCI DSS, GDPR, FERPA, and CCPA/CPRA. Use schema or table naming patterns to identify regulated zones consistently.', 5, 'LOW', TRUE, "CASE WHEN table_schema RLIKE '(pci|hipaa|phi|pii|gdpr|ferpa|sox|glba|fedramp|fisma|nist|ccpa|cpra)' OR table_name RLIKE '(pci|hipaa|phi|pii|gdpr|ferpa|sox|glba|fedramp|fisma|nist|ccpa|cpra)' THEN 1 ELSE 0 END", 'schemas=(pci|hipaa|phi|pii|gdpr|ferpa|sox|glba|fedramp|fisma|nist|ccpa|cpra)'),
        ('COMP_007', 'Compliance', 'Managed Delta Preference', 'Starter control for PCI DSS, HIPAA, GLBA, and NIST. Prefer managed Delta assets for stronger governance and auditability.', 10, 'MEDIUM', TRUE, "CASE WHEN table_type = 'MANAGED' AND data_source_format = 'DELTA' THEN 1 ELSE 0 END", 'frameworks=PCI DSS|HIPAA|GLBA|NIST'),
        ('COMP_008', 'Compliance', 'Freshness Monitoring', 'Starter control for SOX, GLBA, FedRAMP, FISMA, and NIST. Require recently refreshed data for operational and reporting trust.', 10, 'MEDIUM', TRUE, 'CASE WHEN DATEDIFF(current_date(), last_altered) <= 30 THEN 1 ELSE 0 END', 'max_age_days=30;frameworks=SOX|GLBA|FedRAMP|FISMA|NIST'),
        ('COMP_009', 'Compliance', 'ABAC Column Mask Coverage', 'Databricks-native ABAC control for column mask coverage. Assets marked UNSUPPORTED in ABAC inventory are treated as not applicable so they do not reduce cloud-agnostic scoring.', 10, 'MEDIUM', TRUE, "CASE WHEN abac_policy_inventory_status = 'UNSUPPORTED' THEN 1 WHEN abac_mask_policy_present = 1 THEN 1 ELSE 0 END", 'policy_type=column_mask;unsupported=not_applicable'),
        ('COMP_010', 'Compliance', 'ABAC Row Filter Coverage', 'Databricks-native ABAC control for row filter coverage. Assets marked UNSUPPORTED in ABAC inventory are treated as not applicable so they do not reduce cloud-agnostic scoring.', 10, 'MEDIUM', TRUE, "CASE WHEN abac_policy_inventory_status = 'UNSUPPORTED' THEN 1 WHEN abac_row_filter_policy_present = 1 THEN 1 ELSE 0 END", 'policy_type=row_filter;unsupported=not_applicable'),
        ('FN_001', 'Functions', 'Function Description Present', 'Check if UC function has a description/comment', 10, 'HIGH', TRUE, "CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END", NULL),
        ('FN_002', 'Functions', 'Function Naming Convention', 'Check if function follows lowercase snake_case naming', 5, 'MEDIUM', TRUE, "CASE WHEN function_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END", NULL),
        ('FN_003', 'Functions', 'Function Security Mode', 'Check if function uses DEFINER security type', 10, 'MEDIUM', TRUE, "CASE WHEN security_type = 'DEFINER' THEN 1 ELSE 0 END", NULL),
        ('ML_001', 'ML Models', 'Model Description Present', 'Check if registered model has a description', 10, 'HIGH', TRUE, 'CASE WHEN has_description = 1 THEN 1 ELSE 0 END', NULL),
        ('ML_002', 'ML Models', 'Model Has Tags', 'Check if model has governance tags applied', 10, 'MEDIUM', TRUE, 'CASE WHEN has_tags = 1 THEN 1 ELSE 0 END', NULL),
        ('ML_003', 'ML Models', 'Model Has Versions', 'Check if model has at least one registered version', 5, 'HIGH', TRUE, 'CASE WHEN has_versions = 1 THEN 1 ELSE 0 END', NULL),
        ('VOL_001', 'Volumes', 'Volume Description Present', 'Check if volume has a description/comment', 10, 'MEDIUM', TRUE, "CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END", NULL),
        ('VOL_002', 'Volumes', 'Volume Naming Convention', 'Check if volume follows lowercase snake_case naming', 5, 'LOW', TRUE, "CASE WHEN volume_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END", NULL),
        ('CLU_001', 'Clusters', 'UC Security Mode Enabled', 'Check if cluster has Unity Catalog security mode', 15, 'HIGH', TRUE, 'CASE WHEN data_security_mode IS NOT NULL THEN 1 ELSE 0 END', NULL),
        ('CLU_002', 'Clusters', 'Current DBR Version', 'Check if cluster runs DBR 15+ for latest features', 10, 'MEDIUM', TRUE, "CASE WHEN dbr_version RLIKE '^(15|16|17)' THEN 1 ELSE 0 END", '15'),
        ('CLU_003', 'Clusters', 'Auto-Termination Configured', 'Check if cluster auto-terminates within 120 minutes', 10, 'HIGH', TRUE, 'CASE WHEN auto_termination_minutes <= 120 THEN 1 ELSE 0 END', '120'),
        ('CLU_004', 'Clusters', 'Cluster Policy Assigned', 'Check if cluster has a governance policy attached', 10, 'MEDIUM', TRUE, 'CASE WHEN has_cluster_policy = 1 THEN 1 ELSE 0 END', NULL),
        ('CLU_005', 'Clusters', 'Autoscaling Enabled', 'Check if interactive cluster has autoscaling', 5, 'MEDIUM', TRUE, 'CASE WHEN has_autoscaling = 1 THEN 1 ELSE 0 END', NULL),
        ('CLU_006', 'Clusters', 'Cluster Has Tags', 'Check if cluster has tags for cost attribution', 5, 'LOW', TRUE, 'CASE WHEN has_tags = 1 THEN 1 ELSE 0 END', NULL),
        ('WH_001', 'SQL Warehouses', 'Serverless Type', 'Check if warehouse is Serverless for optimal performance', 15, 'MEDIUM', TRUE, 'CASE WHEN is_serverless = 1 THEN 1 ELSE 0 END', NULL),
        ('WH_002', 'SQL Warehouses', 'Efficient Auto-Stop', 'Check if warehouse auto-stops within 15 minutes', 10, 'LOW', TRUE, 'CASE WHEN auto_stop_mins <= 15 THEN 1 ELSE 0 END', '15'),
        ('WH_003', 'SQL Warehouses', 'Warehouse Has Tags', 'Check if warehouse has tags for cost attribution', 5, 'LOW', TRUE, 'CASE WHEN has_tags = 1 THEN 1 ELSE 0 END', NULL)
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.assessment_rules").collect()[0]["cnt"]
    print(f"✅ assessment_rules: {cnt} rules loaded")
    display(spark.sql(f"SELECT * FROM {FULL_SCHEMA}.assessment_rules ORDER BY category, rule_id"))
except Exception as e:
    print(f"❌ assessment_rules: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Dynamic Rule Scoring Helpers
# === Dynamic Rule Scoring Helpers ===
def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def get_enabled_rules(categories):
    if isinstance(categories, str):
        categories = [categories]

    category_list = ", ".join(sql_literal(category) for category in categories)
    rules_df = spark.sql(f"""
        SELECT rule_id, category, weight, formula
        FROM {FULL_SCHEMA}.assessment_rules
        WHERE enabled = TRUE
          AND category IN ({category_list})
        ORDER BY category, rule_id
    """)

    return [
        row.asDict()
        for row in rules_df.collect()
        if row["weight"] is not None and int(row["weight"]) > 0 and row["formula"]
    ]


def build_weighted_score_expression(categories, alias, scale=5.0):
    rules = get_enabled_rules(categories)
    total_weight = sum(int(rule["weight"]) for rule in rules)

    if total_weight == 0:
        return f"CAST(0.0 AS DOUBLE) AS {alias}", total_weight

    weighted_terms = " + ".join(
        f"(({rule['formula']}) * {int(rule['weight'])})"
        for rule in rules
    )

    expression = f"ROUND((({weighted_terms}) * {float(scale)}) / {total_weight}, 2) AS {alias}"
    return expression, total_weight


# COMMAND ----------

# DBTITLE 1,Silver Layer - Metadata Readiness
# === Silver Layer - Metadata Readiness Assessment ===
try:
    metadata_score_expr, _ = build_weighted_score_expression('Metadata Readiness', 'metadata_score', 5.0)

    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_metadata_assessment AS
        WITH col_stats AS (
            SELECT
                table_catalog, table_schema, table_name,
                COUNT(*) AS total_columns,
                SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END) AS documented_columns
            FROM {FULL_SCHEMA}.bronze_columns
            GROUP BY table_catalog, table_schema, table_name
        ),
        base AS (
            SELECT
                t.table_catalog,
                t.table_schema,
                t.table_name,
                t.table_type,
                CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 1 ELSE 0 END AS has_table_description,
                COALESCE(c.total_columns, 0) AS total_columns,
                COALESCE(c.documented_columns, 0) AS documented_columns,
                ROUND(COALESCE(c.documented_columns * 100.0 / NULLIF(c.total_columns, 0), 0), 2) AS column_doc_pct,
                CASE WHEN t.table_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END AS naming_score
            FROM {FULL_SCHEMA}.bronze_tables t
            LEFT JOIN col_stats c
                ON t.table_catalog = c.table_catalog
                AND t.table_schema = c.table_schema
                AND t.table_name = c.table_name
        )
        SELECT
            *,
            {metadata_score_expr}
        FROM base
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_metadata_assessment").collect()[0]["cnt"]
    print(f"✅ silver_metadata_assessment: {cnt:,} tables assessed")
    display(spark.sql(f"""
        SELECT
            ROUND(AVG(has_table_description) * 100, 1) AS pct_with_description,
            ROUND(AVG(column_doc_pct), 1) AS avg_column_doc_pct,
            ROUND(AVG(naming_score) * 100, 1) AS pct_naming_compliant,
            ROUND(AVG(metadata_score), 2) AS avg_metadata_score
        FROM {FULL_SCHEMA}.silver_metadata_assessment
    """))
except Exception as e:
    print(f"❌ silver_metadata_assessment: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Data Quality Assessment
# === Silver Layer - Data Quality Assessment ===
try:
    quality_score_expr, _ = build_weighted_score_expression('Data Quality', 'quality_score', 5.0)

    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_quality_assessment AS
        WITH base AS (
            SELECT
                table_catalog,
                table_schema,
                table_name,
                table_type,
                last_altered,
                DATEDIFF(current_date(), CAST(last_altered AS DATE)) AS days_since_modified,
                CASE WHEN DATEDIFF(current_date(), CAST(last_altered AS DATE)) <= 30 THEN 1 ELSE 0 END AS is_fresh,
                COALESCE(data_source_format, 'UNKNOWN') AS data_source_format,
                CASE WHEN UPPER(COALESCE(data_source_format, '')) = 'DELTA' THEN 1 ELSE 0 END AS is_delta
            FROM {FULL_SCHEMA}.bronze_tables
        )
        SELECT
            *,
            {quality_score_expr}
        FROM base
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_quality_assessment").collect()[0]["cnt"]
    print(f"✅ silver_quality_assessment: {cnt:,} tables assessed")
    display(spark.sql(f"""
        SELECT
            ROUND(AVG(is_fresh) * 100, 1) AS pct_fresh,
            ROUND(AVG(is_delta) * 100, 1) AS pct_delta,
            ROUND(AVG(quality_score), 2) AS avg_quality_score,
            ROUND(AVG(days_since_modified), 0) AS avg_days_since_modified
        FROM {FULL_SCHEMA}.silver_quality_assessment
    """))
except Exception as e:
    print(f"❌ silver_quality_assessment: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Genie Readiness
# === Silver Layer - Genie Readiness Assessment ===
try:
    genie_score_expr, _ = build_weighted_score_expression('Genie Readiness', 'genie_readiness_score', 100.0)

    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_genie_readiness AS
        WITH lineage_stats AS (
            SELECT
                target_table_catalog AS table_catalog,
                target_table_schema AS table_schema,
                target_table_name AS table_name,
                COUNT(*) AS lineage_connection_count
            FROM {FULL_SCHEMA}.bronze_table_lineage
            GROUP BY target_table_catalog, target_table_schema, target_table_name
        ),
        base AS (
            SELECT
                m.table_catalog,
                m.table_schema,
                m.table_name,
                m.has_table_description AS has_description,
                m.column_doc_pct,
                m.naming_score AS naming_compliant,
                CASE WHEN l.lineage_connection_count > 0 THEN 1 ELSE 0 END AS has_lineage,
                COALESCE(l.lineage_connection_count, 0) AS lineage_connection_count,
                COALESCE(l.lineage_connection_count, 0) AS lineage_count,
                CASE
                    WHEN LOWER(m.table_schema) RLIKE '(gold|curated|mart)'
                      OR LOWER(m.table_name) RLIKE '^(fact|dim)_'
                    THEN 1 ELSE 0
                END AS is_gold_layer_candidate
            FROM {FULL_SCHEMA}.silver_metadata_assessment m
            LEFT JOIN lineage_stats l
                ON m.table_catalog = l.table_catalog
                AND m.table_schema = l.table_schema
                AND m.table_name = l.table_name
        )
        SELECT
            *,
            {genie_score_expr}
        FROM base
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_genie_readiness").collect()[0]["cnt"]
    print(f"✅ silver_genie_readiness: {cnt:,} tables assessed")
    display(spark.sql(f"""
        SELECT
            ROUND(AVG(genie_readiness_score), 1) AS avg_genie_score,
            SUM(CASE WHEN genie_readiness_score >= 70 THEN 1 ELSE 0 END) AS genie_ready_count,
            ROUND(SUM(CASE WHEN genie_readiness_score >= 70 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS genie_ready_pct,
            SUM(is_gold_layer_candidate) AS gold_layer_candidates
        FROM {FULL_SCHEMA}.silver_genie_readiness
    """))
except Exception as e:
    print(f"❌ silver_genie_readiness: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Governance Assessment
# === Silver Layer - Governance Assessment ===
try:
    governance_foundation_expr, _ = build_weighted_score_expression('Governance', 'governance_foundation_score', 5.0)
    compliance_score_expr, _ = build_weighted_score_expression('Compliance', 'compliance_score', 5.0)
    governance_score_expr, _ = build_weighted_score_expression(['Governance', 'Compliance'], 'governance_score', 5.0)

    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_governance_assessment AS
        WITH tag_stats AS (
            SELECT
                catalog_name AS table_catalog,
                schema_name AS table_schema,
                table_name,
                COUNT(*) AS tag_count
            FROM {FULL_SCHEMA}.bronze_table_tags
            GROUP BY catalog_name, schema_name, table_name
        ),
        priv_stats AS (
            SELECT
                table_catalog,
                table_schema,
                table_name,
                COUNT(*) AS privilege_count,
                COUNT(*) AS grant_count,
                COUNT(DISTINCT grantee) AS distinct_grantees,
                SUM(CASE WHEN privilege_type = 'ALL PRIVILEGES' THEN 1 ELSE 0 END) AS over_permissioned_grants,
                MAX(CASE WHEN privilege_type = 'ALL PRIVILEGES' THEN 1 ELSE 0 END) AS has_all_privileges
            FROM {FULL_SCHEMA}.bronze_table_privileges
            GROUP BY table_catalog, table_schema, table_name
        ),
        lineage_stats AS (
            SELECT
                target_table_catalog AS table_catalog,
                target_table_schema AS table_schema,
                target_table_name AS table_name,
                COUNT(*) AS lineage_count
            FROM {FULL_SCHEMA}.bronze_table_lineage
            GROUP BY target_table_catalog, target_table_schema, target_table_name
        ),
        abac_stats AS (
            SELECT
                table_catalog,
                table_schema,
                table_name,
                effective_policy_count AS abac_effective_policy_count,
                row_filter_policy_count,
                column_mask_policy_count,
                abac_mask_policy_present,
                abac_row_filter_policy_present,
                inventory_status,
                error_message
            FROM {FULL_SCHEMA}.bronze_abac_policy_coverage
        ),
        base AS (
            SELECT
                t.table_catalog,
                t.table_schema,
                t.table_name,
                t.table_type,
                t.last_altered,
                COALESCE(t.data_source_format, 'UNKNOWN') AS data_source_format,
                CASE WHEN tg.tag_count > 0 THEN 1 ELSE 0 END AS has_tags,
                COALESCE(tg.tag_count, 0) AS tag_count,
                COALESCE(p.privilege_count, 0) AS privilege_count,
                COALESCE(p.grant_count, 0) AS grant_count,
                COALESCE(p.over_permissioned_grants, 0) AS over_permissioned_grants,
                COALESCE(p.has_all_privileges, 0) AS has_all_privileges,
                COALESCE(p.distinct_grantees, 0) AS distinct_grantees,
                COALESCE(m.has_table_description, 0) AS has_table_description,
                COALESCE(m.column_doc_pct, 0) AS column_doc_pct,
                COALESCE(l.lineage_count, 0) AS lineage_count,
                COALESCE(a.abac_effective_policy_count, 0) AS abac_effective_policy_count,
                COALESCE(a.row_filter_policy_count, 0) AS abac_row_filter_policy_count,
                COALESCE(a.column_mask_policy_count, 0) AS abac_column_mask_policy_count,
                COALESCE(a.abac_mask_policy_present, 0) AS abac_mask_policy_present,
                COALESCE(a.abac_row_filter_policy_present, 0) AS abac_row_filter_policy_present,
                COALESCE(a.inventory_status, 'NOT_SCANNED') AS abac_policy_inventory_status,
                COALESCE(a.error_message, '') AS abac_policy_inventory_error,
                CASE
                    WHEN t.table_type IN ('MANAGED', 'STREAMING_TABLE', 'MATERIALIZED_VIEW', 'VIEW', 'METRIC_VIEW') THEN 1
                    ELSE 0
                END AS is_managed
            FROM {FULL_SCHEMA}.bronze_tables t
            LEFT JOIN tag_stats tg
                ON t.table_catalog = tg.table_catalog
                AND t.table_schema = tg.table_schema
                AND t.table_name = tg.table_name
            LEFT JOIN priv_stats p
                ON t.table_catalog = p.table_catalog
                AND t.table_schema = p.table_schema
                AND t.table_name = p.table_name
            LEFT JOIN {FULL_SCHEMA}.silver_metadata_assessment m
                ON t.table_catalog = m.table_catalog
                AND t.table_schema = m.table_schema
                AND t.table_name = m.table_name
            LEFT JOIN lineage_stats l
                ON t.table_catalog = l.table_catalog
                AND t.table_schema = l.table_schema
                AND t.table_name = l.table_name
            LEFT JOIN abac_stats a
                ON t.table_catalog = a.table_catalog
                AND t.table_schema = a.table_schema
                AND t.table_name = a.table_name
        )
        SELECT
            *,
            {governance_foundation_expr},
            {compliance_score_expr},
            {governance_score_expr}
        FROM base
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_governance_assessment").collect()[0]["cnt"]
    print(f"\u2705 silver_governance_assessment: {cnt:,} tables assessed")
    display(spark.sql(f"""
        SELECT
            ROUND(AVG(has_tags) * 100, 1) AS pct_with_tags,
            ROUND(AVG(CASE WHEN privilege_count > 0 THEN 1 ELSE 0 END) * 100, 1) AS pct_with_privileges,
            ROUND(AVG(has_all_privileges) * 100, 1) AS pct_over_permissioned,
            ROUND(AVG(CASE WHEN abac_effective_policy_count > 0 THEN 1 ELSE 0 END) * 100, 1) AS pct_with_any_abac_policy,
            ROUND(AVG(abac_mask_policy_present) * 100, 1) AS pct_with_abac_masks,
            ROUND(AVG(abac_row_filter_policy_present) * 100, 1) AS pct_with_abac_row_filters,
            ROUND(AVG(CASE WHEN abac_policy_inventory_status = 'UNSUPPORTED' THEN 1 ELSE 0 END) * 100, 1) AS pct_abac_inventory_unsupported,
            ROUND(AVG(CASE WHEN abac_policy_inventory_status = 'ERROR' THEN 1 ELSE 0 END) * 100, 1) AS pct_abac_inventory_errors,
            ROUND(AVG(is_managed) * 100, 1) AS pct_managed,
            ROUND(AVG(governance_foundation_score), 2) AS avg_governance_foundation_score,
            ROUND(AVG(compliance_score), 2) AS avg_compliance_score,
            ROUND(AVG(governance_score), 2) AS avg_governance_score
        FROM {FULL_SCHEMA}.silver_governance_assessment
    """))
except Exception as e:
    print(f"\u274c silver_governance_assessment: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Performance Assessment
# === Silver Layer - Performance Assessment ===
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_performance_assessment AS
        SELECT
            statement_type,
            COUNT(*) AS query_count,
            ROUND(AVG(total_duration_ms), 2) AS avg_duration_ms,
            MAX(total_duration_ms) AS max_duration_ms,
            ROUND(PERCENTILE_APPROX(total_duration_ms, 0.5), 2) AS p50_duration_ms,
            SUM(read_bytes) AS total_read_bytes,
            CASE
                WHEN AVG(total_duration_ms) < 5000 THEN 'GOOD'
                WHEN AVG(total_duration_ms) < 30000 THEN 'MODERATE'
                ELSE 'POOR'
            END AS performance_category
        FROM {FULL_SCHEMA}.bronze_query_history
        WHERE statement_type IS NOT NULL
        GROUP BY statement_type
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_performance_assessment").collect()[0]["cnt"]
    print(f"✅ silver_performance_assessment: {cnt} statement types assessed")
    display(spark.sql(f"SELECT * FROM {FULL_SCHEMA}.silver_performance_assessment ORDER BY query_count DESC"))
except Exception as e:
    print(f"❌ silver_performance_assessment: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Functions & Models Assessment
# === Silver Layer - UC Functions & Models Assessment ===
print("=" * 60)
print("SILVER LAYER - Functions & Models Assessment")
print("=" * 60)

# --- 1. Functions Assessment ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_functions_assessment AS
        SELECT
            routine_catalog,
            routine_schema,
            routine_name,
            routine_type,
            routine_owner,
            data_type,
            external_language,
            is_deterministic,
            sql_data_access,
            security_type,
            comment,
            created,
            last_altered,
            -- Assessment metrics
            CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END AS has_description,
            CASE WHEN routine_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END AS naming_compliant,
            CASE WHEN is_deterministic = 'YES' THEN 1 ELSE 0 END AS is_deterministic_flag,
            CASE WHEN security_type = 'DEFINER' THEN 1 ELSE 0 END AS has_security_definer,
            CASE WHEN external_language IS NOT NULL THEN external_language ELSE 'SQL' END AS language,
            -- Readiness score (0-100)
            ROUND(
                (CASE WHEN comment IS NOT NULL AND comment != '' THEN 25.0 ELSE 0 END) +
                (CASE WHEN routine_name RLIKE '^[a-z][a-z0-9_]*$' THEN 20.0 ELSE 0 END) +
                (CASE WHEN is_deterministic = 'YES' THEN 15.0 ELSE 0 END) +
                (CASE WHEN security_type = 'DEFINER' THEN 20.0 ELSE 0 END) +
                (CASE WHEN data_type != 'NULL' THEN 20.0 ELSE 10.0 END)
            , 2) AS function_readiness_score
        FROM {FULL_SCHEMA}.bronze_routines
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_functions_assessment").collect()[0]["cnt"]
    print(f"  ✅ silver_functions_assessment: {cnt:,} functions assessed")
    display(spark.sql(f"""
        SELECT
            ROUND(AVG(has_description) * 100, 1) AS pct_with_description,
            ROUND(AVG(naming_compliant) * 100, 1) AS pct_naming_compliant,
            ROUND(AVG(function_readiness_score), 1) AS avg_readiness_score
        FROM {FULL_SCHEMA}.silver_functions_assessment
    """))
except Exception as e:
    print(f"  ❌ silver_functions_assessment: FAILED - {e}")

# --- 2. ML Models Assessment ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_models_assessment AS
        SELECT
            full_name,
            model_catalog,
            model_schema,
            model_name,
            description,
            creation_timestamp,
            last_updated_timestamp,
            latest_version,
            latest_status,
            tags,
            -- Assessment metrics
            CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END AS has_description,
            CASE WHEN model_name RLIKE '^[a-z][a-z0-9_-]*$' THEN 1 ELSE 0 END AS naming_compliant,
            CASE WHEN latest_version > 0 THEN 1 ELSE 0 END AS has_versions,
            CASE WHEN tags IS NOT NULL AND tags != '{{}}' THEN 1 ELSE 0 END AS has_tags,
            CASE WHEN latest_status = 'READY' THEN 1 ELSE 0 END AS is_production_ready,
            -- Readiness score (0-100)
            ROUND(
                (CASE WHEN description IS NOT NULL AND description != '' THEN 25.0 ELSE 0 END) +
                (CASE WHEN model_name RLIKE '^[a-z][a-z0-9_-]*$' THEN 15.0 ELSE 0 END) +
                (CASE WHEN latest_version > 0 THEN 20.0 ELSE 0 END) +
                (CASE WHEN tags IS NOT NULL AND tags != '{{}}' THEN 20.0 ELSE 0 END) +
                (CASE WHEN latest_status = 'READY' THEN 20.0 ELSE 0 END)
            , 2) AS model_readiness_score
        FROM {FULL_SCHEMA}.bronze_registered_models
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_models_assessment").collect()[0]["cnt"]
    print(f"  ✅ silver_models_assessment: {cnt:,} models assessed")
    if cnt > 0:
        display(spark.sql(f"""
            SELECT
                ROUND(AVG(has_description) * 100, 1) AS pct_with_description,
                ROUND(AVG(naming_compliant) * 100, 1) AS pct_naming_compliant,
                ROUND(AVG(has_versions) * 100, 1) AS pct_with_versions,
                ROUND(AVG(model_readiness_score), 1) AS avg_readiness_score
            FROM {FULL_SCHEMA}.silver_models_assessment
        """))
except Exception as e:
    print(f"  ❌ silver_models_assessment: FAILED - {e}")

# --- 3. Volumes Assessment ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_volumes_assessment AS
        SELECT
            volume_catalog,
            volume_schema,
            volume_name,
            volume_type,
            volume_owner,
            comment,
            created,
            last_altered,
            -- Assessment metrics
            CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END AS has_description,
            CASE WHEN volume_name RLIKE '^[a-z][a-z0-9_]*$' THEN 1 ELSE 0 END AS naming_compliant,
            CASE WHEN volume_type = 'MANAGED' THEN 1 ELSE 0 END AS is_managed,
            -- Readiness score (0-100)
            ROUND(
                (CASE WHEN comment IS NOT NULL AND comment != '' THEN 30.0 ELSE 0 END) +
                (CASE WHEN volume_name RLIKE '^[a-z][a-z0-9_]*$' THEN 25.0 ELSE 0 END) +
                (CASE WHEN volume_type = 'MANAGED' THEN 25.0 ELSE 10.0 END) +
                20.0  -- exists in UC = baseline score
            , 2) AS volume_readiness_score
        FROM {FULL_SCHEMA}.bronze_volumes
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_volumes_assessment").collect()[0]["cnt"]
    print(f"  ✅ silver_volumes_assessment: {cnt:,} volumes assessed")
    display(spark.sql(f"""
        SELECT
            ROUND(AVG(has_description) * 100, 1) AS pct_with_description,
            ROUND(AVG(naming_compliant) * 100, 1) AS pct_naming_compliant,
            ROUND(AVG(is_managed) * 100, 1) AS pct_managed,
            ROUND(AVG(volume_readiness_score), 1) AS avg_readiness_score
        FROM {FULL_SCHEMA}.silver_volumes_assessment
    """))
except Exception as e:
    print(f"  ❌ silver_volumes_assessment: FAILED - {e}")

print("=" * 60)
print("Silver extended assessment complete.")

# COMMAND ----------

# DBTITLE 1,Silver Layer - Clusters & Warehouses Assessment
# === Silver Layer - Clusters & Warehouses Assessment ===
print("=" * 60)
print("SILVER LAYER - Clusters & Warehouses Assessment")
print("=" * 60)

# --- 1. Interactive Clusters Assessment ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_clusters_assessment AS
        SELECT
            cluster_id,
            cluster_name,
            cluster_source,
            owned_by,
            dbr_version,
            data_security_mode,
            auto_termination_minutes,
            worker_count,
            min_autoscale_workers,
            max_autoscale_workers,
            policy_id,
            tags,
            -- Assessment metrics
            CASE WHEN min_autoscale_workers IS NOT NULL AND max_autoscale_workers IS NOT NULL THEN 1 ELSE 0 END AS has_autoscaling,
            CASE WHEN auto_termination_minutes IS NOT NULL AND auto_termination_minutes > 0 AND auto_termination_minutes <= 120 THEN 1 ELSE 0 END AS has_reasonable_auto_term,
            CASE WHEN data_security_mode IS NOT NULL AND data_security_mode != '' THEN 1 ELSE 0 END AS has_security_mode,
            CASE WHEN tags IS NOT NULL AND size(tags) > 0 THEN 1 ELSE 0 END AS has_tags,
            CASE WHEN policy_id IS NOT NULL AND policy_id != '' THEN 1 ELSE 0 END AS has_cluster_policy,
            CASE
                WHEN dbr_version RLIKE '^1[5-9]\\.' OR dbr_version RLIKE '^[2-9][0-9]\\.' THEN 1
                ELSE 0
            END AS has_current_dbr,
            CASE WHEN cluster_source = 'UI' THEN 'Interactive'
                 WHEN cluster_source = 'JOB' THEN 'Job'
                 WHEN cluster_source IN ('PIPELINE', 'PIPELINE_MAINTENANCE') THEN 'Pipeline'
                 ELSE cluster_source END AS compute_type,
            -- Readiness score (0-100)
            ROUND(
                (CASE WHEN min_autoscale_workers IS NOT NULL AND max_autoscale_workers IS NOT NULL THEN 15.0 ELSE 0 END) +
                (CASE WHEN auto_termination_minutes IS NOT NULL AND auto_termination_minutes > 0 AND auto_termination_minutes <= 120 THEN 20.0 ELSE 0 END) +
                (CASE WHEN data_security_mode IS NOT NULL AND data_security_mode != '' THEN 25.0 ELSE 0 END) +
                (CASE WHEN tags IS NOT NULL AND size(tags) > 0 THEN 10.0 ELSE 0 END) +
                (CASE WHEN policy_id IS NOT NULL AND policy_id != '' THEN 15.0 ELSE 0 END) +
                (CASE WHEN dbr_version RLIKE '^1[5-9]\\.' OR dbr_version RLIKE '^[2-9][0-9]\\.' THEN 15.0 ELSE 0 END)
            , 2) AS cluster_readiness_score
        FROM {FULL_SCHEMA}.bronze_clusters
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_clusters_assessment").collect()[0]["cnt"]
    print(f"  \u2705 silver_clusters_assessment: {cnt:,} clusters assessed")
    display(spark.sql(f"""
        SELECT
            compute_type,
            COUNT(*) AS cluster_count,
            ROUND(AVG(has_autoscaling) * 100, 1) AS pct_autoscaling,
            ROUND(AVG(has_reasonable_auto_term) * 100, 1) AS pct_good_auto_term,
            ROUND(AVG(has_security_mode) * 100, 1) AS pct_has_security,
            ROUND(AVG(has_current_dbr) * 100, 1) AS pct_current_dbr,
            ROUND(AVG(cluster_readiness_score), 1) AS avg_score
        FROM {FULL_SCHEMA}.silver_clusters_assessment
        GROUP BY compute_type ORDER BY cluster_count DESC
    """))
except Exception as e:
    print(f"  \u274c silver_clusters_assessment: FAILED - {e}")

# --- 2. SQL Warehouses Assessment ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.silver_warehouses_assessment AS
        SELECT
            warehouse_id,
            warehouse_name,
            warehouse_type,
            warehouse_channel,
            warehouse_size,
            min_clusters,
            max_clusters,
            auto_stop_minutes,
            tags,
            created_by,
            -- Assessment metrics
            CASE WHEN warehouse_type = 'SERVERLESS' THEN 1 ELSE 0 END AS is_serverless,
            CASE WHEN warehouse_type IN ('SERVERLESS', 'PRO') THEN 1 ELSE 0 END AS is_modern_type,
            CASE WHEN auto_stop_minutes IS NOT NULL AND auto_stop_minutes > 0 AND auto_stop_minutes <= 30 THEN 1 ELSE 0 END AS has_efficient_auto_stop,
            CASE WHEN max_clusters > 1 THEN 1 ELSE 0 END AS has_scaling,
            CASE WHEN tags IS NOT NULL AND size(tags) > 0 THEN 1 ELSE 0 END AS has_tags,
            CASE WHEN warehouse_channel = 'CURRENT' THEN 1 ELSE 0 END AS on_current_channel,
            -- Readiness score (0-100)
            ROUND(
                (CASE WHEN warehouse_type = 'SERVERLESS' THEN 30.0
                      WHEN warehouse_type = 'PRO' THEN 20.0
                      ELSE 0 END) +
                (CASE WHEN auto_stop_minutes IS NOT NULL AND auto_stop_minutes > 0 AND auto_stop_minutes <= 30 THEN 20.0 ELSE 10.0 END) +
                (CASE WHEN max_clusters > 1 THEN 15.0 ELSE 5.0 END) +
                (CASE WHEN tags IS NOT NULL AND size(tags) > 0 THEN 15.0 ELSE 0 END) +
                (CASE WHEN warehouse_channel = 'CURRENT' THEN 10.0 ELSE 5.0 END) +
                10.0  -- baseline for being in UC
            , 2) AS warehouse_readiness_score
        FROM {FULL_SCHEMA}.bronze_warehouses
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.silver_warehouses_assessment").collect()[0]["cnt"]
    print(f"  \u2705 silver_warehouses_assessment: {cnt:,} warehouses assessed")
    display(spark.sql(f"""
        SELECT
            warehouse_type,
            COUNT(*) AS wh_count,
            ROUND(AVG(has_efficient_auto_stop) * 100, 1) AS pct_efficient_stop,
            ROUND(AVG(has_scaling) * 100, 1) AS pct_has_scaling,
            ROUND(AVG(has_tags) * 100, 1) AS pct_has_tags,
            ROUND(AVG(warehouse_readiness_score), 1) AS avg_score
        FROM {FULL_SCHEMA}.silver_warehouses_assessment
        GROUP BY warehouse_type ORDER BY wh_count DESC
    """))
except Exception as e:
    print(f"  \u274c silver_warehouses_assessment: FAILED - {e}")

print("=" * 60)
print("Silver compute assessment complete.")

# COMMAND ----------

# DBTITLE 1,Gold Layer - Category Readiness Scores
# === Gold Layer - Category Readiness Scores ===
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_category_scores AS
        WITH metadata_cat AS (
            SELECT table_catalog AS catalog_name, 'Metadata Readiness' AS category,
                ROUND(AVG(metadata_score) / 5.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_metadata_assessment GROUP BY table_catalog
        ),
        governance_cat AS (
            SELECT table_catalog AS catalog_name, 'Governance' AS category,
                ROUND(AVG(governance_score) / 5.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_governance_assessment GROUP BY table_catalog
        ),
        quality_cat AS (
            SELECT table_catalog AS catalog_name, 'Data Quality' AS category,
                ROUND(AVG(quality_score) / 5.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_quality_assessment GROUP BY table_catalog
        ),
        genie_cat AS (
            SELECT table_catalog AS catalog_name, 'Genie Readiness' AS category,
                ROUND(AVG(genie_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_genie_readiness GROUP BY table_catalog
        ),
        performance_cat AS (
            SELECT 'ALL' AS catalog_name, 'Performance' AS category,
                ROUND(SUM(CASE WHEN performance_category = 'GOOD' THEN 1 ELSE 0 END) * 5.0 / NULLIF(COUNT(*), 0), 2) AS score,
                5.0 AS max_score, COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_performance_assessment
        ),
        functions_cat AS (
            SELECT routine_catalog AS catalog_name, 'UC Functions' AS category,
                ROUND(AVG(function_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_functions_assessment GROUP BY routine_catalog
        ),
        models_cat AS (
            SELECT model_catalog AS catalog_name, 'ML Models' AS category,
                ROUND(AVG(model_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_models_assessment GROUP BY model_catalog
        ),
        volumes_cat AS (
            SELECT volume_catalog AS catalog_name, 'Volumes' AS category,
                ROUND(AVG(volume_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_volumes_assessment GROUP BY volume_catalog
        ),
        clusters_cat AS (
            SELECT 'ALL' AS catalog_name, 'Clusters' AS category,
                ROUND(AVG(cluster_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_clusters_assessment
        ),
        warehouses_cat AS (
            SELECT 'ALL' AS catalog_name, 'SQL Warehouses' AS category,
                ROUND(AVG(warehouse_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_warehouses_assessment
        ),
        -- ALL-catalog aggregates for core categories (needed by app Overall Score section)
        metadata_all AS (
            SELECT 'ALL' AS catalog_name, 'Metadata Readiness' AS category,
                ROUND(AVG(metadata_score) / 5.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_metadata_assessment
        ),
        governance_all AS (
            SELECT 'ALL' AS catalog_name, 'Governance' AS category,
                ROUND(AVG(governance_score) / 5.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_governance_assessment
        ),
        quality_all AS (
            SELECT 'ALL' AS catalog_name, 'Data Quality' AS category,
                ROUND(AVG(quality_score) / 5.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_quality_assessment
        ),
        genie_all AS (
            SELECT 'ALL' AS catalog_name, 'Genie Readiness' AS category,
                ROUND(AVG(genie_readiness_score) / 100.0 * 5.0, 2) AS score, 5.0 AS max_score,
                COUNT(*) AS assessed_tables
            FROM {FULL_SCHEMA}.silver_genie_readiness
        ),
        all_scores AS (
            SELECT * FROM metadata_cat UNION ALL
            SELECT * FROM governance_cat UNION ALL
            SELECT * FROM quality_cat UNION ALL
            SELECT * FROM genie_cat UNION ALL
            SELECT * FROM metadata_all UNION ALL
            SELECT * FROM governance_all UNION ALL
            SELECT * FROM quality_all UNION ALL
            SELECT * FROM genie_all UNION ALL
            SELECT * FROM performance_cat UNION ALL
            SELECT * FROM functions_cat UNION ALL
            SELECT * FROM models_cat UNION ALL
            SELECT * FROM volumes_cat UNION ALL
            SELECT * FROM clusters_cat UNION ALL
            SELECT * FROM warehouses_cat
        )
        SELECT
            catalog_name, category, score, max_score,
            ROUND(score / max_score * 100, 1) AS pct,
            CASE
                WHEN score / max_score * 100 < 40 THEN 'RED'
                WHEN score / max_score * 100 < 70 THEN 'AMBER'
                ELSE 'GREEN'
            END AS rag_status,
            assessed_tables,
            current_timestamp() AS last_updated
        FROM all_scores
    """)

    print("✅ gold_category_scores created")
    display(spark.sql(f"SELECT * FROM {FULL_SCHEMA}.gold_category_scores ORDER BY catalog_name, category"))
except Exception as e:
    print(f"❌ gold_category_scores: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Gold Layer - Table Detail Scores
# === Gold Layer - Table Detail Scores ===
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_table_scores AS
        SELECT
            m.table_catalog,
            m.table_schema,
            m.table_name,
            ROUND(m.metadata_score, 2) AS metadata_score,
            ROUND(COALESCE(g.governance_score, 0), 2) AS governance_score,
            ROUND(COALESCE(q.quality_score, 0), 2) AS quality_score,
            ROUND(COALESCE(gr.genie_readiness_score, 0), 2) AS genie_score,
            ROUND(
                (COALESCE(m.metadata_score, 0) / 5.0 * 25) +
                (COALESCE(g.governance_score, 0) / 5.0 * 25) +
                (COALESCE(q.quality_score, 0) / 5.0 * 25) +
                (COALESCE(gr.genie_readiness_score, 0) / 100.0 * 25)
            , 2) AS overall_score,
            CASE
                WHEN (
                    (COALESCE(m.metadata_score, 0) / 5.0 * 25) +
                    (COALESCE(g.governance_score, 0) / 5.0 * 25) +
                    (COALESCE(q.quality_score, 0) / 5.0 * 25) +
                    (COALESCE(gr.genie_readiness_score, 0) / 100.0 * 25)
                ) < 40 THEN 'RED'
                WHEN (
                    (COALESCE(m.metadata_score, 0) / 5.0 * 25) +
                    (COALESCE(g.governance_score, 0) / 5.0 * 25) +
                    (COALESCE(q.quality_score, 0) / 5.0 * 25) +
                    (COALESCE(gr.genie_readiness_score, 0) / 100.0 * 25)
                ) < 70 THEN 'AMBER'
                ELSE 'GREEN'
            END AS rag_status
        FROM {FULL_SCHEMA}.silver_metadata_assessment m
        LEFT JOIN {FULL_SCHEMA}.silver_governance_assessment g
            ON m.table_catalog = g.table_catalog AND m.table_schema = g.table_schema AND m.table_name = g.table_name
        LEFT JOIN {FULL_SCHEMA}.silver_quality_assessment q
            ON m.table_catalog = q.table_catalog AND m.table_schema = q.table_schema AND m.table_name = q.table_name
        LEFT JOIN {FULL_SCHEMA}.silver_genie_readiness gr
            ON m.table_catalog = gr.table_catalog AND m.table_schema = gr.table_schema AND m.table_name = gr.table_name
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_table_scores").collect()[0]["cnt"]
    print(f"✅ gold_table_scores: {cnt:,} tables scored")
    display(spark.sql(f"""
        SELECT rag_status, COUNT(*) AS table_count, ROUND(AVG(overall_score), 1) AS avg_score
        FROM {FULL_SCHEMA}.gold_table_scores
        GROUP BY rag_status ORDER BY rag_status
    """))
except Exception as e:
    print(f"❌ gold_table_scores: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Gold Layer - Recommendations Engine
# === Gold Layer - Recommendations Engine ===
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_recommendations AS

        -- Missing table description
        SELECT table_catalog, table_schema, table_name,
            'Metadata Readiness' AS category, 'META_001' AS rule_id, 'HIGH' AS severity,
            'Add table description for discoverability and Genie readiness' AS recommendation,
            'No description' AS current_value, 'Description present' AS target_value
        FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE has_table_description = 0

        UNION ALL

        -- Column doc < 50%
        SELECT table_catalog, table_schema, table_name,
            'Metadata Readiness', 'META_002', 'HIGH',
            'Document columns - critical for Genie and data governance',
            CONCAT(CAST(ROUND(column_doc_pct, 0) AS STRING), '% documented'), '>=80% documented'
        FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE column_doc_pct < 50 AND total_columns > 0

        UNION ALL

        -- Column doc 50-80%
        SELECT table_catalog, table_schema, table_name,
            'Metadata Readiness', 'META_002', 'MEDIUM',
            'Improve column documentation to reach 80% threshold',
            CONCAT(CAST(ROUND(column_doc_pct, 0) AS STRING), '% documented'), '>=80% documented'
        FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE column_doc_pct >= 50 AND column_doc_pct < 80 AND total_columns > 0

        UNION ALL

        -- No tags
        SELECT table_catalog, table_schema, table_name,
            'Governance', 'GOV_001', 'MEDIUM',
            'Add governance tags for classification and RBAC',
            '0 tags', '>=1 tag'
        FROM {FULL_SCHEMA}.silver_governance_assessment WHERE has_tags = 0

        UNION ALL

        -- Over-permissioned
        SELECT table_catalog, table_schema, table_name,
            'Governance', 'GOV_003', 'HIGH',
            'Review and restrict over-broad ALL PRIVILEGES permissions',
            'ALL PRIVILEGES granted', 'Least-privilege access'
        FROM {FULL_SCHEMA}.silver_governance_assessment WHERE has_all_privileges = 1

        UNION ALL

        -- External / Foreign tables (not managed)
        SELECT table_catalog, table_schema, table_name,
            'Governance', 'GOV_004', 'MEDIUM',
            'Migrate to Unity Catalog managed table for better governance, lineage, and lifecycle management',
            CASE WHEN is_managed = 0 THEN 'External/Foreign' ELSE 'Unknown' END,
            'UC Managed Table'
        FROM {FULL_SCHEMA}.silver_governance_assessment WHERE is_managed = 0

        UNION ALL

        -- ABAC inventory unsupported
        SELECT table_catalog, table_schema, table_name,
            'Governance', 'ABAC_001', 'LOW',
            'ABAC inventory could not be assessed for this table because SHOW EFFECTIVE POLICIES is unsupported on sample assets',
            abac_policy_inventory_status, 'SCANNED'
        FROM {FULL_SCHEMA}.silver_governance_assessment WHERE abac_policy_inventory_status = 'UNSUPPORTED'

        UNION ALL

        -- No ABAC policies detected
        SELECT table_catalog, table_schema, table_name,
            'Governance', 'ABAC_002', 'LOW',
            'No ABAC row filters or column masks detected. Review whether governed tags and centralized masking policies are needed for sensitive data',
            '0 ABAC policies', '>=1 policy where sensitive data requires masking or filtering'
        FROM {FULL_SCHEMA}.silver_governance_assessment
        WHERE abac_policy_inventory_status = 'SCANNED' AND COALESCE(tag_count, 0) > 0 AND COALESCE(abac_effective_policy_count, 0) = 0

        UNION ALL

        -- Not Delta format
        SELECT table_catalog, table_schema, table_name,
            'Data Quality', 'DQ_002', 'LOW',
            'Convert to Delta format for better performance and governance',
            data_source_format, 'DELTA'
        FROM {FULL_SCHEMA}.silver_quality_assessment WHERE is_delta = 0

        UNION ALL

        -- Stale tables
        SELECT table_catalog, table_schema, table_name,
            'Data Quality', 'DQ_001', 'MEDIUM',
            'Investigate stale table - may need refresh or archiving',
            CONCAT(CAST(days_since_modified AS STRING), ' days old'), '<=30 days'
        FROM {FULL_SCHEMA}.silver_quality_assessment WHERE is_fresh = 0

        UNION ALL

        -- Poor naming
        SELECT table_catalog, table_schema, table_name,
            'Genie Readiness', 'GENIE_001', 'MEDIUM',
            'Rename to lowercase snake_case for Genie compatibility',
            table_name, 'lowercase_snake_case'
        FROM {FULL_SCHEMA}.silver_metadata_assessment WHERE naming_score = 0

        UNION ALL

        -- No lineage
        SELECT table_catalog, table_schema, table_name,
            'Genie Readiness', 'GENIE_002', 'MEDIUM',
            'Establish data lineage for impact analysis',
            '0 connections', '>=1 connection'
        FROM {FULL_SCHEMA}.silver_genie_readiness WHERE has_lineage = 0

        UNION ALL

        -- Low Genie readiness
        SELECT table_catalog, table_schema, table_name,
            'Genie Readiness', 'GENIE_003', 'HIGH',
            'Prioritize this table for Genie onboarding improvements',
            CONCAT(CAST(ROUND(genie_readiness_score, 0) AS STRING), '% ready'), '>=70% ready'
        FROM {FULL_SCHEMA}.silver_genie_readiness WHERE genie_readiness_score < 60
    """)

    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_recommendations").collect()[0]["cnt"]
    print(f"\u2705 gold_recommendations: {cnt:,} recommendations generated")
    display(spark.sql(f"""
        SELECT category, severity, COUNT(*) AS rec_count
        FROM {FULL_SCHEMA}.gold_recommendations
        GROUP BY category, severity
        ORDER BY category, severity
    """))
except Exception as e:
    print(f"\u274c gold_recommendations: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Gold Layer - FinOps Insights
# === Gold Layer - FinOps Insights ===
finops_tables = {
    "gold_cost_by_sku": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_cost_by_sku AS
        SELECT
            sku_name,
            usage_date,
            SUM(usage_quantity) AS total_dbus,
            COUNT(*) AS usage_records
        FROM {FULL_SCHEMA}.bronze_billing_usage
        GROUP BY sku_name, usage_date
    """,
    "gold_cost_by_product": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_cost_by_product AS
        SELECT
            billing_origin_product,
            SUM(usage_quantity) AS total_dbus,
            COUNT(*) AS usage_records,
            MIN(usage_date) AS first_usage,
            MAX(usage_date) AS last_usage
        FROM {FULL_SCHEMA}.bronze_billing_usage
        GROUP BY billing_origin_product
    """,
    "gold_expensive_queries": f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_expensive_queries AS
        SELECT
            statement_id,
            statement_type,
            executed_by,
            start_time,
            total_duration_ms,
            read_bytes,
            read_rows,
            produced_rows,
            execution_status
        FROM {FULL_SCHEMA}.bronze_query_history
        ORDER BY total_duration_ms DESC
        LIMIT 100
    """
}

print("=" * 60)
print("GOLD LAYER - FinOps Insights")
print("=" * 60)

for tbl_name, sql in finops_tables.items():
    try:
        spark.sql(sql)
        cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.{tbl_name}").collect()[0]["cnt"]
        print(f"  ✅ {tbl_name}: {cnt:,} rows")
    except Exception as e:
        print(f"  ❌ {tbl_name}: FAILED - {str(e)[:150]}")

print("=" * 60)

# COMMAND ----------

# DBTITLE 1,Gold Layer - Extended Asset Scores & Recommendations
# === Gold Layer - Extended Asset Scores & Recommendations ===
print("=" * 60)
print("GOLD LAYER - Extended Asset Scores")
print("=" * 60)

# --- 1. Gold UC Functions Summary ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_functions_summary AS
        SELECT
            routine_catalog,
            routine_schema,
            routine_name,
            routine_type,
            language,
            has_description,
            naming_compliant,
            is_deterministic_flag,
            has_security_definer,
            function_readiness_score,
            CASE
                WHEN function_readiness_score >= 70 THEN 'GREEN'
                WHEN function_readiness_score >= 40 THEN 'AMBER'
                ELSE 'RED'
            END AS rag_status
        FROM {FULL_SCHEMA}.silver_functions_assessment
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_functions_summary").collect()[0]["cnt"]
    print(f"  ✅ gold_functions_summary: {cnt:,} functions scored")
except Exception as e:
    print(f"  ❌ gold_functions_summary: FAILED - {e}")

# --- 2. Gold ML Models Summary ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_models_summary AS
        SELECT
            model_catalog,
            model_schema,
            model_name,
            full_name,
            has_description,
            naming_compliant,
            has_versions,
            has_tags,
            is_production_ready,
            model_readiness_score,
            CASE
                WHEN model_readiness_score >= 70 THEN 'GREEN'
                WHEN model_readiness_score >= 40 THEN 'AMBER'
                ELSE 'RED'
            END AS rag_status
        FROM {FULL_SCHEMA}.silver_models_assessment
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_models_summary").collect()[0]["cnt"]
    print(f"  ✅ gold_models_summary: {cnt:,} models scored")
except Exception as e:
    print(f"  ❌ gold_models_summary: FAILED - {e}")

# --- 3. Gold Volumes Summary ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_volumes_summary AS
        SELECT
            volume_catalog,
            volume_schema,
            volume_name,
            volume_type,
            has_description,
            naming_compliant,
            is_managed,
            volume_readiness_score,
            CASE
                WHEN volume_readiness_score >= 70 THEN 'GREEN'
                WHEN volume_readiness_score >= 40 THEN 'AMBER'
                ELSE 'RED'
            END AS rag_status
        FROM {FULL_SCHEMA}.silver_volumes_assessment
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_volumes_summary").collect()[0]["cnt"]
    print(f"  ✅ gold_volumes_summary: {cnt:,} volumes scored")
except Exception as e:
    print(f"  ❌ gold_volumes_summary: FAILED - {e}")

# --- 4. Extended Recommendations for Functions & Models ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_extended_recommendations AS

        -- Functions without description
        SELECT routine_catalog AS table_catalog, routine_schema AS table_schema, routine_name AS table_name,
            'Functions' AS category, 'FN_001' AS rule_id, 'HIGH' AS severity,
            'Add description to UC function for discoverability' AS recommendation,
            'No description' AS current_value, 'Description present' AS target_value
        FROM {FULL_SCHEMA}.silver_functions_assessment WHERE has_description = 0

        UNION ALL

        -- Functions with non-compliant naming
        SELECT routine_catalog, routine_schema, routine_name,
            'Functions', 'FN_002', 'MEDIUM',
            'Rename function to follow snake_case naming convention',
            'Non-compliant name', 'snake_case name'
        FROM {FULL_SCHEMA}.silver_functions_assessment WHERE naming_compliant = 0

        UNION ALL

        -- Functions without DEFINER security
        SELECT routine_catalog, routine_schema, routine_name,
            'Functions', 'FN_003', 'MEDIUM',
            'Consider DEFINER security mode for controlled access',
            security_type, 'DEFINER'
        FROM {FULL_SCHEMA}.silver_functions_assessment WHERE has_security_definer = 0

        UNION ALL

        -- Models without description
        SELECT model_catalog, model_schema, model_name,
            'ML Models', 'ML_001', 'HIGH',
            'Add description to registered model for discoverability',
            'No description', 'Description present'
        FROM {FULL_SCHEMA}.silver_models_assessment WHERE has_description = 0

        UNION ALL

        -- Models without tags
        SELECT model_catalog, model_schema, model_name,
            'ML Models', 'ML_002', 'MEDIUM',
            'Add tags to model for governance and classification',
            'No tags', 'Tags applied'
        FROM {FULL_SCHEMA}.silver_models_assessment WHERE has_tags = 0

        UNION ALL

        -- Volumes without description
        SELECT volume_catalog, volume_schema, volume_name,
            'Volumes', 'VOL_001', 'MEDIUM',
            'Add description to volume for discoverability',
            'No description', 'Description present'
        FROM {FULL_SCHEMA}.silver_volumes_assessment WHERE has_description = 0

        UNION ALL

        -- Volumes with non-compliant naming
        SELECT volume_catalog, volume_schema, volume_name,
            'Volumes', 'VOL_002', 'LOW',
            'Rename volume to follow snake_case naming convention',
            'Non-compliant name', 'snake_case name'
        FROM {FULL_SCHEMA}.silver_volumes_assessment WHERE naming_compliant = 0
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_extended_recommendations").collect()[0]["cnt"]
    print(f"  ✅ gold_extended_recommendations: {cnt:,} recommendations generated")
    display(spark.sql(f"""
        SELECT category, rule_id, severity, COUNT(*) AS cnt
        FROM {FULL_SCHEMA}.gold_extended_recommendations
        GROUP BY category, rule_id, severity
        ORDER BY category, rule_id
    """))
except Exception as e:
    print(f"  ❌ gold_extended_recommendations: FAILED - {e}")

print("=" * 60)
print("Gold extended asset scoring complete.")

# COMMAND ----------

# DBTITLE 1,Gold Layer - Compute Scores & Recommendations
# === Gold Layer - Compute Scores & Recommendations ===
print("=" * 60)
print("GOLD LAYER - Compute Scores & Recommendations")
print("=" * 60)

# --- 1. Gold Clusters Summary ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_clusters_summary AS
        SELECT
            cluster_id, cluster_name, compute_type, owned_by,
            dbr_version, data_security_mode,
            has_autoscaling, has_reasonable_auto_term, has_security_mode,
            has_tags, has_cluster_policy, has_current_dbr,
            cluster_readiness_score,
            CASE
                WHEN cluster_readiness_score >= 70 THEN 'GREEN'
                WHEN cluster_readiness_score >= 40 THEN 'AMBER'
                ELSE 'RED'
            END AS rag_status
        FROM {FULL_SCHEMA}.silver_clusters_assessment
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_clusters_summary").collect()[0]["cnt"]
    print(f"  \u2705 gold_clusters_summary: {cnt:,} clusters scored")
except Exception as e:
    print(f"  \u274c gold_clusters_summary: FAILED - {e}")

# --- 2. Gold Warehouses Summary ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_warehouses_summary AS
        SELECT
            warehouse_id, warehouse_name, warehouse_type, warehouse_size,
            is_serverless, is_modern_type, has_efficient_auto_stop,
            has_scaling, has_tags, on_current_channel,
            warehouse_readiness_score,
            CASE
                WHEN warehouse_readiness_score >= 70 THEN 'GREEN'
                WHEN warehouse_readiness_score >= 40 THEN 'AMBER'
                ELSE 'RED'
            END AS rag_status
        FROM {FULL_SCHEMA}.silver_warehouses_assessment
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_warehouses_summary").collect()[0]["cnt"]
    print(f"  \u2705 gold_warehouses_summary: {cnt:,} warehouses scored")
except Exception as e:
    print(f"  \u274c gold_warehouses_summary: FAILED - {e}")

# --- 3. Compute Recommendations ---
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_compute_recommendations AS

        -- Clusters without UC security mode
        SELECT cluster_id AS resource_id, cluster_name AS resource_name,
            'Clusters' AS category, 'CLU_001' AS rule_id, 'HIGH' AS severity,
            'Enable Unity Catalog security mode (USER_ISOLATION or SINGLE_USER)' AS recommendation,
            COALESCE(data_security_mode, 'None') AS current_value, 'USER_ISOLATION' AS target_value
        FROM {FULL_SCHEMA}.silver_clusters_assessment WHERE has_security_mode = 0

        UNION ALL

        -- Clusters with outdated DBR
        SELECT cluster_id, cluster_name,
            'Clusters', 'CLU_002', 'MEDIUM',
            'Upgrade to DBR 15+ for latest features and security patches',
            dbr_version, 'DBR 15.x+'
        FROM {FULL_SCHEMA}.silver_clusters_assessment WHERE has_current_dbr = 0

        UNION ALL

        -- Clusters without auto-termination or > 2 hours
        SELECT cluster_id, cluster_name,
            'Clusters', 'CLU_003', 'HIGH',
            'Set auto-termination to 120 minutes or less to reduce costs',
            CAST(COALESCE(auto_termination_minutes, 0) AS STRING), '<=120 minutes'
        FROM {FULL_SCHEMA}.silver_clusters_assessment WHERE has_reasonable_auto_term = 0

        UNION ALL

        -- Clusters without cluster policy
        SELECT cluster_id, cluster_name,
            'Clusters', 'CLU_004', 'MEDIUM',
            'Assign a cluster policy for governance and cost control',
            'No policy', 'Policy assigned'
        FROM {FULL_SCHEMA}.silver_clusters_assessment WHERE has_cluster_policy = 0

        UNION ALL

        -- Clusters without autoscaling (interactive only)
        SELECT cluster_id, cluster_name,
            'Clusters', 'CLU_005', 'MEDIUM',
            'Enable autoscaling to optimize costs based on workload',
            'Fixed size', 'Autoscaling enabled'
        FROM {FULL_SCHEMA}.silver_clusters_assessment WHERE has_autoscaling = 0 AND compute_type = 'Interactive'

        UNION ALL

        -- Warehouses not serverless
        SELECT warehouse_id, warehouse_name,
            'SQL Warehouses', 'WH_001', 'MEDIUM',
            'Migrate to Serverless warehouse for better performance and cost efficiency',
            warehouse_type, 'SERVERLESS'
        FROM {FULL_SCHEMA}.silver_warehouses_assessment WHERE is_serverless = 0

        UNION ALL

        -- Warehouses without tags
        SELECT warehouse_id, warehouse_name,
            'SQL Warehouses', 'WH_003', 'LOW',
            'Add tags for cost attribution and governance tracking',
            'No tags', 'Tags applied'
        FROM {FULL_SCHEMA}.silver_warehouses_assessment WHERE has_tags = 0
    """)
    cnt = spark.sql(f"SELECT COUNT(*) AS cnt FROM {FULL_SCHEMA}.gold_compute_recommendations").collect()[0]["cnt"]
    print(f"  \u2705 gold_compute_recommendations: {cnt:,} recommendations generated")
    display(spark.sql(f"""
        SELECT category, rule_id, severity, COUNT(*) AS cnt
        FROM {FULL_SCHEMA}.gold_compute_recommendations
        GROUP BY category, rule_id, severity
        ORDER BY category, rule_id
    """))
except Exception as e:
    print(f"  \u274c gold_compute_recommendations: FAILED - {e}")

print("=" * 60)
print("Gold compute scoring complete.")

# COMMAND ----------

# DBTITLE 1,Gold Layer - Executive Summary
# === Gold Layer - Executive Summary ===
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.gold_executive_summary AS
        WITH base_stats AS (
            SELECT
                COUNT(DISTINCT table_catalog) AS total_catalogs,
                COUNT(*) AS total_tables,
                SUM(total_columns) AS total_columns,
                ROUND(AVG(has_table_description) * 100, 1) AS tables_with_descriptions_pct,
                ROUND(AVG(column_doc_pct), 1) AS columns_documented_pct
            FROM {FULL_SCHEMA}.silver_metadata_assessment
        ),
        quality_stats AS (
            SELECT
                ROUND(AVG(is_fresh) * 100, 1) AS fresh_tables_pct,
                ROUND(AVG(is_delta) * 100, 1) AS delta_format_pct
            FROM {FULL_SCHEMA}.silver_quality_assessment
        ),
        genie_stats AS (
            SELECT
                SUM(CASE WHEN genie_readiness_score >= 70 THEN 1 ELSE 0 END) AS genie_ready_tables,
                ROUND(SUM(CASE WHEN genie_readiness_score >= 70 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS genie_ready_pct
            FROM {FULL_SCHEMA}.silver_genie_readiness
        ),
        score_stats AS (
            SELECT
                ROUND(AVG(CASE WHEN category = 'Metadata Readiness' THEN pct END), 1) AS metadata_score,
                ROUND(AVG(CASE WHEN category = 'Governance' THEN pct END), 1) AS governance_score,
                ROUND(AVG(CASE WHEN category = 'Data Quality' THEN pct END), 1) AS quality_score,
                ROUND(AVG(CASE WHEN category = 'Performance' THEN pct END), 1) AS performance_score,
                ROUND(AVG(CASE WHEN category = 'Genie Readiness' THEN pct END), 1) AS genie_score,
                ROUND(AVG(pct), 1) AS overall_readiness_score
            FROM {FULL_SCHEMA}.gold_category_scores
        ),
        rec_stats AS (
            SELECT
                COUNT(*) AS total_recommendations,
                SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) AS high_priority_recommendations
            FROM {FULL_SCHEMA}.gold_recommendations
        ),
        dbu_stats AS (
            SELECT ROUND(COALESCE(SUM(total_dbus), 0), 2) AS total_dbus_consumed
            FROM {FULL_SCHEMA}.gold_cost_by_sku
        ),
        fn_stats AS (
            SELECT
                COUNT(*) AS total_functions,
                ROUND(AVG(function_readiness_score), 1) AS avg_function_score
            FROM {FULL_SCHEMA}.silver_functions_assessment
        ),
        model_stats AS (
            SELECT
                COUNT(*) AS total_models,
                ROUND(AVG(model_readiness_score), 1) AS avg_model_score
            FROM {FULL_SCHEMA}.silver_models_assessment
        ),
        volume_stats AS (
            SELECT
                COUNT(*) AS total_volumes,
                ROUND(AVG(volume_readiness_score), 1) AS avg_volume_score
            FROM {FULL_SCHEMA}.silver_volumes_assessment
        ),
        cluster_stats AS (
            SELECT
                COUNT(*) AS total_clusters,
                ROUND(AVG(cluster_readiness_score), 1) AS avg_cluster_score
            FROM {FULL_SCHEMA}.silver_clusters_assessment
        ),
        warehouse_stats AS (
            SELECT
                COUNT(*) AS total_warehouses,
                ROUND(AVG(warehouse_readiness_score), 1) AS avg_warehouse_score
            FROM {FULL_SCHEMA}.silver_warehouses_assessment
        )
        SELECT
            b.total_catalogs,
            b.total_tables,
            b.total_columns,
            fn.total_functions,
            fn.avg_function_score,
            ml.total_models,
            ml.avg_model_score,
            vol.total_volumes,
            vol.avg_volume_score,
            clu.total_clusters,
            clu.avg_cluster_score,
            whs.total_warehouses,
            whs.avg_warehouse_score,
            s.overall_readiness_score,
            CASE
                WHEN s.overall_readiness_score < 40 THEN 'RED'
                WHEN s.overall_readiness_score < 70 THEN 'AMBER'
                ELSE 'GREEN'
            END AS overall_rag_status,
            s.metadata_score,
            s.governance_score,
            s.quality_score,
            s.performance_score,
            s.genie_score,
            b.tables_with_descriptions_pct,
            b.columns_documented_pct,
            q.delta_format_pct,
            q.fresh_tables_pct,
            g.genie_ready_tables,
            g.genie_ready_pct,
            r.total_recommendations,
            r.high_priority_recommendations,
            d.total_dbus_consumed,
            current_timestamp() AS assessment_date
        FROM base_stats b
        CROSS JOIN quality_stats q
        CROSS JOIN genie_stats g
        CROSS JOIN score_stats s
        CROSS JOIN rec_stats r
        CROSS JOIN dbu_stats d
        CROSS JOIN fn_stats fn
        CROSS JOIN model_stats ml
        CROSS JOIN volume_stats vol
        CROSS JOIN cluster_stats clu
        CROSS JOIN warehouse_stats whs
    """)

    print("✅ gold_executive_summary created")
    display(spark.sql(f"SELECT * FROM {FULL_SCHEMA}.gold_executive_summary"))
except Exception as e:
    print(f"❌ gold_executive_summary: FAILED - {e}")

# COMMAND ----------

# DBTITLE 1,Assessment Complete - Summary
# MAGIC %md
# MAGIC # UC Readiness Assessment Complete
# MAGIC
# MAGIC ## Tables Created
# MAGIC
# MAGIC ### Bronze Layer (Raw Ingestion)
# MAGIC | Table | Source |
# MAGIC | --- | --- |
# MAGIC | `bronze_tables` | system.information_schema.tables |
# MAGIC | `bronze_columns` | system.information_schema.columns |
# MAGIC | `bronze_table_tags` | system.information_schema.table_tags |
# MAGIC | `bronze_column_tags` | system.information_schema.column_tags |
# MAGIC | `bronze_table_privileges` | system.information_schema.table_privileges |
# MAGIC | `bronze_billing_usage` | system.billing.usage |
# MAGIC | `bronze_query_history` | system.query.history |
# MAGIC | `bronze_table_lineage` | system.access.table_lineage |
# MAGIC | `bronze_routines` | system.information_schema.routines |
# MAGIC | `bronze_volumes` | system.information_schema.volumes |
# MAGIC | `bronze_registered_models` | MLflow UC Model Registry |
# MAGIC | `bronze_clusters` | system.compute.clusters (latest state) |
# MAGIC | `bronze_warehouses` | system.compute.warehouses (latest state) |
# MAGIC
# MAGIC ### Silver Layer (Assessment)
# MAGIC | Table | Assessment |
# MAGIC | --- | --- |
# MAGIC | `silver_metadata_assessment` | Table/column descriptions, naming conventions |
# MAGIC | `silver_governance_assessment` | Tags, privileges, over-permissioning |
# MAGIC | `silver_quality_assessment` | Freshness, Delta format |
# MAGIC | `silver_performance_assessment` | Query performance by statement type |
# MAGIC | `silver_genie_readiness` | AI/BI Genie onboarding readiness |
# MAGIC | `silver_functions_assessment` | UC function naming, docs, security scoring |
# MAGIC | `silver_models_assessment` | ML model versioning, docs, tags scoring |
# MAGIC | `silver_volumes_assessment` | Volume naming, docs, type scoring |
# MAGIC | `silver_clusters_assessment` | Cluster security, autoscaling, DBR, policies |
# MAGIC | `silver_warehouses_assessment` | Warehouse type, sizing, auto-stop, tags |
# MAGIC
# MAGIC ### Gold Layer (Scores & Insights)
# MAGIC | Table | Purpose |
# MAGIC | --- | --- |
# MAGIC | `gold_category_scores` | Category-level readiness scores with RAG status |
# MAGIC | `gold_table_scores` | Per-table scores across all dimensions |
# MAGIC | `gold_recommendations` | Actionable improvement recommendations |
# MAGIC | `gold_cost_by_sku` | DBU consumption by SKU |
# MAGIC | `gold_cost_by_product` | DBU consumption by product |
# MAGIC | `gold_expensive_queries` | Top 100 most expensive queries |
# MAGIC | `gold_functions_summary` | Function-level readiness with RAG status |
# MAGIC | `gold_models_summary` | Model-level readiness with RAG status |
# MAGIC | `gold_volumes_summary` | Volume-level readiness with RAG status |
# MAGIC | `gold_clusters_summary` | Cluster-level readiness with RAG status |
# MAGIC | `gold_warehouses_summary` | Warehouse-level readiness with RAG status |
# MAGIC | `gold_compute_recommendations` | Recommendations for clusters and warehouses |
# MAGIC | `gold_extended_recommendations` | Recommendations for functions, models, volumes |
# MAGIC | `gold_executive_summary` | Single-row executive dashboard summary (incl. extended assets) |
# MAGIC
# MAGIC ## Next Steps
# MAGIC 1. **Create Dashboard** \~ Build an executive dashboard from gold layer tables
# MAGIC 2. **Schedule Refresh** \~ Set up a daily/weekly job to re-run this notebook
# MAGIC 3. **Review Recommendations** \~ Query `gold_recommendations` filtered by severity = 'HIGH'
# MAGIC 4. **Wire to Databricks App** \~ Connect dashboard to the FinOps Monitor app
# MAGIC 5. **Customize Rules** \~ Update `assessment_rules` table with organization-specific checks

# COMMAND ----------

# DBTITLE 1,Deploy Databricks App
# === Deploy UC Readiness Accelerator as Databricks App ===
import requests, time, json

# Get workspace context for REST API
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
host = ctx.apiUrl().get()
token = ctx.apiToken().get()

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

APP_NAME = "uc-readiness-accelerator"
APP_SOURCE = "/Workspace/Users/cyrils@systechusa.com/uc-readiness-app"

# Step 1: Check if app exists
print("Checking app status...")
resp = requests.get(f"{host}/api/2.0/apps/{APP_NAME}", headers=headers)

if resp.status_code == 200:
    app_data = resp.json()
    print(f"✅ App '{APP_NAME}' exists.")
    print(f"   URL: {app_data.get('url', 'N/A')}")
    print(f"   Compute: {app_data.get('compute_status', {}).get('state', 'Unknown')}")
else:
    # Create the app
    print(f"Creating app '{APP_NAME}'...")
    create_payload = {
        "name": APP_NAME,
        "description": "UC Readiness Accelerator - Unity Catalog assessment dashboard with executive summary, category scores, recommendations, FinOps insights, performance, and Genie readiness."
    }
    resp = requests.post(f"{host}/api/2.0/apps", headers=headers, json=create_payload)
    if resp.status_code in (200, 201):
        app_data = resp.json()
        print(f"✅ App created!")
        print(f"   URL: {app_data.get('url', 'N/A')}")
    else:
        print(f"❌ Create failed: {resp.status_code} - {resp.text[:200]}")
        app_data = {}

# Step 2: Start compute if needed
compute_state = app_data.get("compute_status", {}).get("state", "")
if compute_state not in ("ACTIVE", "RUNNING"):
    print(f"\nStarting app compute (current: {compute_state})...")
    requests.post(f"{host}/api/2.0/apps/{APP_NAME}/start", headers=headers)
    for i in range(15):
        time.sleep(10)
        r = requests.get(f"{host}/api/2.0/apps/{APP_NAME}", headers=headers)
        if r.status_code == 200:
            state = r.json().get("compute_status", {}).get("state", "")
            print(f"  [{i+1}/15] State: {state}")
            if state == "ACTIVE":
                app_data = r.json()
                break

# Step 3: Deploy source code
print(f"\nDeploying from: {APP_SOURCE}")
deploy_payload = {
    "source_code_path": APP_SOURCE,
    "mode": "SNAPSHOT"
}
resp = requests.post(
    f"{host}/api/2.0/apps/{APP_NAME}/deployments",
    headers=headers,
    json=deploy_payload
)
if resp.status_code in (200, 201):
    deploy_data = resp.json()
    print(f"✅ Deployment initiated!")
    print(f"   Deployment ID: {deploy_data.get('deployment_id', 'N/A')}")
else:
    print(f"⚠\ufe0f Deploy response: {resp.status_code} - {resp.text[:200]}")

# Final status
app_url = app_data.get("url", f"https://{APP_NAME}-<workspace>.azure.databricksapps.com")
print(f"\n{'='*60}")
print(f"\U0001f389 App URL: {app_url}")
print(f"{'='*60}")
print(f"\n⚠\ufe0f  Configure the app:")
print(f"   Go to: Compute > Apps > {APP_NAME} > Settings")
print(f"   Set env var: DATABRICKS_WAREHOUSE_ID = <your-warehouse-id>")
print(f"\n\U0001f4c1 Source files: {APP_SOURCE}/")
print(f"   app.py           - Streamlit dashboard (6 tabs)")
print(f"   app.yaml         - App configuration")
print(f"   requirements.txt - Python dependencies")
