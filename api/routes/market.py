"""
Market intelligence API routes.
"""
from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(tags=["market"])

@router.get("/market")
async def get_market_report():
    """
    Get latest market report: skill demand, salary trends, gap analysis.
    """
    # TODO: Query latest from market_reports table
    return {
        "period": {
            "start": "2026-02-18",
            "end": "2026-02-25"
        },
        "top_skills": [
            {"skill": "Python", "demand": 145, "trend": "stable"},
            {"skill": "RAG", "demand": 67, "trend": "growing"},
            {"skill": "LLM Integration", "demand": 58, "trend": "growing"},
            {"skill": "FastAPI", "demand": 34, "trend": "stable"},
            {"skill": "Kubernetes", "demand": 89, "trend": "stable"}
        ],
        "salary_trends": {
            "AI Engineer": {"min": 120000, "median": 150000, "max": 200000, "currency": "EUR"},
            "ML Platform Engineer": {"min": 130000, "median": 160000, "max": 220000, "currency": "EUR"}
        },
        "gap_analysis": {
            "strengths": ["Python", "System Design", "Banking Domain"],
            "gaps": ["LLM Fine-tuning", "MLOps at scale", "Rust"],
            "bridge_skills": ["Java + AI", "Banking + ML"]
        }
    }
