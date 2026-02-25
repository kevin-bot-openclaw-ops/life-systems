"""
Dashboard API routes.
"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard")
async def get_dashboard():
    """
    Get full synthesized dashboard state.
    Returns: scores, action queue, weekly pulse, last scan.
    """
    # TODO: Query all tables, calculate composite scores
    return {
        "scores": {
            "career": 72,
            "dating": 45,
            "fitness_streak": 8
        },
        "actions_today": {
            "jobs_to_review": 3,
            "drafts_ready": 1,
            "date_logging_needed": True,
            "gym_check_in": False
        },
        "weekly_pulse": {
            "applications_sent": 8,
            "responses_received": 2,
            "dates": 1,
            "gym_sessions": 4,
            "bachata_classes": 2
        },
        "last_scan": "2026-02-25T18:00:00Z",
        "career_score_breakdown": {
            "pipeline_velocity": 65,
            "skill_progress": 75,
            "daily_momentum": 80,
            "goal_proximity": 70
        },
        "dating_score_breakdown": {
            "activity_level": 50,
            "social_breadth": 45,
            "consistency": 40,
            "quality_trend": 45
        }
    }
