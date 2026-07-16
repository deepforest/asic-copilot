import os
import pandas as pd
import numpy as np

# Set random seed for reproducibility
np.random.seed(42)

def generate_datasets():
    data_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(data_dir, exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. Wafer Yield Parametric Data Generation
    # -------------------------------------------------------------
    num_chips = 100
    chip_ids = [f"CX8_{i:03d}" for i in range(1, num_chips + 1)]
    
    # Pre-define specific chips from requirements
    # CX8_001: TT, 8.2W
    # CX8_002: FF, 13.1W (Anomalous!)
    # CX8_003: SS, 6.5W
    specific_chips = {
        "CX8_001": {"Corner": "Typical-Typical (TT)", "Static_Leakage_Power": 8.2},
        "CX8_002": {"Corner": "Fast-Fast (FF)", "Static_Leakage_Power": 13.1},
        "CX8_003": {"Corner": "Slow-Slow (SS)", "Static_Leakage_Power": 6.5}
    }
    
    records = []
    wafers = ["WF_09", "WF_12", "WF_05", "WF_17", "WF_21"]
    
    for i, chip_id in enumerate(chip_ids):
        # Assign wafer
        wafer_id = wafers[i % len(wafers)]
        
        # Specific overrides
        if chip_id in specific_chips:
            corner = specific_chips[chip_id]["Corner"]
            leakage = specific_chips[chip_id]["Static_Leakage_Power"]
        else:
            # Assign corners based on ratio (30% SS, 45% TT, 25% FF)
            r = np.random.rand()
            if r < 0.30:
                corner = "Slow-Slow (SS)"
                # Mean 6.0W, Std Dev 0.5W
                leakage = max(4.0, round(np.random.normal(6.0, 0.5), 1))
            elif r < 0.75:
                corner = "Typical-Typical (TT)"
                # Mean 8.2W, Std Dev 0.7W
                leakage = max(6.0, round(np.random.normal(8.2, 0.7), 1))
            else:
                corner = "Fast-Fast (FF)"
                # Mean 11.2W, Std Dev 0.8W. Cap leakage to not exceed 12.3W for normal FF chips
                leakage = min(12.3, max(9.0, round(np.random.normal(11.2, 0.8), 1)))
        
        records.append({
            "Chip_ID": chip_id,
            "Wafer_ID": wafer_id,
            "Silicon_Revision": "B0",
            "Corner": corner,
            "Static_Leakage_Power": leakage
        })
        
    yield_df = pd.DataFrame(records)
    yield_path = os.path.join(data_dir, "yield_data.csv")
    yield_df.to_csv(yield_path, index=False)
    print(f"Generated yield data at {yield_path} with {len(yield_df)} chips.")
    
    # -------------------------------------------------------------
    # 2. Time-Series Telemetry Data Generation for Outlier Chip CX8_002
    # -------------------------------------------------------------
    start_time = 1710500000
    duration_sec = 600  # 10 minutes
    interval_sec = 1    # 1-second measurements
    timestamps = np.arange(start_time, start_time + duration_sec, interval_sec)
    
    telemetry_records = []
    
    # Chip CX8_002: Fast-Fast corner, runs hot and exceeds T_jmax
    current_temp = 45.0
    for t_idx, ts in enumerate(timestamps):
        # 10-minute stress test profile
        if t_idx < 180:
            # Step 1: Normal startup, power active, temperature rises gradually
            core_voltage = 0.80
            dynamic_power = 15.0 + np.random.normal(0, 0.2)
            # Rises gradually from 45C to ~78C
            target_temp = 45.0 + (78.0 - 45.0) * (t_idx / 180.0)
            current_temp += (target_temp - current_temp) * 0.1 + np.random.normal(0, 0.05)
        elif t_idx < 360:
            # Step 2: Core voltage bump to 0.82V (due to high performance test stage)
            # Temp climbs rapidly from ~78C to 98C
            core_voltage = 0.82
            dynamic_power = 24.0 + np.random.normal(0, 0.4)
            target_temp = 78.0 + (98.0 - 78.0) * ((t_idx - 180) / 180.0)
            current_temp += (target_temp - current_temp) * 0.08 + np.random.normal(0, 0.08)
        elif t_idx < 480:
            # Step 3: Temperature crosses thermal throttling trigger (98C). 
            # Clock is throttled, dynamic power drops, but temperature continues to climb due to high static leakage
            core_voltage = 0.80 # Dropped back due to throttling
            dynamic_power = 18.0 + np.random.normal(0, 0.3)
            # Continues climbing slowly to 102.5C
            target_temp = 98.0 + (102.5 - 98.0) * ((t_idx - 360) / 120.0)
            current_temp += (target_temp - current_temp) * 0.05 + np.random.normal(0, 0.05)
        else:
            # Step 4: Out of control thermal runaway, exceeding 105C (T_jmax)
            core_voltage = 0.80
            dynamic_power = 22.0 + np.random.normal(0, 0.5) # Spikes again under heavy stress
            # Reaches 105.5C
            target_temp = 102.5 + (105.8 - 102.5) * ((t_idx - 480) / 120.0)
            current_temp += (target_temp - current_temp) * 0.05 + np.random.normal(0, 0.05)
            
        # Hardcode the specific points in specification at precise indexes for consistency
        # Minute 3 (timestamp 180): 99.5C, V=0.82, Dynamic_Power=28.8W
        # Let's override second 200 (which corresponds to timestamp 1710500200)
        if ts == 1710500200:
            core_voltage = 0.82
            current_temp = 99.5
            dynamic_power = 28.8
        # Minute 5 (timestamp 300): 105.2C, V=0.80, Dynamic_Power=31.2W
        elif ts == 1710500300:
            core_voltage = 0.80
            current_temp = 105.2
            dynamic_power = 31.2
            
        telemetry_records.append({
            "Timestamp": int(ts),
            "Chip_ID": "CX8_002",
            "Core_Voltage_V": round(core_voltage, 2),
            "Temperature_C": round(current_temp, 1),
            "Dynamic_Power_W": round(dynamic_power, 1)
        })
        
    telem_df = pd.DataFrame(telemetry_records)
    telem_path = os.path.join(data_dir, "telemetry_CX8_002.csv")
    telem_df.to_csv(telem_path, index=False)
    print(f"Generated telemetry data for CX8_002 at {telem_path} with {len(telem_df)} records.")
    
    # -------------------------------------------------------------
    # 3. Time-Series Telemetry Data Generation for Normal Chip CX8_001
    # -------------------------------------------------------------
    # Generating CX8_001 for side-by-side dashboard comparisons
    telemetry_records_001 = []
    current_temp = 42.0
    for t_idx, ts in enumerate(timestamps):
        if t_idx < 180:
            core_voltage = 0.80
            dynamic_power = 12.0 + np.random.normal(0, 0.15)
            target_temp = 42.0 + (65.0 - 42.0) * (t_idx / 180.0)
            current_temp += (target_temp - current_temp) * 0.1 + np.random.normal(0, 0.05)
        elif t_idx < 360:
            core_voltage = 0.82
            dynamic_power = 18.0 + np.random.normal(0, 0.25)
            target_temp = 65.0 + (74.0 - 65.0) * ((t_idx - 180) / 180.0)
            current_temp += (target_temp - current_temp) * 0.08 + np.random.normal(0, 0.08)
        else:
            # Healthy chip: temp stabilizes and dynamic power remains stable
            core_voltage = 0.80
            dynamic_power = 14.0 + np.random.normal(0, 0.2)
            target_temp = 74.0 + np.random.normal(0, 0.5)
            current_temp += (target_temp - current_temp) * 0.05
            
        telemetry_records_001.append({
            "Timestamp": int(ts),
            "Chip_ID": "CX8_001",
            "Core_Voltage_V": round(core_voltage, 2),
            "Temperature_C": round(current_temp, 1),
            "Dynamic_Power_W": round(dynamic_power, 1)
        })
        
    telem_df_001 = pd.DataFrame(telemetry_records_001)
    telem_path_001 = os.path.join(data_dir, "telemetry_CX8_001.csv")
    telem_df_001.to_csv(telem_path_001, index=False)
    print(f"Generated telemetry data for CX8_001 at {telem_path_001} with {len(telem_df_001)} records.")

if __name__ == "__main__":
    generate_datasets()
