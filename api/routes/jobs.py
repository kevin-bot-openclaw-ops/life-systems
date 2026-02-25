"""
Jobs API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(tags=["jobs"])

class JobDecision(BaseModel):
    action: str  # approve, reject, defer

@router.get("/jobs")
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    min_score: Optional[int] = None
):
    """
    Get paginated list of scored job listings.
    """
    # TODO: Query from DB with scores
    return {
        "jobs": [],
        "total": 0,
        "skip": skip,
        "limit": limit
    }

@router.get("/jobs/{job_id}")
async def get_job(job_id: int):
    """
    Get single job with full details + generated draft cover letter.
    """
    # TODO: Query from DB, join with scores and drafts
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/jobs/{job_id}/draft")
async def generate_draft(job_id: int):
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
async def decide_on_job(job_id: int, decision: JobDecision):
    """
    Record decision (approve/reject/defer) on a job.
    """
    # TODO: Insert into decisions table
    return {
        "job_id": job_id,
        "action": decision.action,
        "status": "recorded"
    }
