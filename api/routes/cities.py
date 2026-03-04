"""
Location Optimizer Routes (EPIC-003)
RELOC-MVP-2: City comparison and ranking endpoints
"""
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/cities", tags=["cities"])

# Database path
DB_PATH = "/var/lib/life-systems/life.db"


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Models
class CityResponse(BaseModel):
    """City data response model."""
    id: int
    name: str
    country: str
    is_current: int = Field(0, description="1 if this is the current location")
    dating_pool: Optional[int] = Field(None, description="Approximate active daters")
    ai_job_density: Optional[int] = Field(None, description="Remote AI/ML jobs per month")
    cost_index: Optional[float] = Field(None, description="Cost relative to baseline (1.0)")
    lifestyle_score: Optional[float] = Field(None, description="Lifestyle quality (1-10)")
    community_score: Optional[float] = Field(None, description="Tech community strength (1-10)")
    composite_score: Optional[float] = Field(None, description="Overall weighted score")
    data_source: Optional[str] = Field(None, description="JSON of data sources per dimension")
    last_updated: Optional[str] = Field(None, description="Timestamp of last data update")
    
    class Config:
        from_attributes = True


class ComparisonResponse(BaseModel):
    """Comparison table response."""
    current_city: Optional[CityResponse] = None
    cities: List[CityResponse]
    sorted_by: str = "composite_score"
    dimensions: List[str] = [
        "dating_pool",
        "ai_job_density",
        "cost_index",
        "lifestyle_score",
        "community_score",
        "composite_score"
    ]


@router.get("", response_model=List[CityResponse])
async def list_cities(
    sort_by: str = Query("composite_score", description="Column to sort by"),
    order: str = Query("desc", description="Sort order: 'asc' or 'desc'")
):
    """
    Get all cities with all dimensions.
    
    RELOC-MVP-2 AC-1: Returns all cities with all dimensions
    RELOC-MVP-2 AC-3: Sortable by any dimension
    """
    # Validate sort column
    valid_columns = [
        "name", "country", "dating_pool", "ai_job_density", 
        "cost_index", "lifestyle_score", "community_score", "composite_score"
    ]
    if sort_by not in valid_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by column. Must be one of: {', '.join(valid_columns)}"
        )
    
    # Validate order
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Order must be 'asc' or 'desc'")
    
    # Build query
    # Handle NULL values by treating them as 0 for sorting
    sort_expression = f"COALESCE({sort_by}, 0)"
    query = f"""
        SELECT 
            id, name, country, is_current,
            dating_pool, ai_job_density, cost_index,
            lifestyle_score, community_score, composite_score,
            data_source, last_updated
        FROM cities
        ORDER BY {sort_expression} {order.upper()}
    """
    
    conn = get_db()
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return [CityResponse(**dict(row)) for row in rows]


@router.get("/compare", response_model=ComparisonResponse)
async def compare_cities(
    sort_by: str = Query("composite_score", description="Column to sort by"),
    order: str = Query("desc", description="Sort order: 'asc' or 'desc'")
):
    """
    Get side-by-side comparison table.
    
    RELOC-MVP-2 AC-2: Returns side-by-side comparison table
    RELOC-MVP-2 AC-4: Fuerteventura highlighted as "current" baseline
    """
    conn = get_db()
    
    # Get current city
    current_row = conn.execute(
        """
        SELECT 
            id, name, country, is_current,
            dating_pool, ai_job_density, cost_index,
            lifestyle_score, community_score, composite_score,
            data_source, last_updated
        FROM cities 
        WHERE is_current = 1
        """
    ).fetchone()
    
    current_city = CityResponse(**dict(current_row)) if current_row else None
    
    # Get all cities (sorted)
    valid_columns = [
        "name", "country", "dating_pool", "ai_job_density", 
        "cost_index", "lifestyle_score", "community_score", "composite_score"
    ]
    if sort_by not in valid_columns:
        sort_by = "composite_score"
    
    if order not in ["asc", "desc"]:
        order = "desc"
    
    sort_expression = f"COALESCE({sort_by}, 0)"
    query = f"""
        SELECT 
            id, name, country, is_current,
            dating_pool, ai_job_density, cost_index,
            lifestyle_score, community_score, composite_score,
            data_source, last_updated
        FROM cities
        ORDER BY {sort_expression} {order.upper()}
    """
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    cities = [CityResponse(**dict(row)) for row in rows]
    
    return ComparisonResponse(
        current_city=current_city,
        cities=cities,
        sorted_by=sort_by
    )


@router.get("/{city_id}", response_model=CityResponse)
async def get_city(city_id: int):
    """Get a specific city by ID."""
    conn = get_db()
    row = conn.execute(
        """
        SELECT 
            id, name, country, is_current,
            dating_pool, ai_job_density, cost_index,
            lifestyle_score, community_score, composite_score,
            data_source, last_updated
        FROM cities 
        WHERE id = ?
        """,
        (city_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="City not found")
    
    return CityResponse(**dict(row))
