"""
Life Systems v5 FastAPI Application
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

# Import v5 routers
from .routes import dates as dates_router

# Initialize FastAPI app
app = FastAPI(
    title="Life Systems API v5",
    description="Personal intelligence platform for career, dating, and relocation",
    version="0.1.0"
)

# Register v5 routers
app.include_router(dates_router.router)

# Basic auth
security = HTTPBasic()
LS_USER = os.getenv("LS_USER", "jurek")
LS_PASSWORD = os.getenv("LS_PASSWORD", "LifeSystems2026!")

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

@app.get("/api/health")
async def health():
    """Health check with DB version and table counts."""
    db_path = Path("/var/lib/life-systems/life.db")
    conn = sqlite3.connect(str(db_path))
    
    # Get schema version
    try:
        version_row = conn.execute(
            "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        db_version = version_row[0] if version_row else "unknown"
    except sqlite3.OperationalError:
        db_version = "legacy"
    
    # Get table counts
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

@app.get("/api/dashboard")
async def get_dashboard(username: str = Depends(verify_auth)):
    """Dashboard view model (v5 minimal stub until DASH-MVP-1)."""
    # Wrap in payload.sections structure for compatibility with old frontend
    sections = {
        "career": {
            "score": 0,
            "totalJobs": 0,
            "topJobs": [],
            "funnel": {"discovered": 0, "applied": 0, "responded": 0, "interviewing": 0, "offered": 0},
            "lastScan": None
        },
        "dating": {
            "score": 0,
            "dates": [],
            "weeklyHours": 0,
            "upcomingEvents": []
        },
        "market": {
            "top_skills": [],
            "salary_ranges": {},
            "weekly_summary": "No data yet"
        },
        "relocation": {
            "city_rankings": [],
            "recommendation": "No data yet"
        }
    }
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "sections": sections,
            "conflicts": [],
            "alerts": []
        }
    }
