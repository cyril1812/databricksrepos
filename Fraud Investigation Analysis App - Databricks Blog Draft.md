# How a Middle East Insurer Built an AI-Powered Fraud Command Center on Databricks — The GOAT Way

**By Cyril S. | Databricks Community Blog**

---

## The Challenge: Insurance Fraud in the Middle East

Insurance fraud costs the global industry over $80 billion annually. For Middle East insurers managing complex multi-line portfolios across motor, health, property, and marine, the challenge is compounded by high claim volumes, multi-jurisdictional regulations, and paper-heavy processes. Investigators drown in spreadsheets, PDFs sit unread in shared drives, and by the time a suspicious pattern surfaces, the money is already gone.

What if fraud investigators could simply *ask a question* — in plain English or Arabic — and get an instant, data-backed answer drawn from both structured databases and unstructured claim documents?

That is exactly what we built: the **Insurance Fraud Investigation Command Center**, a production-grade Streamlit application running as a Databricks App, powered entirely by the Databricks Data Intelligence Platform.

---

## The Solution at a Glance

The Command Center is a seven-page analytical application serving fraud investigators, supervisors, and executives:

| Page | What It Does |
|------|-------------|
| **Investigation Pipeline** | Real-time view of all investigations by status (Initiated → In Progress → Completed → Closed) and findings classification (Fraud Confirmed, Suspected, Inconclusive, No Fraud) with high-risk case drill-down |
| **Trend Analysis** | Monthly time-series of fraud amounts detected, recovery rates, investigation costs, and fraud scores with interactive metric selection |
| **Investigator Performance** | Scoreboard ranking investigators by cases handled, average resolution days, recovery amounts, and ROI per investigator |
| **ROI Analysis** | Net benefit calculation — total investigation cost vs. total recovery — giving leadership a clear dollar-value justification for the fraud program |
| **GenAI Insights** | Seven AI-powered sub-tabs including Genie integration, AI summaries, claims document RAG search, a text-to-SQL fraud agent, sentiment analysis, multi-dimensional risk scoring, and ML-powered fraud trend forecasting |
| **AI Supervisor** | A multi-agent supervisor that orchestrates Genie (structured data across 19 tables) and a Claims Document RAG agent (25 PDFs) to answer complex questions spanning both data sources |
| **Observability** | Full-stack AI monitoring: token costs in USD from system.billing, RAG agent latency and success rates, endpoint token usage, ai_query performance, and error logs — all with configurable time ranges |

All of this is served through a single Databricks App deployment with no external infrastructure.

---

## Genie: The Game-Changer for Fraud Teams

If there is one capability that transforms how fraud teams operate, it is **Databricks AI/BI Genie**.

Before Genie, every new question required either a pre-built dashboard (weeks of development) or a SQL-literate analyst (scarce and expensive). With Genie:

- A claims manager asks *"What was total fraud detected last month?"* at 7 AM before a board meeting — and gets the answer in 10 seconds.
- An investigator asks *"Show me all high-risk cases assigned to Investigator 107"* — without knowing that this requires joining multiple fact and dimension tables.
- A finance director asks *"What is our investigation ROI by business line?"* — and Genie writes a four-table join with ROUND and GROUP BY clauses they could never write themselves.

Our Genie Space connects to 19 production tables and is embedded directly in the Streamlit app — no context switching, no separate tool. The conversation is stateful, so users can ask follow-up questions in the same thread.

When extended to Microsoft Teams, Genie meets investigators in their daily workflow. A question in a Teams channel becomes a governed, audited, accurate data retrieval — without ever opening a browser. **Genie democratizes data access without democratizing data risk.**

---

## Multi-Agent Supervisor: Structured + Unstructured Intelligence

The AI Supervisor page represents a true compound AI system. When an investigator asks *"Investigate claim CLM000089 — show the fraud score, amounts, and what the investigation report says"*, the supervisor:

1. Routes the structured data question to the **Genie Space** (fraud scores, claim amounts from 19 SQL tables)
2. Routes the document question to the **Claims RAG Agent** (searches 25 parsed PDF claim documents via Vector Search)
3. Synthesizes both responses into a single, coherent answer

This is built with **Databricks Agent Bricks** and served on a serverless model serving endpoint. The user asks one question; two specialized agents collaborate behind the scenes.

---

## AI Functions Built into SQL

The application leverages Databricks AI Functions (`ai_query`, `ai_analyze_sentiment`, `ai_classify`) directly within SQL:

- **Sentiment Analysis**: `ai_analyze_sentiment()` evaluates investigation outcomes — classifying each case as positive, negative, mixed, or neutral based on financial recovery, fraud scores, and resolution timelines.

- **Risk Scoring**: `ai_classify()` performs multi-dimensional risk classification (Severity × Likelihood × Impact) using LLM reasoning, with a rule-based fallback for instant results.

- **Executive Summaries**: `ai_query()` calls Claude to generate narrative summaries from portfolio statistics.

- **Fraud Trend Forecasting**: A hybrid statistical model (linear regression + exponential smoothing) generates forecasts with 95% confidence intervals, and then `ai_query()` produces an LLM-powered narrative interpretation of the trend.

Every AI function call is measured. The Observability tab tracks latency per row (e.g., `ai_analyze_sentiment` at \~5s/row, `ai_classify` at \~10s/row), so teams can make informed choices between AI-enhanced and rule-based modes.

---

## Document Intelligence: From PDF to Insight

Twenty-five claim documents — submission forms, settlement notifications, investigation reports, denial letters — were ingested into a Unity Catalog Volume, parsed using `ai_parse_document()`, chunked (both flat and hierarchical strategies), embedded with `databricks-bge-large-en`, and indexed in Vector Search. The RAG agent retrieves relevant chunks and uses Claude to synthesize answers. An investigator can ask *"Which claims were denied and why?"* and get a grounded, citation-backed answer in seconds.

---

## Full-Stack AI Observability

The Observability page provides production-grade monitoring across the entire AI stack:

- **Token Cost ($)**: Queries `system.billing.usage` joined with `system.billing.list_prices` to show actual USD costs by endpoint, by SKU, with daily trend charts. During development, the entire AI stack cost single-digit dollars per week.
- **RAG Agent Performance**: Request volume, average/P50/P95 latency, and success rates over time.
- **Endpoint Usage**: Per-endpoint breakdown of input/output tokens, error counts, and request volumes.
- **AI Query Performance**: Call volume and duration metrics segmented by agent type (Supervisor, Claims RAG, Sentiment, etc.).
- **Error Logs**: Unified error feed across all AI components with source attribution.

---

## AgentBuild™ — Reference Architecture

<!-- Insert image: AgentBuild_Reference_Architecture.png -->
![AgentBuild™ – Reference Architecture](AgentBuild_Reference_Architecture.png)

The architecture follows a left-to-right data flow across five layers, unified by the **Unity Catalog governance layer** at the foundation:

| Layer | Components | Role in Our Solution |
|-------|-----------|---------------------|
| **Data Sources** | Lakebase, Lakehouse, Metric Views | 19 Delta tables (fraud investigations, claims, customers, policies), parsed claim documents, and AI result tables |
| **Mosaic AI** | Model Serving, Serverless Inference | Serverless endpoints hosting Claude, Llama, BGE-Large-EN embeddings — all with scale-to-zero and pay-per-token economics |
| **Agentic Framework** | Agent Bricks (Workflow Orchestration), Mosaic AI Agent Evaluation (LLM as judge, MLflow) | Multi-agent supervisor orchestrates Genie + Claims RAG Agent; MLflow evaluators score relevance, safety, and groundedness |
| **Genie** | Genie — Data Retrieval Engine | Genie Space connected to 19 tables — translates natural language to governed SQL, embedded in the Streamlit app and deployable to Microsoft Teams |
| **Serving Layer** | Databricks Apps, AI/BI Dashboard, Agentic Actions, API Integrations | Streamlit app served as a Databricks App; AI/BI dashboards for executive reporting; API integrations for Teams and downstream systems |

**Unified Governance Layer (Unity Catalog):**

> Governance | Lineage | Access Control | Model Registry | Tool Permission

**Governance**: Unity Catalog is the single governance plane for data, models, and agents. Tables carry row-level and column-level policies, models are versioned with schemas, and agent tools are permissioned — no bolt-on security layer needed.

**Lineage**: Every data path is traced automatically — from Genie queries joining fact and dimension tables to RAG retrievals from Vector Search indexes. Compliance teams can answer "where did this number come from?" without chasing engineers.

**Access Control**: One permission model governs tables, AI endpoints, Genie Spaces, and system tables. When Genie generates SQL on behalf of a user, it inherits that user's permissions transparently — investigators, supervisors, and finance each see only what they should.

**Model Registry & Tool Permissions**: Every agent and ML model is registered with version history, evaluation metrics, and deployment lineage. Tool permissions restrict agents to only the functions and endpoints they are authorized to call — preventing scope escalation.

---

## How We Applied GOAT Principles

We designed this application around the **GOAT** principles — **G**overned, **O**pen, **A**I-Native, and lower **T**CO. Every asset — tables, models, agents, and documents — is governed under Unity Catalog with full lineage, row-level security, and audit tracking; no shadow data exists anywhere. The entire stack is built on open-source technologies (Delta Lake, MLflow, LangChain, Streamlit), meaning we can swap any LLM or UI framework without touching business logic. AI is not an add-on — Genie, multi-agent orchestration, and SQL AI Functions are embedded directly into investigator workflows as the primary interface. Finally, serverless-everything economics (SQL Warehouses, Model Serving, Databricks Apps) with scale-to-zero and real-time billing visibility keep the entire AI stack running at single-digit dollars per week — one platform replacing five.

---

## Results and Impact

| Metric | Before | After |
|--------|--------|-------|
| Time to answer an ad-hoc fraud question | 2-3 days (analyst queue) | 10-30 seconds (Genie or Agent) |
| Document search across claim PDFs | Manual — hours per investigation | RAG-powered — seconds with citations |
| Cost visibility for AI operations | None | Real-time USD breakdown by endpoint |
| Infrastructure components to manage | 5+ separate tools | 1 platform (Databricks) |
| Governance model | Per-tool, inconsistent | Unified via Unity Catalog |
| Vendor lock-in risk | High (proprietary formats) | Low (Delta Lake, MLflow, LangChain) |

---

## Getting Started with Genie

The fastest path to value on Databricks is **Genie**. It requires no model training, no agent code, and no application development — just your existing Unity Catalog tables and business context.

1. **Create a Genie Space**: Select your Unity Catalog schema and tables. Add business definitions (e.g., "total fraud = SUM(FRAUD_AMOUNT_DETECTED)") so Genie understands your domain language.

2. **Embed or extend**: Deploy Genie inside a Databricks App for a custom analytics experience, surface it through AI/BI Dashboards for self-service reporting, or push it to Microsoft Teams so users query data without leaving their collaboration tool.

3. **Layer in agents**: Once Genie handles structured data queries, add Agent Bricks to orchestrate Genie alongside RAG agents, document search, or external APIs — building compound AI systems that answer questions no single tool can.

4. **Monitor and optimize**: Use `system.billing` and `system.serving.endpoint_usage` to track every token, every dollar, and every query. Genie's governed foundation means every interaction is audited from day one.

Genie is not the end state — it is the starting point. From a single Genie Space, you scale into multi-agent supervisors, embedded AI applications, and enterprise-wide data intelligence — all on one platform, all governed, all serverless.

---

*The Fraud Investigation Command Center was built on the Databricks Data Intelligence Platform running on Azure, using Unity Catalog, AI/BI Genie, Mosaic AI Agent Framework, Vector Search, Model Serving, AI Functions, MLflow, and Databricks Apps. The application serves fraud investigators across the Middle East insurance market.*

---

**Tags:** #Databricks #Genie #AI #FraudDetection #Insurance #UnifiedGovernance #GOAT #MosaicAI #DataIntelligencePlatform #UnityCatalog
