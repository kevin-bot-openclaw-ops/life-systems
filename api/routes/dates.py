"""
Dating Module Routes (EPIC-001)
DATE-MVP-1: CRUD endpoints for date logging
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from ..models import DateCreate, DateResponse, DateUpdate

router = APIRouter(prefix="/api/dates", tags=["dates"])

# Database path
DB_PATH = "/var/lib/life-systems/life.db"


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.post("", response_model=DateResponse, status_code=201)
async def create_date(date: DateCreate):
    """
    Log a new date.
    
    DATE-MVP-1 AC-1: Accepts JSON, validates, stores, returns 201
    """
    conn = get_db()
    cursor = conn.execute(
        """
        INSERT INTO dates (who, source, quality, went_well, improve, date_of)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (date.who, date.source, date.quality, date.went_well, date.improve, date.date_of)
    )
    date_id = cursor.lastrowid
    conn.commit()
    
    # Fetch the created record
    row = conn.execute("SELECT * FROM dates WHERE id = ?", (date_id,)).fetchone()
    conn.close()
    
    return DateResponse(**dict(row))


@router.get("", response_model=List[DateResponse])
async def list_dates(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    who: Optional[str] = None
):
    """
    List dates with optional filtering.
    
    DATE-MVP-1 AC-2: Returns list with pagination
    DATE-MVP-1 AC-3: Filters by person (who parameter)
    """
    conn = get_db()
    
    if who:
        query = "SELECT * FROM dates WHERE who = ? AND archived = 0 ORDER BY date_of DESC LIMIT ? OFFSET ?"
        params = (who, limit, offset)
    else:
        query = "SELECT * FROM dates WHERE archived = 0 ORDER BY date_of DESC LIMIT ? OFFSET ?"
        params = (limit, offset)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [DateResponse(**dict(row)) for row in rows]


@router.get("/stats")
async def get_date_stats():
    """
    Get date statistics by source.
    
    DATE-MVP-1 AC-4: Returns source breakdown (count + avg quality per source)
    """
    conn = get_db()
    cursor = conn.execute("""
        SELECT 
            source,
            COUNT(*) as count,
            AVG(quality) as avg_quality,
            MAX(quality) as max_quality,
            MIN(quality) as min_quality
        FROM dates
        WHERE archived = 0
        GROUP BY source
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    stats = {}
    for row in rows:
        stats[row['source']] = {
            "count": row['count'],
            "avg_quality": round(row['avg_quality'], 1) if row['avg_quality'] else 0,
            "max_quality": row['max_quality'],
            "min_quality": row['min_quality']
        }
    
    return {
        "by_source": stats,
        "total_dates": sum(s['count'] for s in stats.values())
    }


@router.get("/trends")
async def get_date_trends():
    """
    Get quality trends over time.
    
    DATE-MVP-1 AC-5: Returns 4-week rolling average quality
    """
    conn = get_db()
    
    # Get dates from last 4 weeks, grouped by week
    four_weeks_ago = (datetime.now() - timedelta(days=28)).date()
    
    cursor = conn.execute("""
        SELECT 
            strftime('%Y-%W', date_of) as week,
            AVG(quality) as avg_quality,
            COUNT(*) as count
        FROM dates
        WHERE archived = 0 AND date_of >= ?
        GROUP BY week
        ORDER BY week
    """, (four_weeks_ago,))
    
    rows = cursor.fetchall()
    
    # Calculate overall trend
    if len(rows) >= 2:
        first_week_avg = rows[0]['avg_quality']
        last_week_avg = rows[-1]['avg_quality']
        trend = "up" if last_week_avg > first_week_avg else "down" if last_week_avg < first_week_avg else "stable"
    else:
        trend = "insufficient_data"
    
    conn.close()
    
    weekly_data = [
        {
            "week": row['week'],
            "avg_quality": round(row['avg_quality'], 1),
            "count": row['count']
        }
        for row in rows
    ]
    
    return {
        "weeks": weekly_data,
        "trend": trend,
        "four_week_avg": round(sum(w['avg_quality'] for w in weekly_data) / len(weekly_data), 1) if weekly_data else 0
    }


@router.get("/{date_id}", response_model=DateResponse)
async def get_date(date_id: int):
    """Get a specific date by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM dates WHERE id = ?", (date_id,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Date not found")
    
    return DateResponse(**dict(row))


@router.patch("/{date_id}", response_model=DateResponse)
async def update_date(date_id: int, update: DateUpdate):
    """Update a date entry."""
    conn = get_db()
    
    # Check if exists
    existing = conn.execute("SELECT id FROM dates WHERE id = ?", (date_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Date not found")
    
    # Build dynamic UPDATE query
    update_fields = []
    params = []
    
    if update.who is not None:
        update_fields.append("who = ?")
        params.append(update.who)
    if update.source is not None:
        update_fields.append("source = ?")
        params.append(update.source)
    if update.quality is not None:
        update_fields.append("quality = ?")
        params.append(update.quality)
    if update.went_well is not None:
        update_fields.append("went_well = ?")
        params.append(update.went_well)
    if update.improve is not None:
        update_fields.append("improve = ?")
        params.append(update.improve)
    if update.date_of is not None:
        update_fields.append("date_of = ?")
        params.append(update.date_of)
    if update.archived is not None:
        update_fields.append("archived = ?")
        params.append(update.archived)
    
    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(date_id)
    query = f"UPDATE dates SET {', '.join(update_fields)} WHERE id = ?"
    
    conn.execute(query, params)
    conn.commit()
    
    # Return updated record
    row = conn.execute("SELECT * FROM dates WHERE id = ?", (date_id,)).fetchone()
    conn.close()
    
    return DateResponse(**dict(row))


@router.delete("/{date_id}", status_code=204)
async def delete_date(date_id: int):
    """Soft delete a date (set archived = 1)."""
    conn = get_db()
    
    result = conn.execute("UPDATE dates SET archived = 1 WHERE id = ?", (date_id,))
    conn.commit()
    conn.close()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Date not found")
    
    return None
