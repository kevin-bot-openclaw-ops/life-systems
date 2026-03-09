"""
TASK-050: Sprint Loop Meta Heartbeat Integration

Lightweight check before expensive GOAL computations.
Skips processing when no new data since last sprint.
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List


# Configuration
SHARE_TOKEN = "a50ea3e50186487ca3ad094bc3e177ac"  # Working token
BASE_URL = "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com"
STATE_FILE = Path("/tmp/kevin-meta-state.json")
LOOKBACK_DAYS = 7

# Dormancy thresholds (days since last log)
DORMANCY_THRESHOLDS = {
    'bumble': 3,
    'tinder': 3,
    'date': 7,
    'gym': 2,
    'duo-lingo': 3,
}


class MetaHeartbeat:
    """Lightweight heartbeat to detect new data and dormancy."""
    
    def __init__(self, share_token: str = SHARE_TOKEN, state_file: Path = STATE_FILE):
        self.share_token = share_token
        self.base_url = BASE_URL
        self.state_file = state_file
    
    def fetch_meta(self, lookback_days: int = LOOKBACK_DAYS) -> Dict:
        """
        Fetch meta information from Activities API.
        
        Args:
            lookback_days: How far back to look for activity
            
        Returns:
            Dict with lastOccurrenceAt, activeTypes, daysSinceLastLog
        """
        url = f"{self.base_url}/shared/{self.share_token}/meta?lookbackDays={lookback_days}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def load_previous_state(self) -> Optional[Dict]:
        """Load state from previous sprint."""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load state: {e}")
            return None
    
    def save_current_state(self, meta: Dict) -> None:
        """Save current meta for next sprint."""
        from datetime import timezone
        state = {
            'lastOccurrenceAt': meta['lastOccurrenceAt'],
            'activeTypes': meta['activeTypes'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'daysSinceLastLog': meta.get('daysSinceLastLog', {})
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def has_new_data(self, current_meta: Dict, previous_state: Optional[Dict]) -> bool:
        """
        Check if there's new data since last sprint.
        
        Args:
            current_meta: Current meta from API
            previous_state: Previous state from file
            
        Returns:
            True if new data exists, False otherwise
        """
        if previous_state is None:
            # First run, consider it "new data"
            return True
        
        prev_last_at = previous_state.get('lastOccurrenceAt')
        curr_last_at = current_meta.get('lastOccurrenceAt')
        
        # If timestamps differ, there's new data
        if prev_last_at != curr_last_at:
            return True
        
        return False
    
    def detect_dormancy(self, meta: Dict) -> List[Dict]:
        """
        Detect dormant activity types based on daysSinceLastLog.
        
        Args:
            meta: Meta data with daysSinceLastLog
            
        Returns:
            List of dormancy alerts
        """
        alerts = []
        days_since = meta.get('daysSinceLastLog', {})
        
        for activity_type, threshold in DORMANCY_THRESHOLDS.items():
            days = days_since.get(activity_type, 0)
            
            if days >= threshold:
                alerts.append({
                    'type': activity_type,
                    'days_silent': days,
                    'threshold': threshold,
                    'severity': 'warning' if days < threshold * 2 else 'critical'
                })
        
        return alerts
    
    def check(self) -> Dict:
        """
        Main heartbeat check.
        
        Returns:
            Dict with decision (skip/proceed) and metadata
        """
        # Fetch current meta
        current_meta = self.fetch_meta()
        
        # Load previous state
        previous_state = self.load_previous_state()
        
        # Check for new data
        has_new = self.has_new_data(current_meta, previous_state)
        
        # Detect dormancy
        dormancy_alerts = self.detect_dormancy(current_meta)
        
        # Save current state for next time
        self.save_current_state(current_meta)
        
        from datetime import timezone
        result = {
            'decision': 'proceed' if has_new else 'skip',
            'has_new_data': has_new,
            'last_occurrence_at': current_meta.get('lastOccurrenceAt'),
            'active_types': current_meta.get('activeTypes', 0),
            'dormancy_alerts': dormancy_alerts,
            'previous_last_at': previous_state.get('lastOccurrenceAt') if previous_state else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return result
    
    def should_skip_goal_computations(self) -> tuple[bool, Dict]:
        """
        Convenience method for sprint loop integration.
        
        Returns:
            (should_skip: bool, report: Dict)
        """
        report = self.check()
        should_skip = report['decision'] == 'skip'
        
        return should_skip, report


def sprint_loop_heartbeat() -> Dict:
    """
    Entry point for Kevin's sprint loop.
    
    Returns:
        Dict with decision and report
    """
    heartbeat = MetaHeartbeat()
    should_skip, report = heartbeat.should_skip_goal_computations()
    
    # Print decision
    if should_skip:
        print(f"✅ No new data since {report['previous_last_at']}")
        print("⏭️  Skipping GOAL computations (saves ~75% of sprint compute)")
    else:
        print(f"🆕 New data detected! Last activity: {report['last_occurrence_at']}")
        print(f"📊 {report['active_types']} active types")
        print("▶️  Proceeding with GOAL task execution")
    
    # Print dormancy alerts
    if report['dormancy_alerts']:
        print("\n⚠️  DORMANCY ALERTS:")
        for alert in report['dormancy_alerts']:
            emoji = '🔴' if alert['severity'] == 'critical' else '🟡'
            print(f"{emoji} {alert['type']}: {alert['days_silent']} days silent (threshold: {alert['threshold']})")
    
    return report


def main():
    """CLI entry point for testing."""
    report = sprint_loop_heartbeat()
    
    print("\n" + "="*60)
    print("FULL REPORT:")
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
