import pandas as pd
import numpy as np
from backend.agent.math_utils import (
    calculate_3sigma_threshold,
    detect_leakage_outliers,
    detect_thermal_violations
)

def test_calculate_3sigma_threshold():
    # Setup values with mean=10, std=2
    # Standard deviation on [6, 8, 10, 12, 14] is 3.162 (using ddof=1)
    values = [6.0, 8.0, 10.0, 12.0, 14.0]
    mean, std, threshold = calculate_3sigma_threshold(values)
    
    assert mean == 10.0
    assert np.isclose(std, 3.162277, atol=1e-5)
    assert np.isclose(threshold, 10.0 + 3.0 * std, atol=1e-5)
    
    # Empty list case
    m2, s2, t2 = calculate_3sigma_threshold([])
    assert m2 == 0.0
    assert s2 == 0.0
    assert t2 == 0.0

def test_detect_leakage_outliers():
    # Create mock yield DataFrame
    df = pd.DataFrame([
        {"Chip_ID": "CX_NORMAL_1", "Corner": "TT", "Static_Leakage_Power": 8.0},
        {"Chip_ID": "CX_NORMAL_2", "Corner": "FF", "Static_Leakage_Power": 11.0},
        {"Chip_ID": "CX_OUTLIER", "Corner": "FF", "Static_Leakage_Power": 15.0}
    ])
    
    # 3-sigma threshold = 12.5W
    outliers = detect_leakage_outliers(df, threshold=12.5)
    
    assert len(outliers) == 1
    assert outliers[0]["Chip_ID"] == "CX_OUTLIER"
    assert outliers[0]["Value"] == 15.0
    assert outliers[0]["Limit"] == 12.5

def test_detect_thermal_violations():
    # Create mock telemetry DataFrame
    df = pd.DataFrame([
        {"Timestamp": 100, "Chip_ID": "CX_CHIP_1", "Temperature_C": 80.0},
        {"Timestamp": 110, "Chip_ID": "CX_CHIP_1", "Temperature_C": 106.0}, # Violation!
        {"Timestamp": 120, "Chip_ID": "CX_CHIP_1", "Temperature_C": 104.0},
        {"Timestamp": 100, "Chip_ID": "CX_CHIP_2", "Temperature_C": 90.0}
    ])
    
    # Tjmax = 105.0C
    violations = detect_thermal_violations(df, t_jmax=105.0)
    
    assert len(violations) == 1
    assert violations[0]["Chip_ID"] == "CX_CHIP_1"
    assert violations[0]["Value"] == 106.0 # Peak temperature
    assert violations[0]["Timestamp"] == 110 # First violation timestamp
