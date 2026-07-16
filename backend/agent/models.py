from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class AnomalyReport(BaseModel):
    anomalous_chip_ids: List[str] = Field(
        description="List of chip IDs flagged as anomalous or violating constraints."
    )
    violation_type: Literal["Thermal", "Leakage_Power", "Voltage_Overstress"] = Field(
        description="The primary violation type detected."
    )
    confidence_score: float = Field(
        description="The confidence score of the analysis (between 0.0 and 1.0)."
    )
    root_cause_explanation: str = Field(
        description="Detailed root-cause analysis explanation of why the chip(s) failed."
    )

class RouterDecision(BaseModel):
    target_revision: str = Field(
        description="The silicon revision target extracted from the query (e.g., 'B0'). Defaults to 'B0' if not specified."
    )
    sources: List[Literal["spec", "yield", "telemetry"]] = Field(
        description="List of required data sources to answer the engineering query."
    )
    target_chip_id: Optional[str] = Field(
        None, description="The specific Chip ID mentioned in the query (e.g., 'CX8_002'), if any."
    )
    explanation: str = Field(
        description="Brief engineering explanation of why these sources and parameters were selected."
    )
