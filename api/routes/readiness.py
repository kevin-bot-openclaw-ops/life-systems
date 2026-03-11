"""
API routes for GOAL1-02 Readiness Score
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
from typing import Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from goals.readiness_score import ReadinessScoreEngine

router = APIRouter(prefix="/api/readiness", tags=["readiness"])


@router.get("/score")
async def get_readiness_score(date: Optional[str] = None):
    """
    Get readiness score for a specific date.
    
    Args:
        date: ISO date string (YYYY-MM-DD), defaults to today
        
    Returns:
        Readiness score with breakdown and recommendations
    """
    try:
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date=date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_readiness_trend(days: int = 30):
    """
    Get readiness score trend for last N days.
    
    Args:
        days: Number of days to look back (default 30, max 90)
        
    Returns:
        List of daily scores
    """
    if days > 90:
        raise HTTPException(status_code=400, detail="Maximum 90 days allowed")
    
    try:
        engine = ReadinessScoreEngine()
        
        # Compute scores for each day
        today = datetime.now(timezone.utc).date()
        scores = []
        
        for day_offset in range(days):
            score_date = today - timedelta(days=day_offset)
            try:
                day_score = engine.compute_score(date=score_date.isoformat())
                scores.append({
                    'date': score_date.isoformat(),
                    'score': day_score['score'],
                    'status': day_score['status'],
                    'color': day_score['color']
                })
            except Exception as e:
                # Skip days with errors (likely no data)
                continue
        
        # Reverse to chronological order
        scores.reverse()
        
        return {
            'days': days,
            'count': len(scores),
            'scores': scores
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_readiness_dashboard():
    """
    Get complete readiness dashboard data.
    
    Returns:
        Dict with current score, 7-day trend, and recommendations
    """
    try:
        engine = ReadinessScoreEngine()
        
        # Current score
        current = engine.compute_score()
        
        # 7-day trend
        today = datetime.now(timezone.utc).date()
        trend = []
        
        for day_offset in range(7):
            score_date = today - timedelta(days=day_offset)
            try:
                day_score = engine.compute_score(date=score_date.isoformat())
                trend.append({
                    'date': score_date.isoformat(),
                    'score': day_score['score']
                })
            except:
                continue
        
        trend.reverse()
        
        return {
            'current': current,
            'trend_7d': trend,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
