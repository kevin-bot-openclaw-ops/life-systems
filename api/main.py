"""
Life Systems FastAPI Application
Main entry point for the web service.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import secrets

from .database import Database, init_db
from .models import (
    Job, JobDetail, DashboardState, MarketReport,
    DraftRequest, DraftResponse, DecisionRequest
)
from .scanner import run_scan
from .draft_generator import generate_draft


# Initialize FastAPI app
app = FastAPI(
    title="Life Systems API",
    description="Personal intelligence platform for career, dating, and relocation",
    version="0.1.0"
)

# Basic auth
security = HTTPBasic()

# Environment variables
LS_USER = os.getenv("LS_USER", "admin")
LS_PASSWORD = os.getenv("LS_PASSWORD", "changeme")


def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication."""
    correct_username = secrets.compare_digest(credentials.username, LS_USER)
    correct_password = secrets.compare_digest(credentials.password, LS_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Database dependency
def get_db():
    """Get database connection."""
    db_path = Path(os.getenv("DB_PATH", "/var/lib/life-systems/life.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Database(str(db_path))


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    db_path = Path(os.getenv("DB_PATH", "/var/lib/life-systems/life.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(str(db_path))


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/jobs", response_model=List[Job])
async def get_jobs(
    limit: int = 10,
    offset: int = 0,
    min_score: Optional[float] = None,
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Get scored job listings."""
    jobs = db.get_jobs(limit=limit, offset=offset, min_score=min_score)
    return jobs


@app.get("/api/jobs/{job_id}", response_model=JobDetail)
async def get_job_detail(
    job_id: str,
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Get detailed job listing with generated draft cover letter."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get existing draft or generate new one
    draft = db.get_draft(job_id)
    if not draft:
        draft_text = generate_draft(job)
        draft_id = db.save_draft(job_id, draft_text)
        draft = {"id": draft_id, "job_id": job_id, "text": draft_text}
    
    return JobDetail(**job, draft=draft)


@app.get("/api/dashboard")
async def get_dashboard(
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """
    Get dashboard view model (TASK-039 compliant).
    
    Returns DashboardViewModel shape as specified in TASK-039-subtasks.md (039-A):
    {
      "career": {score, totalJobs, topJobs[], funnel, lastScan},
      "dating": {score, dates[], weeklyHours, upcomingEvents[]},
      "system": {version, lastHealthCheck, status},
      "alerts": [],
      "fetchedAt": "ISO timestamp"
    }
    """
    # Import the TASK-039 compliant builder
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from database.dashboard_v2 import get_dashboard_view_model
    
    # Build and return view model
    return get_dashboard_view_model()


@app.get("/api/market", response_model=MarketReport)
async def get_market_report(
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Get latest market intelligence report."""
    report = db.get_latest_market_report()
    if not report:
        raise HTTPException(status_code=404, detail="No market report available")
    return report


@app.post("/api/jobs/{job_id}/draft", response_model=DraftResponse)
async def create_draft(
    job_id: str,
    request: Optional[DraftRequest] = None,
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Generate a cover letter draft for a job."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Generate draft
    draft_text = generate_draft(
        job,
        variant=request.variant if request else None
    )
    
    # Save to database
    draft_id = db.save_draft(job_id, draft_text)
    
    return DraftResponse(
        id=draft_id,
        job_id=job_id,
        text=draft_text,
        created_at=datetime.utcnow()
    )


@app.post("/api/jobs/{job_id}/decide")
async def decide_on_job(
    job_id: str,
    decision: DecisionRequest,
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Record a decision on a job (approve/reject/defer)."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Record decision
    db.save_decision(
        job_id=job_id,
        action=decision.action,
        reason=decision.reason
    )
    
    return {
        "status": "success",
        "job_id": job_id,
        "action": decision.action
    }


@app.get("/api/widget")
async def get_widget_data(
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Get minimal data for iPhone Scriptable widget."""
    state = db.get_dashboard_state()
    
    return {
        "career_score": state.get("career_score", 0),
        "dating_score": state.get("dating_score", 0),
        "gym_streak": state.get("gym_streak", 0),
        "actions_today": state.get("actions_today", 0)
    }


@app.post("/api/scan")
async def trigger_scan(
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Manually trigger a job scan (admin only)."""
    results = await run_scan(db)
    return {
        "status": "success",
        "jobs_found": len(results),
        "timestamp": datetime.utcnow().isoformat()
    }


# Mount static files (React SPA)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_spa():
    """Serve React SPA."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Life Systems API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info"
    )
