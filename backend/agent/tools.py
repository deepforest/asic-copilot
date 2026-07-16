import os
import re
import pandas as pd
from typing import Dict, Any, List, Optional

# Base directory for data
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "data"
)

def get_asic_spec() -> Dict[str, Any]:
    """
    Retrieves design specifications from the local asic_spec.md file.
    Returns:
        Dict: Parsed specifications containing maximum safe temperature, nominal voltage, 
              leakage threshold, and throttling points.
    """
    spec_path = os.path.join(DATA_DIR, "asic_spec.md")
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"Specification file not found at {spec_path}")
        
    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    spec_data = {}
    
    # Simple regex parsing of the key-value specification items
    t_jmax_match = re.search(r"Maximum Safe Operating Temperature \(T_jmax\):\s*([\d\.]+)", content)
    v_dd_match = re.search(r"Nominal Voltage Core Supply \(V_dd\):\s*([\d\.]+)", content)
    p_leak_match = re.search(r"Maximum Acceptable Static Leakage Power \(P_leakage_max\):\s*([\d\.]+)", content)
    throttling_match = re.search(r"Dynamic Thermal Throttling trigger point:\s*([\d\.]+)", content)
    
    if t_jmax_match:
        spec_data["T_jmax"] = float(t_jmax_match.group(1))
    if v_dd_match:
        spec_data["V_dd"] = float(v_dd_match.group(1))
    if p_leak_match:
        spec_data["P_leakage_max"] = float(p_leak_match.group(1))
    if throttling_match:
        spec_data["Throttling_Trigger"] = float(throttling_match.group(1))
        
    spec_data["raw_markdown"] = content
    return spec_data

def query_yield_database(
    silicon_revision: str = "B0", 
    corner: Optional[str] = None,
    chip_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Queries the structured wafer yield database (yield_data.csv).
    Args:
        silicon_revision: The target silicon revision (default 'B0').
        corner: Optional filter for process corner (e.g. 'Fast-Fast (FF)').
        chip_id: Optional filter for specific Chip ID.
    Returns:
        List[Dict]: List of matching wafer measurement records.
    """
    yield_path = os.path.join(DATA_DIR, "yield_data.csv")
    if not os.path.exists(yield_path):
        raise FileNotFoundError(f"Yield data file not found at {yield_path}")
        
    df = pd.read_csv(yield_path)
    
    # Apply filters
    df_filtered = df[df["Silicon_Revision"] == silicon_revision]
    
    if chip_id:
        df_filtered = df_filtered[df_filtered["Chip_ID"] == chip_id]
    if corner:
        df_filtered = df_filtered[df_filtered["Corner"].str.contains(corner, case=False, na=False)]
        
    return df_filtered.to_dict(orient="records")

def load_telemetry(chip_id: str) -> List[Dict[str, Any]]:
    """
    Loads time-series sensor telemetry logs for a specific chip.
    Args:
        chip_id: The Chip ID to retrieve telemetry for.
    Returns:
        List[Dict]: Time-series records containing temperature, voltage, and dynamic power.
    """
    telemetry_filename = f"telemetry_{chip_id}.csv"
    telemetry_path = os.path.join(DATA_DIR, telemetry_filename)
    
    if not os.path.exists(telemetry_path):
        # Return empty list if no telemetry file is available for the chip
        return []
        
    df = pd.read_csv(telemetry_path)
    return df.to_dict(orient="records")
