"""
Insights API routes (patterns, accountability, optimization).
"""
from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(tags=["insights"])

@router.get("/insights")
async def get_insights():
    """
    Get insights: patterns, accountability, optimization recommendations.
    """
    # TODO: Generate from dates + fitness + jobs data
    return {
        "patterns": [
            "You rate dates higher at activity venues vs. bars (4.2 vs 3.1 avg)",
            "Wednesday has highest match response rate (67%)",
            "Your best dates happen after gym days (+40% rating)"
        ],
        "accountability": [
            "No bachata in 2 weeks - last class: Feb 10",
            "Zero dates logged this month",
            "Gym streak at 8 days - longest in 3 months!"
        ],
        "optimization": [
            "Schedule dates on Wednesdays for better response",
            "Activity-based dates (bachata, surfing) outperform dinner dates",
            "Gym streak > 5 days correlates with +40% higher date ratings"
        ],
        "correlations": {
            "gym_streak_vs_date_rating": 0.68,
            "bachata_frequency_vs_matches": 0.54,
            "applications_sent_vs_gym_sessions": 0.42
        }
    }
