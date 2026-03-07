"""
Activities Data Bridge
Fetches activity data from the external Activities app (share token API) and stores in local SQLite.

Share token: a50ea3e50186487ca3ad094bc3e177ac (read-only, Jurek's data)
Base URL: https://xznxeho9da.execute-api.eu-central-1.amazonaws.com

Activity-to-Goal Mapping:
- bumble, tinder → GOAL-1 (dating)
- duo-lingo → GOAL-3 (relocation prep - Spanish learning)
- gym, walking, swimming, uttanasana, yoga → Health
- sauna, nerve-stimulus → Health (stress management)
- sun-exposure → Health (testosterone optimization)
- coffee → Health (track overconsumption)
- sleep, nap → Health (recovery)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

# Activities API configuration
SHARE_TOKEN = "a50ea3e50186487ca3ad094bc3e177ac"
BASE_URL = "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com"

# Activity type to goal mapping
ACTIVITY_GOAL_MAP = {
    "bumble": "GOAL-1",
    "tinder": "GOAL-1",
    "duo-lingo": "GOAL-3",
    "gym": "Health",
    "walking": "Health",
    "swimming": "Health",
    "uttanasana": "Health",
    "yoga": "Health",
    "sauna": "Health",
    "nerve-stimulus": "Health",
    "sun-exposure": "Health",
    "coffee": "Health",
    "sleep": "Health",
    "nap": "Health",
}


class ActivitiesBridge:
    """Bridge between Activities app and Life Systems SQLite database."""
    
    def __init__(self, db_path: str = "life.db"):
        self.db_path = db_path
        self.base_url = BASE_URL
        self.share_token = SHARE_TOKEN
        
    def fetch_date_range(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        Fetch activities for a date range.
        
        Args:
            from_date: YYYY-MM-DD
            to_date: YYYY-MM-DD
            
        Returns:
            List of activity occurrences
        """
        url = f"{self.base_url}/shared/{self.share_token}/occurrences/dates/{from_date}/{to_date}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("occurrences", [])
        except Exception as e:
            logger.error(f"Failed to fetch activities from {from_date} to {to_date}: {e}")
            return []
    
    def fetch_today(self) -> List[Dict[str, Any]]:
        """Fetch today's activities."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.fetch_date_range(today, today)
    
    def backfill_30_days(self) -> int:
        """
        Backfill last 30 days of activities.
        
        Returns:
            Number of new activities stored
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        from_str = start_date.strftime("%Y-%m-%d")
        to_str = end_date.strftime("%Y-%m-%d")
        
        occurrences = self.fetch_date_range(from_str, to_str)
        return self.store_activities(occurrences)
    
    def parse_occurrence(self, occ: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single occurrence from the API into our internal format.
        
        API format:
        {
          "id": "uuid",
          "activityType": {"id": "uuid", "name": "bumble", ...},
          "moment": "2026-03-07T10:00:00Z",  (for MOMENT activities)
          "start": "2026-03-07T10:00:00Z",    (for SPAN activities)
          "finish": "2026-03-07T11:00:00Z",
          "note": "text",
          "measurements": [...],
          "tags": [...]
        }
        
        Returns:
            Parsed activity dict or None if should be skipped
        """
        try:
            activity_type_name = occ.get("activityType", {}).get("name", "unknown")
            
            # Skip activities we don't track
            if activity_type_name not in ACTIVITY_GOAL_MAP:
                return None
            
            # Determine timestamp and duration
            if "moment" in occ:
                # MOMENT activity (instant event like coffee, bumble swipe)
                occurred_at = occ["moment"]
                duration_minutes = None
            elif "start" in occ and "finish" in occ:
                # SPAN activity (duration-based like gym, sleep)
                occurred_at = occ["start"]
                start = datetime.fromisoformat(occ["start"].replace("Z", "+00:00"))
                finish = datetime.fromisoformat(occ["finish"].replace("Z", "+00:00"))
                duration_minutes = int((finish - start).total_seconds() / 60)
            else:
                logger.warning(f"Activity {occ.get('id')} has no timestamp, skipping")
                return None
            
            # Extract occurred_date (YYYY-MM-DD)
            occurred_date = occurred_at.split("T")[0]
            
            # Parse measurements (API returns array of measurement objects)
            measurements_raw = occ.get("measurements", [])
            measurements = {}
            for m in measurements_raw:
                meas_type = m.get("type", {}).get("name", "unknown")
                if "value" in m:
                    measurements[meas_type] = m["value"]
                elif "count" in m:
                    measurements[meas_type] = m["count"]
            
            # Parse tags
            tags_raw = occ.get("tags", [])
            tags = [t.get("name", "") for t in tags_raw if "name" in t]
            
            return {
                "activity_id": occ["id"],
                "activity_type": activity_type_name,
                "occurred_at": occurred_at,
                "occurred_date": occurred_date,
                "duration_minutes": duration_minutes,
                "note": occ.get("note"),
                "tags": json.dumps(tags),
                "measurements": json.dumps(measurements),
                "goal_mapping": ACTIVITY_GOAL_MAP[activity_type_name],
            }
        
        except Exception as e:
            logger.error(f"Failed to parse occurrence {occ.get('id', 'unknown')}: {e}")
            return None
    
    def store_activities(self, occurrences: List[Dict[str, Any]]) -> int:
        """
        Store activities in the database.
        
        Args:
            occurrences: List of raw occurrence dicts from API
            
        Returns:
            Number of new activities stored
        """
        if not occurrences:
            return 0
        
        parsed = []
        for occ in occurrences:
            parsed_occ = self.parse_occurrence(occ)
            if parsed_occ:
                parsed.append(parsed_occ)
        
        if not parsed:
            logger.info("No trackable activities in fetched occurrences")
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_count = 0
        for activity in parsed:
            try:
                cursor.execute("""
                    INSERT INTO activities (
                        activity_id, activity_type, occurred_at, occurred_date,
                        duration_minutes, note, tags, measurements, goal_mapping
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity["activity_id"],
                    activity["activity_type"],
                    activity["occurred_at"],
                    activity["occurred_date"],
                    activity["duration_minutes"],
                    activity["note"],
                    activity["tags"],
                    activity["measurements"],
                    activity["goal_mapping"],
                ))
                new_count += 1
            except sqlite3.IntegrityError:
                # Activity already exists (UNIQUE constraint on activity_id)
                pass
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {new_count} new activities (out of {len(parsed)} fetched)")
        return new_count
    
    def is_first_run(self) -> bool:
        """Check if this is the first run (no activities in database)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM activities")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    
    def sync(self) -> Dict[str, Any]:
        """
        Main sync method. Call this from cron.
        
        On first run: backfill 30 days
        On subsequent runs: fetch today's activities
        
        Returns:
            Sync stats dict
        """
        start_time = datetime.now()
        
        if self.is_first_run():
            logger.info("First run detected - backfilling 30 days")
            new_count = self.backfill_30_days()
            logger.info(f"Backfill complete: {new_count} activities stored")
        else:
            logger.info("Fetching today's activities")
            occurrences = self.fetch_today()
            new_count = self.store_activities(occurrences)
            logger.info(f"Sync complete: {new_count} new activities")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "new_count": new_count,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """CLI entry point for manual sync."""
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "life.db"
    bridge = ActivitiesBridge(db_path)
    
    print("Syncing activities...")
    stats = bridge.sync()
    print(f"✓ Synced {stats['new_count']} new activities in {stats['duration_seconds']:.1f}s")


if __name__ == "__main__":
    main()
