"""
Media Intelligence Agent — FastAPI Service
Exposes the pipeline as a standalone REST API.

Endpoints:
    POST /research          — run full pipeline, returns report
    GET  /health            — confirms service is running
    GET  /report/{outlet}   — fetch a previously generated report
    GET  /reports           — list all generated reports
    GET  /docs              — interactive API documentation (auto-generated)

Usage:
    python3 src/app.py
    # Service runs at http://localhost:8000

Test with curl:
    curl -X POST http://localhost:8000/research \
         -H "Content-Type: application/json" \
         -d '{"outlet": "Reuters"}'

Test with Postman:
    Method: POST
    URL:    http://localhost:8000/research
    Body:   {"outlet": "Reuters"}  (raw JSON)
"""
import os
import sys
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

from src.agent.graph import run_pipeline

load_dotenv()

# ── App setup ─────────────────────────────────────────────
app = FastAPI(
    title="Media Intelligence Agent",
    description=(
        "Autonomous competitive intelligence agent for media outlets. "
        "Give it an outlet name, get back a validated benchmark report."
    ),
    version="1.0.0",
)

# Serve the web UI
UI_PATH = Path(__file__).parent / "web" / "index.html"

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_ui():
    """Serve the Media Intelligence Agent web interface."""
    if UI_PATH.exists():
        return HTMLResponse(content=UI_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>UI not found</h1><p>Visit <a href='/docs'>/docs</a> for the API.</p>")


# ── Request / Response models ─────────────────────────────
class ResearchRequest(BaseModel):
    """Input model for the /research endpoint."""
    outlet: str

    class Config:
        json_schema_extra = {
            "example": {"outlet": "Der Spiegel"}
        }


class ResearchResponse(BaseModel):
    """Output model for the /research endpoint."""
    outlet:     str
    report:     str
    saved_to:   str
    generated:  str
    char_count: int


class HealthResponse(BaseModel):
    """Output model for the /health endpoint."""
    status:  str
    version: str
    time:    str


# ── Endpoints ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """
    Health check endpoint.
    Returns 200 if the service is running.
    Use this to confirm the API is up before sending research requests.
    """
    return HealthResponse(
        status  = "ok",
        version = "1.0.0",
        time    = datetime.now().isoformat(),
    )


@app.post("/research", response_model=ResearchResponse, tags=["Research"])
def research_outlet(request: ResearchRequest):
    """
    Run the full Media Intelligence pipeline for a named outlet.

    This endpoint:
    1. Identifies 2 competitors automatically
    2. Researches all 3 outlets using 6 data sources
    3. Retrieves industry context from Pinecone RAG
    4. Performs temporal drift analysis
    5. Scores all outlets with consensus scoring (Krippendorff's Alpha)
    6. Generates a structured Markdown report

    The report is saved to /reports/ and returned in the response.

    **Warning:** This endpoint takes 3-8 minutes to complete.
    It makes multiple API calls and runs 54 LLM evaluations.
    """
    outlet = request.outlet.strip()

    if not outlet:
        raise HTTPException(
            status_code=400,
            detail="Outlet name cannot be empty."
        )

    print(f"\n[app] Research request received: {outlet}")

    try:
        report = run_pipeline(outlet_name=outlet, save_report=True)

        if not report:
            raise HTTPException(
                status_code=500,
                detail="Pipeline completed but no report was generated."
            )

        # Build the saved filename
        filename = outlet.lower().replace(" ", "_").replace("/", "_")
        saved_to = f"reports/{filename}.md"

        return ResearchResponse(
            outlet     = outlet,
            report     = report,
            saved_to   = saved_to,
            generated  = datetime.now().isoformat(),
            char_count = len(report),
        )

    except HTTPException:
        raise

    except Exception as e:
        print(f"[app] Pipeline error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {str(e)}"
        )


@app.get("/report/{outlet_name}", tags=["Reports"])
def get_report(outlet_name: str):
    """
    Fetch a previously generated report by outlet name.

    The outlet name is converted to a filename automatically:
    'Der Spiegel' → reports/der_spiegel.md

    Returns the report as plain text Markdown.
    Returns 404 if the report has not been generated yet.
    """
    filename = outlet_name.lower().replace(" ", "_").replace("/", "_")
    filepath = f"reports/{filename}.md"

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"No report found for '{outlet_name}'. Run POST /research first."
        )

    with open(filepath, "r", encoding="utf-8") as f:
        report = f.read()

    return PlainTextResponse(content=report, media_type="text/markdown")


@app.get("/reports", tags=["Reports"])
def list_reports():
    """
    List all previously generated reports.
    Returns a list of outlet names with their file paths and sizes.
    """
    report_files = glob.glob("reports/*.md")

    reports = []
    for filepath in sorted(report_files):
        filename = os.path.basename(filepath)
        outlet   = filename.replace(".md", "").replace("_", " ").title()
        size     = os.path.getsize(filepath)
        modified = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()

        reports.append({
            "outlet":    outlet,
            "file":      filepath,
            "size_chars": size,
            "generated": modified,
        })

    return {
        "count":   len(reports),
        "reports": reports,
    }


# ── Entry point ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*60)
    print("  Media Intelligence Agent — FastAPI Service")
    print("="*60)
    print("  API:           http://localhost:8000")
    print("  Documentation: http://localhost:8000/docs")
    print("  Health check:  http://localhost:8000/health")
    print("="*60 + "\n")

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
