# Databricks AI/BI Genie & Microsoft Teams Integration Guide

The Streamlit App serves as the centralized dashboard. However, for true ad-hoc queries, the Databricks Platform offers native NLP via **Genie**.

## Step 1: Create the Genie Space
1. Login to your Databricks Workspace.
2. In the left navigation bar, go to **Genie** (under New or Data Intelligence).
3. Click **New Genie Space**.
4. Select the Unity Catalog schema where your data resides:
   - **Catalog**: `salama_insurance`
   - **Schema**: `salama_silver`
   - **Tables**: Select `fact_fraud_investigation` and related analytics views.
5. Provide contextual knowledge:
   - E.g., Explain that "total fraud" equals `SUM(FRAUD_AMOUNT_DETECTED)`.
6. Save and test the room locally in Databricks.

## Step 2: Integrate with Microsoft Teams
Databricks seamlessly extends Genie to Microsoft Teams so investigators can chat with data outside of the Streamlit App.

1. Open your created **Salama Genie Space**.
2. Click on the **Settings Menu** (gear icon) -> **Integrations**.
3. Select **Microsoft Teams**.
4. In Microsoft Teams, an admin must add the "Databricks AI/BI Genie" App from the Teams marketplace.
5. Provide the linked connection string or app credentials given in Databricks to the Teams app configurations.
6. **Result**: Your investigators can tag the Genie bot in a discussion (e.g., `@DatabricksGenie How many open investigations does Investigator 103 have?`) and receive a data-backed response straight from the Unity Catalog.

*Note: In `app.py`, the link generated in Tab 5 relies on the workspace link generated after completing Step 1.*
