import os
from backend.agent.tools import get_asic_spec, query_yield_database, load_telemetry

def test_get_asic_spec():
    spec = get_asic_spec()
    assert isinstance(spec, dict)
    assert spec["T_jmax"] == 105.0
    assert spec["V_dd"] == 0.8
    assert spec["P_leakage_max"] == 12.5
    assert spec["Throttling_Trigger"] == 98.0
    assert "raw_markdown" in spec

def test_query_yield_database():
    records = query_yield_database(silicon_revision="B0")
    assert len(records) > 0
    # Must contain CX8_002 as FF with 13.1W
    outlier = [r for r in records if r["Chip_ID"] == "CX8_002"]
    assert len(outlier) == 1
    assert outlier[0]["Corner"] == "Fast-Fast (FF)"
    assert outlier[0]["Static_Leakage_Power"] == 13.1

def test_load_telemetry():
    # Load for CX8_002
    records = load_telemetry("CX8_002")
    assert len(records) > 0
    # Check schema
    first = records[0]
    assert "Timestamp" in first
    assert "Chip_ID" in first
    assert first["Chip_ID"] == "CX8_002"
    assert "Temperature_C" in first
    assert "Core_Voltage_V" in first
    assert "Dynamic_Power_W" in first
    
    # Load for non-existent chip
    records_empty = load_telemetry("CX8_NONEXIST")
    assert len(records_empty) == 0
