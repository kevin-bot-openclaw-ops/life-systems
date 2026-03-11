"""
Tests for GOAL1-01: Dating Pool Monitor & Relocation Trigger
"""

import pytest
import sqlite3
import json
import os
from datetime import datetime, timedelta
from goals.dating_pool_monitor import (
    DatingPoolMonitor,
    PoolStatus,
    DatingMetrics,
    PoolAlert
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with schema."""
    db_path = tmp_path / "test_life.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create activities table
    cursor.execute('''
    CREATE TABLE activities (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        duration_seconds INTEGER,
        note TEXT,
        tags TEXT,
        measurements TEXT,
        goal_mapping TEXT,
        fetched_at TEXT,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    return str(db_path)


def create_dating_activity(db_path, activity_type, days_ago, swipes, right, left, 
                          matches=0, conversations=0, dates=0, note=None, location=None):
    """Helper to insert a dating activity."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    occurred_at = (datetime.now() - timedelta(days=days_ago)).isoformat() + 'Z'
    activity_id = f"test-{activity_type}-{days_ago}"
    
    measurements = [
        {"kind": {"type": "COUNT", "unit": "swipes"}, "value": swipes},
        {"kind": {"type": "COUNT", "unit": "right"}, "value": right},
        {"kind": {"type": "COUNT", "unit": "left"}, "value": left},
    ]
    
    if matches > 0:
        measurements.append({"kind": {"type": "COUNT", "unit": "matches"}, "value": matches})
    if conversations > 0:
        measurements.append({"kind": {"type": "COUNT", "unit": "conversations"}, "value": conversations})
    if dates > 0:
        measurements.append({"kind": {"type": "COUNT", "unit": "dates"}, "value": dates})
    
    tags = ["app", activity_type, "dating"]
    if location:
        tags.append(f"loc:{location}")
    
    cursor.execute('''
    INSERT INTO activities 
    (id, type, occurred_at, note, tags, measurements, goal_mapping, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        activity_id,
        activity_type,
        occurred_at,
        note,
        json.dumps(tags),
        json.dumps(measurements),
        'GOAL-1',
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()


class TestDatingMetrics:
    """Test metric computation."""
    
    def test_metrics_empty_database(self, test_db):
        """Test metrics with no data."""
        monitor = DatingPoolMonitor(test_db, use_api=False)
        metrics = monitor.get_dating_metrics(days=7)
        
        assert metrics.total_swipes == 0
        assert metrics.matches == 0
        assert metrics.match_rate == 0.0
        assert metrics.dates_scheduled == 0
    
    def test_metrics_single_activity(self, test_db):
        """Test metrics with one activity."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=2)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        metrics = monitor.get_dating_metrics(days=7)
        
        assert metrics.total_swipes == 30
        assert metrics.right_swipes == 25
        assert metrics.matches == 2
        assert metrics.match_rate == 0.08  # 2/25
    
    def test_metrics_multiple_activities(self, test_db):
        """Test metrics aggregation across multiple activities."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=2)
        create_dating_activity(test_db, "tinder", days_ago=2, 
                             swipes=20, right=18, left=2, matches=1)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        metrics = monitor.get_dating_metrics(days=7)
        
        assert metrics.total_swipes == 50
        assert metrics.right_swipes == 43
        assert metrics.matches == 3
        assert abs(metrics.match_rate - 0.0698) < 0.001  # 3/43 ≈ 0.0698
    
    def test_metrics_date_filtering(self, test_db):
        """Test that old activities are excluded."""
        create_dating_activity(test_db, "bumble", days_ago=5, 
                             swipes=30, right=25, left=5)
        create_dating_activity(test_db, "bumble", days_ago=10, 
                             swipes=30, right=25, left=5)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        metrics_7d = monitor.get_dating_metrics(days=7)
        metrics_14d = monitor.get_dating_metrics(days=14)
        
        assert metrics_7d.total_swipes == 30
        assert metrics_14d.total_swipes == 60
    
    def test_metrics_location_filtering(self, test_db):
        """Test filtering by location tag."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, location="corralejo")
        create_dating_activity(test_db, "tinder", days_ago=2, 
                             swipes=20, right=18, left=2, location="madrid")
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        metrics_corralejo = monitor.get_dating_metrics(days=7, location="corralejo")
        metrics_madrid = monitor.get_dating_metrics(days=7, location="madrid")
        
        assert metrics_corralejo.total_swipes == 30
        assert metrics_madrid.total_swipes == 20


class TestPoolAlerts:
    """Test alert generation logic."""
    
    def test_healthy_pool_no_alert(self, test_db):
        """Test no alert when pool is healthy."""
        # Good metrics: 10% match rate, 2 dates scheduled
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=3, dates=2)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        alert = monitor.generate_alert()
        
        assert alert is None
    
    def test_yellow_alert_low_match_rate(self, test_db):
        """Test Yellow alert: low match rate in 7 days."""
        # Low match rate: 2% with 50+ swipes, but HAS dates (so not RED)
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=1, dates=1)
        create_dating_activity(test_db, "tinder", days_ago=3, 
                             swipes=20, right=20, left=0, matches=0)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        alert = monitor.generate_alert()
        
        assert alert is not None
        assert alert.status == PoolStatus.THINNING
        assert alert.severity == "warning"
        assert "thinning" in alert.one_liner.lower()
    
    def test_red_alert_no_dates_14d(self, test_db):
        """Test Red alert: no dates in 14 days + low match rate."""
        # 0 dates, 0% match rate over 14 days
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=0, dates=0)
        create_dating_activity(test_db, "tinder", days_ago=8, 
                             swipes=20, right=20, left=0, matches=0, dates=0)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        alert = monitor.generate_alert()
        
        assert alert is not None
        assert alert.status == PoolStatus.DEPLETED
        assert alert.severity == "critical"
        assert "depleted" in alert.one_liner.lower()
        assert "0 dates" in alert.one_liner
    
    def test_critical_alert_location_time(self, test_db):
        """Test Critical alert: Red + 21+ days in location."""
        # Same conditions as Red, but simulate long time in location
        # Create activities spanning 25 days (to get 25 unique dates)
        for days_ago in range(0, 25):
            create_dating_activity(test_db, "bumble", days_ago=days_ago, 
                                 swipes=10, right=8, left=2, matches=0, dates=0,
                                 location="corralejo")
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        days_in_location = monitor.get_days_in_current_location()
        alert = monitor.generate_alert()
        
        assert days_in_location >= 21, f"Expected >=21 days, got {days_in_location}"
        assert alert is not None
        assert alert.status == PoolStatus.CRITICAL
        assert alert.severity == "critical"
        assert "CRITICAL" in alert.one_liner
        assert "relocate" in alert.one_liner.lower()
    
    def test_alert_includes_actions(self, test_db):
        """Test that alerts include actionable buttons."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=0, dates=0)
        create_dating_activity(test_db, "tinder", days_ago=8, 
                             swipes=20, right=20, left=0, matches=0, dates=0)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        alert = monitor.generate_alert()
        
        assert alert is not None
        assert len(alert.actions) > 0
        assert any("flight" in action["text"].lower() for action in alert.actions)
    
    def test_alert_data_table_format(self, test_db):
        """Test alert includes properly formatted data table."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=0)
        create_dating_activity(test_db, "tinder", days_ago=3, 
                             swipes=20, right=20, left=0, matches=0)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        alert = monitor.generate_alert()
        
        assert alert is not None
        assert len(alert.data_table) == 2  # 7d and 14d rows
        assert "period" in alert.data_table[0]
        assert "swipes" in alert.data_table[0]
        assert "match_rate" in alert.data_table[0]


class TestDashboardCard:
    """Test dashboard card generation."""
    
    def test_dashboard_card_healthy(self, test_db):
        """Test card for healthy pool."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=3, dates=1)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        card = monitor.get_dashboard_card()
        
        assert card["status"] == "HEALTHY"
        assert card["severity"] == "info"
        assert "healthy" in card["one_liner"].lower()
        assert len(card["data_table"]) > 0
    
    def test_dashboard_card_depleted(self, test_db):
        """Test card for depleted pool."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5, matches=0, dates=0)
        create_dating_activity(test_db, "tinder", days_ago=8, 
                             swipes=20, right=20, left=0, matches=0, dates=0)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        card = monitor.get_dashboard_card()
        
        assert card["status"] == "DEPLETED"
        assert card["severity"] == "critical"
        assert "depleted" in card["one_liner"].lower()
        assert len(card["actions"]) > 0


class TestLocationTracking:
    """Test location tenure tracking."""
    
    def test_no_location_tags(self, test_db):
        """Test with activities that have no location tags."""
        create_dating_activity(test_db, "bumble", days_ago=1, 
                             swipes=30, right=25, left=5)
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        days = monitor.get_days_in_current_location()
        
        assert days == 0
    
    def test_single_location(self, test_db):
        """Test counting days in single location."""
        for days_ago in range(0, 5):
            create_dating_activity(test_db, "bumble", days_ago=days_ago, 
                                 swipes=10, right=8, left=2, location="corralejo")
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        days = monitor.get_days_in_current_location()
        
        assert days == 5
    
    def test_location_change(self, test_db):
        """Test that counting stops at location change."""
        # Recent activities in Madrid
        for days_ago in range(0, 3):
            create_dating_activity(test_db, "bumble", days_ago=days_ago, 
                                 swipes=10, right=8, left=2, location="madrid")
        
        # Older activities in Corralejo (should not be counted)
        for days_ago in range(4, 10):
            create_dating_activity(test_db, "bumble", days_ago=days_ago, 
                                 swipes=10, right=8, left=2, location="corralejo")
        
        monitor = DatingPoolMonitor(test_db, use_api=False)
        days = monitor.get_days_in_current_location()
        
        assert days == 3  # Only Madrid days


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
