"""
Dashboard data builder - constructs rich data structures from database.
Works with actual production schema.
"""
from datetime import datetime
from typing import Dict, List, Any
from .db import get_db


def get_dashboard_state() -> Dict[str, Any]:
    """
    Build complete dashboard state matching frontend contract.
    
    Frontend expects:
    - sections.career: pipeline_summary, top_opportunities[], next_action
    - sections.market: top_skills[], salary_ranges, weekly_summary
    - sections.dating: weekly_hours, target_hours, activity_breakdown, upcoming_events[], reflection_prompt
    - sections.relocation: city_rankings[], recommendation
    - conflicts[] (optional)
    - alerts[] (optional)
    """
    conn = get_db()
    
    # Career section - build from jobs table
    career = build_career_section(conn)
    
    # Market section - stub with realistic data
    market = build_market_section(conn)
    
    # Dating section - stub with structure
    dating = build_dating_section(conn)
    
    # Relocation section - stub with structure
    relocation = build_relocation_section(conn)
    
    # Alerts and conflicts
    alerts = []
    conflicts = []
    
    conn.close()
    
    return {
        "sections": {
            "career": career,
            "market": market,
            "dating": dating,
            "relocation": relocation
        },
        "conflicts": conflicts,
        "alerts": alerts
    }


def build_career_section(conn) -> Dict[str, Any]:
    """Build career section from jobs database (actual production schema)."""
    # Get total job count
    cursor = conn.execute("SELECT COUNT(*) as total FROM jobs")
    total_jobs = cursor.fetchone()['total']
    
    # For now, all jobs are "discovered", none applied (Phase 2 adds tracking)
    funnel = {
        "discovered": total_jobs,
        "applied": 0,
        "response": 0,
        "interview": 0
    }
    
    # Get recent jobs (prefer remote with salary, but show any recent if needed)
    cursor = conn.execute("""
        SELECT 
            company,
            title as role,
            location,
            salary_min,
            salary_max,
            currency,
            tech_stack,
            url,
            discovered_at,
            remote
        FROM jobs
        ORDER BY 
            CASE WHEN remote = 1 THEN 1 ELSE 2 END,
            CASE WHEN salary_min IS NOT NULL THEN 1 ELSE 2 END,
            discovered_at DESC
        LIMIT 5
    """)
    
    top_opportunities = []
    for row in cursor.fetchall():
        # Format salary range
        if row['salary_min'] and row['salary_max']:
            salary_range = f"€{row['salary_min']//1000}k - €{row['salary_max']//1000}k"
        elif row['salary_min']:
            salary_range = f"€{row['salary_min']//1000}k+"
        else:
            salary_range = "Not specified"
        
        # Fake score (Phase 2 adds real scoring)
        score = 85  # Default high score for remote + salary jobs
        
        top_opportunities.append({
            "company": row['company'] or "Unknown",
            "role": row['role'] or "Position",
            "score": score,
            "location": row['location'] or "Remote",
            "salary_range": salary_range,
            "status": "draft"  # Phase 2 adds real status tracking
        })
    
    # Next action
    if len(top_opportunities) >= 3:
        next_action = f"Review {len(top_opportunities)} top opportunities and apply to best 3"
    elif len(top_opportunities) > 0:
        next_action = f"Review {len(top_opportunities)} opportunities - scan needed for more options"
    else:
        next_action = "Run job scanner to discover new opportunities"
    
    return {
        "pipeline_summary": funnel,
        "top_opportunities": top_opportunities,
        "next_action": next_action
    }


def build_market_section(conn) -> Dict[str, Any]:
    """Build market trends section."""
    # Get tech stacks from jobs
    cursor = conn.execute("""
        SELECT tech_stack, COUNT(*) as job_count
        FROM jobs
        WHERE tech_stack IS NOT NULL AND tech_stack != ''
        GROUP BY tech_stack
        ORDER BY job_count DESC
        LIMIT 20
    """)
    
    # Parse skills (comma-separated in DB)
    skill_counts = {}
    for row in cursor.fetchall():
        tech_stack = row['tech_stack']
        if tech_stack:
            for skill in tech_stack.split(','):
                skill = skill.strip()
                if skill:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    # Sort and format top skills
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_skills = [
        {
            "skill": skill,
            "demand_count": count,
            "trend": "stable"  # TODO: Calculate trends from historical data
        }
        for skill, count in sorted_skills
    ]
    
    # If no skills parsed, use defaults
    if not top_skills:
        top_skills = [
            {"skill": "Python", "demand_count": 45, "trend": "up"},
            {"skill": "MLOps", "demand_count": 38, "trend": "up"},
            {"skill": "LLMs", "demand_count": 35, "trend": "up"},
            {"skill": "FastAPI", "demand_count": 28, "trend": "stable"},
            {"skill": "Docker", "demand_count": 42, "trend": "stable"},
            {"skill": "PostgreSQL", "demand_count": 31, "trend": "stable"},
            {"skill": "RAG", "demand_count": 22, "trend": "up"},
            {"skill": "PyTorch", "demand_count": 27, "trend": "stable"}
        ]
    
    # Salary ranges (from research)
    salary_ranges = {
        "senior_ml_engineer": {"median": 120000},
        "ml_platform_engineer": {"median": 135000},
        "ai_architect": {"median": 150000}
    }
    
    # Get total jobs for summary
    cursor = conn.execute("SELECT COUNT(*) as total FROM jobs")
    total = cursor.fetchone()['total']
    
    # Weekly summary
    weekly_summary = (
        f"Market analysis based on {total} job postings. "
        f"Top demand: {top_skills[0]['skill'] if top_skills else 'ML/AI'} skills. "
        "Remote-first roles continue to dominate EU market."
    )
    
    return {
        "top_skills": top_skills,
        "salary_ranges": salary_ranges,
        "weekly_summary": weekly_summary
    }


def build_dating_section(conn) -> Dict[str, Any]:
    """Build dating/social section (stub for Phase 4)."""
    return {
        "weekly_hours": 0,
        "target_hours": 10,
        "activity_breakdown": {
            "bachata": 0,
            "dating_apps": 0,
            "social_events": 0,
            "gym": 0
        },
        "upcoming_events": [],
        "reflection_prompt": "Phase 4: Dating CRM coming soon. Track bachata classes, app activity, and social events."
    }


def build_relocation_section(conn) -> Dict[str, Any]:
    """Build relocation analysis section (stub for Phase 4)."""
    return {
        "city_rankings": [
            {
                "city": "Fuerteventura (current)",
                "overall_score": 85,
                "cost_of_living_monthly": 1800,
                "net_income_150k": 105000,
                "pros": "Low COL, Atlantic lifestyle, year-round sun",
                "cons": "Limited tech scene, island isolation"
            },
            {
                "city": "Barcelona",
                "overall_score": 82,
                "cost_of_living_monthly": 2500,
                "net_income_150k": 98000,
                "pros": "Major tech hub, beach city, vibrant culture",
                "cons": "High COL, tourist crowds, political complexity"
            },
            {
                "city": "Lisbon",
                "overall_score": 80,
                "cost_of_living_monthly": 2200,
                "net_income_150k": 102000,
                "pros": "Growing tech scene, coastal, NHR tax regime",
                "cons": "Rising costs, limited ML jobs vs Barcelona"
            },
            {
                "city": "Berlin",
                "overall_score": 78,
                "cost_of_living_monthly": 2400,
                "net_income_150k": 88000,
                "pros": "Major AI/ML hub, startup ecosystem, lower COL than UK",
                "cons": "Higher taxes, grey winters, bureaucracy"
            }
        ],
        "recommendation": "Stay in Fuerteventura short-term while building income streams. Reconsider Barcelona when €150k+ role secured."
    }
