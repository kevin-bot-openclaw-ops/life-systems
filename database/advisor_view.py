"""
Advisor View Builder - ACT-M1-1
Builds Health & Attractiveness Optimizer + Dating Intelligence sections.
Follows ADR-005 (motivation-first: one-liner + data table + actions).
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from .db import get_db


def build_health_optimizer_view(conn) -> Dict[str, Any]:
    """
    Build Health & Attractiveness Optimizer section.
    Returns: T-score, morning routine, exercise streak, stress trend, missing items.
    """
    today = datetime.now().date().isoformat()
    
    # 1. T-optimization score (use live readiness API)
    try:
        from goals.readiness_score import ReadinessScoreEngine
        engine = ReadinessScoreEngine()
        readiness = engine.compute_score(date=today)
        # Use readiness score directly (it's more accurate than local DB)
        breakdown_dict = {}
        for item in readiness['breakdown']:
            comp = item['component'].lower().replace(' ', '-').replace('resistance-training', 'exercise').replace('sun-exposure', 'sun').replace('cold/heat-stress', 'cold').replace('sleep-quality', 'sleep').replace('low-cortisol', 'coffee_penalty')
            breakdown_dict[comp] = item['earned']
        
        t_score_data = {
            'score': int(readiness['score'] * 10 / 7.0),  # Scale 0-7.0 to 0-10
            'max_score': 10,
            'breakdown': breakdown_dict,
            'missing_items': [item['component'].lower().split()[0] for item in readiness['breakdown'] if item['status'] == 'missing'],
            'sparkline': calculate_t_score_sparkline(conn)
        }
    except Exception as e:
        # Fallback to local DB if readiness API fails
        t_score_data = calculate_t_optimization_score(conn, today)
    
    # 2. Morning routine adherence (last 7 days)
    morning_routine = calculate_morning_routine_adherence(conn)
    
    # 3. Exercise streak
    exercise_streak = calculate_exercise_streak(conn)
    
    # 4. Stress trend (last 14 days)
    stress_trend = calculate_stress_trend(conn)
    
    # 5. One-liner summary (motivation-first per ADR-005)
    one_liner = generate_health_one_liner(
        t_score_data, morning_routine, exercise_streak, stress_trend
    )
    
    return {
        "section": "health_optimizer",
        "goal_ref": "Health (all goals)",
        "one_liner": one_liner,
        "t_score": t_score_data,
        "morning_routine": morning_routine,
        "exercise_streak": exercise_streak,
        "stress_trend": stress_trend,
        "actions": generate_health_actions(t_score_data, morning_routine)
    }


def calculate_t_optimization_score(conn, today: str) -> Dict[str, Any]:
    """
    Calculate T-optimization score for today (0-10).
    Components: sun+2, exercise+2, cold+2, sauna+1, sleep(7h)+2, coffee-1
    """
    cursor = conn.execute("""
        SELECT 
            SUM(CASE WHEN type = 'sun-exposure' THEN 2 ELSE 0 END) as sun_pts,
            SUM(CASE WHEN type IN ('gym', 'walking', 'swimming') THEN 2 ELSE 0 END) as exercise_pts,
            SUM(CASE WHEN type = 'nerve-stimulus' AND (tags LIKE '%cold%' OR note LIKE '%cold%') THEN 2 ELSE 0 END) as cold_pts,
            SUM(CASE WHEN type = 'sauna' THEN 1 ELSE 0 END) as sauna_pts,
            SUM(CASE WHEN type IN ('sleep', 'nap') AND duration_seconds >= 25200 THEN 2 ELSE 0 END) as sleep_pts,
            SUM(CASE WHEN type = 'coffee' THEN -1 ELSE 0 END) as coffee_penalty
        FROM activities
        WHERE date(occurred_at) = ?
    """, (today,))
    
    row = cursor.fetchone()
    if not row:
        return {
            "score": 0,
            "max_score": 10,
            "breakdown": {},
            "missing_items": ["sun", "exercise", "cold", "sauna", "sleep"],
            "sparkline": [0] * 7
        }
    
    sun = row['sun_pts'] or 0
    exercise = row['exercise_pts'] or 0
    cold = row['cold_pts'] or 0
    sauna = row['sauna_pts'] or 0
    sleep = row['sleep_pts'] or 0
    coffee_penalty = row['coffee_penalty'] or 0
    
    score = max(0, min(10, sun + exercise + cold + sauna + sleep + coffee_penalty))
    
    # Identify missing items
    missing = []
    if sun == 0:
        missing.append("sun")
    if exercise == 0:
        missing.append("exercise")
    if cold == 0:
        missing.append("cold")
    if sauna == 0:
        missing.append("sauna")
    if sleep == 0:
        missing.append("sleep")
    
    # 7-day sparkline
    sparkline = calculate_t_score_sparkline(conn)
    
    return {
        "score": int(score),
        "max_score": 10,
        "breakdown": {
            "sun": int(sun),
            "exercise": int(exercise),
            "cold": int(cold),
            "sauna": int(sauna),
            "sleep": int(sleep),
            "coffee_penalty": int(coffee_penalty)
        },
        "missing_items": missing,
        "sparkline": sparkline
    }


def calculate_t_score_sparkline(conn) -> List[int]:
    """Calculate T-score for last 7 days for sparkline."""
    sparkline = []
    for days_ago in range(6, -1, -1):
        date = (datetime.now().date() - timedelta(days=days_ago)).isoformat()
        cursor = conn.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'sun-exposure' THEN 2 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN type IN ('gym', 'walking', 'swimming') THEN 2 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN type = 'nerve-stimulus' AND (tags LIKE '%cold%' OR note LIKE '%cold%') THEN 2 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN type = 'sauna' THEN 1 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN type IN ('sleep', 'nap') AND duration_seconds >= 25200 THEN 2 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN type = 'coffee' THEN -1 ELSE 0 END), 0) as score
            FROM activities
            WHERE date(occurred_at) = ?
        """, (date,))
        row = cursor.fetchone()
        score = max(0, min(10, row['score'] or 0))
        sparkline.append(int(score))
    
    return sparkline


def calculate_morning_routine_adherence(conn) -> Dict[str, Any]:
    """
    Calculate morning routine adherence (last 7 days).
    Complete day = yoga + walk before 11am.
    """
    cursor = conn.execute("""
        WITH daily_counts AS (
            SELECT 
                date(occurred_at) as occurred_date,
                COUNT(DISTINCT CASE 
                    WHEN type IN ('yoga', 'walking') 
                        AND strftime('%H', occurred_at) < '11' 
                    THEN type 
                END) as morning_count,
                GROUP_CONCAT(DISTINCT CASE 
                    WHEN type IN ('yoga', 'walking') 
                        AND strftime('%H', occurred_at) < '11' 
                    THEN type 
                END) as activities_done
            FROM activities
            WHERE date(occurred_at) >= date('now', '-7 days')
            GROUP BY date(occurred_at)
        )
        SELECT 
            COUNT(CASE WHEN morning_count >= 2 THEN 1 END) as complete_days,
            ROUND(
                CAST(COUNT(CASE WHEN morning_count >= 2 THEN 1 END) AS REAL) / 
                7.0 * 100
            , 0) as adherence_pct
        FROM daily_counts
    """)
    
    row = cursor.fetchone()
    
    if not row or row['complete_days'] is None:
        return {
            "complete_days": 0,
            "total_days": 7,
            "adherence_pct": 0,
            "today_status": {"yoga": False, "walk": False}
        }
    
    # Today's status
    today = datetime.now().date().isoformat()
    cursor = conn.execute("""
        SELECT 
            MAX(CASE WHEN type = 'yoga' AND strftime('%H', occurred_at) < '11' THEN 1 ELSE 0 END) as yoga_done,
            MAX(CASE WHEN type = 'walking' AND strftime('%H', occurred_at) < '11' THEN 1 ELSE 0 END) as walk_done
        FROM activities
        WHERE date(occurred_at) = ?
    """, (today,))
    
    today_row = cursor.fetchone()
    
    return {
        "complete_days": int(row['complete_days']),
        "total_days": 7,
        "adherence_pct": int(row['adherence_pct']),
        "today_status": {
            "yoga": bool(today_row['yoga_done']) if today_row else False,
            "walk": bool(today_row['walk_done']) if today_row else False
        }
    }


def calculate_exercise_streak(conn) -> Dict[str, Any]:
    """
    Calculate current exercise streak and personal best.
    Exercise = gym, yoga, walking, swimming.
    """
    cursor = conn.execute("""
        SELECT DISTINCT date(occurred_at) as occurred_date
        FROM activities
        WHERE type IN ('gym', 'yoga', 'walking', 'swimming')
        ORDER BY date(occurred_at) DESC
    """)
    
    dates = [row['occurred_date'] for row in cursor.fetchall()]
    
    if not dates:
        return {
            "current_streak": 0,
            "personal_best": 0,
            "last_exercise_date": None
        }
    
    # Calculate current streak
    current_streak = 0
    today = datetime.now().date()
    
    for i, date_str in enumerate(dates):
        date = datetime.fromisoformat(date_str).date()
        expected_date = today - timedelta(days=i)
        
        if date == expected_date:
            current_streak += 1
        else:
            break
    
    # Calculate personal best (scan all dates)
    personal_best = 0
    temp_streak = 1
    
    for i in range(len(dates) - 1):
        current = datetime.fromisoformat(dates[i]).date()
        next_date = datetime.fromisoformat(dates[i + 1]).date()
        
        if (current - next_date).days == 1:
            temp_streak += 1
            personal_best = max(personal_best, temp_streak)
        else:
            temp_streak = 1
    
    personal_best = max(personal_best, temp_streak, current_streak)
    
    return {
        "current_streak": current_streak,
        "personal_best": personal_best,
        "last_exercise_date": dates[0] if dates else None
    }


def calculate_stress_trend(conn) -> Dict[str, Any]:
    """
    Calculate stress trend (last 14 days).
    Stress indicator = nerve-stimulus with stress/anxiety tags.
    """
    cursor = conn.execute("""
        SELECT 
            date(occurred_at) as occurred_date,
            COUNT(*) as stress_count
        FROM activities
        WHERE type = 'nerve-stimulus'
            AND (tags LIKE '%stress%' OR tags LIKE '%anxiety%' OR note LIKE '%stress%' OR note LIKE '%anxiety%')
            AND date(occurred_at) >= date('now', '-14 days')
        GROUP BY date(occurred_at)
        ORDER BY date(occurred_at) ASC
    """)
    
    stress_by_date = {row['occurred_date']: row['stress_count'] for row in cursor.fetchall()}
    
    # Generate 14-day chart data
    chart_data = []
    for days_ago in range(13, -1, -1):
        date = (datetime.now().date() - timedelta(days=days_ago)).isoformat()
        chart_data.append({
            "date": date,
            "count": stress_by_date.get(date, 0)
        })
    
    # Calculate trend (week 1 vs week 2)
    week1_count = sum(d['count'] for d in chart_data[:7])
    week2_count = sum(d['count'] for d in chart_data[7:])
    
    if week1_count == 0:
        trend = "stable"
        change_pct = 0
    else:
        change_pct = int(((week2_count - week1_count) / week1_count) * 100)
        if change_pct > 50:
            trend = "escalating"
        elif change_pct < -50:
            trend = "improving"
        else:
            trend = "stable"
    
    # Recovery recommendations
    recommendations = []
    if trend == "escalating":
        recommendations = ["sauna", "ocean swim", "yoga"]
    elif week2_count > 0:
        recommendations = ["sauna", "breathwork"]
    
    return {
        "trend": trend,
        "change_pct": change_pct,
        "week1_count": week1_count,
        "week2_count": week2_count,
        "chart_data": chart_data,
        "recommendations": recommendations
    }


def generate_health_one_liner(
    t_score_data: Dict,
    morning_routine: Dict,
    exercise_streak: Dict,
    stress_trend: Dict
) -> str:
    """
    Generate motivation-first one-liner for health section per ADR-005.
    """
    score = t_score_data['score']
    streak = exercise_streak['current_streak']
    adherence = morning_routine['adherence_pct']
    
    if score >= 8 and streak >= 5:
        return f"Crushing it: {score}/10 T-score, {streak}-day exercise streak. You're primed for high-quality dates."
    elif score >= 6:
        return f"Solid day: {score}/10 T-score. Morning routine {adherence}% consistent this week. Keep building momentum."
    elif score >= 4:
        return f"Room to improve: {score}/10 T-score. Missing: {', '.join(t_score_data['missing_items'][:2])}. Small wins compound."
    else:
        return f"Low energy day: {score}/10 T-score. Prioritize: {', '.join(t_score_data['missing_items'][:3])} before tonight."


def generate_health_actions(t_score_data: Dict, morning_routine: Dict) -> List[Dict]:
    """Generate actionable buttons for health section."""
    actions = []
    
    # Action 1: Complete missing T-optimization items
    if t_score_data['missing_items']:
        missing = t_score_data['missing_items']
        if 'sun' in missing and datetime.now().hour < 16:
            actions.append({
                "type": "accept",
                "label": "Log Sun Exposure",
                "type": "sun-exposure",
                "duration_minutes": 20
            })
        if 'exercise' in missing:
            actions.append({
                "type": "accept",
                "label": "Log Gym Session",
                "type": "gym",
                "duration_minutes": 45
            })
        if 'sauna' in missing:
            actions.append({
                "type": "accept",
                "label": "Log Sauna",
                "type": "sauna",
                "duration_minutes": 20
            })
    
    # Action 2: Morning routine reminder
    if not morning_routine['today_status']['yoga'] and datetime.now().hour < 11:
        actions.append({
            "type": "accept",
            "label": "Log Morning Yoga",
            "type": "yoga",
            "duration_minutes": 15
        })
    
    if not morning_routine['today_status']['walk'] and datetime.now().hour < 11:
        actions.append({
            "type": "accept",
            "label": "Log Morning Walk",
            "type": "walking",
            "duration_minutes": 20
        })
    
    return actions[:3]  # Max 3 buttons per ADR-005


def build_dating_intelligence_view(conn) -> Dict[str, Any]:
    """
    Build Dating Intelligence section.
    Returns: pool status, source comparison, activity correlation, decision advice.
    """
    # 1. Dating pool exhaustion check
    pool_status = check_dating_pool_exhaustion(conn)
    
    # 2. Source comparison (if enough data)
    source_comparison = calculate_source_comparison(conn)
    
    # 3. Activity-dating correlation (if 10+ dates)
    activity_correlation = calculate_activity_dating_correlation(conn)
    
    # 4. One-liner summary
    one_liner = generate_dating_one_liner(pool_status, source_comparison, activity_correlation)
    
    return {
        "section": "dating_intelligence",
        "goal_ref": "GOAL-1 (find partner)",
        "one_liner": one_liner,
        "pool_status": pool_status,
        "source_comparison": source_comparison,
        "activity_correlation": activity_correlation,
        "actions": generate_dating_actions(pool_status)
    }


def check_dating_pool_exhaustion(conn) -> Dict[str, Any]:
    """Check for dating pool exhaustion (R-ACT-01 logic)."""
    cursor = conn.execute("""
        WITH dating_sessions AS (
            SELECT 
                type,
                date(occurred_at) as occurred_date,
                note,
                CASE 
                    WHEN note LIKE '%0 match%' OR note LIKE '%no match%' THEN 0
                    ELSE 1
                END as had_matches
            FROM activities
            WHERE type IN ('bumble', 'tinder')
                AND date(occurred_at) >= date('now', '-14 days')
            ORDER BY date(occurred_at) DESC
        )
        SELECT 
            type as app,
            COUNT(*) as total_sessions,
            SUM(had_matches) as sessions_with_matches,
            COUNT(*) - SUM(had_matches) as zero_match_sessions
        FROM dating_sessions
        GROUP BY type
    """)
    
    apps = cursor.fetchall()
    exhausted_apps = []
    
    for app_row in apps:
        if app_row['zero_match_sessions'] >= 3:
            exhausted_apps.append(app_row['app'])
    
    # Get location comparison (from cities table)
    cursor = conn.execute("""
        SELECT name, dating_pool
        FROM cities
        WHERE is_current = 0
        ORDER BY dating_pool DESC
        LIMIT 3
    """)
    
    top_cities = cursor.fetchall()
    
    return {
        "exhausted": len(exhausted_apps) > 0,
        "exhausted_apps": exhausted_apps,
        "current_location": "Fuerteventura",
        "alternative_cities": [
            {"name": row['name'], "pool_size": row['dating_pool']} 
            for row in top_cities
        ] if top_cities else []
    }


def calculate_source_comparison(conn) -> Optional[Dict[str, Any]]:
    """Calculate source comparison (app vs events vs social) if 5+ dates."""
    cursor = conn.execute("""
        SELECT 
            source,
            AVG(quality) as avg_quality,
            COUNT(*) as count,
            COUNT(DISTINCT who) as unique_people
        FROM dates
        WHERE date_of >= date('now', '-90 days')
        GROUP BY source
        HAVING count >= 2
        ORDER BY avg_quality DESC
    """)
    
    sources = cursor.fetchall()
    
    if len(sources) < 2:
        return None
    
    return {
        "sources": [
            {
                "source": row['source'],
                "avg_quality": round(row['avg_quality'], 1),
                "count": row['count'],
                "unique_people": row['unique_people']
            }
            for row in sources
        ],
        "best_source": sources[0]['source'] if sources else None
    }


def calculate_activity_dating_correlation(conn) -> Optional[Dict[str, Any]]:
    """Calculate activity-dating correlation (R-ACT-06 logic) if 10+ dates."""
    cursor = conn.execute("SELECT COUNT(*) as total FROM dates")
    total_dates = cursor.fetchone()['total']
    
    if total_dates < 10:
        return None
    
    cursor = conn.execute("""
        WITH date_quality AS (
            SELECT 
                date_of,
                quality
            FROM dates
            WHERE date_of >= date('now', '-90 days')
        ),
        same_day_activities AS (
            SELECT 
                dq.date_of,
                dq.quality,
                SUM(CASE WHEN a.type IN ('gym', 'yoga', 'walking') AND strftime('%H', a.occurred_at) < '12' THEN 1 ELSE 0 END) as morning_exercise,
                SUM(CASE WHEN a.type = 'coffee' THEN 1 ELSE 0 END) as coffee_count
            FROM date_quality dq
            LEFT JOIN activities a ON a.occurred_date = dq.date_of
            GROUP BY dq.date_of, dq.quality
        )
        SELECT 
            AVG(CASE WHEN morning_exercise > 0 THEN quality END) as avg_quality_with_exercise,
            AVG(CASE WHEN morning_exercise = 0 THEN quality END) as avg_quality_no_exercise,
            AVG(CASE WHEN coffee_count >= 3 THEN quality END) as avg_quality_high_coffee,
            COUNT(CASE WHEN morning_exercise > 0 THEN 1 END) as dates_with_exercise
        FROM same_day_activities
    """)
    
    row = cursor.fetchone()
    
    if not row or row['avg_quality_with_exercise'] is None:
        return None
    
    return {
        "avg_quality_with_exercise": round(row['avg_quality_with_exercise'], 1) if row['avg_quality_with_exercise'] else None,
        "avg_quality_no_exercise": round(row['avg_quality_no_exercise'], 1) if row['avg_quality_no_exercise'] else None,
        "avg_quality_high_coffee": round(row['avg_quality_high_coffee'], 1) if row['avg_quality_high_coffee'] else None,
        "dates_with_exercise": row['dates_with_exercise']
    }


def generate_dating_one_liner(
    pool_status: Dict,
    source_comparison: Optional[Dict],
    activity_correlation: Optional[Dict]
) -> str:
    """Generate motivation-first one-liner for dating section."""
    if pool_status['exhausted']:
        apps = ', '.join(pool_status['exhausted_apps'])
        if pool_status['alternative_cities']:
            top_city = pool_status['alternative_cities'][0]
            multiplier = top_city['pool_size'] // 200  # Fuerteventura baseline ~200
            return f"Pool exhausted on {apps}. {top_city['name']} has {multiplier}x larger dating pool."
        else:
            return f"Pool exhausted on {apps}. Try: new photos, different app, or social events."
    
    if source_comparison and len(source_comparison['sources']) >= 2:
        best = source_comparison['sources'][0]
        return f"{best['source']} is your best bet -- {best['avg_quality']} avg quality across {best['count']} dates."
    
    if activity_correlation:
        return "Your best dates happen on days with morning exercise. Worst: after 3+ coffees."
    
    return "Log more dates to unlock intelligence patterns."


def generate_dating_actions(pool_status: Dict) -> List[Dict]:
    """Generate actionable buttons for dating section."""
    actions = []
    
    if pool_status['exhausted']:
        actions.append({
            "type": "view_details",
            "label": "Compare Cities",
            "url": "/api/cities/comparison"
        })
        actions.append({
            "type": "snooze",
            "label": "Remind Me in 1 Week",
            "duration_hours": 168
        })
    else:
        actions.append({
            "type": "accept",
            "label": "Log Dating App Session",
            "type": "tinder",
            "duration_minutes": 15
        })
    
    return actions[:3]


def get_advisor_view() -> Dict[str, Any]:
    """
    Main entry point for advisor view.
    Combines Health Optimizer + Dating Intelligence sections.
    """
    conn = get_db()
    
    health = build_health_optimizer_view(conn)
    dating = build_dating_intelligence_view(conn)
    
    conn.close()
    
    return {
        "advisor": {
            "health_optimizer": health,
            "dating_intelligence": dating
        },
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
