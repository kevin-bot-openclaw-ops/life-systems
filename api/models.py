"""
Life Systems v5 Data Models
Pydantic schemas matching database tables from EPIC-001 through EPIC-004.
"""
from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator


# EPIC-001: Dating Module Models

class DateCreate(BaseModel):
    """Request model for creating a date entry."""
    who: str = Field(..., min_length=1, description="Person's name or identifier")
    source: Literal['app', 'event', 'social'] = Field(..., description="How you met")
    quality: int = Field(..., ge=1, le=10, description="Date quality rating (1-10)")
    went_well: Optional[str] = Field(None, description="What went well")
    improve: Optional[str] = Field(None, description="What to improve next time")
    date_of: date = Field(..., description="Date of the date (YYYY-MM-DD)")


class DateResponse(BaseModel):
    """Response model for a date entry."""
    id: int
    who: str
    source: Literal['app', 'event', 'social']
    quality: int
    went_well: Optional[str]
    improve: Optional[str]
    date_of: date
    created_at: datetime
    archived: int = 0
    
    class Config:
        from_attributes = True


class DateUpdate(BaseModel):
    """Request model for updating a date entry."""
    who: Optional[str] = None
    source: Optional[Literal['app', 'event', 'social']] = None
    quality: Optional[int] = Field(None, ge=1, le=10)
    went_well: Optional[str] = None
    improve: Optional[str] = None
    date_of: Optional[date] = None
    archived: Optional[int] = Field(None, ge=0, le=1)


# EPIC-002: Career Advisor Models

class JobCreate(BaseModel):
    """Request model for creating a job entry."""
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    description: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    status: Literal['new', 'reviewed', 'approved', 'skipped', 'saved', 'applied', 
                    'interviewing', 'offered', 'rejected', 'archived'] = 'new'


class JobResponse(BaseModel):
    """Response model for a job listing."""
    id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    salary_range: Optional[str]
    description: Optional[str]
    source: str
    source_url: Optional[str]
    discovered_at: datetime
    status: str
    archived: int
    
    class Config:
        from_attributes = True


class JobScoreCreate(BaseModel):
    """Request model for scoring a job."""
    job_id: int
    role_match: Optional[float] = Field(None, ge=0, le=10)
    remote_friendly: Optional[float] = Field(None, ge=0, le=10)
    salary_fit: Optional[float] = Field(None, ge=0, le=10)
    tech_overlap: Optional[float] = Field(None, ge=0, le=10)
    company_quality: Optional[float] = Field(None, ge=0, le=10)
    composite: Optional[float] = None


class DecisionCreate(BaseModel):
    """Request model for making a job decision."""
    job_id: int
    action: Literal['approve', 'skip', 'save']
    reasoning: Optional[str] = None


# EPIC-003: Location Optimizer Models

class CityCreate(BaseModel):
    """Request model for adding a city."""
    name: str
    country: str
    is_current: int = 0
    dating_pool: Optional[int] = None
    ai_job_density: Optional[int] = None
    cost_index: Optional[float] = None
    lifestyle_score: Optional[float] = Field(None, ge=1, le=10)
    community_score: Optional[float] = Field(None, ge=1, le=10)
    composite_score: Optional[float] = None
    data_source: Optional[str] = None  # JSON


class CityResponse(BaseModel):
    """Response model for a city."""
    id: int
    name: str
    country: str
    is_current: int
    dating_pool: Optional[int]
    ai_job_density: Optional[int]
    cost_index: Optional[float]
    lifestyle_score: Optional[float]
    community_score: Optional[float]
    composite_score: Optional[float]
    data_source: Optional[str]
    last_updated: datetime
    
    class Config:
        from_attributes = True


class CityNoteCreate(BaseModel):
    """Request model for adding a city note."""
    city_id: int
    dimension: str
    note: str
    source: Optional[str] = None


# EPIC-004: Intelligence Layer Models

class AnalysisCreate(BaseModel):
    """Request model for creating an analysis."""
    type: Literal['rules', 'weekly_ai', 'life_move']
    domain: Optional[str] = None
    one_liner: str
    data_table: Optional[str] = None  # JSON
    actions: Optional[str] = None  # JSON
    source_rule_ids: Optional[str] = None  # JSON
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None


class AnalysisResponse(BaseModel):
    """Response model for an analysis."""
    id: int
    type: str
    domain: Optional[str]
    one_liner: str
    data_table: Optional[str]
    actions: Optional[str]
    source_rule_ids: Optional[str]
    token_count: Optional[int]
    cost_usd: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RuleCreate(BaseModel):
    """Request model for creating a rule."""
    id: str  # e.g., R-DATE-01
    name: str
    domain: str
    trigger_condition: str
    min_data_points: int = 0
    enabled: int = 1


class RecommendationResponse(BaseModel):
    """Response model for a recommendation."""
    id: int
    analysis_id: Optional[int]
    rule_id: Optional[str]
    one_liner: str
    data_table: Optional[str]
    goal_alignment: Optional[str]
    priority: Optional[int]
    time_sensitive: int
    acted_on: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Dashboard View Models

class DashboardCareer(BaseModel):
    """Career section for dashboard."""
    score: int = 0
    totalJobs: int = 0
    topJobs: List[dict] = []
    funnel: dict = {
        "discovered": 0,
        "applied": 0,
        "responded": 0,
        "interviewing": 0,
        "offered": 0
    }
    lastScan: Optional[str] = None


class DashboardDating(BaseModel):
    """Dating section for dashboard."""
    score: int = 0
    dates: List[dict] = []
    weeklyHours: int = 0
    upcomingEvents: List[dict] = []


class DashboardSystem(BaseModel):
    """System section for dashboard."""
    version: str = "0.1.0"
    lastHealthCheck: str
    status: Literal["ok", "degraded", "down"] = "ok"


class DashboardViewModel(BaseModel):
    """Complete dashboard view model (TASK-039 compliant)."""
    career: DashboardCareer
    dating: DashboardDating
    system: DashboardSystem
    alerts: List[dict] = []
    fetchedAt: str
