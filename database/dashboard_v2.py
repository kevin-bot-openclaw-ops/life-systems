"""
Dashboard data builder v2 - TASK-039 compliant API response.
Returns DashboardViewModel shape as specified in TASK-039-subtasks.md (039-A).
"""
from datetime import datetime
from typing import Dict, List, Any
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
            sources
        FROM jobs
        ORDER BY 
            CASE WHEN remote = 1 THEN 1 ELSE 2 END,
            CASE WHEN salary_min IS NOT NULL THEN 1 ELSE 2 END,
            discovered_at DESC
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
            "source": row['sources'] or "unknown"
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
