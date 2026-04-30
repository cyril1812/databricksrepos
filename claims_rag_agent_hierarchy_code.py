
import mlflow
from databricks_langchain import ChatDatabricks, VectorSearchRetrieverTool
from langchain.agents import create_agent

mlflow.langchain.autolog()

# Configuration
VS_INDEX = "salama_insurance.salama_silver.claim_documents_index_hierarchy"
LLM_ENDPOINT = "databricks-claude-sonnet-4-5"

# Retriever tool
claims_hierarchy_retriever = VectorSearchRetrieverTool(
    index_name=VS_INDEX,
    tool_name="claims_hierarchy_document_search",
    tool_description=(
        "Searches Salama Insurance claim documents using hierarchy-aware chunks. "
        "Each chunk preserves its document section context (e.g., Policyholder Details, "
        "Claim Summary, Investigation Findings, Settlement Terms). "
        "Use this tool to find information about specific claims, policy details, "
        "claimed amounts, settlement amounts, fraud investigations, denial reasons, "
        "and customer information."
    ),
    num_results=5,
    columns=["chunk_id", "document_name", "document_type", "section_name", "chunk_text"],
)

# LLM
llm = ChatDatabricks(endpoint=LLM_ENDPOINT, temperature=0.1)

# System prompt
SYSTEM_PROMPT = """You are a Salama Insurance Claims Assistant AI agent (Hierarchy-Enhanced).
You help insurance staff search and analyze claim documents including:
- Claim Submission Forms (policyholder info, policy details, claimed amounts)
- Settlement Notifications (approved amounts, payment details)
- Investigation Reports (fraud scores, investigation findings)
- Denial Letters (rejection reasons, appeal process)

IMPORTANT CITATION RULES:
1. Always cite the DOCUMENT NAME and SECTION NAME when providing information.
2. When information comes from multiple sections, organize your response by section.
3. If you cannot find the answer, say so clearly.
4. Format financial amounts with AED currency."""

# Build agent
agent = create_agent(
    model=llm,
    tools=[claims_hierarchy_retriever],
    system_prompt=SYSTEM_PROMPT,
)

mlflow.models.set_model(agent)
