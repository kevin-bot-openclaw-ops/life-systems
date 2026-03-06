"""
Dashboard data builder v2 - TASK-039 compliant API response.
Returns DashboardViewModel shape as specified in TASK-039-subtasks.md (039-A).
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from .db import get_db


def get_dashboard_view_model() -> Dict[str, Any]:
    """
    Build DashboardViewModel matching TASK-039 spec (subtask 039-A).
    
    Returns:
    {
      "career": {
        "score": number,
        "totalJobs": number,
        "topJobs": [{id, title, company, location, score, discoveredAt, source}],
        "funnel": {discovered, applied, responded, interviewing, offered},
        "lastScan": "ISO timestamp"|null
      },
      "dating": {
        "score": number,
        "dates": [],
        "weeklyHours": number,
        "upcomingEvents": []
      },
      "system": {
        "version": string,
        "lastHealthCheck": string,
        "status": "ok"|"degraded"|"down"
      },
      "alerts": [],
      "fetchedAt": "ISO timestamp"
    }
    """
    conn = get_db()
    
    # Career section
    career = build_career_view(conn)
    
    # Dating section (stub until Phase 4)
    dating = {
        "score": 0,
        "dates": [],
        "weeklyHours": 0,
        "upcomingEvents": []
    }
    
    # Location section (DASH-M1-2)
    location = build_location_view(conn)
    
    # System section
    system = {
        "version": "0.1.0",
        "lastHealthCheck": datetime.utcnow().isoformat() + "Z",
        "status": "ok"
    }
    
    # Alerts (empty for now)
    alerts = []
    
    conn.close()
    
    return {
        "career": career,
        "dating": dating,
        "location": location,
        "system": system,
        "alerts": alerts,
        "fetchedAt": datetime.utcnow().isoformat() + "Z"
    }


def build_career_view(conn) -> Dict[str, Any]:
    """Build career section from jobs table."""
    # Get total job count
    cursor = conn.execute("SELECT COUNT(*) as total FROM jobs")
    total_jobs = cursor.fetchone()['total']
    
    # Get top 5 jobs
    cursor = conn.execute("""
        SELECT 
            id,
            title,
            company,
            location,
            discovered_at,
            source
        FROM jobs
        ORDER BY discovered_at DESC
        LIMIT 5
    """)
    
    top_jobs = []
    for row in cursor.fetchall():
        top_jobs.append({
            "id": row['id'],
            "title": row['title'] or "Position",
            "company": row['company'] or "Unknown",
            "location": row['location'] or "Remote",
            "score": 85,  # Phase 2 adds real scoring
            "discoveredAt": row['discovered_at'],
            "source": row['source'] or "unknown"
        })
    
    # Funnel (Phase 2 adds real tracking)
    funnel = {
        "discovered": total_jobs,
        "applied": 0,
        "responded": 0,
        "interviewing": 0,
        "offered": 0
    }
    
    # Score (simple calculation)
    career_score = min(100, (total_jobs // 3))  # 300 jobs = 100 score
    
    # Last scan timestamp (get from most recent job)
    cursor = conn.execute("SELECT MAX(discovered_at) as last_scan FROM jobs")
    last_scan_row = cursor.fetchone()
    last_scan = last_scan_row['last_scan'] if last_scan_row else None
    
    return {
        "score": career_score,
        "totalJobs": total_jobs,
        "topJobs": top_jobs,
        "funnel": funnel,
        "lastScan": last_scan
    }


def build_location_view(conn) -> Dict[str, Any]:
    """
    Build location section from cities table.
    DASH-M1-2: Location Section in Advisor View
    
    Returns advisor-format section:
    {
        "goal": "GOAL-3: Location Optionality",
        "one_liner": str,
        "data_table": List[Dict],
        "actions": List[Dict],
        "empty_state": bool,
        "days_until_deadline": int
    }
    """
    from datetime import date
    
    # Calculate days until May 1, 2026 deadline (ADR-006)
    deadline = date(2026, 5, 1)
    today = date.today()
    days_remaining = (deadline - today).days
    
    # Get top 3 cities by composite score
    cursor = conn.execute("""
        SELECT 
            name,
            country,
            is_current,
            dating_pool,
            ai_job_density,
            cost_index,
            lifestyle_score,
            community_score,
            composite_score
        FROM cities
        WHERE composite_score IS NOT NULL
        ORDER BY composite_score DESC
        LIMIT 3
    """)
    
    top_cities = cursor.fetchall()
    
    if not top_cities:
        return {
            "goal": "GOAL-3: Location Optionality",
            "one_liner": f"After city data is loaded, I'll show you the best relocation options. ({days_remaining} days until May 1 decision)",
            "data_table": [],
            "actions": [],
            "empty_state": True,
            "days_until_deadline": days_remaining
        }
    
    # Get current city
    cursor = conn.execute("""
        SELECT 
            name,
            dating_pool,
            ai_job_density
        FROM cities
        WHERE is_current = 1
    """)
    current_row = cursor.fetchone()
    
    # Build one-liner (motivation-first format per ADR-005)
    recommended = top_cities[0]
    
    if current_row:
        # Calculate improvements vs current
        current_dating = current_row['dating_pool'] or 1
        current_jobs = current_row['ai_job_density'] or 1
        rec_dating = recommended['dating_pool'] or 1
        rec_jobs = recommended['ai_job_density'] or 1
        
        dating_multiplier = rec_dating / current_dating
        jobs_multiplier = rec_jobs / current_jobs
        
        improvements = []
        if dating_multiplier >= 2:
            improvements.append(f"{'doubles' if dating_multiplier < 3 else f'{int(dating_multiplier)}x'} your dating pool")
        if jobs_multiplier >= 2:
            improvements.append(f"{int(jobs_multiplier)}x more AI jobs")
        
        if len(improvements) >= 2:
            one_liner = f"{recommended['name']} {improvements[0]} and has {improvements[1]} -- strongest candidate. ({days_remaining} days until decision)"
        elif len(improvements) == 1:
            one_liner = f"{recommended['name']} {improvements[0]} -- strongest candidate. ({days_remaining} days until decision)"
        else:
            one_liner = f"{recommended['name']} scores highest overall ({recommended['composite_score']:.1f}/10) -- strongest candidate. ({days_remaining} days until decision)"
    else:
        one_liner = f"{recommended['name']} scores highest overall ({recommended['composite_score']:.1f}/10) -- strongest candidate. ({days_remaining} days until decision)"
    
    # Build data table (top 3 cities comparison)
    data_table = []
    for city in top_cities:
        data_table.append({
            "city": f"{'★ ' if city['is_current'] else ''}{city['name']}",
            "dating_pool": f"~{city['dating_pool']:,}" if city['dating_pool'] else "N/A",
            "ai_jobs_mo": city['ai_job_density'] if city['ai_job_density'] else "N/A",
            "cost_index": f"{city['cost_index']:.2f}x" if city['cost_index'] else "N/A",
            "lifestyle": f"{city['lifestyle_score']:.1f}/10" if city['lifestyle_score'] else "N/A",
            "score": f"{city['composite_score']:.1f}/10" if city['composite_score'] else "N/A"
        })
    
    # Actions
    actions = [
        {
            "type": "primary",
            "label": "Full Analysis",
            "href": "/api/cities/recommendation"
        }
    ]
    
    return {
        "goal": "GOAL-3: Location Optionality",
        "one_liner": one_liner,
        "data_table": data_table,
        "actions": actions,
        "empty_state": False,
        "days_until_deadline": days_remaining
    }
