"""
Recommendations API routes for LEARN-M2-1

Exposes unified recommendation feed that aggregates:
- SYNTH rules (dating, career, location)
- ACT rules (health, activities)
- AI analyses (future)

Decision tracking enables feedback loop to Activities API.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os

from synthesis.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["recommendations"])


# --- Pydantic Models ---

class RecommendationResponse(BaseModel):
    """Single recommendation from the unified feed."""
    rule_id: str
    domain: str
    one_liner: str
    data_table: List[Dict[str, Any]]
    goal_alignment: str
    priority_score: float
    cross_domain_context: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, str]]
    fired_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "rule_id": "R-DATE-01",
                "domain": "dating",
                "one_liner": "Thursday bachata is your best bet -- 3x quality vs apps.",
                "data_table": [
                    {"source": "bachata", "avg_quality": 8.2, "count": 5},
                    {"source": "bumble", "avg_quality": 6.1, "count": 12}
                ],
                "goal_alignment": "GOAL-1 (find partner)",
                "priority_score": 95.0,
                "cross_domain_context": {
                    "health_score": 7.0,
                    "stress_level": "low",
                    "exercise_streak": 3
                },
                "actions": [
                    {"label": "Accept + Log", "type": "accept"},
                    {"label": "Snooze 4h", "type": "snooze"},
                    {"label": "Dismiss", "type": "dismiss"}
                ],
                "fired_at": "2026-03-08T15:03:00Z"
            }
        }


class RecommendationsListResponse(BaseModel):
    """List of top recommendations."""
    recommendations: List[RecommendationResponse]
    total_count: int
    generated_at: str


class DecisionRequest(BaseModel):
    """Request to record a decision on a recommendation."""
    action: str = Field(..., regex="^(accept|snooze|dismiss)$")
    
    class Config:
        schema_extra = {
            "example": {
                "action": "accept"
            }
        }


class DecisionResponse(BaseModel):
    """Response after recording a decision."""
    status: str
    action: str
    rule_id: str
    snooze_until: Optional[str] = None
    activity_logged: bool = False
    activity_result: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "action": "accept",
                "rule_id": "R-ACT-05",
                "snooze_until": None,
                "activity_logged": True,
                "activity_result": {"id": "abc123", "type": "uttanasana"}
            }
        }


# --- Dependency ---

def get_recommendation_engine() -> RecommendationEngine:
    """
    Dependency: Create RecommendationEngine instance.
    
    Reads DB path and Activities token from environment.
    """
    db_path = os.getenv("DB_PATH", "life.db")
    activities_token = os.getenv("ACTIVITIES_JWT_TOKEN")  # Kevin's JWT token
    
    return RecommendationEngine(db_path, activities_token)


# --- Endpoints ---

@router.get("/recommendations", response_model=RecommendationsListResponse)
def get_recommendations(
    limit: int = 5,
    domain: Optional[str] = None,
    include_context: bool = True,
    engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Get top N prioritized recommendations.
    
    Query params:
    - limit: Max recommendations to return (default 5, max 20)
    - domain: Filter by domain ('dating', 'career', 'location', 'activities')
    - include_context: Include cross-domain context (default true)
    
    Returns:
        RecommendationsListResponse with top recommendations
    
    Example:
        GET /api/recommendations?limit=3&domain=dating
    """
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
    
    if domain and domain not in ['dating', 'career', 'location', 'activities']:
        raise HTTPException(
            status_code=400, 
            detail="domain must be one of: dating, career, location, activities"
        )
    
    try:
        recommendations = engine.get_top_recommendations(
            limit=limit,
            domain=domain,
            include_cross_domain_context=include_context
        )
        
        return RecommendationsListResponse(
            recommendations=[RecommendationResponse(**rec) for rec in recommendations],
            total_count=len(recommendations),
            generated_at=datetime.utcnow().isoformat() + 'Z'
        )
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{rule_id}/decide", response_model=DecisionResponse)
def decide_on_recommendation(
    rule_id: str,
    request: DecisionRequest,
    engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Record a decision on a recommendation.
    
    Path params:
    - rule_id: Rule ID from the recommendation (e.g., "R-DATE-01")
    
    Body:
    - action: 'accept', 'snooze', or 'dismiss'
    
    Actions:
    - accept: Log to Activities API (close feedback loop)
    - snooze: Hide for 4 hours, then reappear
    - dismiss: Don't show again for this data pattern
    
    Returns:
        DecisionResponse with action result
    
    Example:
        POST /api/recommendations/R-ACT-05/decide
        {"action": "accept"}
    """
    if not rule_id:
        raise HTTPException(status_code=400, detail="rule_id is required")
    
    try:
        # First, fetch the current recommendation to get full context
        all_recommendations = engine.get_top_recommendations(limit=20)
        
        # Find the recommendation matching this rule_id
        recommendation = None
        for rec in all_recommendations:
            if rec['rule_id'] == rule_id:
                recommendation = rec
                break
        
        if not recommendation:
            raise HTTPException(
                status_code=404, 
                detail=f"Recommendation with rule_id={rule_id} not found or already processed"
            )
        
        # Record the decision
        result = engine.record_decision(
            rule_id=rule_id,
            action=request.action,
            recommendation=recommendation
        )
        
        return DecisionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording decision: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/history")
def get_recommendation_history(
    limit: int = 20,
    action_filter: Optional[str] = None,
    engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Get history of recommendation decisions.
    
    Query params:
    - limit: Max history items to return (default 20, max 100)
    - action_filter: Filter by action ('accept', 'snooze', 'dismiss')
    
    Returns:
        List of decisions with timestamps
    
    Example:
        GET /api/recommendations/history?action_filter=accept&limit=10
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    
    if action_filter and action_filter not in ['accept', 'snooze', 'dismiss']:
        raise HTTPException(
            status_code=400,
            detail="action_filter must be one of: accept, snooze, dismiss"
        )
    
    try:
        import sqlite3
        
        conn = sqlite3.connect(engine.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    id, rule_id, domain, one_liner, goal_alignment,
                    action, decided_at, snooze_until
                FROM recommendation_decisions
                {where_clause}
                ORDER BY decided_at DESC
                LIMIT ?
            """
            
            params = []
            where_clause = ""
            
            if action_filter:
                where_clause = "WHERE action = ?"
                params.append(action_filter)
            
            params.append(limit)
            
            cursor.execute(query.format(where_clause=where_clause), params)
            rows = cursor.fetchall()
            
            history = [dict(row) for row in rows]
            
            return {
                "history": history,
                "total_count": len(history),
                "generated_at": datetime.utcnow().isoformat() + 'Z'
            }
        
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error fetching recommendation history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
