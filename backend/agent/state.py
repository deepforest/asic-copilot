from typing import TypedDict, List, Dict, Any, Optional

class ASICState(TypedDict):
    user_query: str
    target_revision: str
    required_sources: List[str]               # e.g., ["spec", "yield", "telemetry"]
    retrieved_spec_data: Optional[Dict[str, Any]]
    retrieved_yield_data: Optional[List[Dict[str, Any]]]
    retrieved_telemetry_data: Optional[List[Dict[str, Any]]]
    flaged_anomalies: Optional[List[Dict[str, Any]]]
    final_markdown_report: Optional[str]
    trace_logs: List[str]                     # To record intermediate agent step logs
