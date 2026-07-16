import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple

def calculate_3sigma_threshold(leakage_values: List[float]) -> Tuple[float, float, float]:
    """
    Calculates the mean (μ), standard deviation (σ), and the 3σ outlier threshold (μ + 3σ).
    Args:
        leakage_values: List or array of static leakage power values.
    Returns:
        Tuple: (mean, standard_deviation, 3sigma_threshold)
    """
    if not leakage_values:
        return 0.0, 0.0, 0.0
        
    arr = np.array(leakage_values, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    threshold = mean + 3.0 * std
    return mean, std, threshold

def detect_leakage_outliers(df_yield: pd.DataFrame, threshold: float) -> List[Dict[str, Any]]:
    """
    Identifies records in the wafer yield dataframe that exceed the 3-sigma threshold.
    Args:
        df_yield: Yield records DataFrame containing 'Chip_ID', 'Corner', and 'Static_Leakage_Power'.
        threshold: The pre-calculated 3-sigma cutoff limit.
    Returns:
        List[Dict]: Outlier chip details ready to be reported.
    """
    if df_yield.empty or "Static_Leakage_Power" not in df_yield.columns:
        return []
        
    outliers = df_yield[df_yield["Static_Leakage_Power"] > threshold]
    
    flagged = []
    for _, row in outliers.iterrows():
        flagged.append({
            "Chip_ID": row["Chip_ID"],
            "Violation_Type": "Leakage_Power",
            "Metric": "Static Leakage Power",
            "Value": float(row["Static_Leakage_Power"]),
            "Limit": threshold,
            "Context": f"Fast-leakage outlier detected in corner {row['Corner']} (value exceeds 3-sigma limit of {threshold:.2f}W)."
        })
    return flagged

def detect_thermal_violations(df_telemetry: pd.DataFrame, t_jmax: float) -> List[Dict[str, Any]]:
    """
    Identifies records in the time-series telemetry dataframe that exceed maximum junction temp (T_jmax).
    Args:
        df_telemetry: Telemetry records DataFrame containing 'Timestamp', 'Chip_ID', and 'Temperature_C'.
        t_jmax: The maximum safe junction temperature ceiling.
    Returns:
        List[Dict]: Thermal violation details ready to be reported.
    """
    if df_telemetry.empty or "Temperature_C" not in df_telemetry.columns:
        return []
        
    violations = df_telemetry[df_telemetry["Temperature_C"] > t_jmax]
    
    flagged = []
    # Group by chip to report the peak temperature and first timestamp of violation
    for chip_id, group in violations.groupby("Chip_ID"):
        peak_row = group.loc[group["Temperature_C"].idxmax()]
        first_violation_row = group.iloc[0]
        flagged.append({
            "Chip_ID": chip_id,
            "Violation_Type": "Thermal",
            "Metric": "Junction Temperature",
            "Value": float(peak_row["Temperature_C"]),
            "Limit": t_jmax,
            "Timestamp": int(first_violation_row["Timestamp"]),
            "Context": f"Critical junction temperature breached! Max temp: {peak_row['Temperature_C']}°C (exceeds T_jmax ceiling of {t_jmax}°C)."
        })
    return flagged
