"""
Location Optimizer Routes (EPIC-003)
RELOC-MVP-2: City comparison and ranking endpoints
RELOC-M1-1: Composite scoring + recommendation generator
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/cities", tags=["cities"])

# Database path
DB_PATH = "/var/lib/life-systems/life.db"
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "location_scoring.json"


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_scoring_config() -> Dict[str, Any]:
    """Load scoring configuration from JSON file."""
    if not CONFIG_PATH.exists():
        # Default config if file doesn't exist
        return {
            "weights": {
                "dating_pool": 0.20,
                "ai_job_density": 0.20,
                "cost_index": 0.20,
                "lifestyle_score": 0.20,
                "community_score": 0.20
            },
            "normalization": {
                "dating_pool": {"min": 0, "max": 5000, "invert": False},
                "ai_job_density": {"min": 0, "max": 200, "invert": False},
                "cost_index": {"min": 0.5, "max": 2.0, "invert": True},
                "lifestyle_score": {"min": 1, "max": 10, "invert": False},
                "community_score": {"min": 1, "max": 10, "invert": False}
            }
        }
    
    with open(CONFIG_PATH) as f:
        return json.load(f)


def normalize_value(value: Optional[float], dimension: str, config: Dict[str, Any]) -> float:
    """
    Normalize a dimension value to 0-1 scale.
    
    Args:
        value: Raw value
        dimension: Dimension name
        config: Scoring configuration
    
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    norm_config = config["normalization"].get(dimension, {})
    min_val = norm_config.get("min", 0)
    max_val = norm_config.get("max", 10)
    invert = norm_config.get("invert", False)
    
    # Clamp value to range
    clamped = max(min_val, min(value, max_val))
    
    # Normalize to 0-1
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (clamped - min_val) / (max_val - min_val)
    
    # Invert if lower is better (e.g., cost)
    if invert:
        normalized = 1.0 - normalized
    
    return normalized


def calculate_composite_score(city: Dict[str, Any], config: Dict[str, Any]) -> float:
    """
    Calculate composite score for a city using weighted average of normalized dimensions.
    
    Args:
        city: City data dictionary
        config: Scoring configuration
    
    Returns:
        Composite score (0-10 scale)
    """
    weights = config["weights"]
    dimensions = ["dating_pool", "ai_job_density", "cost_index", "lifestyle_score", "community_score"]
    
    total_score = 0.0
    total_weight = 0.0
    
    for dim in dimensions:
        value = city.get(dim)
        if value is not None:
            normalized = normalize_value(value, dim, config)
            weight = weights.get(dim, 0.2)
            total_score += normalized * weight
            total_weight += weight
    
    # Return on 0-10 scale
    if total_weight == 0:
        return 0.0
    
    return round((total_score / total_weight) * 10, 2)


def update_all_composite_scores():
    """Recalculate and update composite scores for all cities."""
    config = load_scoring_config()
    conn = get_db()
    
    cities = conn.execute("SELECT * FROM cities").fetchall()
    
    for city_row in cities:
        city = dict(city_row)
        score = calculate_composite_score(city, config)
        
        conn.execute(
            "UPDATE cities SET composite_score = ? WHERE id = ?",
            (score, city["id"])
        )
    
    conn.commit()
    conn.close()


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


class DimensionComparison(BaseModel):
    """Comparison of a single dimension between current and recommended city."""
    dimension: str
    current_value: Optional[float]
    recommended_value: Optional[float]
    change_pct: Optional[float] = Field(None, description="Percentage change from current")
    change_abs: Optional[float] = Field(None, description="Absolute change from current")


class RecommendationResponse(BaseModel):
    """City recommendation with motivation-first format."""
    one_liner: str = Field(..., description="Motivation-first summary")
    recommended_city: CityResponse
    current_city: Optional[CityResponse] = None
    top_3: List[CityResponse]
    trade_offs: List[str] = Field(default_factory=list, description="Key trade-offs to consider")
    dimension_comparisons: List[DimensionComparison] = Field(default_factory=list)


@router.get("/recommendation", response_model=RecommendationResponse)
async def get_recommendation():
    """
    Get city recommendation with motivation-first one-liner format.
    
    RELOC-M1-1 AC-1: Composite score calculated with configurable weights
    RELOC-M1-1 AC-2: Returns one-liner + comparison table + top 3 ranked
    RELOC-M1-1 AC-3: Includes trade-offs
    
    Returns:
        Recommendation with one-liner, top city, top 3, and trade-offs
    """
    # Recalculate all composite scores first
    update_all_composite_scores()
    
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
    
    # Get top 3 cities by composite score
    top_rows = conn.execute(
        """
        SELECT 
            id, name, country, is_current,
            dating_pool, ai_job_density, cost_index,
            lifestyle_score, community_score, composite_score,
            data_source, last_updated
        FROM cities
        WHERE composite_score IS NOT NULL
        ORDER BY composite_score DESC
        LIMIT 3
        """
    ).fetchall()
    
    conn.close()
    
    if not top_rows:
        raise HTTPException(status_code=404, detail="No cities found in database")
    
    top_3 = [CityResponse(**dict(row)) for row in top_rows]
    recommended = top_3[0]
    
    # Generate dimension comparisons
    dimension_comparisons = []
    trade_offs = []
    
    if current_city:
        dimensions = [
            ("dating_pool", "dating pool"),
            ("ai_job_density", "AI job density"),
            ("cost_index", "cost of living"),
            ("lifestyle_score", "lifestyle"),
            ("community_score", "community")
        ]
        
        for dim_key, dim_name in dimensions:
            current_val = getattr(current_city, dim_key)
            rec_val = getattr(recommended, dim_key)
            
            if current_val is not None and rec_val is not None:
                # Calculate change
                if dim_key == "cost_index":
                    # For cost, lower is better
                    change_abs = rec_val - current_val
                    change_pct = (change_abs / current_val) * 100 if current_val > 0 else 0
                    
                    if change_abs > 0.1:
                        trade_offs.append(
                            f"Cost of living is {change_abs:.0%} higher ({rec_val:.1f}x vs {current_val:.1f}x baseline)"
                        )
                    elif change_abs < -0.1:
                        trade_offs.append(
                            f"Cost of living is {-change_abs:.0%} lower ({rec_val:.1f}x vs {current_val:.1f}x baseline)"
                        )
                else:
                    change_abs = rec_val - current_val
                    change_pct = (change_abs / current_val) * 100 if current_val > 0 else 0
                
                dimension_comparisons.append(
                    DimensionComparison(
                        dimension=dim_name,
                        current_value=current_val,
                        recommended_value=rec_val,
                        change_pct=round(change_pct, 1),
                        change_abs=round(change_abs, 1)
                    )
                )
    
    # Generate one-liner (motivation-first format)
    one_liner = _generate_one_liner(recommended, current_city, dimension_comparisons)
    
    # Add additional trade-offs
    if current_city and recommended:
        if recommended.lifestyle_score and current_city.lifestyle_score:
            score_diff = recommended.lifestyle_score - current_city.lifestyle_score
            if abs(score_diff) >= 1:
                trade_offs.append(
                    f"Lifestyle score: {recommended.lifestyle_score:.1f}/10 vs {current_city.lifestyle_score:.1f}/10"
                )
        
        if recommended.community_score and current_city.community_score:
            score_diff = recommended.community_score - current_city.community_score
            if abs(score_diff) >= 1:
                trade_offs.append(
                    f"Community score: {recommended.community_score:.1f}/10 vs {current_city.community_score:.1f}/10"
                )
    
    return RecommendationResponse(
        one_liner=one_liner,
        recommended_city=recommended,
        current_city=current_city,
        top_3=top_3,
        trade_offs=trade_offs,
        dimension_comparisons=dimension_comparisons
    )


def _generate_one_liner(
    recommended: CityResponse,
    current: Optional[CityResponse],
    comparisons: List[DimensionComparison]
) -> str:
    """
    Generate motivation-first one-liner recommendation.
    
    Format: "{City} {multiplier} your {dimension} and has {value} {dimension} -- strongest candidate."
    
    Args:
        recommended: Top recommended city
        current: Current city (baseline)
        comparisons: Dimension comparisons
    
    Returns:
        One-liner string
    """
    if not current:
        return f"{recommended.name} scores highest overall ({recommended.composite_score:.1f}/10) -- strongest candidate for relocation."
    
    # Find most significant improvements
    improvements = []
    
    for comp in comparisons:
        if comp.change_pct and comp.change_pct > 0:
            if comp.dimension == "dating pool" and comp.change_pct >= 50:
                multiplier = comp.recommended_value / comp.current_value if comp.current_value > 0 else 0
                improvements.append((comp.change_pct, f"{'doubles' if multiplier >= 2 else 'increases'} your dating pool"))
            elif comp.dimension == "AI job density" and comp.change_pct >= 50:
                multiplier = comp.recommended_value / comp.current_value if comp.current_value > 0 else 0
                improvements.append((comp.change_pct, f"has {int(multiplier)}x more AI jobs"))
            elif comp.dimension in ["lifestyle", "community"] and comp.change_abs >= 2:
                improvements.append((comp.change_pct, f"{comp.dimension} {comp.recommended_value:.0f}/10"))
    
    # Sort by significance
    improvements.sort(reverse=True)
    
    if len(improvements) >= 2:
        return f"{recommended.name} {improvements[0][1]} and {improvements[1][1]} -- strongest candidate."
    elif len(improvements) == 1:
        return f"{recommended.name} {improvements[0][1]} -- strongest candidate."
    else:
        return f"{recommended.name} scores highest overall ({recommended.composite_score:.1f}/10 vs {current.composite_score:.1f}/10) -- strongest candidate."


@router.post("/recalculate")
async def recalculate_scores():
    """
    Manually trigger composite score recalculation for all cities.
    
    Returns:
        Status and count of updated cities
    """
    update_all_composite_scores()
    
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
    conn.close()
    
    return {
        "status": "success",
        "message": f"Recalculated composite scores for {count} cities",
        "config_path": str(CONFIG_PATH)
    }
