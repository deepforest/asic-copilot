import os
import pytest
from backend.agent.router import route_query
from backend.agent.models import RouterDecision

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY environment variable is not set.")
def test_route_query():
    # Test query about specs
    decision_spec = route_query("What is the maximum junction temperature T_jmax defined in CX8 spec sheet?")
    assert isinstance(decision_spec, RouterDecision)
    assert "spec" in decision_spec.sources
    
    # Test query about yield
    decision_yield = route_query("Analyze wafer yield static leakage and tell me if we have any FF corner outliers.")
    assert isinstance(decision_yield, RouterDecision)
    assert "yield" in decision_yield.sources
    
    # Test query about telemetry
    decision_telem = route_query("Load the dynamic power and core temperature telemetry logs for chip CX8_002.")
    assert isinstance(decision_telem, RouterDecision)
    assert "telemetry" in decision_telem.sources
    assert decision_telem.target_chip_id == "CX8_002"
