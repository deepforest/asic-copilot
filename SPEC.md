# System Specification: ASIC Copilot (Multi-Source Characterization Analytics Agent)

## 1. System Overview & Objectives
The ASIC Copilot is an agentic diagnostics system designed for the bring-up and characterization phases of network ASIC chips (such as high-performance Ethernet switches or DPUs). During silicon characterization, physical performance datasets are gathered across different PVT (Process, Voltage, Temperature) corners. 

The primary objective of the ASIC Copilot is to automate the cross-referencing of static design limits (unstructured specifications) with structured wafer yield databases (parametric ATE tests) and real-time sensor telemetry logs (time-series CSVs) to identify silicon anomalies (e.g., chips consuming too much static leakage power or violating thermal throttling limits) from natural language engineering queries.

---

## 2. System Architecture & Workflow
The system utilizes a stateful, routing multi-agent architecture built with Python and LangGraph. The pipeline consists of the following nodes:

```
                            ┌────────────────────────┐
                            │ 1. Analytics Router    │
                            └───────────┬────────────┘
                                        │ (Determine required sources)
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
          ┌──────────────────┐┌──────────────────┐┌──────────────────┐
          │ 2a. Spec Finder  ││ 2b. Yield SQL    ││ 2c. Telemetry CSV│
          │ (Unstructured RAG)││ (Parametric DB)  ││ (Time-Series)    │
          └─────────┬────────┘└─────────┬────────┘└─────────┬────────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                            ┌────────────────────────┐
                            │ 3. Correlation Agent   │
                            │  (Heuristic / Stat)    │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │ 4. Insights Generator  │
                            └────────────────────────┘
```

### 2.1 Node 1: Analytics Router (Supervisor Agent)
*   **Purpose**: Parses the engineer's natural language question.
*   **Operation**: Employs an LLM with structured outputs to classify which data sources are required to address the query.
*   **Routes**: Spec Finder Tool, Yield SQL Tool, Telemetry CSV Tool, or a combination of all three.

### 2.2 Nodes 2a, 2b, 2c: Data Collectors (Deterministic Tools)
*   **Spec Finder Tool (Node 2a)**: Queries design threshold parameters, specifically the Maximum Safe Operating Temperature ($T_{\text{jmax}}$), Nominal Voltage Core Supply ($V_{\text{dd}}$), Maximum Acceptable Static Leakage Power ($P_{\text{leakage\_max}}$), and the Dynamic Thermal Throttling trigger point, from an unstructured specification markdown file.
*   **Yield SQL Tool (Node 2b)**: Queries a structured wafer parametric database containing wafer measurements, filtering for specific Chip IDs, corners (e.g., Typical-Typical (TT), Fast-Fast (FF), Slow-Slow (SS)), and Silicon Revision codes.
*   **Telemetry CSV Tool (Node 2c)**: Ingests and processes time-series logs of sensor outputs (voltage, temperature, dynamic power) recorded during stress workloads.

### 2.3 Node 3: Correlation & Anomaly Agent (Python Logic & LLM)
*   **Purpose**: Correlates the gathered raw data and executes mathematical validations.
*   **Statistical Outlier Check**: Calculates the mean ($\mu$) and standard deviation ($\sigma$) of the static leakage values in the Yield database and flags outliers using a $3\sigma$ filter:
    $$\text{Power}_{\text{leakage}} > \mu_{\text{leakage}} + 3\sigma_{\text{leakage}}$$
*   **Thermal Exception Check**: Maps the active temperature sensor readings from the time-series telemetry against the maximum safe thermal ceiling ($T_{\text{jmax}}$) retrieved by the Spec Finder to identify safety limit violations and overstressed chips.

### 2.4 Node 4: Insights Generator
*   **Purpose**: Synthesizes the statistical findings into an executive-level diagnostic report.
*   **Output**: A clean, markdown-formatted report optimized for an ASIC Product Manager highlighting anomalous chips, process corners at risk (e.g., Fast-Fast corners exhibiting high leakage), and recommended testing modifications.

---

## 3. Data Schema & Reference Mock Data

### 3.1 Unstructured Design Specification (`asic_spec.md`)
```markdown
# CX8 ASIC Thermal & Power Limits (Rev B0)
- Maximum Safe Operating Temperature (T_jmax): 105.0°C
- Nominal Voltage Core Supply (V_dd): 0.8V
- Maximum Acceptable Static Leakage Power (P_leakage_max): 12.5W
- Dynamic Thermal Throttling trigger point: 98.0°C
```

### 3.2 Structured Wafer Parametric Database (Yield SQL)
Represented in-memory as a SQLite database table or a Pandas DataFrame with the following schema and reference records:

| Chip_ID | Wafer_ID | Silicon_Revision | Corner | Static_Leakage_Power (W) |
| :--- | :--- | :--- | :--- | :--- |
| CX8_001 | WF_09 | B0 | Typical-Typical (TT) | 8.2 |
| CX8_002 | WF_09 | B0 | Fast-Fast (FF) | 13.1 (Anomalous!) |
| CX8_003 | WF_12 | B0 | Slow-Slow (SS) | 6.5 |

### 3.3 Time-Series Test Telemetry (`telemetry_CX8_002.csv`)
Raw sensor telemetry logs recorded during stress testing for Chip CX8_002:
```csv
Timestamp,Chip_ID,Core_Voltage_V,Temperature_C,Dynamic_Power_W
1710500000,CX8_002,0.80,45.2,15.1
1710500100,CX8_002,0.80,78.5,22.4
1710500200,CX8_002,0.82,99.5,28.8  # Temperature exceeds thermal throttling trigger!
1710500300,CX8_002,0.80,105.2,31.2 # Exceeds T_jmax (Critical Thermal Exception!)
```

---

## 4. Technical Requirements & Deliverables

### 4.1 State Management (LangGraph)
*   **Requirement**: Implement an `ASICState` class (using Python's `TypedDict` or `Pydantic`) containing:
    *   Input natural language query
    *   Extracted targets (e.g., Silicon Revision, Chip ID)
    *   Required data sources list (`["spec", "yield", "telemetry"]`)
    *   Retrieved specification data, wafer yield datasets, and time-series telemetry logs
    *   Flagged anomalies list
    *   Final output markdown report
    *   Agent routing trace history

### 4.2 Structured Output Routing
*   **Requirement**: The Analytics Router must use structured LLM output formatting (e.g., Pydantic schema validation) to extract required data sources and search parameters (like revision codes or corners).

### 4.3 Statistical Calculation Helper
*   **Requirement**: Write clean mathematical helper functions using NumPy and Pandas. The helper must calculate standard deviation ($\sigma$), mean ($\mu$), and detect static leakage outliers and thermal ceiling limit breaches.
*   **Constraint**: No verilog parsing or hardware description syntax compilation is allowed; analytics must focus exclusively on the physical measurements and limits.

### 4.4 Interface & Tracing
*   **FastAPI API Server**: Serves endpoints for chat-agent invocation (`POST /api/chat`) and raw dataset querying. Serves the static compiled React UI.
*   **Console Logging & Trace**: Running `main.py` locally or starting the agent must print a detailed execution flow displaying supervisor decisions, tool outputs, statistical calculations, and the final diagnostic report.
