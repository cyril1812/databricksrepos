# Databricks FinOps Monitor — Usage Guide
## How to Monitor and Optimize Your Databricks Costs

---

## Getting Started

### Step 1: Launch the App

1. Navigate to **Databricks Apps** in the left sidebar of your workspace
2. Find and launch **Databricks FinOps Monitor**
3. The app opens with a dark-themed dashboard

### Step 2: Connect to Your SQL Warehouse

1. In the **sidebar**, enter your SQL Warehouse ID
   - Find this in: SQL Warehouses > your warehouse > Connection Details > HTTP Path
   - Copy the warehouse ID (the alphanumeric string after `/warehouses/`)
2. Click **Connect** — a success message confirms the connection
3. The app now has access to your system tables

### Step 3: Set Your Filters

| Filter | Purpose | Recommendation |
| --- | --- | --- |
| Date Range | Scope the analysis window | Start with last 30 days for a full picture |
| Azure Subscription | Narrow to specific subscriptions | Use "All" unless you manage multiple |
| Workspace | Focus on a specific workspace | Useful for team-level cost reviews |
| Monthly Budget | Set your spend target | Enter your actual monthly budget allocation |
| SLA Threshold | Define job completion target | 95% is a common starting point |

---

## Cost Monitoring Workflows

### Workflow 1: Daily Cost Check (5 minutes)

**Goal**: Quickly identify if spend is on track.

1. Open the **Cost FinOps** tab
2. Review the top-level metrics:
   - Total spend (current period)
   - Daily average cost
   - Top spending products
3. Check the **spend trend chart** — look for unexpected spikes
4. If a spike exists, drill into the **breakdown by product** to identify the source

**Key Questions Answered:**
- Are we on track for the month?
- Did any product spike unexpectedly?
- Who are the top cost contributors?

---

### Workflow 2: Budget Tracking & Breach Prevention

**Goal**: Predict and prevent budget overruns before they happen.

1. Navigate to the **Budget Management** section
2. Set your **Monthly Budget** in the sidebar (e.g., $5,000)
3. Review the dashboard panels:

| Panel | What It Shows | Action If Concerning |
| --- | --- | --- |
| Budget Utilization % | How much budget is consumed | > 75% early in month = investigate |
| Projected Monthly Total | Forecasted end-of-month spend | If > budget, take action now |
| Breach Prediction Date | When budget will be exhausted | If < 7 days away, escalate |
| Daily Burn Rate | Average daily cost | Compare to budget/30 for pace |
| Burndown Chart | Actual vs. expected spend pace | Line above pace = overspending |

4. **Budget Alerts** trigger at configurable thresholds:
   - **50%** — Informational, halfway through budget
   - **75%** — Warning, review spend patterns
   - **90%** — High alert, take immediate cost-saving action
   - **100%** — Critical, budget exhausted

**Proactive Actions:**
- If projected overshoot > 20%, run the Auto-Remediation scan
- If burn rate doubled recently, check the Anomaly Detection tab
- Share the burndown chart with stakeholders for visibility

---

### Workflow 3: Anomaly Detection (Spot Unusual Spend)

**Goal**: Catch cost spikes before they drain your budget.

1. Open the **Anomaly Detection** section
2. Select your detection method:

| Method | Best For | Sensitivity |
| --- | --- | --- |
| Z-Score | Steady-state workloads with consistent patterns | Threshold: 2.5σ (adjustable) |
| IQR | Workloads with occasional legitimate spikes | Multiplier: 1.5x (less aggressive) |
| Isolation Forest | Complex patterns, multiple variables | ML-based, 5% contamination |

3. Choose your **granularity**:
   - **Per-Job**: Which specific job is costing more than expected?
   - **Per-Cluster**: Which cluster is burning more than usual?
   - **Per-User**: Is a specific user's workload growing unexpectedly?
   - **Per-Workspace**: Cross-workspace comparison
   - **Per-Product**: Which product category spiked?

4. Review flagged anomalies:
   - **Deviation %**: How far above/below normal is this?
   - **Expected Value**: What the cost should have been
   - **Anomaly Score**: Confidence that this is truly abnormal

**Common Anomaly Causes:**
- Forgotten dev clusters left running overnight
- Retry storms from failing jobs
- Autoscaling hitting maximum with inefficient queries
- New workloads without cost awareness
- Zombie endpoints (model serving, vector search) with no traffic

---

## Cost Optimization Workflows

### Workflow 4: Identify and Eliminate Waste (Auto-Remediation)

**Goal**: Find idle or oversized resources and take action.

1. Navigate to the **Auto-Remediation** section
2. The engine scans three categories:

#### A. Idle Clusters

Clusters with low utilization that are burning money:

| Metric | Threshold | Recommended Action |
| --- | --- | --- |
| Avg CPU < 5% | Nearly zero usage | Terminate (likely abandoned) |
| Avg CPU < 15% | Underutilized | Resize to fewer workers |
| Avg Memory < 30% | Over-provisioned | Right-size instance type |
| Running > 4 hours idle | No active workloads | Enable auto-termination |

**What to do:**
- Review the list of flagged clusters
- Note the **Estimated Waste Cost** column
- For "terminate" recommendations: verify no active notebooks, then terminate
- For "resize" recommendations: reduce worker count by 50%

#### B. Runaway Jobs

Jobs that cost more than expected or run too long:

- Jobs with abnormally high daily cost (vs. historical average)
- Jobs exceeding duration thresholds (stuck or inefficient)
- Failed jobs that keep retrying (retry storms)

**What to do:**
- Check if the job is failing and retrying endlessly
- Review query plans for inefficient SQL
- Consider adding timeout limits to job configurations

#### C. Oversized Warehouses

SQL warehouses that are bigger than needed:

- Low query concurrency vs. cluster size
- High idle time between queries
- Auto-scaling rarely reaching minimum

**What to do:**
- Reduce warehouse size by one tier
- Enable auto-stop (10 min recommended)
- Consider serverless for bursty workloads

#### Dry Run vs. Live Mode

- **Dry Run (default)**: Report findings only — no changes made
- **Live Mode**: Execute remediation actions automatically

> **Best Practice**: Always start with Dry Run. Review findings, validate they're safe to act on, then switch to Live Mode for confirmed waste.

---

### Workflow 5: Enforce Cost Guardrails

**Goal**: Prevent cost overruns by enforcing policies proactively.

1. Open the **Guardrails** section
2. The engine checks two policy categories:

#### Cluster Policy Compliance

| Policy | What It Checks | Why It Matters |
| --- | --- | --- |
| Auto-Termination | Is auto-termination enabled? | Prevents clusters from running indefinitely |
| Max Workers | Are workers within limit (default: 20)? | Prevents accidental over-provisioning |
| Long-Running + Idle | Running > 4 hrs with low util? | Catches forgotten interactive clusters |

#### Tag Compliance

| Required Tag | Purpose |
| --- | --- |
| `project` | Cost attribution to business initiative |
| `owner` | Accountability for resource spend |
| `env` | Distinguish dev/staging/prod (apply different budgets) |

**Enforcement Actions:**
- Non-compliant resources are flagged with severity (HIGH/MEDIUM/LOW)
- In Live Mode, actions can be executed automatically
- All actions are audit-logged with timestamps

---

### Workflow 6: Resource Cleanup Action Plans

**Goal**: Get a prioritized list of resources to shut down or resize.

1. Navigate to the **Action Plans** section
2. Review resources categorized by priority:

| Priority | Monthly Cost | Action Urgency |
| --- | --- | --- |
| CRITICAL | >= $200/month | Act today — significant daily burn |
| HIGH | >= $50/month | Act this week |
| MEDIUM | >= $10/month | Schedule for next review cycle |

3. Each resource shows:
   - **Product type**: Vector Search, Model Serving, Cluster, Warehouse, etc.
   - **Owner**: Who created or manages this resource
   - **Projected monthly cost**: Based on recent daily burn rate
   - **Recommended action**: DELETE, TERMINATE, STOP, DISABLE, or REVIEW

4. Work through the list top-to-bottom (highest savings first)

**Common Quick Wins:**

| Resource Type | Typical Action | Savings Potential |
| --- | --- | --- |
| Unused Vector Search endpoints | Delete endpoint | $50–$500/month |
| Idle Model Serving endpoints | Delete endpoint | $100–$1,000/month |
| Dev clusters left running | Terminate + enable auto-stop | $20–$200/month |
| Oversized SQL warehouses | Downsize one tier | $50–$300/month |
| Unused Lakebase resources | Delete resource | $30–$150/month |

---

### Workflow 7: AI-Powered Cost Analysis (Chat Agent)

**Goal**: Ask natural language questions about your costs.

1. Open the **AI FinOps Agent** tab
2. Type your question in plain English. Examples:

**Discovery Questions:**
- "What are my top 5 most expensive jobs this week?"
- "Which workspace is spending the most?"
- "Show me cost by product for the last 7 days"
- "Who is the top cost contributor in my team?"

**Diagnostic Questions:**
- "Why did costs spike on Tuesday?"
- "Which clusters have been running for more than 24 hours?"
- "Are there any failed jobs that keep retrying?"
- "What's my Vector Search spend trend?"

**Optimization Questions:**
- "What can I do to reduce costs by 20%?"
- "Which resources should I shut down?"
- "Recommend right-sizing for my interactive clusters"
- "Compare this week's spend to last week"

3. The agent generates SQL, executes it against system tables, and returns results with recommendations

---

## Monitoring Best Practices

### Daily Routine (5 min)

1. Check budget utilization % — on track?
2. Glance at anomaly alerts — anything flagged?
3. Review any critical-priority action plan items

### Weekly Review (15 min)

1. Run full anomaly detection across all granularities
2. Review Auto-Remediation scan results
3. Check guardrail compliance — new violations?
4. Update budget if spending patterns changed
5. Download PDF report for stakeholder review

### Monthly Optimization Sprint (1 hour)

1. Review full month spend vs. budget
2. Execute action plan (start with CRITICAL items)
3. Enforce tag compliance on all new resources
4. Adjust anomaly thresholds based on false positives
5. Review scheduled enforcement job results
6. Set next month's budget based on trends

---

## Scheduled Enforcement (Automated Monitoring)

For continuous cost governance without manual effort, schedule the enforcement job:

### Setup

1. Create a Databricks Job using `finops_enforcement_job.py`
2. Configure parameters:
   - `dry_run`: `true` (start safe)
   - `monthly_budget`: your budget amount
   - `warehouse_id`: your SQL Warehouse ID
3. Schedule: Every 4 hours

### What It Does Automatically

- Scans all clusters for policy compliance
- Checks tag compliance
- Detects idle resources
- Identifies runaway jobs
- Logs all findings (even in dry-run mode)
- Optionally executes remediation (when `dry_run=false`)

### Graduating to Live Enforcement

1. Run with `dry_run=true` for 1–2 weeks
2. Review the audit log — are all flagged items truly wasteful?
3. If false positive rate < 5%, switch to `dry_run=false`
4. Monitor the first few live runs closely
5. Set up alerting on the job itself (email on failure)

---

## PDF Reports

Each tab has a **Download PDF** button for offline sharing:

- **Use Cases**: Monthly stakeholder reviews, audit documentation, budget justification
- **Contents**: Metrics, charts (rendered as images), data tables
- **Format**: Landscape A4 with branded headers and timestamps

---

## Tips for Maximum Cost Savings

1. **Enable auto-termination on ALL clusters** (30 min recommended)
2. **Tag everything** — untagged resources can't be attributed to teams
3. **Review Model Serving endpoints monthly** — unused endpoints burn $100+/day
4. **Use serverless** for bursty workloads instead of always-on clusters
5. **Set budget alerts at 75%** — gives you a week to react
6. **Run anomaly detection daily** — catches issues before they compound
7. **Automate the enforcement job** — manual reviews get skipped under pressure
8. **Right-size iteratively** — reduce by 25%, monitor, reduce again if stable
9. **Check Vector Search endpoints** — often created for POCs and forgotten
10. **Review Predictive Optimization costs** — system-managed spend can surprise you

---

## Glossary

| Term | Definition |
| --- | --- |
| DBU | Databricks Unit — the billing unit for compute consumption |
| Burn Rate | Average daily cost (total spend / days elapsed) |
| Budget Breach | When actual or projected spend exceeds the budget |
| Guardrail | An automated policy check that flags or prevents violations |
| Anomaly | A cost data point significantly deviating from historical patterns |
| Remediation | An automated action to fix a cost issue (terminate, resize, stop) |
| Dry Run | Simulate actions without executing them (safe mode) |
| Service Principal | A machine identity (UUID) that runs system workloads |
| Identity Resolution | Mapping opaque UUIDs to human-readable names |
| Action Plan | A prioritized list of cost-saving actions with projected savings |

---

## Support & Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| No data appears | System table access not granted | Ask admin to grant SELECT on system.billing.usage |
| Budget shows $0 | Date range has no billing data | Expand the date range |
| Anomalies all false positives | Threshold too sensitive | Increase Z-Score threshold to 3.0 |
| Remediation says "permission denied" | SDK doesn't have cluster/warehouse perms | Run as a principal with cluster management rights |
| AI Agent returns errors | LLM endpoint not active | Verify `databricks-meta-llama-3-3-70b-instruct` is serving |
| PDF download empty | kaleido not installed | Redeploy app (requirements.txt includes it) |
| Workspace names show IDs | Mapping table missing | Create `uae_insurance.uae_silver.workspace_mapping` |

---

*Last updated: 2025*
