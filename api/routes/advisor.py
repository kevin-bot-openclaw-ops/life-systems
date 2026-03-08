"""
Advisor View API - ACT-M1-1
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from database.advisor_view import get_advisor_view
from database.db import get_db

router = APIRouter(tags=["advisor"])


class RecommendationDecision(BaseModel):
    """Decision on a recommendation (accept/snooze/dismiss)."""
    action: str  # "accept", "snooze", "dismiss"
    recommendation_id: str
    duration_hours: Optional[int] = None  # For snooze


class ActivityLog(BaseModel):
    """Log an activity to Activities API (Kevin's JWT auth)."""
    activity_type: str
    duration_minutes: int
    note: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("/advisor")
async def get_advisor():
    """
    Get advisor view with Health Optimizer + Dating Intelligence sections.
    Returns: one-liner + data tables + action buttons per ADR-005.
    """
    try:
        return get_advisor_view()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advisor/decide")
async def decide_recommendation(decision: RecommendationDecision):
    """
    Handle recommendation decision: accept/snooze/dismiss.
    
    - accept: Logs activity if applicable, marks recommendation as accepted
    - snooze: Suppresses recommendation for N hours
    - dismiss: Marks recommendation as dismissed (won't show again for same pattern)
    """
    conn = get_db()
    
    if decision.action == "accept":
        # Log to recommendations table as accepted
        conn.execute("""
            INSERT INTO recommendations (
                rule_id, one_liner, data_table, actions, 
                decision, decided_at
            ) VALUES (?, ?, ?, ?, 'accepted', ?)
        """, (
            decision.recommendation_id,
            "",  # Would fetch from cache in production
            "{}",
            "{}",
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        
        return {"status": "accepted", "message": "Recommendation accepted"}
    
    elif decision.action == "snooze":
        duration_hours = decision.duration_hours or 4
        resume_at = datetime.utcnow() + timedelta(hours=duration_hours)
        
        conn.execute("""
            INSERT INTO recommendations (
                rule_id, one_liner, data_table, actions,
                decision, snoozed_until
            ) VALUES (?, ?, ?, ?, 'snoozed', ?)
        """, (
            decision.recommendation_id,
            "",
            "{}",
            "{}",
            resume_at.isoformat()
        ))
        conn.commit()
        
        return {
            "status": "snoozed",
            "resume_at": resume_at.isoformat(),
            "message": f"Snoozed for {duration_hours} hours"
        }
    
    elif decision.action == "dismiss":
        conn.execute("""
            INSERT INTO recommendations (
                rule_id, one_liner, data_table, actions,
                decision, decided_at
            ) VALUES (?, ?, ?, ?, 'dismissed', ?)
        """, (
            decision.recommendation_id,
            "",
            "{}",
            "{}",
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        
        return {"status": "dismissed", "message": "Recommendation dismissed"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: accept, snooze, dismiss")


@router.post("/advisor/log-activity")
async def log_activity(activity: ActivityLog):
    """
    Log activity to Activities API using Kevin's JWT auth.
    This is called when user clicks [Accept + Log] button.
    
    NOTE: This requires Kevin's JWT token for Activities API.
    For MVP, we'll store in local activities table. 
    In production, this would call Activities API.
    """
    conn = get_db()
    
    # For MVP: Store locally in activities table
    occurred_at = datetime.utcnow().isoformat()
    occurred_date = datetime.utcnow().date().isoformat()
    
    conn.execute("""
        INSERT INTO activities (
            activity_type,
            occurred_at,
            occurred_date,
            duration_minutes,
            note,
            tags,
            goal_mapping
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        activity.activity_type,
        occurred_at,
        occurred_date,
        activity.duration_minutes,
        activity.note or "",
        json.dumps(activity.tags or []),
        "Health"  # Default mapping
    ))
    conn.commit()
    conn.close()
    
    return {
        "status": "logged",
        "activity_type": activity.activity_type,
        "duration_minutes": activity.duration_minutes,
        "occurred_at": occurred_at
    }


@router.get("/advisor/health")
async def get_health_optimizer():
    """Get only Health & Attractiveness Optimizer section."""
    from database.advisor_view import build_health_optimizer_view
    
    conn = get_db()
    health = build_health_optimizer_view(conn)
    conn.close()
    
    return health


@router.get("/advisor/dating")
async def get_dating_intelligence():
    """Get only Dating Intelligence section."""
    from database.advisor_view import build_dating_intelligence_view
    
    conn = get_db()
    dating = build_dating_intelligence_view(conn)
    conn.close()
    
    return dating
