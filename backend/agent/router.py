import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.agent.models import RouterDecision

def get_router_agent() -> ChatGoogleGenerativeAI:
    """
    Initializes the Gemini model with structured output mapping to RouterDecision.
    """
    # Use gemini-3.5-flash as the primary active Flash model in July 2026.
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        temperature=0.0,
        google_api_key=api_key
    )
    
    return llm.with_structured_output(RouterDecision)

# Prompt template for routing query classification
ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are the Analytics Router (Supervisor) for the ASIC Copilot system.\n"
        "Your task is to analyze the engineer's natural language query and decide which data sources are required to answer it.\n\n"
        "Available Data Sources:\n"
        "1. 'spec': Design specification containing limits like T_jmax, core voltage limits, static leakage ceilings, and dynamic thermal throttling limits.\n"
        "2. 'yield': Wafer parametric yield measurements (Static_Leakage_Power, wafer ID, corner TT/FF/SS, chip ID).\n"
        "3. 'telemetry': Time-series logs (temperature, core voltage, dynamic power) recorded during stress tests. Telemetry is chip-specific.\n\n"
        "Guidelines:\n"
        "- If the query asks about design limits, safety thresholds, or maximum values (e.g., 'What is T_jmax?', 'What is the max leakage current?'), you need 'spec'.\n"
        "- If the query asks about wafer yields, parametric tests, leakage averages, or process corners (TT, FF, SS) (e.g., 'Which fast-fast chips leaked the most?', 'What is the average TT leakage?'), you need 'yield'.\n"
        "- If the query asks about active sensor telemetry, real-time temperature profiles, dynamic power spikes, or core voltage during testing (e.g., 'Show telemetry for chip CX8_002', 'Did CX8_002 experience thermal throttling?'), you need 'telemetry'.\n"
        "- If the query asks to cross-reference sensor logs with design specs or check for specs violations (e.g., 'Tell me if any chips violated thermal-to-power limits during testing'), you need all three ('spec', 'yield', 'telemetry').\n\n"
        "Determine:\n"
        "- The target silicon revision (e.g., 'B0' or 'A1'). Default to 'B0' if not mentioned.\n"
        "- The list of required sources (a subset of ['spec', 'yield', 'telemetry']).\n"
        "- The target chip ID (e.g. 'CX8_002') if the engineer refers to a specific chip. Extract it carefully."
    )),
    ("human", "{query}")
])

def route_query(query: str) -> RouterDecision:
    """
    Invokes the Analytics Router to classify the query.
    """
    router = get_router_agent()
    formatted_prompt = ROUTER_PROMPT.format_messages(query=query)
    decision = router.invoke(formatted_prompt)
    return decision
