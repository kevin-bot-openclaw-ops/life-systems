"""
Action queue API routes.
"""
from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(tags=["actions"])

@router.get("/actions")
async def get_actions():
    """
    Get today's action queue: jobs to review, drafts ready, date logging, gym check-in.
    """
    # TODO: Query actions table + related data
    return {
        "pending": [
            {
                "id": 1,
                "type": "review_job",
                "title": "Review: Stripe ML Engineer (score: 89)",
                "job_id": 123,
                "priority": 1
            },
            {
                "id": 2,
                "type": "approve_draft",
                "title": "Review draft for Apollo.io",
                "job_id": 121,
                "draft_id": 5,
                "priority": 2
            },
            {
                "id": 3,
                "type": "log_date",
                "title": "Log yesterday's date (Faby)",
                "priority": 3
            },
            {
                "id": 4,
                "type": "log_gym",
                "title": "Did you work out today?",
                "priority": 4
            }
        ],
        "completed_today": 2,
        "total_pending": 4
    }
