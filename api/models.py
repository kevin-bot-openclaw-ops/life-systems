"""
Pydantic models for API requests and responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Job(BaseModel):
    """Job listing summary."""
    id: str
    title: str
    company: str
    location: str
    remote: bool
    score: float = Field(..., ge=0, le=100)
    discovered_at: datetime
    sources: List[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobDetail(Job):
    """Detailed job listing with full description and draft."""
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = "EUR"
    tech_stack: List[str] = []
    url: str
    draft: Optional[Dict[str, Any]] = None


class DraftRequest(BaseModel):
    """Request to generate a cover letter draft."""
    variant: Optional[str] = Field(
        default="general",
        description="Draft variant: fintech, ml_research, platform, or general"
    )


class DraftResponse(BaseModel):
    """Generated cover letter draft."""
    id: str
    job_id: str
    text: str
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DecisionRequest(BaseModel):
    """Decision on a job application."""
    action: str = Field(..., pattern="^(approve|reject|defer)$")
    reason: Optional[str] = None


class SkillDemand(BaseModel):
    """Skill demand data."""
    skill: str
    demand_count: int
    trend: str  # "rising", "stable", "falling"
    avg_salary: Optional[int] = None


class MarketReport(BaseModel):
    """Market intelligence report."""
    generated_at: datetime
    top_skills: List[SkillDemand]
    salary_ranges: Dict[str, Dict[str, int]]  # role_type -> {min, max, avg}
    gap_analysis: List[str]  # Skills Jurek lacks that are in high demand
    weekly_summary: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CareerMetrics(BaseModel):
    """Career pipeline metrics."""
    discovered: int
    applied: int
    responded: int
    interviewing: int
    offered: int


class DashboardState(BaseModel):
    """Synthesized dashboard state."""
    career_score: int = Field(..., ge=0, le=100)
    jobs_today: int
    drafts_pending: int
    market_summary: str
    last_scan: Optional[datetime] = None
    last_scan_ago: str = "never"
    
    # Career pipeline
    career_metrics: Optional[CareerMetrics] = None
    top_opportunities: List[Job] = []
    
    # Market trends
    top_skills: List[SkillDemand] = []
    
    # Alerts
    alerts: List[Dict[str, Any]] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
