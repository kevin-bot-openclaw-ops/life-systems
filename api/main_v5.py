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
from .routes import readiness as readiness_router
from .routes import advisor as advisor_router
from .routes import jobs as jobs_router
from .routes import cities as cities_router

# Initialize FastAPI app
app = FastAPI(
    title="Life Systems API v5",
    description="Personal intelligence platform for career, dating, and relocation",
    version="0.1.0"
)

# Register v5 routers
# Note: dates, readiness, cities already have /api prefix in their router definition
app.include_router(dates_router.router)  # Has prefix="/api/dates" in file
app.include_router(readiness_router.router)  # Has prefix="/api/readiness" in file
app.include_router(cities_router.router)  # Has prefix="/api/cities" in file
# advisor and jobs need /api prefix added here
app.include_router(advisor_router.router, prefix="/api")
app.include_router(jobs_router.router, prefix="/api")

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
    """
    Personal Life Strategy Advisor Dashboard (DASH-MVP-1)
    
    Follows ADR-005: Every section has [one-liner + data table + actions]
    Connected to GOAL-1 (partner), GOAL-2 (career), GOAL-3 (location)
    """
    db_path = Path("/var/lib/life-systems/life.db")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # GOAL-1: Dating section
    dating = _build_dating_advisor(conn)
    
    # GOAL-2: Career section
    career = _build_career_advisor(conn)
    
    # GOAL-3: Location section
    location = _build_location_advisor(conn)
    
    # Top recommendations across all domains
    recommendations = _build_recommendations(conn)
    
    conn.close()
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "advisor": {
            "dating": dating,
            "career": career,
            "location": location,
            "recommendations": recommendations
        }
    }


def _build_dating_advisor(conn) -> dict:
    """GOAL-1: Find life partner - dating insights."""
    # Count total dates
    cursor = conn.execute("SELECT COUNT(*) as count FROM dates WHERE archived = 0")
    total_dates = cursor.fetchone()['count']
    
    if total_dates == 0:
        return {
            "one_liner": "After your first 3 dates, I'll show you which sources work best for finding quality connections.",
            "data_table": [],
            "actions": [
                {"type": "primary", "label": "Log a date", "href": "/api/dates"},
                {"type": "secondary", "label": "View guide", "href": "/docs/IPHONE-SHORTCUT-GUIDE.md"}
            ],
            "empty_state": True
        }
    
    # Get source breakdown
    cursor = conn.execute("""
        SELECT 
            source,
            COUNT(*) as count,
            AVG(quality) as avg_quality,
            MAX(quality) as max_quality
        FROM dates
        WHERE archived = 0
        GROUP BY source
        ORDER BY avg_quality DESC
    """)
    
    sources = []
    for row in cursor.fetchall():
        sources.append({
            "source": row['source'].title(),
            "dates": row['count'],
            "avg_quality": round(row['avg_quality'], 1),
            "best": row['max_quality']
        })
    
    # Generate one-liner
    if sources:
        best_source = sources[0]
        one_liner = f"{best_source['source']} is your strongest channel — {best_source['avg_quality']}/10 average quality across {best_source['dates']} dates."
    else:
        one_liner = f"You've logged {total_dates} dates. Keep tracking to see which sources work best."
    
    return {
        "one_liner": one_liner,
        "data_table": sources,
        "actions": [
            {"type": "primary", "label": "Log another date", "href": "/api/dates"},
            {"type": "secondary", "label": "View all dates", "href": "/api/dates"}
        ],
        "goal": "GOAL-1: Find life partner",
        "empty_state": False
    }


def _build_career_advisor(conn) -> dict:
    """GOAL-2: Strong AI career position - job opportunities."""
    # Count jobs discovered
    cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status = 'new'")
    total_jobs = cursor.fetchone()['count']
    
    if total_jobs == 0:
        return {
            "one_liner": "After 1 week of job scanning, I'll surface your strongest AI/ML matches from 3 sources.",
            "data_table": [],
            "actions": [
                {"type": "primary", "label": "Run scanner now", "href": "/api/scan"},
                {"type": "secondary", "label": "View scanner status", "href": "/api/health"}
            ],
            "empty_state": True
        }
    
    # Get top 3 jobs (by discovered_at for now, will be by score after DISC-MVP-2)
    cursor = conn.execute("""
        SELECT 
            id,
            title,
            company,
            location,
            salary_range,
            source
        FROM jobs
        WHERE status = 'new' AND archived = 0
        ORDER BY discovered_at DESC
        LIMIT 3
    """)
    
    jobs = []
    for row in cursor.fetchall():
        jobs.append({
            "id": row['id'],
            "title": row['title'],
            "company": row['company'] or "Unknown",
            "location": row['location'] or "Remote",
            "salary": row['salary_range'] or "Not specified",
            "source": row['source']
        })
    
    # Generate one-liner
    one_liner = f"{total_jobs} new AI/ML jobs discovered. Review top matches below."
    
    return {
        "one_liner": one_liner,
        "data_table": jobs,
        "actions": [
            {"type": "primary", "label": "Review all jobs", "href": "/api/jobs"},
            {"type": "secondary", "label": "Scan for more", "href": "/api/scan"}
        ],
        "goal": "GOAL-2: Strong AI career position",
        "empty_state": False
    }


def _build_location_advisor(conn) -> dict:
    """GOAL-3: Optimal location decision - city comparison (CORRECTED 2026-03-07)."""
    from datetime import datetime, timedelta
    
    # Count cities evaluated
    cursor = conn.execute("SELECT COUNT(*) as count FROM cities")
    total_cities = cursor.fetchone()['count']
    
    if total_cities == 0:
        return {
            "one_liner": "Add 3+ candidate cities to get a data-backed recommendation on where to live for best dating + career outcomes.",
            "data_table": [],
            "actions": [
                {"type": "primary", "label": "Add cities", "href": "/api/cities"},
                {"type": "secondary", "label": "View research", "href": "/docs/RELOC-DATA-SOURCES.md"}
            ],
            "empty_state": True
        }
    
    # Get top 3 cities by composite score (corrected model)
    cursor = conn.execute("""
        SELECT 
            name,
            country,
            dating_pool_verified,
            onsite_hybrid_ai_jobs,
            remote_ai_jobs,
            language_advantage,
            dating_culture_fit,
            composite_score
        FROM cities
        ORDER BY composite_score DESC NULLS LAST
        LIMIT 3
    """)
    
    cities = []
    top_city = None
    for i, row in enumerate(cursor.fetchall()):
        city_data = {
            "city": f"{row['name']}, {row['country']}",
            "dating_pool": f"{row['dating_pool_verified']:,}" if row['dating_pool_verified'] else "TBD",
            "onsite_jobs": f"{row['onsite_hybrid_ai_jobs']}" if row['onsite_hybrid_ai_jobs'] is not None else "TBD",
            "remote_jobs": f"{row['remote_ai_jobs']}" if row['remote_ai_jobs'] is not None else "TBD",
            "score": round(row['composite_score'], 2) if row['composite_score'] else 0
        }
        cities.append(city_data)
        
        if i == 0:
            top_city = row
    
    # Generate one-liner with corrected comparison
    if cities and cities[0]['score'] > 0:
        # Calculate comparison to Fuerteventura
        cursor = conn.execute("""
            SELECT dating_pool_verified, onsite_hybrid_ai_jobs
            FROM cities
            WHERE name = 'Fuerteventura'
        """)
        fuerte = cursor.fetchone()
        
        if fuerte and top_city:
            dating_multiplier = top_city['dating_pool_verified'] / max(fuerte['dating_pool_verified'], 1)
            jobs_multiplier = top_city['onsite_hybrid_ai_jobs'] / max(fuerte['onsite_hybrid_ai_jobs'], 1)
            
            # Days until May 1, 2026 decision deadline
            decision_date = datetime(2026, 5, 1)
            days_until = (decision_date - datetime.utcnow()).days
            
            one_liner = f"{top_city['name']} leads with {dating_multiplier:.0f}x larger dating pool and {jobs_multiplier:.0f}x more local AI jobs. ({days_until} days until May 1 decision)."
        else:
            one_liner = f"{cities[0]['city']} ranks highest — strongest combination of dating pool + career options."
    else:
        one_liner = f"{total_cities} cities added. Complete data collection to see ranking."
    
    return {
        "one_liner": one_liner,
        "data_table": cities,
        "actions": [
            {"type": "primary", "label": "Full comparison", "href": "/api/cities"},
            {"type": "secondary", "label": "View details", "href": "/api/cities/recommendation"}
        ],
        "goal": "GOAL-3: Optimal location decision (May 1, 2026 deadline)",
        "empty_state": False
    }



def _build_recommendations(conn) -> list:
    """Top 3 cross-domain recommendations."""
    # For now, return static seed recommendations until rules engine is built
    return [
        {
            "one_liner": "Log your next date within 24 hours to build consistent tracking habits.",
            "priority": 1,
            "goal": "GOAL-1",
            "action": {"type": "primary", "label": "Log date", "href": "/api/dates"}
        },
        {
            "one_liner": "Review new job matches before they get stale (most posted <48h ago).",
            "priority": 2,
            "goal": "GOAL-2",
            "action": {"type": "primary", "label": "Review jobs", "href": "/api/jobs"}
        },
        {
            "one_liner": "Add Madrid to city comparison — it's showing strong signals for both dating and AI jobs.",
            "priority": 3,
            "goal": "GOAL-3",
            "action": {"type": "primary", "label": "Add city", "href": "/api/cities"}
        }
    ]


# Serve advisor frontend
from fastapi.responses import FileResponse

@app.get("/")
async def serve_advisor():
    """Serve Personal Life Strategy Advisor (DASH-MVP-1)."""
    advisor_path = Path(__file__).parent / "static" / "advisor.html"
    if advisor_path.exists():
        return FileResponse(advisor_path)
    return {"message": "Life Systems API", "docs": "/docs"}
