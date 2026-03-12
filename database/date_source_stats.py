"""
Date Source Conversion Tracking

Analyzes dating success by channel (app, event, social) to identify
which sources produce the highest quality dates and follow-up rates.

Epic: EPIC-001 Dating Module
Task: DATE-M1-2
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import sqlite3
from datetime import datetime


@dataclass
class SourceStats:
    """Statistics for a dating source channel"""
    source: str
    date_count: int
    avg_quality: float
    follow_up_rate: float  # % of first dates that led to 2+ dates
    total_quality_points: int
    people_met: int
    repeat_dates: int


@dataclass
class SourceComparison:
    """Complete source comparison with ranking"""
    stats: List[SourceStats]
    best_source: str
    best_avg_quality: float
    one_liner: str
    data_table: List[Dict]
    sample_size_warning: Optional[str] = None


def get_source_stats(db_path: str = "/var/lib/life-systems/life.db") -> SourceComparison:
    """
    Compute source conversion statistics from dates table.
    
    Returns SourceComparison with ranked sources and ADR-005 formatted output.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get basic per-source stats
    cursor.execute("""
        SELECT 
            source,
            COUNT(*) as date_count,
            AVG(quality) as avg_quality,
            SUM(quality) as total_quality,
            COUNT(DISTINCT who) as people_met
        FROM dates
        WHERE archived = 0
        GROUP BY source
        ORDER BY avg_quality DESC, date_count DESC
    """)
    
    source_rows = cursor.fetchall()
    
    # Compute follow-up rates (people who had 2+ dates)
    cursor.execute("""
        SELECT 
            d.source,
            COUNT(DISTINCT d.who) as repeat_people
        FROM dates d
        WHERE d.archived = 0
        AND d.who IN (
            SELECT who 
            FROM dates 
            WHERE archived = 0
            GROUP BY who 
            HAVING COUNT(*) >= 2
        )
        GROUP BY d.source
    """)
    
    repeat_dates_map = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Build stats list
    stats_list = []
    for row in source_rows:
        source, date_count, avg_quality, total_quality, people_met = row
        repeat_dates = repeat_dates_map.get(source, 0)
        
        follow_up_rate = (repeat_dates / people_met * 100) if people_met > 0 else 0.0
        
        stats_list.append(SourceStats(
            source=source,
            date_count=date_count,
            avg_quality=round(avg_quality, 1),
            follow_up_rate=round(follow_up_rate, 1),
            total_quality_points=total_quality,
            people_met=people_met,
            repeat_dates=repeat_dates
        ))
    
    conn.close()
    
    # Empty state
    if not stats_list:
        return SourceComparison(
            stats=[],
            best_source="",
            best_avg_quality=0.0,
            one_liner="No dates logged yet. Log your first date to start tracking.",
            data_table=[],
            sample_size_warning="Start logging dates to see source comparison."
        )
    
    # Rank sources
    best = stats_list[0]
    total_dates = sum(s.date_count for s in stats_list)
    
    # Generate one-liner (ADR-005: motivation-first)
    if len(stats_list) == 1:
        one_liner = f"Your {best.source} dates average {best.avg_quality:.1f}/10 quality ({best.date_count} dates)."
    else:
        second = stats_list[1]
        diff = best.avg_quality - second.avg_quality
        one_liner = (
            f"{best.source.capitalize()} is your best channel: "
            f"{best.avg_quality:.1f}/10 avg quality vs {second.source} {second.avg_quality:.1f}/10 "
            f"({'+' if diff > 0 else ''}{diff:.1f} point edge). "
            f"Focus {best.source} for quality."
        )
    
    # Build comparison table
    data_table = [
        {
            "Source": s.source.capitalize(),
            "Dates": s.date_count,
            "Avg Quality": f"{s.avg_quality:.1f}/10",
            "People Met": s.people_met,
            "Follow-up Rate": f"{s.follow_up_rate:.0f}%",
        }
        for s in stats_list
    ]
    
    # Sample size warning
    warning = None
    if total_dates < 10:
        warning = f"Small sample size ({total_dates} dates). Patterns will strengthen after 10+ dates."
    
    return SourceComparison(
        stats=stats_list,
        best_source=best.source,
        best_avg_quality=best.avg_quality,
        one_liner=one_liner,
        data_table=data_table,
        sample_size_warning=warning
    )


def get_follow_up_details(db_path: str = "/var/lib/life-systems/life.db") -> List[Dict]:
    """Get list of people with multiple dates for detailed breakdown."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            who,
            source,
            COUNT(*) as date_count,
            MIN(date_of) as first_date,
            MAX(date_of) as last_date,
            AVG(quality) as avg_quality
        FROM dates
        WHERE archived = 0
        GROUP BY who
        HAVING COUNT(*) >= 2
        ORDER BY date_count DESC, avg_quality DESC
    """)
    
    results = []
    for row in cursor.fetchall():
        who, source, count, first, last, avg_q = row
        results.append({
            "who": who,
            "source": source,
            "dates": count,
            "first_date": first,
            "last_date": last,
            "avg_quality": round(avg_q, 1)
        })
    
    conn.close()
    return results


if __name__ == "__main__":
    # Test with current data
    comparison = get_source_stats()
    
    print("DATE-M1-2: Source Conversion Tracking")
    print("=" * 60)
    print()
    print(f"One-liner: {comparison.one_liner}")
    print()
    print("Source Comparison:")
    for row in comparison.data_table:
        print(f"  {row}")
    print()
    if comparison.sample_size_warning:
        print(f"⚠️  {comparison.sample_size_warning}")
    print()
    
    # Show follow-up details
    follow_ups = get_follow_up_details()
    if follow_ups:
        print("People with multiple dates:")
        for person in follow_ups:
            print(f"  {person['who']}: {person['dates']} dates, avg quality {person['avg_quality']}/10")
    else:
        print("No repeat dates yet.")
