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

try:
    from .database import Database, init_db
    from .scanner import run_scan
    from .draft_generator import generate_draft
except ImportError:
    # Old v4 modules may not exist, that's OK
    Database = None
    init_db = None
    run_scan = None
    generate_draft = None

# Import v5 routers
from .routes import dates as dates_router
from .routes import cities as cities_router
from .routes import jobs as jobs_router
from .routes import advisor as advisor_router
from .routes import readiness as readiness_router

# Import v5 models for backward compatibility
from .models import JobResponse as Job


# Initialize FastAPI app
app = FastAPI(
    title="Life Systems API",
    description="Personal intelligence platform for career, dating, and relocation",
    version="0.1.0"
)

# Register v5 routers
app.include_router(dates_router.router, prefix="/api")
app.include_router(cities_router.router, prefix="/api")
app.include_router(jobs_router.router, prefix="/api")
app.include_router(advisor_router.router, prefix="/api")
app.include_router(readiness_router.router, prefix="/api")

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
    """
    Health check endpoint with DB version and table counts.
    SHARED-MVP-1 acceptance criteria.
    """
    import sqlite3
    
    db_path = Path(os.getenv("DB_PATH", "/var/lib/life-systems/life.db"))
    
    # Get DB version and table counts
    conn = sqlite3.connect(str(db_path))
    
    # Get schema version
    try:
        version_row = conn.execute(
            "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        db_version = version_row[0] if version_row else "unknown"
    except sqlite3.OperationalError:
        db_version = "legacy"
    
    # Get table counts (exclude metadata and v4 archived tables)
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
            AND name NOT LIKE '%_v4'
            AND name NOT IN ('schema_version', 'sqlite_sequence')
        ORDER BY name
    """)
    
    table_counts = {}
    for row in cursor.fetchall():
        table_name = row[0]
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        table_counts[table_name] = count
    
    conn.close()
    
    return {
        "status": "ok",
        "version": "0.1.0",
        "db_version": db_version,
        "db_tables": table_counts,
        "timestamp": datetime.utcnow().isoformat()
    }


# V4 legacy endpoints removed - now using v5 jobs router above
# See api/routes/jobs.py for APPL-MVP-1 implementation


@app.get("/api/dashboard")
async def get_dashboard(
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """
    Get dashboard view model (advisor paradigm).
    
    Returns advisor-format shape for advisor.html:
    {
      "advisor": {
        "career": {goal, one_liner, data_table, actions, empty_state},
        "dating": {goal, one_liner, data_table, actions, empty_state},
        "location": {goal, one_liner, data_table, actions, empty_state},
        "recommendations": []
      },
      "timestamp": "ISO timestamp"
    }
    """
    # Import the TASK-039 compliant builder
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from database.dashboard_v2 import get_dashboard_view_model
    
    # Build view model
    data = get_dashboard_view_model()
    
    # Location already in advisor format
    location_advisor = data.get("location", {})
    
    # Transform career to advisor format
    career_data = data.get("career", {})
    career_advisor = _transform_career_to_advisor(career_data)
    
    # Transform dating to advisor format (stub for now)
    dating_data = data.get("dating", {})
    dating_advisor = {
        "goal": "GOAL-1: Partner + Family",
        "one_liner": "After you log your first date, I'll start tracking patterns.",
        "data_table": [],
        "actions": [],
        "empty_state": True
    }
    
    # Build advisor response
    advisor_data = {
        "advisor": {
            "dating": dating_advisor,
            "career": career_advisor,
            "location": location_advisor,
            "recommendations": []
        },
        "timestamp": data.get("fetchedAt", datetime.utcnow().isoformat())
    }
    
    return advisor_data


def _transform_career_to_advisor(career_data: dict) -> dict:
    """Transform TASK-039 career format to advisor format."""
    total_jobs = career_data.get("totalJobs", 0)
    top_jobs = career_data.get("topJobs", [])
    
    if total_jobs == 0:
        return {
            "goal": "GOAL-2: Senior AI/ML Role (€150k+)",
            "one_liner": "Job scanner is running. New opportunities will appear here.",
            "data_table": [],
            "actions": [],
            "empty_state": True
        }
    
    # Build one-liner (motivation-first)
    best_job = top_jobs[0] if top_jobs else None
    if best_job:
        one_liner = f"{total_jobs} new roles match your criteria. Top: {best_job['title']} at {best_job['company']}."
    else:
        one_liner = f"{total_jobs} new roles match your criteria."
    
    # Build data table from top 5 jobs
    data_table = []
    for job in top_jobs[:5]:
        data_table.append({
            "company": job.get("company", "Unknown"),
            "role": job.get("title", "Position"),
            "location": job.get("location", "Remote"),
            "discovered": job.get("discoveredAt", "")[:10] if job.get("discoveredAt") else ""
        })
    
    # Actions
    actions = [
        {
            "type": "primary",
            "label": "Review Jobs",
            "href": "/api/jobs"
        }
    ]
    
    return {
        "goal": "GOAL-2: Senior AI/ML Role (€150k+)",
        "one_liner": one_liner,
        "data_table": data_table,
        "actions": actions,
        "empty_state": False
    }


@app.get("/api/market")
async def get_market_report(
    username: str = Depends(verify_auth),
    db: Database = Depends(get_db)
):
    """Get latest market intelligence report."""
    report = db.get_latest_market_report()
    if not report:
        raise HTTPException(status_code=404, detail="No market report available")
    return report


# V4 legacy endpoints for /draft and /decide removed - now using v5 jobs router above


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
