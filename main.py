import os
import sys
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel

from backend.agent.graph import run_asic_copilot
from backend.agent.tools import get_asic_spec, query_yield_database, load_telemetry

app = FastAPI(
    title="ASIC Copilot API",
    description="API backend for Multi-Source Semiconductor Analytics Agent",
    version="1.0.0"
)

# Enable CORS for local development (React running on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in dev, can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schema for chat requests
class ChatRequest(BaseModel):
    message: str

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Accepts a natural language query, runs it through the LangGraph agent state machine, 
    and returns the diagnostic results and execution logs.
    """
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set. Please add it to your environment variables."
        )
        
    try:
        results = run_asic_copilot(request.message)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Execution Failed: {str(e)}")

@app.get("/api/data/spec")
async def get_spec_endpoint():
    """
    Returns the parsed design specifications for CX8 Rev B0.
    """
    try:
        return get_asic_spec()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/yield")
async def get_yield_endpoint(
    silicon_revision: str = "B0", 
    corner: Optional[str] = None,
    chip_id: Optional[str] = None
):
    """
    Returns wafer parametric yield data with optional revision, corner, and chip ID filters.
    """
    try:
        records = query_yield_database(
            silicon_revision=silicon_revision,
            corner=corner,
            chip_id=chip_id
        )
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/telemetry/{chip_id}")
async def get_telemetry_endpoint(chip_id: str):
    """
    Returns the time-series stress test sensor telemetry log for the specified chip.
    """
    try:
        records = load_telemetry(chip_id)
        if not records:
            raise HTTPException(
                status_code=404, 
                detail=f"Telemetry logs for chip '{chip_id}' not found."
            )
        return records
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY"))}

# -----------------------------------------------------------------------------
# Static Frontend Hosting
# -----------------------------------------------------------------------------

# Mount static React build if it exists (for unified single-service deployments)
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

if os.path.exists(FRONTEND_DIST_DIR):
    assets_dir = os.path.join(FRONTEND_DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        
    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        # Let API endpoints fall through (preventing overriding)
        if catchall.startswith("api/") or catchall.startswith("docs") or catchall.startswith("redoc") or catchall.startswith("openapi.json"):
            return None
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))

# -----------------------------------------------------------------------------
# Console Demonstration Mode
# -----------------------------------------------------------------------------

def run_console_demo():
    """
    Runs a default engineering query through the ASIC Copilot agent and prints the execution traces.
    """
    print("=" * 80)
    print(" ASIC COPILOT: CONSOLE DEMONSTRATION RUN")
    print("=" * 80)
    
    query = "Analyze our latest PVT run for Revision B0 and tell me if any chips violated our thermal-to-power specifications"
    print(f"Target Query: '{query}'\n")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("[WARNING] GEMINI_API_KEY environment variable is missing!")
        print("Please set the key to execute live LLM calls. Example:")
        print("  $env:GEMINI_API_KEY='AIzaSy...'")
        print("\nExiting demonstration...")
        return
        
    try:
        # Run agent
        state = run_asic_copilot(query)
        
        # Print Traces
        print("--- AGENT EXECUTION TRACE ---")
        for log in state.get("trace_logs", []):
            print(log)
            print("-" * 50)
            
        print("\n--- DETECTED ANOMALIES (STRUCTURED Pydantic OUTPUT) ---")
        import json
        print(json.dumps(state.get("flaged_anomalies"), indent=2))
        
        print("\n--- FINAL DIAGNOSTIC REPORT ---")
        print(state.get("final_markdown_report"))
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] Demonstration execution failed: {str(e)}")
        print("=" * 80)

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the ASIC Copilot API server or run console demo.")
    parser.add_argument("--demo", action="store_true", help="Run the default query console demonstration and exit.")
    args = parser.parse_args()
    
    if args.demo:
        run_console_demo()
    else:
        # Check if running in a container, bind to 0.0.0.0 for deployment
        port = int(os.getenv("PORT", 8000))
        print(f"Starting ASIC Copilot FastAPI server on port {port}...")
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
