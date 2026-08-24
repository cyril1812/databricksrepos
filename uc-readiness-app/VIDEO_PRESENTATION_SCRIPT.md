# 🎬 UC Readiness Accelerator — Video Presentation Script
## Databricks Unity Catalog Assessment Dashboard v1.0

---

## VIDEO METADATA
- **Title:** UC Readiness Accelerator — Assess, Score, and Fix Your Unity Catalog in Minutes
- **Duration:** 12–14 minutes
- **Target Audience:** Data Platform Engineers, Data Governance Teams, UC Migration Leads, CDOs
- **Tone:** Professional, consultative, demo-driven
- **Theme:** Light mode (white/blue professional palette)

---

## SCENE 1: OPENING HOOK (0:00 – 0:40)

### Visual
Fade in: split screen — left side shows a sprawling catalog of undocumented tables, right side shows the UC Readiness dashboard with a 73% GREEN score

### Narration
> "You've migrated to Unity Catalog. You've got hundreds — maybe thousands — of tables. But how do you know if they're *actually ready*? Are they documented? Governed? Genie-ready?
>
> Most teams find out the hard way — when an analyst can't find data, when compliance asks about access controls, or when Genie gives hallucinated answers because tables lack descriptions.
>
> Today I'll show you a tool that assesses every table in your catalog against enterprise governance standards, scores them with RAG status, and lets you fix gaps — all from a single app."

### Key Talking Point
- Problem: UC migration ≠ UC readiness (documentation, governance, quality gaps)
- Solution: automated assessment + one-click remediation

---

## SCENE 2: ARCHITECTURE & DATA MODEL (0:40 – 1:45)

### Visual
Architecture diagram showing the assessment pipeline flow:
- **Bronze Layer**: `information_schema` tables, system tables → raw metadata
- **Silver Layer**: Dimension-specific assessments (metadata, governance, quality, performance, Genie)
- **Gold Layer**: Aggregated scores, recommendations, executive summaries

### Narration
> "The app is built on a medallion architecture inside Unity Catalog. A pipeline notebook scans `information_schema`, Databricks system tables, lineage metadata, and effective policy metadata to produce bronze-level raw inventory.
>
> Silver tables assess each dimension independently — metadata completeness, governance posture, ABAC policy coverage, data quality signals, query performance, Genie readiness, and compliance-aligned controls that are observable directly in Databricks.
>
> Gold tables aggregate everything into table-level scores, category rollups, executive summaries, and prioritized recommendations. The Streamlit app reads from `governiq.uc_assessment` and walks through executive summary, detailed assessment, compute, recommendations, FinOps, performance, Genie readiness, compliance, AI insights, rules, and remediation actions."

### Show on Screen
- Schema diagram: `bronze_columns` + `bronze_abac_policy_coverage` → `silver_governance_assessment` → `gold_table_scores` / `gold_recommendations`
- `app.yaml` configuration (Streamlit app)
- Connection setup with SQL Warehouse
- Highlight that ABAC inventory is captured from effective table policies and unsupported assets are tracked separately

---

## SCENE 3: CONNECTING & GLOBAL FILTERS (1:45 – 2:30)

### Visual
Live demo: Sidebar with SQL Warehouse ID → Connected → Catalog/Schema filters

### Narration
> "Enter your SQL Warehouse ID, and the app connects securely using your workspace credentials. No tokens, no secrets.
>
> Global filters let you scope the assessment to a specific catalog or schema — essential for large environments where different teams own different domains. Every tab respects these filters, so you can drill down to just your team's tables."

### Demo Actions
1. Enter warehouse ID → show green "Connected" indicator
2. Show catalog dropdown (All, democatalog, etc.)
3. Select a specific schema → show filter pills appearing
4. Show the "Source: democatalog.uc_assessment" caption

---

## SCENE 4: EXECUTIVE SUMMARY TAB (2:30 – 3:45)

### Visual
Tab 1: Executive Summary — RAG banner, metric cards, gauge charts, key indicators

### Narration
> "The Executive Summary gives leadership a single-glance view of UC health. The overall readiness score is front and center with a color-coded RAG banner — RED below 40%, AMBER between 40 and 70%, GREEN above 70%.
>
> Six metric cards show total catalogs, tables, columns, recommendations, high-priority issues, and DBU consumption. Below that, gauge charts break down scores across five dimensions: Metadata, Governance, Data Quality, Performance, and Genie Readiness.
>
> Key indicators surface the most actionable numbers: what percentage of tables have descriptions, how many columns are documented, Delta format adoption rate, freshness, and Genie readiness."

### Demo Actions
1. Show the RAG banner (e.g., "Overall Readiness Score: 58% AMBER")
2. Walk through the six metric cards
3. Point out the five gauge charts — identify the weakest dimension
4. Show key indicators row (tables with descriptions %, columns documented %, etc.)

### Key Value Proposition
> "A CDO can open this tab and in 10 seconds know: we're AMBER at 58%, our biggest gap is Governance at 34%, and we have 127 high-priority recommendations to address."

---

## SCENE 5: DETAILED ASSESSMENT TAB (3:45 – 4:45)

### Visual
Tab 2: Detailed Assessment — pie chart (RAG distribution), histogram (score spread), bar chart (by catalog), table detail grid

### Narration
> "Detailed Assessment lets you explore individual table health. The RAG distribution pie chart shows what proportion of tables are RED, AMBER, or GREEN. The score histogram reveals whether you have a bimodal distribution — some tables well-maintained, others neglected.
>
> The grouped bar chart compares category scores across catalogs, instantly revealing which catalogs are governance-rich and which need attention. Below, a filterable data grid shows every table with its scores and RAG status — sortable, searchable, and color-coded."

### Demo Actions
1. Show RAG pie chart (e.g., 40% RED, 35% AMBER, 25% GREEN)
2. Point out the score histogram with RED/GREEN threshold lines at 40 and 70
3. Show category scores grouped by catalog
4. Filter the table grid by "RED only" to show critical tables
5. Sort by overall_score ascending to find worst-performing assets

---

## SCENE 6: RECOMMENDATIONS TAB (4:45 – 6:00)

### Visual
Tab 4: Recommendations — severity counters, ABAC inventory summary, category/severity chart, ABAC-focused recommendation grid, filterable recommendation list

### Narration
> "The Recommendations tab turns assessment data into a prioritized action plan. At the top, you still get the overall HIGH, MEDIUM, and LOW severity counts, but now the view also surfaces ABAC inventory statistics so teams can see not just what needs a policy, but whether a table was actually scannable for policy coverage.
>
> A grouped bar chart shows where recommendations cluster by category and severity. Right below that, the app highlights ABAC-focused recommendations — including assets that are unsupported for ABAC inventory and sensitive tables that carry governance tags but still lack masking or row-filter policies.
>
> The recommendation list then shows exactly what to fix: which table, what category, the current state, and the target state. That makes it easy to split sprint work between metadata cleanup, RBAC hardening, and ABAC policy rollout."

### Demo Actions
1. Show severity counters at the top of the tab
2. Open the ABAC Inventory Summary and point out scanned vs unsupported assets
3. Show the ABAC-focused recommendation rows
4. Display the category × severity bar chart
5. Filter to `HIGH` severity only
6. Filter to `Governance` or ABAC-related recommendations
7. Open one recommendation and compare `current_value` to `target_value`

### Key Value Proposition
> "Instead of a vague 'improve governance,' the tool tells you whether a table is untagged, missing explicit access controls, unsupported for ABAC inventory, or sensitive but still lacking masking and row filters. That specificity turns recommendations into executable backlog items."

---

## SCENE 7: FinOps INSIGHTS TAB (5:45 – 6:30)

### Visual
Tab 4: FinOps Insights — DBU consumption by product, top SKUs, expensive queries table

### Narration
> "FinOps Insights connects governance to cost. You see DBU consumption by billing product — SQL warehouses, jobs, model serving, interactive clusters — revealing where compute spend concentrates.
>
> The top 15 SKUs breakdown shows exactly which resource types drive cost. And the expensive queries table surfaces the heaviest individual statements — helping you identify optimization candidates or runaway processes."

### Demo Actions
1. Show DBU consumption bar chart (top 12 products)
2. Show top SKUs by usage
3. Scroll through the expensive queries table
4. Note the workspace-level scope indicator (not affected by catalog filter)

---

## SCENE 8: PERFORMANCE TAB (6:30 – 7:10)

### Visual
Tab 5: Performance — avg duration by statement type (color-coded GOOD/MODERATE/POOR), query volume chart, detail table

### Narration
> "The Performance tab categorizes query patterns into GOOD, MODERATE, and POOR based on average duration. Statement types — SELECT, MERGE, INSERT — are individually assessed.
>
> If your MERGE statements are POOR while SELECTs are GOOD, you know exactly where to focus optimization efforts. The detail view shows query counts alongside performance categories for a complete operational picture."

### Demo Actions
1. Show avg duration bar chart with color-coded performance categories
2. Show query volume by statement type
3. Show the performance detail table with color formatting

---

## SCENE 9: GENIE READINESS TAB (7:10 – 8:15)

### Visual
Tab 6: Genie Readiness — counters, score distribution histogram, ready/not-ready tables, quick wins

### Narration
> "This is where UC assessment meets AI readiness. Genie — Databricks' natural language analytics interface — needs well-documented, consistently named, lineage-connected tables to deliver accurate answers.
>
> The Genie Readiness score evaluates each table on five criteria: has a description, columns are documented, naming is compliant, lineage exists, and it's a gold-layer candidate. Tables scoring 70% or above are Genie-ready.
>
> The Quick Wins section is gold — it tells you exactly which single actions would unlock the most tables for Genie: 'Add table descriptions for 45 tables' or 'Fix naming conventions for 12 tables.'"

### Demo Actions
1. Show counters: Total Tables, Genie Ready, Not Ready, Gold Candidates
2. Show score distribution histogram with the 70% threshold line
3. Expand the "Genie-Ready Tables" list (score >= 70%)
4. Expand the "Tables Needing Improvement" list
5. Show Quick Wins recommendations ordered by impact

### Key Value Proposition
> "If your goal is to enable Genie for self-service analytics, this tab tells you exactly how many tables are ready today and what minimal effort gets the next batch across the line."

---

## SCENE 10: COMPLIANCE TAB (8:15 – 9:10)

### Visual
Tab 8: Compliance — compliance score histogram, Databricks-native control mapping, ABAC coverage metrics, unsupported tables summary, ABAC recommendations

### Narration
> "The Compliance tab is intentionally cloud-agnostic. It only scores controls that can be observed directly inside Databricks — Unity Catalog tags, grants, lineage, managed Delta posture, documentation coverage, and effective ABAC policy inventory.
>
> At the top, the app summarizes average compliance score along with classified assets, least-privilege coverage, audit traceability, and a second row of ABAC metrics: protected tables, masked tables, row-filtered tables, and tables that are unsupported for ABAC inventory.
>
> A dedicated ABAC Coverage Overview breaks down scanned versus unsupported tables, and an unsupported-table summary makes it explicit when a table could not participate in ABAC inventory — for example Databricks sample assets or other non-governable objects. That keeps the score honest instead of silently treating unsupported assets as failures.
>
> The lower section ties everything back to action with ABAC recommendations and a compliance gap table that explains the top issue for each weak asset."

### Demo Actions
1. Show the cloud-agnostic compliance framing message at the top
2. Walk through the compliance KPI row and the ABAC KPI row
3. Open the compliance score distribution chart
4. Show the ABAC Coverage Overview table
5. Scroll through the unsupported tables summary and point out example error messages
6. Show the covered vs out-of-scope control matrices
7. Open the ABAC recommendations section and then the assets-needing-attention grid

### Key Value Proposition
> "This tab gives compliance and governance teams a defensible score based only on Databricks-native evidence — while still documenting where ABAC inventory is unsupported or out of scope instead of hiding that nuance."

---

## SCENE 11: ASSESSMENT RULES TAB (9:10 – 9:45)

### Visual
Tab 10: Assessment Rules — methodology explanation, RAG thresholds, category weights, rule cards with severity/weight

### Narration
> "Full transparency on how scores are calculated. The methodology section explains the three RAG bands: RED below 40% means critical gaps blocking adoption, AMBER means partially ready with notable improvement areas, GREEN above 70% means production-ready.
>
> Category weights are documented, and every individual rule is displayed as a card showing its ID, name, description, severity, and weight in the overall score. This is also where teams can explain why ABAC coverage, documentation, RBAC, and compliance checks appear in the score the way they do."

### Demo Actions
1. Show the three RAG threshold cards (RED / AMBER / GREEN)
2. Show category weight explanation
3. Show the rule weights bar chart
4. Browse rule cards by category (Metadata Readiness, Governance, Data Quality, Compliance, etc.)
5. Point out severity indicators (HIGH = red, MEDIUM = amber, LOW = blue)

---

## SCENE 12: ACTIONS TAB — QUICK FIX (9:45 – 10:30)

### Visual
Tab 8 (Actions) → Quick Fix sub-view — table descriptions, governance tags, OPTIMIZE, column descriptions, external tables

### Narration
> "This is where the app goes from assessment to action. The Quick Fix view lets you remediate gaps directly — no switching to a notebook or SQL editor.
>
> Select a table missing a description, type a business-friendly comment, click Apply — and a `COMMENT ON TABLE` statement executes immediately against your catalog. Same for governance tags with `ALTER TABLE SET TAGS`, column descriptions, and even running `OPTIMIZE` on Delta tables.
>
> The external tables section flags non-managed tables that lack UC governance benefits, prompting you to consider migration to managed tables."

### Demo Actions
1. Show "Add Table Description" card — select a table, type a description, click Apply
2. Show success message
3. Show "Add Governance Tags" card — set a classification tag
4. Show "Run OPTIMIZE" — select a Delta table, execute
5. Show "Add Column Description" — pick an undocumented column
6. Show external/foreign tables review section

### Key Value Proposition
> "One person can fix 50 table descriptions in 10 minutes without leaving the app. That's the difference between assessment reports that gather dust and ones that drive immediate improvement."

---

## SCENE 13: ACTIONS TAB — EXPORT & SCRIPTS (10:30 – 11:10)

### Visual
Tab 8 (Actions) → Export & Scripts sub-view — CSV export, SQL script generation, Excel Scorecard

### Narration
> "For teams that need offline workflows or management reporting, the Export section delivers. Download recommendations as CSV for Jira import or sprint planning.
>
> The SQL Script Generator creates ready-to-run fix scripts — `COMMENT ON TABLE` statements for all undocumented tables, `ALTER TABLE SET TAGS` for untagged assets, even conversion notes for non-Delta tables. Copy it into a notebook and run.
>
> The crown jewel is the Excel Scorecard — a multi-sheet workbook matching enterprise Data Governance Readiness Framework format. It includes Instructions, a Scorecard with 1–4 ratings per dimension, an Executive Dashboard with maturity levels, a Recommendations action plan with priority/effort/owner/status tracking, and per-asset rule details."

### Demo Actions
1. Click "Download CSV" for recommendations
2. Generate SQL script with "Missing Table Descriptions" selected → show code output
3. Click "Generate Excel Scorecard" → download the XLSX
4. Open the Excel file briefly showing the five professional sheets

---

## SCENE 14: ACTIONS TAB — BULK IMPORT (11:10 – 11:50)

### Visual
Tab 8 (Actions) → Bulk Import sub-view — CSV template downloads, upload, preview SQL, apply

### Narration
> "For large-scale remediation, Bulk Import accepts CSV files to apply changes at scale. Download a template, fill it with your team's knowledge — table descriptions, column comments, or metric view definitions — then upload.
>
> The app previews the generated SQL before execution, so you can verify exactly what will change. Click Apply, and a progress bar tracks each statement. Successes and failures are clearly separated, with error details available for troubleshooting."

### Demo Actions
1. Download the table descriptions template → show the CSV format (catalog, schema, table_name, description)
2. Upload a pre-filled example CSV
3. Show the "Preview SQL (dry run)" expander
4. Click "Apply All Table Descriptions" → show progress bar
5. Show success count and any errors
6. Show the Metric Views upload section — CREATE VIEW + COMMENT in one step

### Key Value Proposition
> "A data steward can prepare 200 table descriptions in a spreadsheet, upload once, and apply them all in 30 seconds. That's bulk governance at the speed of a single click."

---

## SCENE 15: CLOSING & RECAP (11:50 – 12:30)

### Visual
Side-by-side: Before (undocumented catalog, RED status) → After (documented, GREEN status)

### Narration
> "To summarize: the UC Readiness Accelerator gives you complete visibility into Unity Catalog health, scores every table against Databricks-native governance standards, surfaces prioritized recommendations, and now makes ABAC coverage visible end to end — including scanned assets, unsupported assets, and policy-specific follow-up actions.
>
> Deploy it as a Databricks App, connect your SQL warehouse, and within minutes you'll know where your catalog stands, which controls are covered directly in Databricks, and what to do next through Quick Fix, exports, or bulk remediation."

### Closing Slide
- **Assessment Dimensions:** Metadata, Governance, Data Quality, Performance, Genie Readiness, Compliance
- **Scoring:** RAG status (RED <40%, AMBER 40–70%, GREEN >70%)
- **ABAC Visibility:** Protected, masked, row-filtered, scanned, and unsupported assets
- **Actions:** Quick Fix, SQL Scripts, Excel Scorecard, Bulk CSV Import
- **Tech Stack:** Streamlit, Databricks SQL, Plotly, openpyxl
- **Data Source:** `governiq.uc_assessment` (medallion architecture)

---

## PRODUCTION NOTES

### Recommended Screen Recording Setup
- **Resolution:** 1920x1080 or 2560x1440
- **Browser:** Chrome/Edge (standard mode — app uses light theme)
- **Font Size:** Browser zoom 110–125% for readability
- **App Theme:** Light (white background, blue/slate accents)

### Data Preparation
Before recording, ensure assessment tables are populated with varied results:
- Mix of RED, AMBER, and GREEN tables for visual variety
- At least 2–3 catalogs with different scores for comparison charts
- Some tables with missing descriptions (for Actions demo)
- Some tables without tags (for governance demo)
- Some tagged or sensitive tables without ABAC policies (for ABAC recommendation demo)
- Some unsupported/sample tables that appear in the ABAC inventory exceptions list
- At least one non-Delta table (for quality assessment)

### B-Roll Suggestions
- Gauge chart animation filling up (Plotly transitions)
- RAG status badge switching from RED → GREEN after a fix
- Excel scorecard file opening in Excel/Google Sheets
- Bulk import progress bar completing
- SQL script scrolling with syntax highlighting
- Architecture diagram animation (Bronze → Silver → Gold)

### Transitions
- Use tab switching as natural scene transitions (built into the app UX)
- Close-up on metric cards when discussing specific numbers
- Zoom into chart legends when explaining color coding

### Music/Audio
- Professional, upbeat corporate tech background
- Volume ducked during narration
- Subtle click sounds when demonstrating button interactions (optional)

### Post-Production
- Lower-third captions for key terms: "RAG Status", "Genie Readiness", "Medallion Architecture"
- Highlight cursor/pointer during click demonstrations
- Add chapter markers for each scene (YouTube compatibility)
- Consider a thumbnail showing: gauge at 73% GREEN with "UC Ready?" text

---

## APPENDIX: KEY TALKING POINTS FOR Q&A

### "How does it differ from Databricks built-in tools?"
> "Unity Catalog provides the infrastructure — this app provides the assessment layer. It evaluates whether your *usage* of UC meets governance standards, documentation completeness, and Genie readiness. Think of it as a governance audit tool built on top of UC's system tables."

### "What tables does it scan?"
> "It scans `information_schema` metadata, Databricks system tables for billing, query history, and access signals, plus effective Unity Catalog policy metadata for ABAC inventory. The pipeline synthesizes those sources into bronze, silver, and gold assessment layers and reports unsupported assets separately when ABAC inventory cannot be applied."

### "Can I customize the rules?"
> "Yes. Rules are stored in `assessment_rules` table with weights and severities. Add your own organization-specific rules, adjust weights, or change severity thresholds."

### "Does it modify my data?"
> "Only in the Actions tab — and only when you explicitly click Apply. The assessment itself is read-only. Quick Fix actions use standard DDL such as `COMMENT ON`, `ALTER TABLE SET TAGS`, and `OPTIMIZE`. The ABAC inventory step is read-only as well; it only inspects effective policies and records coverage results."

### "How do I deploy it?"
> "It's a Databricks App — `app.yaml` defines the Streamlit command. Deploy with `databricks apps deploy` or via the UI. It needs a SQL Warehouse with access to the assessment schema, Unity Catalog metadata, and the target catalogs you want to assess."

---

## FILE REFERENCE (Application Structure)

```
uc-readiness-app/
├── app.py              # Main Streamlit app (executive, recommendations, compliance, actions, and more)
├── app.yaml            # Databricks App configuration
└── requirements.txt    # Python dependencies (streamlit, plotly, openpyxl, databricks-sql-connector)
```

### Data Schema (`governiq.uc_assessment`)
```
Bronze:
  ├── bronze_columns                  — Raw column metadata
  ├── bronze_abac_policy_coverage     — Table-level ABAC inventory scan results
  └── bronze_abac_effective_policies  — Effective row filters and column masks by table

Silver:
  ├── silver_metadata_assessment      — Table/column documentation scores
  ├── silver_governance_assessment    — Tags, privileges, managed status, ABAC coverage metrics
  ├── silver_quality_assessment       — Delta format, freshness, format type
  ├── silver_performance_assessment   — Query duration, volume, categories
  └── silver_genie_readiness          — Composite Genie readiness score

Gold:
  ├── gold_executive_summary          — Single-row overall metrics
  ├── gold_table_scores               — Per-table composite scores + RAG
  ├── gold_category_scores            — Category aggregations by catalog
  ├── gold_recommendations            — Prioritized fix actions, including ABAC issues
  ├── gold_cost_by_product            — DBU by billing product
  ├── gold_cost_by_sku                — DBU by SKU
  ├── gold_expensive_queries          — Top costly queries
  └── assessment_rules                — Rule definitions (ID, weight, severity)
```
