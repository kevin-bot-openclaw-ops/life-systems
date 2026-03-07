"""
Activities Data Bridge
Fetches behavioral data from Jurek's Activities app via share token.
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import requests


# Constants
SHARE_TOKEN = "a50ea3e50186487ca3ad094bc3e177ac"
BASE_URL = "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com"
DB_PATH = Path("/var/lib/life-systems/life.db")

# Activity type to goal mapping
ACTIVITY_GOAL_MAP = {
    "bumble": "GOAL-1",
    "tinder": "GOAL-1",
    "uttanasana": "Health",
    "gym": "Health",
    "walking": "Health",
    "swimming": "Health",
    "sauna": "Health",
    "nerve-stimulus": "Health",
    "sun-exposure": "Health",
    "coffee": "Health",
    "duo-lingo": "GOAL-3",
    "sleep": "Health",
    "nap": "Health",
}


class ActivitiesBridge:
    """Fetches and stores activities from the Activities app."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.share_token = SHARE_TOKEN
        self.base_url = BASE_URL
        
    def fetch_date(self, date: str) -> List[Dict]:
        """
        Fetch all activities for a specific date.
        
        Args:
            date: ISO date string (YYYY-MM-DD)
            
        Returns:
            List of occurrence dicts from API
            
        Raises:
            requests.HTTPError: If API returns error status
        """
        url = f"{self.base_url}/shared/{self.share_token}/occurrences/dates/{date}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def fetch_date_range(self, from_date: str, to_date: str) -> List[Dict]:
        """
        Fetch all activities for a date range.
        
        Args:
            from_date: ISO date string (YYYY-MM-DD)
            to_date: ISO date string (YYYY-MM-DD)
            
        Returns:
            List of occurrence dicts from API
        """
        url = f"{self.base_url}/shared/{self.share_token}/occurrences/dates/{from_date}/{to_date}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def parse_occurrence(self, occ: Dict) -> Dict:
        """
        Parse an occurrence from API into internal Activity model.
        
        Args:
            occ: Raw occurrence dict from API
            
        Returns:
            Activity dict ready for SQLite insertion
        """
        activity_type = occ["activityType"]
        temporal_mark = occ["temporalMark"]
        
        # Extract occurred_at timestamp
        if temporal_mark["type"] == "MOMENT":
            occurred_at = temporal_mark["at"]
            duration_seconds = None
        else:  # SPAN
            occurred_at = temporal_mark["start"]
            start = datetime.fromisoformat(temporal_mark["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(temporal_mark["end"].replace("Z", "+00:00"))
            duration_seconds = int((end - start).total_seconds())
        
        # Map to goal
        goal_mapping = ACTIVITY_GOAL_MAP.get(activity_type, "Health")
        
        return {
            "id": occ["id"],
            "type": activity_type,
            "occurred_at": occurred_at,
            "duration_seconds": duration_seconds,
            "note": occ.get("note"),
            "tags": json.dumps(occ.get("tags", [])),
            "measurements": json.dumps(occ.get("measurements", [])),
            "goal_mapping": goal_mapping,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    
    def store_activities(self, activities: List[Dict]) -> int:
        """
        Store activities in SQLite database.
        
        Args:
            activities: List of parsed activity dicts
            
        Returns:
            Number of new activities inserted (deduplicated)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        inserted = 0
        for activity in activities:
            try:
                cursor.execute("""
                    INSERT INTO activities 
                    (id, type, occurred_at, duration_seconds, note, tags, measurements, goal_mapping, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity["id"],
                    activity["type"],
                    activity["occurred_at"],
                    activity["duration_seconds"],
                    activity["note"],
                    activity["tags"],
                    activity["measurements"],
                    activity["goal_mapping"],
                    activity["fetched_at"],
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                # Activity already exists (duplicate ID), skip
                pass
        
        conn.commit()
        conn.close()
        return inserted
    
    def sync_today(self) -> Dict:
        """
        Sync today's activities.
        
        Returns:
            Stats dict with activities_fetched, activities_new, duration
        """
        start = datetime.utcnow()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        try:
            occurrences = self.fetch_date(today)
            activities = [self.parse_occurrence(occ) for occ in occurrences]
            new_count = self.store_activities(activities)
            
            duration = (datetime.utcnow() - start).total_seconds()
            
            return {
                "date": today,
                "activities_fetched": len(occurrences),
                "activities_new": new_count,
                "duration_seconds": duration,
                "success": True,
                "error": None,
            }
        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds()
            return {
                "date": today,
                "activities_fetched": 0,
                "activities_new": 0,
                "duration_seconds": duration,
                "success": False,
                "error": str(e),
            }
    
    def backfill(self, days: int = 30) -> Dict:
        """
        Backfill activities from the past N days.
        
        Args:
            days: Number of days to backfill (default 30)
            
        Returns:
            Stats dict with total activities fetched and inserted
        """
        start = datetime.utcnow()
        to_date = datetime.utcnow().strftime("%Y-%m-%d")
        from_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        try:
            occurrences = self.fetch_date_range(from_date, to_date)
            activities = [self.parse_occurrence(occ) for occ in occurrences]
            new_count = self.store_activities(activities)
            
            duration = (datetime.utcnow() - start).total_seconds()
            
            return {
                "from_date": from_date,
                "to_date": to_date,
                "activities_fetched": len(occurrences),
                "activities_new": new_count,
                "duration_seconds": duration,
                "success": True,
                "error": None,
            }
        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds()
            return {
                "from_date": from_date,
                "to_date": to_date,
                "activities_fetched": 0,
                "activities_new": 0,
                "duration_seconds": duration,
                "success": False,
                "error": str(e),
            }
    
    def is_first_run(self) -> bool:
        """Check if this is the first run (activities table is empty)."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM activities")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0


def main():
    """CLI entry point for activities bridge."""
    bridge = ActivitiesBridge()
    
    # Check if first run
    if bridge.is_first_run():
        print("🔄 First run detected. Backfilling last 30 days...")
        stats = bridge.backfill(days=30)
    else:
        print("🔄 Syncing today's activities...")
        stats = bridge.sync_today()
    
    # Print stats
    if stats["success"]:
        print(f"✅ Success!")
        print(f"   Fetched: {stats['activities_fetched']} activities")
        print(f"   New: {stats['activities_new']} activities")
        print(f"   Duration: {stats['duration_seconds']:.2f}s")
    else:
        print(f"❌ Error: {stats['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
