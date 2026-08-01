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

import uuid
import threading
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
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

# ── In-memory job store ──────────────────────────────────
# Stores pipeline jobs by job_id so the UI can poll for results
# Key: job_id (str), Value: {status, report, notion_url, error}
_jobs: dict = {}

# ── In-memory job store ──────────────────────────────────
# CORS + ngrok interstitial bypass
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_ngrok_header(request: Request, call_next):
    """Bypass ngrok browser warning interstitial for all responses."""
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

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
    outlet:          str
    recipient_email: str = ""
    force_refresh:   bool = False

    class Config:
        json_schema_extra = {
            "example": {"outlet": "Der Spiegel", "recipient_email": "analyst@company.com"}
        }


class ResearchResponse(BaseModel):
    """Output model for the /research endpoint."""
    outlet:     str
    report:     str
    saved_to:   str
    generated:  str
    char_count: int
    notion_url: str = ""


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


@app.post("/research", tags=["Research"])
def research_outlet(request: ResearchRequest, req_obj: Request = None):
    """
    Start the Media Intelligence pipeline for a named outlet.
    Returns a job_id immediately. Poll GET /job/{job_id} for results.

    This avoids timeout issues on proxies (ngrok, Render) that close
    connections after 30 seconds. The pipeline runs in a background thread.
    """
    outlet = request.outlet.strip()
    if not outlet:
        raise HTTPException(status_code=400, detail="Outlet name cannot be empty.")

    # Deduplication -- if this outlet is already running, return existing job
    if not request.force_refresh:
        for existing_id, existing_job in _jobs.items():
            if (existing_job.get("outlet","").lower() == outlet.lower()
                    and existing_job.get("status") == "running"):
                print(f"[app] Dedup: returning existing job {existing_id} for {outlet}")
                return {"job_id": existing_id, "status": "running", "outlet": outlet}

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "report": None, "notion_url": "", "error": None}

    # Fire-and-forget N8N notification (runs in background)
    def notify_n8n(job_id: str, outlet: str, recipient: str):
        """Trigger N8N webhook after job completes -- handles Slack + Gmail."""
        import time
        n8n_url = os.getenv("N8N_WEBHOOK_URL", "")
        if not n8n_url:
            return
        # Wait for job to complete then notify N8N
        max_wait = 600  # 10 minutes
        interval = 15
        waited   = 0
        while waited < max_wait:
            time.sleep(interval)
            waited += interval
            job = _jobs.get(job_id, {})
            if job.get("status") in ("complete", "cached"):
                # Check if already notified (e.g. via cache hit)
                if job.get("n8n_notified"):
                    print(f"[app] N8N already notified for job {job_id} -- skipping duplicate")
                    break
                try:
                    import requests as req
                    payload = {
                        "outlet":          outlet,
                        "recipient_email": recipient,
                        "job_id":          job_id,
                        "notion_url":      job.get("notion_url", ""),
                        "overall_score":   job.get("overall_score", 0),
                        "report_url":      job.get("report_url", ""),
                    }
                    req.post(n8n_url, json=payload, timeout=10)
                    _jobs[job_id]["n8n_notified"] = True
                    print(f"[app] N8N notified for job {job_id}")
                except Exception as e:
                    print(f"[app] N8N notification failed: {e}")
                break
            if job.get("status") in ("error",):
                break

    def run_job():
        from datetime import datetime, timedelta
        try:
            print(f"\n[app] Starting pipeline for: {outlet} (job: {job_id})")
            filename = outlet.lower().replace(" ", "_").replace("/", "_")

            # Check Notion cache first (7 days)
            if not request.force_refresh:
                try:
                    from src.integrations.notion_client import list_reports_from_notion
                    reports = list_reports_from_notion()
                    from datetime import datetime, timedelta
                    cutoff  = datetime.now() - timedelta(days=7)
                    cutoff_str = cutoff.strftime("%Y-%m-%d")
                    print(f"[app] Cache check for '{outlet}' -- cutoff: {cutoff_str}")
                    print(f"[app] Notion has {len(reports)} reports: {[r.get('outlet') for r in reports]}")
                    match   = next((
                        r for r in reports
                        if r.get("outlet","").lower() == outlet.lower()
                        and r.get("generated","") >= cutoff_str
                    ), None)
                    print(f"[app] Cache match: {match.get('outlet') if match else 'None'}")
                    if match:
                        print(f"[app] Cache hit for {outlet} -- serving from Notion")
                        cached_report = open(f"reports/{filename}.md", encoding="utf-8").read() if __import__("os").path.exists(f"reports/{filename}.md") else ""
                        notion_url    = match.get("notion_url","")
                        overall_score = match.get("overall_score", 0)
                        recipient     = _jobs[job_id].get("recipient_email","")

                        _jobs[job_id]["status"]       = "cached"
                        _jobs[job_id]["report"]       = cached_report
                        _jobs[job_id]["saved_to"]     = f"reports/{filename}.md"
                        _jobs[job_id]["generated"]    = match.get("generated","")
                        _jobs[job_id]["char_count"]   = len(cached_report)
                        _jobs[job_id]["outlet"]       = outlet
                        _jobs[job_id]["notion_url"]   = notion_url
                        _jobs[job_id]["overall_score"]= overall_score
                        _jobs[job_id]["source"]       = "cache"
                        _jobs[job_id]["competitors"]  = match.get("competitors","")
                        _jobs[job_id]["top_dimension"]= match.get("top_dimension","")

                        # Trigger N8N notification for cache hit
                        n8n_url = os.getenv("N8N_WEBHOOK_URL", "")
                        if n8n_url:
                            try:
                                import requests as req
                                req.post(n8n_url, json={
                                    "outlet":          outlet,
                                    "recipient_email": recipient,
                                    "notion_url":      notion_url,
                                    "overall_score":   overall_score,
                                    "slack":           True,
                                    "source":          "cache",
                                    "ip":              _jobs[job_id].get("ip","unknown"),
                                }, timeout=10)
                                print(f"[app] N8N notified (cache hit) for {outlet}")
                                _jobs[job_id]["n8n_notified"] = True
                            except Exception as e:
                                print(f"[app] N8N notification failed: {e}")
                        return
                except Exception as cache_err:
                    print(f"[app] Cache check failed, running pipeline: {cache_err}")

            report = run_pipeline(outlet_name=outlet, save_report=True)
            if not report:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"]  = "Pipeline produced no report"
                return
            filename   = outlet.lower().replace(" ", "_").replace("/", "_")
            # Build a public report URL if available
            base_url   = os.getenv("PUBLIC_URL", "http://localhost:8000")
            report_url = f"{base_url}/report/{filename}"

            # Fetch notion_url from Notion database after save
            notion_url = ""
            try:
                from src.integrations.notion_client import list_reports_from_notion
                reports = list_reports_from_notion()
                match = next((r for r in reports if r.get("outlet","").lower() == outlet.lower()), None)
                if match:
                    notion_url = match.get("notion_url", "")
            except Exception:
                pass

            _jobs[job_id]["status"]     = "complete"
            _jobs[job_id]["report"]     = report
            _jobs[job_id]["saved_to"]   = f"reports/{filename}.md"
            _jobs[job_id]["generated"]  = datetime.now().isoformat()
            _jobs[job_id]["char_count"] = len(report)
            _jobs[job_id]["outlet"]     = outlet
            _jobs[job_id]["report_url"] = report_url
            _jobs[job_id]["notion_url"] = notion_url
            print(f"[app] Job {job_id} complete: {len(report)} chars | Notion: {notion_url[:50] if notion_url else 'not found'}")
        except Exception as e:
            print(f"[app] Job {job_id} failed: {e}")
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"]  = str(e)

    # Store recipient and IP for N8N notification
    _jobs[job_id]["recipient_email"] = request.recipient_email or ""
    forwarded = req_obj.headers.get("x-forwarded-for", "") if hasattr(req_obj, "headers") else ""
    _jobs[job_id]["ip"] = forwarded.split(",")[0].strip() if forwarded else "unknown"

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    # Start N8N notifier thread (fire and forget)
    # Only if not already notified via cache hit
    n8n_url = os.getenv("N8N_WEBHOOK_URL", "")
    if n8n_url and not _jobs[job_id].get("n8n_notified"):
        n8n_thread = threading.Thread(
            target=notify_n8n,
            args=(job_id, outlet, request.recipient_email or ""),
            daemon=True
        )
        n8n_thread.start()

    return {"job_id": job_id, "status": "running", "outlet": outlet}


@app.get("/job/{job_id}", tags=["Research"])
def get_job_status(job_id: str):
    """
    Poll this endpoint to check if a pipeline job is complete.
    Returns status: running | complete | error
    When complete, returns the full report.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


@app.post("/send-report", tags=["Reports"])
async def send_report(request: Request):
    """
    Send an already-generated report to an email address.
    Triggers N8N Workflow 1 with slack=false (email only, no Slack).
    Called from the UI when user enters email after viewing the report.
    """
    body = await request.json()
    outlet    = (body.get("outlet", "") or "").strip()
    recipient = (body.get("recipient_email", "") or "").strip()

    if not outlet:
        raise HTTPException(status_code=400, detail="outlet is required")
    if not recipient:
        raise HTTPException(status_code=400, detail="recipient_email is required")

    # Basic email validation
    import re
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", recipient):
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Use dedicated email-only webhook (no Slack)
    n8n_email_url = os.getenv("N8N_EMAIL_WEBHOOK_URL",
                    os.getenv("N8N_WEBHOOK_URL","").replace("media-intelligence-notify","media-intelligence-email"))
    if not n8n_email_url:
        raise HTTPException(status_code=500, detail="N8N webhook not configured")

    try:
        import requests as req
        payload = {
            "outlet":          outlet,
            "recipient_email": recipient,
            "notion_url":      "",
            "overall_score":   0,
        }
        resp = req.post(n8n_email_url, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"[app] Report sent to {recipient} for outlet: {outlet}")
        return {"status": "sent", "outlet": outlet, "recipient": recipient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")


@app.get("/reports-library", tags=["Reports"])
def list_reports_library():
    """
    Fetch all past reports from the Notion database.
    Returns a list of reports with outlet, date, score, and Notion URL.
    """
    try:
        from src.integrations.notion_client import list_reports_from_notion
        reports = list_reports_from_notion()
        return {"count": len(reports), "reports": reports}
    except Exception as e:
        return {"count": 0, "reports": [], "error": str(e)}


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
