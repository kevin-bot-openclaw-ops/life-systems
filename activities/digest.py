"""
Daily Activities Digest Generator
Groups activities by goal and creates motivation-first summary.
"""

import sqlite3
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional


DB_PATH = Path("/var/lib/life-systems/life.db")


class DailyDigest:
    """Generates daily activity digest in motivation-first format."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        
    def _get_activities_for_date(self, target_date: date) -> List[Dict]:
        """Fetch all activities for a specific date."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        date_str = target_date.isoformat()
        next_day = (target_date + timedelta(days=1)).isoformat()
        
        query = """
            SELECT id, type, occurred_at, duration_seconds, note, 
                   tags, measurements, goal_mapping
            FROM activities
            WHERE occurred_at >= ? AND occurred_at < ?
            ORDER BY occurred_at
        """
        
        cursor = conn.execute(query, (date_str, next_day))
        activities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return activities
    
    def _group_by_goal(self, activities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group activities by goal mapping."""
        groups = defaultdict(list)
        for activity in activities:
            goal = activity["goal_mapping"] or "Other"
            groups[goal].append(activity)
        return dict(groups)
    
    def _calculate_duration_minutes(self, activities: List[Dict]) -> int:
        """Sum duration_seconds across activities, convert to minutes."""
        total_seconds = sum(a["duration_seconds"] or 0 for a in activities)
        return total_seconds // 60
    
    def _extract_key_notes(self, activities: List[Dict], max_notes: int = 3) -> List[str]:
        """Extract non-empty notes from activities."""
        notes = []
        for activity in activities:
            note = activity.get("note", "").strip()
            if note and len(notes) < max_notes:
                notes.append(f"{activity['type']}: {note}")
        return notes
    
    def _detect_anomalies(self, activities: List[Dict], target_date: date) -> List[str]:
        """Detect notable patterns or absences."""
        anomalies = []
        
        # Get activities from yesterday and past week for comparison
        conn = sqlite3.connect(self.db_path)
        
        # Check for broken streaks (gym, walking, yoga)
        streak_types = ["gym", "uttanasana", "walking"]
        today_types = {a["type"] for a in activities}
        
        for activity_type in streak_types:
            if activity_type in today_types:
                # Check streak length
                query = """
                    SELECT COUNT(DISTINCT DATE(occurred_at)) as days
                    FROM activities
                    WHERE type = ?
                    AND DATE(occurred_at) >= DATE(?, '-7 days')
                    AND DATE(occurred_at) <= DATE(?)
                """
                cursor = conn.execute(query, (activity_type, target_date.isoformat(), target_date.isoformat()))
                streak_days = cursor.fetchone()[0]
                
                if streak_days >= 3:
                    anomalies.append(f"{streak_days}-day {activity_type} streak maintained")
            else:
                # Check if there was a streak that just broke
                query = """
                    SELECT COUNT(DISTINCT DATE(occurred_at)) as days
                    FROM activities
                    WHERE type = ?
                    AND DATE(occurred_at) >= DATE(?, '-7 days')
                    AND DATE(occurred_at) < DATE(?)
                """
                cursor = conn.execute(query, (activity_type, target_date.isoformat(), target_date.isoformat()))
                recent_days = cursor.fetchone()[0]
                
                if recent_days >= 3:
                    anomalies.append(f"No {activity_type} today (streak broken at {recent_days} days)")
        
        # Check for first occurrences in 2+ weeks
        for activity_type in today_types:
            if activity_type in ["sauna", "swimming", "sun-exposure"]:
                query = """
                    SELECT MAX(DATE(occurred_at)) as last_date
                    FROM activities
                    WHERE type = ?
                    AND DATE(occurred_at) < DATE(?)
                """
                cursor = conn.execute(query, (activity_type, target_date.isoformat()))
                last_date_str = cursor.fetchone()[0]
                
                if last_date_str:
                    last_date = datetime.fromisoformat(last_date_str).date()
                    days_since = (target_date - last_date).days
                    if days_since >= 7:
                        anomalies.append(f"First {activity_type} in {days_since} days — nice!")
        
        # Check for excessive coffee
        coffee_count = sum(1 for a in activities if a["type"] == "coffee")
        if coffee_count >= 3:
            anomalies.append(f"{coffee_count} coffees today — might impact sleep")
        
        # Check for dating app activity with no matches
        dating_apps = [a for a in activities if a["type"] in ["bumble", "tinder"]]
        for app in dating_apps:
            note = (app.get("note") or "").lower()
            if "no match" in note or "0 match" in note:
                anomalies.append(f"{app['type']}: {app.get('note', 'no matches')}")
        
        conn.close()
        return anomalies
    
    def generate_one_liner(self, activities: List[Dict], groups: Dict[str, List[Dict]]) -> str:
        """Generate motivation-first one-liner summary."""
        if not activities:
            return "No activities logged today. Everything okay?"
        
        total_count = len(activities)
        goal_summary = []
        
        # Prioritize non-Health goals first (GOAL-1, GOAL-2, GOAL-3)
        priority_goals = ["GOAL-1", "GOAL-2", "GOAL-3"]
        for goal in priority_goals:
            if goal in groups:
                count = len(groups[goal])
                types = list(set(a["type"] for a in groups[goal]))
                
                if goal == "GOAL-1":
                    # Dating-specific summary
                    bumble = sum(1 for a in groups[goal] if a["type"] == "bumble")
                    tinder = sum(1 for a in groups[goal] if a["type"] == "tinder")
                    apps = []
                    if bumble:
                        apps.append(f"{bumble} Bumble")
                    if tinder:
                        apps.append(f"{tinder} Tinder")
                    
                    # Check for matches in notes
                    has_matches = any("match" in (a.get("note") or "").lower() and "no match" not in (a.get("note") or "").lower() 
                                     for a in groups[goal])
                    match_status = "matches found" if has_matches else "0 matches"
                    
                    goal_summary.append(f"GOAL-1: {', '.join(apps)} ({match_status})")
                
                elif goal == "GOAL-3":
                    # Learning-specific (Duo-lingo)
                    sessions = count
                    goal_summary.append(f"GOAL-3: {sessions} Spanish lesson{'s' if sessions > 1 else ''}")
                
                elif goal == "GOAL-2":
                    # Career/learning
                    goal_summary.append(f"GOAL-2: {count} session{'s' if count > 1 else ''}")
        
        # Add Health summary
        if "Health" in groups:
            health_types = list(set(a["type"] for a in groups["Health"]))
            health_count = len(groups["Health"])
            
            # Prioritize exercise types
            exercise_types = [t for t in health_types if t in ["gym", "uttanasana", "walking", "swimming"]]
            wellness_types = [t for t in health_types if t in ["sauna", "sun-exposure", "nerve-stimulus"]]
            
            health_parts = []
            if exercise_types:
                health_parts.append(f"{len([a for a in groups['Health'] if a['type'] in exercise_types])} exercise")
            if wellness_types:
                health_parts.append(f"{len([a for a in groups['Health'] if a['type'] in wellness_types])} wellness")
            
            if not health_parts:
                health_parts.append(f"{health_count} health")
            
            goal_summary.append(f"Health: {', '.join(health_parts)}")
        
        summary = f"Today: {total_count} activities. " + ". ".join(goal_summary) + "."
        return summary
    
    def generate_data_table(self, groups: Dict[str, List[Dict]]) -> List[List[str]]:
        """Generate data table: type | count | duration | goal | key notes."""
        # Header
        table = [["Activity Type", "Count", "Duration", "Goal", "Key Notes"]]
        
        # Group and summarize by type within each goal
        type_summaries = {}
        
        for goal, activities in groups.items():
            for activity in activities:
                act_type = activity["type"]
                key = (act_type, goal)
                
                if key not in type_summaries:
                    type_summaries[key] = {
                        "count": 0,
                        "duration_seconds": 0,
                        "notes": []
                    }
                
                type_summaries[key]["count"] += 1
                type_summaries[key]["duration_seconds"] += activity.get("duration_seconds") or 0
                
                note = (activity.get("note") or "").strip()
                if note and len(type_summaries[key]["notes"]) < 1:  # Only first note
                    type_summaries[key]["notes"].append(note[:40])  # Truncate long notes
        
        # Convert to table rows
        for (act_type, goal), summary in sorted(type_summaries.items(), key=lambda x: (x[0][1], -x[1]["count"])):
            duration_min = summary["duration_seconds"] // 60
            duration_str = f"{duration_min}m" if duration_min > 0 else "-"
            notes_str = summary["notes"][0] if summary["notes"] else "-"
            
            table.append([
                act_type,
                str(summary["count"]),
                duration_str,
                goal,
                notes_str
            ])
        
        return table
    
    def generate_digest(self, target_date: Optional[date] = None) -> Tuple[str, List[List[str]], List[str]]:
        """
        Generate complete daily digest.
        
        Args:
            target_date: Date to generate digest for (defaults to today)
            
        Returns:
            Tuple of (one_liner, data_table, anomalies)
        """
        if target_date is None:
            target_date = date.today()
        
        activities = self._get_activities_for_date(target_date)
        groups = self._group_by_goal(activities)
        
        one_liner = self.generate_one_liner(activities, groups)
        data_table = self.generate_data_table(groups)
        anomalies = self._detect_anomalies(activities, target_date)
        
        return one_liner, data_table, anomalies
    
    def format_for_slack(self, one_liner: str, data_table: List[List[str]], anomalies: List[str]) -> str:
        """Format digest as Slack markdown."""
        lines = []
        
        # One-liner (bold)
        lines.append(f"*{one_liner}*\n")
        
        # Data table (fixed-width for alignment)
        if len(data_table) > 1:  # Has data beyond header
            # Calculate column widths
            col_widths = [max(len(str(row[i])) for row in data_table) for i in range(len(data_table[0]))]
            
            # Format header
            header = " | ".join(data_table[0][i].ljust(col_widths[i]) for i in range(len(data_table[0])))
            lines.append(f"```\n{header}")
            lines.append("-" * len(header))
            
            # Format data rows
            for row in data_table[1:]:
                row_str = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
                lines.append(row_str)
            
            lines.append("```\n")
        
        # Anomalies (if any)
        if anomalies:
            lines.append("*Notable:*")
            for anomaly in anomalies:
                lines.append(f"• {anomaly}")
        
        return "\n".join(lines)
