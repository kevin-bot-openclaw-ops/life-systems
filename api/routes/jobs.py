"""
Jobs API routes - APPL-MVP-1 implementation.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3
from datetime import datetime
import secrets
import os

router = APIRouter(tags=["jobs"])
security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication."""
    LS_USER = os.getenv("LS_USER", "admin")
    LS_PASSWORD = os.getenv("LS_PASSWORD", "changeme")
    
    correct_username = secrets.compare_digest(credentials.username, LS_USER)
    correct_password = secrets.compare_digest(credentials.password, LS_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def get_db():
    """Get database connection."""
    return sqlite3.connect("database/life.db")

class JobDecision(BaseModel):
    action: str = Field(..., pattern="^(approve|skip|save)$", description="Decision action: approve, skip, or save")
    reasoning: Optional[str] = Field(None, description="Optional reasoning for the decision")

@router.get("/jobs")
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    min_score: Optional[int] = None,
    status: Optional[str] = None,
    username: str = Depends(verify_auth)
):
    """
    Get paginated list of scored job listings.
    
    - **skip**: Number of jobs to skip (default: 0)
    - **limit**: Maximum number of jobs to return (default: 20)
    - **min_score**: Minimum total score filter (optional)
    - **status**: Filter by job status: new, reviewed, approved, skipped, saved, applied, etc. (optional)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Build query
    query = """
        SELECT j.id, j.external_id, j.source, j.title, j.company, j.url, 
               j.location, j.remote, j.salary_min, j.salary_max, j.salary_currency,
               j.description, j.status, j.discovered_at, j.created_at,
               s.total_score, s.role_match, s.remote_score, s.salary_fit, 
               s.tech_overlap, s.company_size
        FROM jobs j
        LEFT JOIN scores s ON j.id = s.job_id
        WHERE 1=1
    """
    params = []
    
    if min_score is not None:
        query += " AND s.total_score >= ?"
        params.append(min_score)
    
    if status is not None:
        query += " AND j.status = ?"
        params.append(status)
    
    # Get total count
    count_query = query.replace("SELECT j.id, j.external_id, j.source, j.title, j.company, j.url, j.location, j.remote, j.salary_min, j.salary_max, j.salary_currency, j.description, j.status, j.discovered_at, j.created_at, s.total_score, s.role_match, s.remote_score, s.salary_fit, s.tech_overlap, s.company_size", "SELECT COUNT(*)")
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    # Add pagination
    query += " ORDER BY j.discovered_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, skip])
    
    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "jobs": jobs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/jobs/{job_id}")
async def get_job(job_id: int, username: str = Depends(verify_auth)):
    """
    Get single job with full details + generated draft cover letter.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT j.id, j.external_id, j.source, j.title, j.company, j.url, 
               j.location, j.remote, j.salary_min, j.salary_max, j.salary_currency,
               j.description, j.requirements, j.posted_date, j.status, 
               j.discovered_at, j.created_at,
               s.total_score, s.role_match, s.remote_score, s.salary_fit, 
               s.tech_overlap, s.company_size, s.scored_at,
               d.action, d.decided_at, d.notes AS decision_notes
        FROM jobs j
        LEFT JOIN scores s ON j.id = s.job_id
        LEFT JOIN decisions d ON j.id = d.job_id
        WHERE j.id = ?
    """, (job_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    columns = [desc[0] for desc in cursor.description]
    job = dict(zip(columns, row))
    
    return job

@router.post("/jobs/{job_id}/draft")
async def generate_draft(job_id: int, username: str = Depends(verify_auth)):
    """
    Generate cover letter draft using Claude API.
    Requires ANTHROPIC_API_KEY env var.
    """
    # TODO: Implement Claude API call
    return {
        "draft_id": 1,
        "content": "Draft will be generated via Claude API in Phase 5",
        "variant": "ai_engineer"
    }

@router.post("/jobs/{job_id}/decide")
async def decide_on_job(job_id: int, decision: JobDecision, username: str = Depends(verify_auth)):
    """
    Record decision (approve/skip/save) on a job.
    
    - **action**: One of: approve, skip, save
    - **reasoning**: Optional explanation for the decision
    
    This will update the job status and create a decision record.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if job exists
    cursor.execute("SELECT id, status FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Map action to status
    status_map = {
        "approve": "approved",
        "skip": "skipped",
        "save": "saved"
    }
    new_status = status_map[decision.action]
    
    try:
        # Update job status
        cursor.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (new_status, job_id)
        )
        
        # Insert decision record
        cursor.execute(
            "INSERT INTO decisions (job_id, action, notes, decided_at) VALUES (?, ?, ?, ?)",
            (job_id, decision.action, decision.reasoning, datetime.utcnow().isoformat())
        )
        
        conn.commit()
        
        return {
            "job_id": job_id,
            "action": decision.action,
            "status": new_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording decision: {str(e)}")
    finally:
        conn.close()
