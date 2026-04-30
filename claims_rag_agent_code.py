
import mlflow
from databricks_langchain import ChatDatabricks, VectorSearchRetrieverTool
from langchain.agents import create_agent

mlflow.langchain.autolog()

# Configuration
VS_INDEX = "salama_insurance.salama_silver.claim_documents_index"
LLM_ENDPOINT = "databricks-claude-sonnet-4-5"

# Retriever tool
claims_retriever = VectorSearchRetrieverTool(
    index_name=VS_INDEX,
    tool_name="claims_document_search",
    tool_description=(
        "Searches Salama Insurance claim documents including claim submission forms, "
        "settlement notifications, investigation reports, and denial letters. "
        "Use this tool to find information about specific claims, policy details, "
        "claimed amounts, settlement amounts, fraud investigations, denial reasons, "
        "and customer information."
    ),
    num_results=5,
    columns=["chunk_id", "document_name", "document_type", "chunk_text"],
)

# LLM
llm = ChatDatabricks(endpoint=LLM_ENDPOINT, temperature=0.1)

# System prompt
SYSTEM_PROMPT = """You are a Salama Insurance Claims Assistant AI agent. You help insurance staff
search and analyze claim documents including:
- Claim Submission Forms (policyholder info, policy details, claimed amounts)
- Settlement Notifications (approved amounts, payment details)
- Investigation Reports (fraud scores, investigation findings)
- Denial Letters (rejection reasons, appeal process)

Always cite the document name and type when providing information.
If you cannot find the answer in the retrieved documents, say so clearly.
Format financial amounts with AED currency and proper formatting."""

# Build agent
agent = create_agent(
    model=llm,
    tools=[claims_retriever],
    system_prompt=SYSTEM_PROMPT,
)

# Set the model (required by MLflow models-from-code)
mlflow.models.set_model(agent)
