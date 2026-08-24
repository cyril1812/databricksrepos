# GovernIQ — Complete KPI Reference Guide
## UC Readiness Accelerator v1.0

---

## LEVEL 1: OVERALL READINESS SCORE

| KPI | Description | Formula | Range | RAG Thresholds |
| --- | --- | --- | --- | --- |
| Overall UC Readiness Score | Weighted average of 4 core category percentages | AVG(Metadata%, Governance%, Data Quality%, Genie%) | 0–100% | RED <40, AMBER 40–69, GREEN ≥70 |

---

## LEVEL 2: CORE CATEGORY SCORES (Table-Level Assessment)

Each table is scored individually, then category scores are aggregated as AVG across all tables.

### 1. Metadata Readiness Score

**Per-table max: 5.0 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Table Description | META_001 | Table has a non-empty comment/description | `CASE WHEN comment IS NOT NULL AND comment != '' THEN 2.0 ELSE 0 END` | 2.0 |
| Column Documentation | META_002 | Percentage of columns with descriptions | `(documented_columns / total_columns) × 2.0` | 0–2.0 |
| Naming Convention | META_003 | Table follows lowercase snake_case pattern | `CASE WHEN table_name RLIKE '^[a-z][a-z0-9_]* THEN 1.0 ELSE 0 END` | 1.0 |

**Category Percentage:** `AVG(all table metadata_scores) / 5.0 × 100`

---

### 2. Governance Score

**Per-table max: 5.0 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Has Tags | GOV_001 | Table has at least one governance tag | `CASE WHEN tag_count > 0 THEN 1.5 ELSE 0 END` | 1.5 |
| Has Explicit Grants | GOV_002 | Table has explicit privilege grants defined | `CASE WHEN grant_count > 0 THEN 1.5 ELSE 0 END` | 1.5 |
| No Over-Permissioning | GOV_003 | No ALL PRIVILEGES grants on the table | `CASE WHEN over_permissioned_grants = 0 THEN 1.0 ELSE 0 END` | 1.0 |
| Is Managed Table | GOV_004 | Table is Unity Catalog managed (not external) | `CASE WHEN table_type = 'MANAGED' THEN 1.0 ELSE 0 END` | 1.0 |

**Category Percentage:** `AVG(all table governance_scores) / 5.0 × 100`

---

### 3. Data Quality Score

**Per-table max: 5.0 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Delta Format | DQ_002 | Table uses Delta format (enables OPTIMIZE, Z-ORDER, time travel) | `CASE WHEN data_source_format = 'DELTA' THEN 2.5 ELSE 0 END` | 2.5 |
| Freshness (30d) | DQ_001 | Table was modified within the last 30 days | `CASE WHEN last_altered >= current_date() - 30 THEN 2.5 ELSE 0 END` | 2.5 |

**Category Percentage:** `AVG(all table quality_scores) / 5.0 × 100`

---

### 4. Genie Readiness Score

**Per-table max: 100 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Table Description | GENIE_001 | Table has documentation for Genie AI | `has_table_description × 20` | 20 |
| Column Documentation | GENIE_003 | At least 80% of columns documented | `MIN(column_doc_pct, 100) / 100 × 30` | 0–30 |
| Business-Friendly Naming | GENIE_001 | No numeric suffixes or cryptic abbreviations | `naming_compliant × 15` | 15 |
| Has Lineage | GENIE_002 | Table has lineage connections (used in pipelines) | `CASE WHEN lineage_connection_count > 0 THEN 15 ELSE 0 END` | 15 |
| Gold Layer Candidate | — | Schema matches gold/curated/mart OR name matches fact_/dim_ | `CASE WHEN schema RLIKE '(gold|curated|mart)' OR name RLIKE '^(fact|dim)_' THEN 20 ELSE 0 END` | 20 |

**Category Percentage:** `AVG(all table genie_readiness_scores) / 100 × 100`

---

### 5. Performance Score

| Component | Rule ID | Description | Formula | Assessment |
| --- | --- | --- | --- | --- |
| Delta Format | PERF_001 | Enables OPTIMIZE and Z-ORDER | Binary check per table | GOOD/POOR |
| Query Duration | PERF_002 | Avg query duration by statement type | Categorized: GOOD (<5s), MODERATE (5–30s), POOR (>30s) | Per statement type |

**Category Percentage:** `100%` when all tables are Delta and queries perform well.

---

## LEVEL 3: EXTENDED CATEGORY SCORES

### 6. UC Functions Score

**Per-function max: 100 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Has Description | FN_001 | Function has a description/comment | `CASE WHEN comment IS NOT NULL THEN 40 ELSE 0 END` | 40 |
| Naming Convention | FN_002 | Function follows lowercase snake_case | `CASE WHEN name RLIKE '^[a-z][a-z0-9_]* THEN 20 ELSE 0 END` | 20 |
| Security Mode | FN_003 | Function uses DEFINER security type | `CASE WHEN security_type = 'DEFINER' THEN 40 ELSE 0 END` | 40 |

**Category Percentage:** `AVG(function_readiness_score)`

---

### 7. ML Models Score

**Per-model max: 100 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Has Description | ML_001 | Registered model has a description | `CASE WHEN has_description = 1 THEN 30 ELSE 0 END` | 30 |
| Naming Convention | — | Model follows snake_case naming | `CASE WHEN naming_compliant = 1 THEN 20 ELSE 0 END` | 20 |
| Has Versions | ML_003 | Model has at least one registered version | `CASE WHEN has_versions = 1 THEN 30 ELSE 0 END` | 30 |
| Has Tags | ML_002 | Model has governance tags | `CASE WHEN has_tags = 1 THEN 10 ELSE 0 END` | 10 |
| Production Ready | — | Description + versions + naming all present | `CASE WHEN is_production_ready = 1 THEN 10 ELSE 0 END` | 10 |

**Category Percentage:** `AVG(model_readiness_score)`

---

### 8. Volumes Score

**Per-volume max: 100 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Has Description | VOL_001 | Volume has a description/comment | `CASE WHEN has_description = 1 THEN 50 ELSE 0 END` | 50 |
| Naming Convention | VOL_002 | Volume follows lowercase snake_case | `CASE WHEN naming_compliant = 1 THEN 30 ELSE 0 END` | 30 |
| Is Managed | — | Volume is managed type (not external) | `CASE WHEN is_managed = 1 THEN 20 ELSE 0 END` | 20 |

**Category Percentage:** `AVG(volume_readiness_score)`

---

### 9. Clusters Score

**Per-cluster max: 100 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| UC Security Mode | CLU_001 | Cluster has Unity Catalog security mode enabled | `CASE WHEN has_security_mode = 1 THEN 25 ELSE 0 END` | 25 |
| Current DBR (15+) | CLU_002 | Runs Databricks Runtime 15+ for latest features | `CASE WHEN has_current_dbr = 1 THEN 15 ELSE 0 END` | 15 |
| Auto-Termination ≤120m | CLU_003 | Auto-terminates within 120 minutes | `CASE WHEN has_reasonable_auto_term = 1 THEN 20 ELSE 0 END` | 20 |
| Cluster Policy | CLU_004 | Governance policy is attached | `CASE WHEN has_cluster_policy = 1 THEN 15 ELSE 0 END` | 15 |
| Autoscaling | CLU_005 | Min workers < max workers | `CASE WHEN has_autoscaling = 1 THEN 15 ELSE 0 END` | 15 |
| Has Tags | CLU_006 | Custom tags for cost attribution | `CASE WHEN has_tags = 1 THEN 10 ELSE 0 END` | 10 |

**Category Percentage:** `AVG(cluster_readiness_score)`

---

### 10. SQL Warehouses Score

**Per-warehouse max: 100 points**

| Component | Rule ID | Description | Formula | Points |
| --- | --- | --- | --- | --- |
| Is Serverless | WH_001 | Warehouse type is Serverless | `CASE WHEN is_serverless = 1 THEN 30 ELSE 0 END` | 30 |
| Modern Type | — | PRO or SERVERLESS (not CLASSIC) | `CASE WHEN is_modern_type = 1 THEN 20 ELSE 0 END` | 20 |
| Efficient Auto-Stop | WH_002 | Auto-stop configured ≤ 15 minutes | `CASE WHEN has_efficient_auto_stop = 1 THEN 20 ELSE 0 END` | 20 |
| Has Scaling | — | Max clusters > 1 for elasticity | `CASE WHEN has_scaling = 1 THEN 15 ELSE 0 END` | 15 |
| Has Tags | WH_003 | Tags for cost attribution | `CASE WHEN has_tags = 1 THEN 10 ELSE 0 END` | 10 |
| Current Channel | — | Uses CURRENT release channel | `CASE WHEN on_current_channel = 1 THEN 5 ELSE 0 END` | 5 |

**Category Percentage:** `AVG(warehouse_readiness_score)`

---

## LEVEL 4: EXECUTIVE DASHBOARD KPIs

| # | KPI Name | Description | Data Source | Calculation |
| --- | --- | --- | --- | --- |
| 1 | Total Catalogs | Count of distinct catalogs assessed | `gold_table_scores` | `COUNT(DISTINCT table_catalog)` |
| 2 | Total Tables | Count of tables assessed | `gold_table_scores` | `COUNT(*)` |
| 3 | Total Columns | Sum of columns across all tables | `silver_metadata_assessment` | `SUM(total_columns)` |
| 4 | Total Recommendations | Remediation items generated | `gold_recommendations` | `COUNT(*)` |
| 5 | HIGH Priority | Critical severity recommendations | `gold_recommendations` | `COUNT(*) WHERE severity = 'HIGH'` |
| 6 | DBUs (30d) | Total DBU consumption in billing period | `bronze_billing_usage` | `SUM(usage_quantity) WHERE usage_type='COMPUTE_TIME'` |
| 7 | UC Functions | Registered UC functions | `system.information_schema.routines` | `COUNT(*)` |
| 8 | ML Models | Registered ML models | `gold_models_summary` | `COUNT(*)` |
| 9 | Volumes | UC volumes | `system.information_schema.volumes` | `COUNT(*)` |
| 10 | Clusters | Interactive clusters | `gold_clusters_summary` | `COUNT(*)` |
| 11 | SQL Warehouses | SQL warehouses | `gold_warehouses_summary` | `COUNT(*)` |
| 12 | Streaming Tables | STREAMING_TABLE type assets | `silver_metadata_assessment` | `COUNT(*) WHERE table_type='STREAMING_TABLE'` |
| 13 | Tables with Descriptions % | % tables with non-null comments | `silver_metadata_assessment` | `AVG(has_table_description) × 100` |
| 14 | Columns Documented % | Average column documentation percentage | `silver_metadata_assessment` | `AVG(column_doc_pct)` |
| 15 | Delta Format % | % tables using Delta format | `silver_quality_assessment` | `AVG(is_delta) × 100` |
| 16 | Fresh Tables (30d) % | % tables modified within 30 days | `silver_quality_assessment` | `AVG(is_fresh) × 100` |
| 17 | Genie-Ready Count | Tables scoring ≥70 on Genie readiness | `silver_genie_readiness` | `COUNT(*) WHERE genie_readiness_score >= 70` |

---

## LEVEL 5: FINOPS KPIs

| # | KPI Name | Description | Formula | Visualization |
| --- | --- | --- | --- | --- |
| 1 | Total DBUs | Total compute DBUs consumed | `SUM(usage_quantity) WHERE usage_type='COMPUTE_TIME'` | Counter |
| 2 | Daily Average | Mean daily DBU consumption | `total_dbus / COUNT(DISTINCT usage_date)` | Counter |
| 3 | 30-Day Forecast | Projected monthly burn rate | `last_7d_daily_avg × 30` | Counter |
| 4 | Active Users | Distinct billing identities | `COUNT(DISTINCT identity_metadata.created_by)` | Counter |
| 5 | Serverless vs Classic | Split of compute type | `SUM(CASE WHEN sku LIKE '%SERVERLESS%' ...)` | Donut chart |
| 6 | Cost by Product | DBU breakdown by product | `GROUP BY billing_origin_product` | Horizontal bar |
| 7 | Cost by User | Per-user DBU attribution | `GROUP BY identity_metadata.created_by` | Bar + table |
| 8 | Day-of-Week Pattern | Usage distribution across days | `GROUP BY DAYOFWEEK(usage_date), product` | Heatmap |
| 9 | Top SKUs | Highest-consuming SKU names | `GROUP BY sku_name ORDER BY total DESC` | Table |
| 10 | Top Expensive Queries | Longest-running queries | `ORDER BY total_duration_ms DESC` | Table |
| 11 | Burn Rate Trend | Increasing / Stable / Decreasing | `last_7d_avg vs prior_7d_avg (±20% threshold)` | Metric + insight |

---

## LEVEL 6: PERFORMANCE KPIs

| # | KPI Name | Description | Formula | Visualization |
| --- | --- | --- | --- | --- |
| 1 | P50 Latency | Median query duration | `PERCENTILE(total_duration_ms, 0.5)` | Counter |
| 2 | P95 Latency | 95th percentile duration (SLA metric) | `PERCENTILE(total_duration_ms, 0.95)` | Counter |
| 3 | P99 Latency | 99th percentile duration | `PERCENTILE(total_duration_ms, 0.99)` | Counter |
| 4 | Avg Queue Time | Time waiting for compute resources | `AVG(waiting_for_compute_duration_ms)` | Counter |
| 5 | Failed Query Rate | Percentage of failed queries | `SUM(CASE WHEN status='FAILED') / COUNT(*) × 100` | Counter |
| 6 | Spill-to-Disk Count | Queries with memory pressure | `COUNT(*) WHERE spilled_local_bytes > 0` | Table |
| 7 | Latency by Type | P50/P95/P99 per statement type | `PERCENTILE(...) GROUP BY statement_type` | Grouped bar |
| 8 | Time Breakdown | Queue vs Compile vs Execute phases | `AVG(waiting + compile + execution)` | Stacked bar |
| 9 | Peak Hour Heatmap | Query volume by day × hour | `COUNT(*) GROUP BY DOW, HOUR` | Heatmap |
| 10 | Duration Trend | Daily avg + P95 latency over time | `AVG/P95 GROUP BY DATE(start_time)` | Line + bar |
| 11 | Regression Detection | Auto-detect latency degradation | `last_7d_avg > prior_7d_avg × 1.2` | Alert callout |
| 12 | Failed Query Patterns | Top error messages by frequency | `GROUP BY error_message ORDER BY COUNT DESC` | Bar + table |
| 13 | Hot Tables | Most referenced tables from lineage | `COUNT(*) GROUP BY target_table` | Horizontal bar |
| 14 | Throttled Queries | Queries waiting >5s at capacity | `SUM(waiting_at_capacity_ms > 5000)` | Per warehouse |
| 15 | Warehouse Sizing | Scale Up / Right-Sized / Monitor | Rule: queue>2s OR throttle>10% → Scale Up | Card per WH |

---

## RAG THRESHOLDS (Universal)

| Status | Score Range | Hex Color | Interpretation |
| --- | --- | --- | --- |
| RED | 0 – 39.9% | #ef4444 | Critical — immediate action required |
| AMBER | 40 – 69.9% | #f59e0b | Needs improvement — plan remediation |
| GREEN | 70 – 100% | #22c55e | Healthy — meets governance standards |

---

## ASSESSMENT RULES (31 Total)

| Category | Count | Rule IDs |
| --- | --- | --- |
| Metadata Readiness | 3 | META_001, META_002, META_003 |
| Governance | 4 | GOV_001, GOV_002, GOV_003, GOV_004 |
| Data Quality | 2 | DQ_001, DQ_002 |
| Performance | 2 | PERF_001, PERF_002 |
| Genie Readiness | 3 | GENIE_001, GENIE_002, GENIE_003 |
| UC Functions | 3 | FN_001, FN_002, FN_003 |
| ML Models | 3 | ML_001, ML_002, ML_003 |
| Volumes | 2 | VOL_001, VOL_002 |
| Clusters | 6 | CLU_001–CLU_006 |
| SQL Warehouses | 3 | WH_001, WH_002, WH_003 |

---

## DATA PIPELINE ARCHITECTURE

```
Bronze (Raw Ingestion)          Silver (Assessment)              Gold (Aggregation)
─────────────────────          ────────────────────             ──────────────────
bronze_tables          →       silver_metadata_assessment   →   gold_table_scores
bronze_columns         →       silver_governance_assessment →   gold_category_scores
bronze_table_privileges→       silver_quality_assessment    →   gold_recommendations
bronze_table_tags      →       silver_genie_readiness       →   gold_executive_summary
bronze_table_lineage   →       silver_performance_assessment→   gold_expensive_queries
bronze_billing_usage                                        →   gold_cost_by_product
bronze_query_history                                        →   gold_cost_by_sku
                                                            →   gold_models_summary
                                                            →   gold_functions_summary
                                                            →   gold_volumes_summary
                                                            →   gold_clusters_summary
                                                            →   gold_warehouses_summary
```

---

## TOTAL KPI COUNT

| Level | Category | KPI Count |
| --- | --- | --- |
| 1 | Overall Score | 1 |
| 2 | Core Categories (5) | 5 aggregate + 12 components |
| 3 | Extended Categories (5) | 5 aggregate + 20 components |
| 4 | Executive Dashboard | 17 |
| 5 | FinOps | 11 |
| 6 | Performance | 15 |
| — | Assessment Rules | 31 |
| **Total** | **Unique KPIs/Metrics** | **~80** |

---

*GovernIQ v1.0 | Schema: democatalog.uc_assessment | Generated: June 2026*
