import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.agent.state import ASICState
from backend.agent.models import RouterDecision, AnomalyReport
from backend.agent.router import route_query
from backend.agent.tools import get_asic_spec, query_yield_database, load_telemetry

# -----------------------------------------------------------------------------
# LangGraph Node Implementations
# -----------------------------------------------------------------------------

def router_node(state: ASICState) -> Dict[str, Any]:
    """
    Supervisor router node that parses query and determines data routing.
    """
    query = state["user_query"]
    trace = list(state.get("trace_logs", []))
    
    trace.append(f"[Analytics Router] Analyzing query: '{query}'")
    decision: RouterDecision = route_query(query)
    
    trace.append(
        f"[Analytics Router] Router Decision:\n"
        f"  - Target Revision: {decision.target_revision}\n"
        f"  - Sources Selected: {decision.sources}\n"
        f"  - Target Chip: {decision.target_chip_id}\n"
        f"  - Rationale: {decision.explanation}"
    )
    
    return {
        "target_revision": decision.target_revision,
        "required_sources": decision.sources,
        "trace_logs": trace,
        # Save target chip ID to retrieve telemetry later if available
        "retrieved_spec_data": None,
        "retrieved_yield_data": None,
        "retrieved_telemetry_data": None,
        "flaged_anomalies": None,
        "final_markdown_report": None
    }

def data_collector_node(state: ASICState) -> Dict[str, Any]:
    """
    Data collectors node that runs deterministic data fetching tools.
    """
    sources = state["required_sources"]
    revision = state["target_revision"]
    trace = list(state.get("trace_logs", []))
    
    spec_data = None
    yield_data = None
    telemetry_data = None
    
    # 1. Spec Finder
    if "spec" in sources:
        trace.append("[Data Collector] Fetching design limits using Spec Finder...")
        try:
            spec_data = get_asic_spec()
            trace.append(
                f"[Data Collector] Spec Finder loaded limits:\n"
                f"  - Tjmax: {spec_data.get('T_jmax')}°C\n"
                f"  - Core Vdd: {spec_data.get('V_dd')}V\n"
                f"  - Max Leakage: {spec_data.get('P_leakage_max')}W\n"
                f"  - Throttling Point: {spec_data.get('Throttling_Trigger')}°C"
            )
        except Exception as e:
            trace.append(f"[Data Collector ERROR] Spec Finder failed: {str(e)}")
            
    # 2. Yield SQL
    if "yield" in sources:
        trace.append(f"[Data Collector] Querying wafer yield database for Silicon Revision '{revision}'...")
        try:
            yield_data = query_yield_database(silicon_revision=revision)
            trace.append(f"[Data Collector] Yield SQL tool retrieved {len(yield_data)} chip parametric records.")
        except Exception as e:
            trace.append(f"[Data Collector ERROR] Yield SQL failed: {str(e)}")
            
    # 3. Telemetry CSV
    if "telemetry" in sources:
        # Determine which chips to load telemetry for.
        # If target chip is specified in query, load that.
        # Otherwise, check if we have yield data, and default to the anomalous chip if known, 
        # or load telemetry for typical and outlier chips (CX8_001, CX8_002) for comparison.
        chips_to_query = []
        
        # User specified chip
        user_query_lower = state["user_query"].lower()
        if "cx8_001" in user_query_lower:
            chips_to_query.append("CX8_001")
        if "cx8_002" in user_query_lower:
            chips_to_query.append("CX8_002")
        if "cx8_003" in user_query_lower:
            chips_to_query.append("CX8_003")
            
        # Fallback if no specific chip is mentioned in query
        if not chips_to_query:
            # Check if CX8_002 is listed in yield (our mock database contains it)
            chips_to_query = ["CX8_002"] # Default to primary telemetry source
            
        telemetry_data = []
        for chip_id in chips_to_query:
            trace.append(f"[Data Collector] Loading time-series telemetry logs for chip '{chip_id}'...")
            try:
                records = load_telemetry(chip_id)
                if records:
                    telemetry_data.extend(records)
                    trace.append(f"[Data Collector] Loaded {len(records)} telemetry records for '{chip_id}'.")
                else:
                    trace.append(f"[Data Collector] No telemetry logs found for chip '{chip_id}'.")
            except Exception as e:
                trace.append(f"[Data Collector ERROR] Telemetry tool failed for {chip_id}: {str(e)}")
                
    return {
        "retrieved_spec_data": spec_data,
        "retrieved_yield_data": yield_data,
        "retrieved_telemetry_data": telemetry_data,
        "trace_logs": trace
    }

def correlation_node(state: ASICState) -> Dict[str, Any]:
    """
    Correlation and anomaly agent node that executes 3-sigma checks and thermal thresholds.
    """
    trace = list(state.get("trace_logs", []))
    spec = state.get("retrieved_spec_data")
    yield_records = state.get("retrieved_yield_data")
    telemetry_records = state.get("retrieved_telemetry_data")
    
    anomalies = []
    summary_stats = {}
    
    # 1. Yield Analysis (3-Sigma Outlier Leakage Check)
    if yield_records:
        from backend.agent.math_utils import calculate_3sigma_threshold, detect_leakage_outliers
        
        df_yield = pd.DataFrame(yield_records)
        leakages = df_yield["Static_Leakage_Power"].astype(float).tolist()
        
        # Calculate statistics using helper function
        mean_leakage, std_leakage, threshold_3sigma = calculate_3sigma_threshold(leakages)
        
        summary_stats["mean_leakage"] = mean_leakage
        summary_stats["std_leakage"] = std_leakage
        summary_stats["threshold_3sigma"] = threshold_3sigma
        
        trace.append(
            f"[Correlation Agent] Wafer parametric yield statistical analysis:\n"
            f"  - Mean static leakage (μ): {mean_leakage:.2f}W\n"
            f"  - Standard deviation (σ): {std_leakage:.2f}W\n"
            f"  - 3σ statistical threshold (μ + 3σ): {threshold_3sigma:.2f}W"
        )
        
        # Detect outliers using helper
        leakage_anomalies = detect_leakage_outliers(df_yield, threshold_3sigma)
        anomalies.extend(leakage_anomalies)
        
        for outlier in leakage_anomalies:
            trace.append(
                f"[Correlation Agent WARNING] Chip '{outlier['Chip_ID']}' flagged as dynamic static leakage outlier: "
                f"{outlier['Value']}W exceeds 3σ threshold of {threshold_3sigma:.2f}W!"
            )
            
        # Also check against absolute spec limit if spec is available
        if spec and "P_leakage_max" in spec:
            abs_limit = spec["P_leakage_max"]
            leakage_spec_breakers = df_yield[df_yield["Static_Leakage_Power"] > abs_limit]
            for _, row in leakage_spec_breakers.iterrows():
                # Avoid duplicate flagging if already captured as 3-sigma outlier
                if not any(a["Chip_ID"] == row["Chip_ID"] and a["Violation_Type"] == "Leakage_Power" for a in anomalies):
                    anomalies.append({
                        "Chip_ID": row["Chip_ID"],
                        "Violation_Type": "Leakage_Power",
                        "Metric": "Static Leakage Power",
                        "Value": float(row["Static_Leakage_Power"]),
                        "Limit": abs_limit,
                        "Context": f"Static leakage exceeds hard design ceiling of {abs_limit}W."
                    })
                    trace.append(
                        f"[Correlation Agent WARNING] Chip '{row['Chip_ID']}' violated absolute leakage spec: "
                        f"{row['Static_Leakage_Power']}W exceeds limit of {abs_limit}W!"
                    )

    # 2. Telemetry Analysis (Thermal Exception Check)
    if telemetry_records:
        from backend.agent.math_utils import detect_thermal_violations
        
        df_telem = pd.DataFrame(telemetry_records)
        
        # Determine thermal limits (T_jmax)
        t_jmax = spec.get("T_jmax", 105.0) if spec else 105.0
        throttling_point = spec.get("Throttling_Trigger", 98.0) if spec else 98.0
        
        trace.append(
            f"[Correlation Agent] Analyzing time-series telemetry records...\n"
            f"  - Target safe temperature (T_jmax): {t_jmax}°C\n"
            f"  - Throttling point: {throttling_point}°C"
        )
        
        # Detect thermal violations using helper
        thermal_anomalies = detect_thermal_violations(df_telem, t_jmax)
        anomalies.extend(thermal_anomalies)
        
        for violation in thermal_anomalies:
            trace.append(
                f"[Correlation Agent WARNING] Chip '{violation['Chip_ID']}' triggered critical thermal exception: "
                f"Temperature reached {violation['Value']}°C, exceeding limit of {t_jmax}°C!"
            )
            
        # Group by Chip ID to log status of normal/throttled chips
        for chip_id, group in df_telem.groupby("Chip_ID"):
            max_temp = float(group["Temperature_C"].max())
            if max_temp > throttling_point and max_temp <= t_jmax:
                trace.append(
                    f"[Correlation Agent INFO] Chip '{chip_id}' experienced thermal throttling: "
                    f"Max temp reached {max_temp}°C (crossed trigger point of {throttling_point}°C) but did not exceed T_jmax."
                )
                
            # 2.3 Voltage Overstress Check
            # (e.g. if voltage exceeds core nominal Vdd + 2% which is 0.816V for CX8 B0)
            nominal_vdd = spec.get("V_dd", 0.8) if spec else 0.8
            overstress_threshold = nominal_vdd * 1.025 # 2.5% margin
            voltage_breaches = group[group["Core_Voltage_V"] > overstress_threshold]
            if not voltage_breaches.empty:
                anomalies.append({
                    "Chip_ID": chip_id,
                    "Violation_Type": "Voltage_Overstress",
                    "Metric": "Core Voltage",
                    "Value": max_volt,
                    "Limit": overstress_threshold,
                    "Context": f"Voltage overstress detected! Active voltage reached {max_volt}V (exceeds nominal Vdd margin threshold of {overstress_threshold}V)."
                })
                trace.append(
                    f"[Correlation Agent WARNING] Chip '{chip_id}' experienced core voltage overstress: "
                    f"Core voltage reached {max_volt}V (exceeds nominal limit of {nominal_vdd}V by >2.5%)!"
                )

    # 3. LLM Structured Evaluation (Generate AnomalyReport)
    flagged_reports = []
    if anomalies:
        trace.append("[Correlation Agent] Packaging anomalies and requesting structured LLM evaluation...")
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.0, google_api_key=api_key)
            structured_eval = llm.with_structured_output(AnomalyReport)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are the Correlation and Anomaly Evaluation Agent for ASIC Copilot.\n"
                    "Your job is to examine the list of raw anomalies detected by physical checks and generate a unified, structured AnomalyReport.\n"
                    "Provide a clear, engineering-accurate root-cause explanation for the failure, explaining the physical interaction between process, voltage, temperature, and leakage power.\n"
                    "For example, explain that Fast-Fast process corner chips have shorter channel lengths, leading to high static leakage power, which generates self-heating and triggers thermal runaway and failures under stress workloads."
                )),
                ("human", "Detected raw anomalies: {anomalies_list}\n\nSpecs: {spec_sheet}\n\nSummary stats: {stats_info}")
            ])
            
            evaluation: AnomalyReport = structured_eval.invoke(
                prompt.format_messages(
                    anomalies_list=str(anomalies),
                    spec_sheet=str(spec),
                    stats_info=str(summary_stats)
                )
            )
            
            flagged_reports.append(evaluation.model_dump())
            trace.append(
                f"[Correlation Agent] LLM Evaluation Completed:\n"
                f"  - Affected Chips: {evaluation.anomalous_chip_ids}\n"
                f"  - Violation: {evaluation.violation_type}\n"
                f"  - Confidence: {evaluation.confidence_score}\n"
                f"  - Explanation: {evaluation.root_cause_explanation}"
            )
        except Exception as e:
            trace.append(f"[Correlation Agent ERROR] LLM evaluation failed: {str(e)}")
            # Fallback to manual dictionary packaging if LLM call fails
            anomalous_chips = list(set([a["Chip_ID"] for a in anomalies]))
            primary_violation = anomalies[0]["Violation_Type"] if anomalies else "Thermal"
            fallback_report = {
                "anomalous_chip_ids": anomalous_chips,
                "violation_type": primary_violation,
                "confidence_score": 0.8,
                "root_cause_explanation": f"Automated check flagged chips {anomalous_chips} due to physical exceptions. Details: {[a['Context'] for a in anomalies]}"
            }
            flagged_reports.append(fallback_report)
    else:
        trace.append("[Correlation Agent] Statistical and threshold checks passed. No silicon anomalies detected.")

    return {
        "flaged_anomalies": flagged_reports,
        "trace_logs": trace
    }

def insights_generator_node(state: ASICState) -> Dict[str, Any]:
    """
    Node that synthesizes all retrieved data and statistical calculations into a markdown report.
    """
    trace = list(state.get("trace_logs", []))
    trace.append("[Insights Generator] Compiling final diagnostics report for ASIC Product Manager...")
    
    query = state["user_query"]
    spec = state.get("retrieved_spec_data")
    yield_records = state.get("retrieved_yield_data")
    telemetry_records = state.get("retrieved_telemetry_data")
    anomalies = state.get("flaged_anomalies") or []
    
    # Construct details block
    yield_summary = "Not Requested"
    if yield_records:
        df_yield = pd.DataFrame(yield_records)
        mean_leak = df_yield["Static_Leakage_Power"].mean()
        std_leak = df_yield["Static_Leakage_Power"].std()
        max_leak_chip = df_yield.loc[df_yield["Static_Leakage_Power"].idxmax()]
        
        yield_summary = (
            f"- Total parametric chips queried: {len(df_yield)}\n"
            f"- Average static leakage (μ): {mean_leak:.2f}W\n"
            f"- Standard deviation (σ): {std_leak:.2f}W\n"
            f"- Maximum leakage recorded: {max_leak_chip['Static_Leakage_Power']}W (Chip {max_leak_chip['Chip_ID']} in wafer {max_leak_chip['Wafer_ID']}, {max_leak_chip['Corner']} corner)\n"
            f"- Outliers exceeding μ + 3σ ({mean_leak + 3*std_leak:.2f}W): "
            f"{list(df_yield[df_yield['Static_Leakage_Power'] > (mean_leak + 3*std_leak)]['Chip_ID'])}"
        )
        
    telem_summary = "Not Requested"
    if telemetry_records:
        df_telem = pd.DataFrame(telemetry_records)
        telem_summary = ""
        for chip_id, group in df_telem.groupby("Chip_ID"):
            max_t = group["Temperature_C"].max()
            max_v = group["Core_Voltage_V"].max()
            max_p = group["Dynamic_Power_W"].max()
            telem_summary += (
                f"**Chip {chip_id} telemetry statistics:**\n"
                f"- Maximum Junction Temperature: {max_t}°C\n"
                f"- Peak Core Supply Voltage: {max_v}V\n"
                f"- Peak Dynamic Power consumption: {max_p}W\n"
            )
            
    # Request LLM to write a professional markdown report summarizing everything
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.2, google_api_key=api_key)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert ASIC diagnostics assistant for ASIC Copilot.\n"
                "Your role is to write a brief, direct, and technically precise engineering answer to the engineer's query.\n"
                "Do NOT write a formal, verbose, multi-section 'executive report' or add document metadata (like 'Prepared for Product Manager').\n"
                "Directly answer the query using the gathered data. State the specific findings, highlight design limit violations or corner exceptions with values (e.g. static leakage, core temperature limits), and explain the root cause briefly in an engineering-focused tone.\n"
                "Keep the output concise, structured, and easy for an engineer to read. Use bullet points or short tables only if helpful to organize metrics."
            )),
            ("human", (
                "Engineer Query: {query}\n\n"
                "Specifications: {spec}\n\n"
                "Wafer Yield Analysis summary:\n{yield_summary}\n\n"
                "Telemetry Sensor log summary:\n{telem_summary}\n\n"
                "Flagged Anomaly reports: {anomalies}"
            ))
        ])
        
        report_content = llm.invoke(
            prompt.format_messages(
                query=query,
                spec=str(spec),
                yield_summary=yield_summary,
                telem_summary=telem_summary,
                anomalies=str(anomalies)
            )
        )
        if isinstance(report_content.content, list):
            report_markdown = "".join(
                [block.get("text", "") if isinstance(block, dict) else str(block) 
                 for block in report_content.content]
            )
        else:
            report_markdown = str(report_content.content)
    except Exception as e:
        trace.append(f"[Insights Generator ERROR] Report generation failed: {str(e)}")
        # Fallback report
        report_markdown = (
            f"# Silicon Anomaly Report (ASIC Copilot)\n\n"
            f"**Query**: {query}\n\n"
            f"## Analysis Findings\n"
            f"- **Parametric Yield Results**: {yield_summary}\n"
            f"- **Telemetry log details**: {telem_summary}\n"
            f"- **Flagged exceptions**: {anomalies}\n\n"
            f"*Note: Detailed LLM report generation was bypassed due to API error: {str(e)}*"
        )
        
    trace.append("[Insights Generator] Report generated successfully.")
    
    return {
        "final_markdown_report": report_markdown,
        "trace_logs": trace
    }

# -----------------------------------------------------------------------------
# LangGraph Graph Assembly & Compilation
# -----------------------------------------------------------------------------

def build_asic_graph() -> StateGraph:
    """
    Compiles the stateful routing graph for the ASIC Copilot.
    """
    builder = StateGraph(ASICState)
    
    # Define Nodes
    builder.add_node("router", router_node)
    builder.add_node("collector", data_collector_node)
    builder.add_node("correlation", correlation_node)
    builder.add_node("generator", insights_generator_node)
    
    # Define Edges
    builder.add_edge(START, "router")
    builder.add_edge("router", "collector")
    builder.add_edge("collector", "correlation")
    builder.add_edge("correlation", "generator")
    builder.add_edge("generator", END)
    
    return builder.compile()

# Instantiate the compiled application
asic_copilot_app = build_asic_graph()

def run_asic_copilot(query: str) -> Dict[str, Any]:
    """
    Helper function to run a query through the Compiled ASIC Copilot Graph.
    """
    initial_state = {
        "user_query": query,
        "target_revision": "B0",
        "required_sources": [],
        "retrieved_spec_data": None,
        "retrieved_yield_data": None,
        "retrieved_telemetry_data": None,
        "flaged_anomalies": None,
        "final_markdown_report": None,
        "trace_logs": []
    }
    
    # Run the pipeline
    final_state = asic_copilot_app.invoke(initial_state)
    return final_state
