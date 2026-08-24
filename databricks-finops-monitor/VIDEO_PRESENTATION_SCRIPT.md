# 🎬 Databricks FinOps Monitor — Video Presentation Script
## AI-Enhanced Edition v2.0

---

## VIDEO METADATA
- **Title:** Databricks FinOps Monitor — AI-Enhanced Cloud Cost Intelligence
- **Duration:** 8–10 minutes
- **Target Audience:** Cloud/Platform Engineers, FinOps Practitioners, Engineering Managers, CFOs
- **Tone:** Professional, demo-driven, value-focused

---

## SCENE 1: OPENING HOOK (0:00 – 0:30)

### Visual
Dark screen fade-in → Databricks logo → Dashboard overview shot (wide angle)

### Narration
> "Cloud costs are the silent killer of engineering budgets. A forgotten cluster here, an oversized warehouse there — and suddenly you're 40% over budget with no visibility into why.
>
> Today I'll show you how we built an AI-powered FinOps command center on Databricks that doesn't just monitor costs — it predicts, detects anomalies, enforces guardrails, and auto-remediates waste in real time."

### Key Talking Point
- Problem: lack of cost visibility, reactive cost management
- Solution: proactive, AI-driven FinOps on Databricks system tables

---

## SCENE 2: ARCHITECTURE OVERVIEW (0:30 – 1:30)

### Visual
Architecture diagram showing:
- Databricks System Tables (billing.usage, compute.clusters, lakeflow.jobs)
- Streamlit App (deployed as Databricks App)
- AI/ML Layer (LLM for chat + Isolation Forest for anomaly detection)
- Databricks SDK (for automated remediation actions)

### Narration
> "The architecture is elegantly simple. We query Databricks system tables directly — billing usage, compute clusters, job run timelines — through a SQL warehouse connection.
>
> The Streamlit app is deployed as a native Databricks App with dark-themed UI. On top of raw data, we layer three AI capabilities: an LLM-powered FinOps agent using Meta Llama 3.3 70B for natural language queries, anomaly detection using Z-Score, IQR, and Isolation Forest algorithms, and automated remediation via the Databricks SDK."

### Show on Screen
- `app.yaml` config (Streamlit command, dark theme)
- Module dependency diagram: `finops_anomaly.py`, `finops_budget.py`, `finops_remediation.py`, `finops_guardrails.py`, `finops_action_plan.py`

---

## SCENE 3: CONNECTING & FILTERING (1:30 – 2:15)

### Visual
Live demo: Sidebar with SQL Warehouse ID input → Connection success → Filters panel

### Narration
> "Getting started is simple. Enter your SQL Warehouse ID and the app connects securely using your Databricks credentials — no API keys to manage.
>
> From the sidebar, you can filter by Azure subscription, workspace name, date range, and SLA thresholds. The app dynamically loads workspace mappings from a Unity Catalog table, so multi-workspace environments are first-class citizens."

### Demo Actions
1. Enter warehouse ID → show "Connected" success
2. Show subscription multi-select dropdown
3. Show workspace filter
4. Adjust date range (last 30 days)
5. Set SLA threshold to 60 minutes

---

## SCENE 4: JOB MONITORING TAB (2:15 – 3:15)

### Visual
Tab 1: Job Monitoring Dashboard — metric cards, failure charts, SLA breaches

### Narration
> "The Job Monitoring tab gives you instant visibility into your Lakeflow Jobs health. At the top, metric cards show total runs, success rate, average duration, and SLA breach count.
>
> Below that, we surface failed jobs with AI-powered root cause analysis. The LLM examines error codes, termination reasons, and historical patterns to explain *why* a job failed — not just *that* it failed."

### Demo Actions
1. Show metric cards (total runs, success %, avg duration, SLA breaches)
2. Scroll to failure analysis section
3. Highlight an AI root cause explanation
4. Show the identity resolution (UUID → human-readable service principal names)

### Key Value Proposition
> "Instead of manually digging through logs, the AI tells you: 'This job failed because a upstream Delta table was being optimized during the read window. Consider adding retry logic or scheduling after the optimization window.'"

---

## SCENE 5: COST & FinOps TAB (3:15 – 4:15)

### Visual
Tab 2: Cost & FinOps — spending trends, cost by product/user/workspace, optimization recommendations

### Narration
> "The Cost & FinOps tab is the heart of the application. You see daily and cumulative spending trends with Plotly interactive charts. Costs are broken down by billing product — SQL warehouses, jobs, model serving, vector search, DLT pipelines, and more.
>
> We resolve every cost to an owner using identity metadata from system tables, plus audit log enrichment for services like Vector Search that report 'unknown' owners. No cost goes unattributed."

### Demo Actions
1. Show daily spend trend chart (stacked area by product)
2. Show cost-by-owner breakdown
3. Show workspace comparison view
4. Highlight the identity resolution logic (UUIDs → SP names)

---

## SCENE 6: AI COST FORECAST (4:15 – 5:00)

### Visual
Tab 3: AI Cost Forecast — prediction chart with confidence bands

### Narration
> "Predicting future costs lets you act before budgets are breached. Our AI forecast module projects spending trends forward, showing expected costs with confidence intervals.
>
> This isn't a simple linear extrapolation — it accounts for weekly seasonality patterns, growth trends, and historical anomaly exclusion to give you actionable projections."

### Demo Actions
1. Show forecast chart with historical actuals + predicted future
2. Point out confidence bands (upper/lower bounds)
3. Show projected monthly cost vs. budget comparison

---

## SCENE 7: BUDGET & ANOMALY DETECTION (5:00 – 6:00)

### Visual
Tab 5: Budget & Anomaly — budget utilization gauges, anomaly timeline, severity distribution

### Narration
> "Budget management meets intelligent anomaly detection. Set budgets by team, project, or workspace, and the system tracks burn rate in real time.
>
> For anomaly detection, we offer three methods: Z-Score for rolling-window statistical deviations, IQR for robust quartile-based outlier detection, and Isolation Forest — a machine learning algorithm from scikit-learn that catches complex, multi-dimensional anomalies that statistical methods miss."

### Demo Actions
1. Show budget utilization gauge/progress bars
2. Switch between anomaly detection methods (Z-Score → IQR → Isolation Forest)
3. Show anomaly timeline with flagged spikes
4. Show top offenders summary (which resources caused anomalies)

### Key Value Proposition
> "Last month, Isolation Forest caught a $1,200/day Vector Search endpoint that was provisioned for testing but never decommissioned. The Z-Score method missed it because the cost ramped up gradually."

---

## SCENE 8: GUARDRAILS & AUTO-REMEDIATION (6:00 – 7:15)

### Visual
Tab 6: Guardrails & Remediation — cluster compliance violations, idle cluster scan, runaway jobs, tag compliance

### Narration
> "This is where passive monitoring becomes active governance. The Guardrail Engine scans your environment for policy violations — clusters without auto-termination, oversized worker pools, missing cost-allocation tags.
>
> The Remediation Engine goes further. It scans for idle clusters with under 15% CPU utilization, identifies runaway jobs exceeding cost thresholds, and can automatically terminate, resize, or flag resources for review."

### Demo Actions
1. Show cluster compliance scan results (no auto-termination violations)
2. Show idle cluster scan (CPU/memory utilization below thresholds)
3. Show estimated waste cost per resource
4. Toggle dry_run mode on/off to explain safe vs. active remediation
5. Show audit log of all actions taken

### Key Value Proposition
> "In dry-run mode, it reports what it *would* do. Flip to active mode, and it uses the Databricks SDK to actually terminate abandoned clusters and stop idle warehouses — with full audit trails."

---

## SCENE 9: ACTION PLAN GENERATOR (7:15 – 8:00)

### Visual
Tab 7: Action Plan — prioritized resource cleanup table with DELETE/STOP/TERMINATE actions

### Narration
> "The Action Plan tab synthesizes everything into a single, prioritized cleanup list. It queries the last 7 days of billing, identifies every actively burning resource, projects monthly costs, and assigns priority levels: Critical for over $200/month, High for $50+, Medium for $10+.
>
> Each item has a specific recommended action: DELETE ENDPOINT for unused Vector Search, TERMINATE CLUSTER for abandoned compute, STOP APP for idle Databricks Apps."

### Demo Actions
1. Show prioritized action plan table (Critical → High → Medium → Low)
2. Highlight projected monthly savings total
3. Show action types (DELETE, TERMINATE, STOP, DISABLE, REVIEW)
4. Show integration with GuardrailEngine for enforcement

---

## SCENE 10: AI FinOps AGENT (8:00 – 9:00)

### Visual
Tab 8: AI FinOps Agent — chat interface with natural language queries

### Narration
> "Finally, the AI FinOps Agent lets anyone ask cost questions in plain English. Powered by Meta Llama 3.3 70B Instruct, it generates SQL queries against your system tables, executes them, and returns insights conversationally.
>
> Ask 'What's my most expensive job this month?' or 'Show me cost trends for the data engineering team' — and get instant, accurate answers without writing a single SQL query."

### Demo Actions
1. Type: "What are my top 5 most expensive resources this week?"
2. Show AI generating and executing SQL
3. Show formatted response with cost breakdown
4. Type: "Which clusters have been idle for over 24 hours?"
5. Show AI response with actionable recommendations

---

## SCENE 11: CLOSING & CALL TO ACTION (9:00 – 9:45)

### Visual
Split screen: problem (manual cost spreadsheets) vs. solution (FinOps Monitor dashboard)

### Narration
> "To recap: this single Databricks App replaces manual cost reviews, reactive alerting, and spreadsheet-based tracking with an intelligent, proactive FinOps platform.
>
> The entire solution runs on Databricks system tables — no external tools, no data exports, no additional infrastructure. Deploy it as a Databricks App, connect your SQL warehouse, and start saving.
>
> The code is modular: add custom guardrails in `finops_guardrails.py`, tune anomaly thresholds in `finops_anomaly.py`, or extend the AI agent with your own prompts."

### Closing Slide
- **Key Stats:** 8 integrated modules, 3 anomaly detection algorithms, real-time remediation, LLM-powered chat
- **Tech Stack:** Streamlit, Databricks SQL, Databricks SDK, Plotly, scikit-learn, Meta Llama 3.3 70B
- **Data Sources:** system.billing.usage, system.compute.clusters, system.lakeflow.*, system.access.audit

---

## PRODUCTION NOTES

### Recommended Screen Recording Setup
- **Resolution:** 1920x1080 or 2560x1440
- **Browser:** Chrome/Edge with dark mode
- **App Theme:** Dark (configured in app.yaml)
- **Font Size:** Increase browser zoom to 110-125% for readability

### B-Roll Suggestions
- Close-up of metric cards transitioning
- Anomaly detection chart with spike highlighted
- AI agent chat typing animation
- Code editor showing module structure
- Architecture diagram animation (draw.io or Excalidraw)

### Music/Audio
- Subtle tech/ambient background track
- Volume ducked during narration
- Sound effects for transitions (subtle whoosh)

### Post-Production
- Add lower-third captions for key terms (FinOps, System Tables, Guardrails)
- Highlight mouse cursor during demos
- Add zoom-in effects on important metric values
- Chapter markers for YouTube/video platforms

---

## FILE REFERENCE (Application Structure)

```
databricks-finops-monitor/
├── app.py                      # Main Streamlit app (8 tabs)
├── app.yaml                    # Databricks App config
├── requirements.txt            # Python dependencies
├── finops_anomaly.py           # Anomaly detection (Z-Score, IQR, Isolation Forest)
├── finops_budget.py            # Budget management & tracking
├── finops_remediation.py       # Auto-remediation engine (idle clusters, runaway jobs)
├── finops_guardrails.py        # Policy enforcement (compliance, tags)
├── finops_action_plan.py       # Resource cleanup plan generator
├── finops_enforcement_job.py   # Scheduled enforcement job
├── FinOps Guardrails Builder   # Setup notebook
└── AI FinOps Enhancement Builder  # Enhancement notebook
```
