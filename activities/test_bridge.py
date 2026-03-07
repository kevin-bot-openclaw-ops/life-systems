"""
Tests for Activities Data Bridge
"""

import json
import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from activities.bridge import ActivitiesBridge, ACTIVITY_GOAL_MAP


# Test database path
TEST_DB = Path("/tmp/test_activities.db")


@pytest.fixture
def test_db():
    """Create a test database."""
    # Remove existing test DB
    if TEST_DB.exists():
        TEST_DB.unlink()
    
    # Create database with activities table
    conn = sqlite3.connect(str(TEST_DB))
    conn.executescript("""
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            duration_seconds INTEGER,
            note TEXT,
            tags TEXT,
            measurements TEXT,
            goal_mapping TEXT,
            fetched_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_activities_type ON activities(type);
        CREATE INDEX idx_activities_occurred_at ON activities(occurred_at);
        CREATE INDEX idx_activities_goal ON activities(goal_mapping);
    """)
    conn.commit()
    conn.close()
    
    yield TEST_DB
    
    # Cleanup
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture
def mock_api_response_moment():
    """Mock API response for MOMENT activity (bumble)."""
    return [
        {
            "id": "test-id-1",
            "userId": "test-user",
            "schemaVersion": 1,
            "activityType": "bumble",
            "temporalMark": {
                "type": "MOMENT",
                "at": "2026-03-07T15:19:36.329Z"
            },
            "measurements": [
                {"kind": {"type": "COUNT", "unit": "swipes"}, "value": 29.0},
                {"kind": {"type": "COUNT", "unit": "rigth"}, "value": 24.0},
                {"kind": {"type": "COUNT", "unit": "left"}, "value": 5.0}
            ],
            "tags": ["app", "bumble", "dating"],
            "note": "no matches",
            "reason": None,
            "location": None,
            "recordedAt": "2026-03-07T15:19:37.599917837Z"
        }
    ]


@pytest.fixture
def mock_api_response_span():
    """Mock API response for SPAN activity (yoga)."""
    return [
        {
            "id": "test-id-2",
            "userId": "test-user",
            "schemaVersion": 1,
            "activityType": "uttanasana",
            "temporalMark": {
                "type": "SPAN",
                "start": "2026-03-07T10:24:14.740Z",
                "end": "2026-03-07T10:25:14.740Z",
                "plannedDuration": 60.0,
                "isOpen": False
            },
            "measurements": [
                {"kind": {"type": "INTENSITY", "maxValue": 5}, "value": 3.0},
                {"kind": {"type": "RATING", "maxValue": 5}, "value": 4.0}
            ],
            "tags": [],
            "note": None,
            "reason": None,
            "location": None,
            "recordedAt": "2026-03-07T10:24:16.188426615Z"
        }
    ]


def test_parse_occurrence_moment(test_db):
    """Test parsing a MOMENT activity (point-in-time)."""
    bridge = ActivitiesBridge(db_path=test_db)
    
    occ = {
        "id": "test-1",
        "activityType": "bumble",
        "temporalMark": {
            "type": "MOMENT",
            "at": "2026-03-07T15:19:36.329Z"
        },
        "note": "no matches",
        "tags": ["app", "dating"],
        "measurements": [{"kind": {"type": "COUNT", "unit": "swipes"}, "value": 29.0}]
    }
    
    activity = bridge.parse_occurrence(occ)
    
    assert activity["id"] == "test-1"
    assert activity["type"] == "bumble"
    assert activity["occurred_at"] == "2026-03-07T15:19:36.329Z"
    assert activity["duration_seconds"] is None  # MOMENT has no duration
    assert activity["note"] == "no matches"
    assert activity["goal_mapping"] == "GOAL-1"  # bumble maps to GOAL-1
    assert json.loads(activity["tags"]) == ["app", "dating"]
    assert len(json.loads(activity["measurements"])) == 1


def test_parse_occurrence_span(test_db):
    """Test parsing a SPAN activity (has duration)."""
    bridge = ActivitiesBridge(db_path=test_db)
    
    occ = {
        "id": "test-2",
        "activityType": "uttanasana",
        "temporalMark": {
            "type": "SPAN",
            "start": "2026-03-07T10:24:14.740Z",
            "end": "2026-03-07T10:25:14.740Z",
            "isOpen": False
        },
        "note": None,
        "tags": [],
        "measurements": []
    }
    
    activity = bridge.parse_occurrence(occ)
    
    assert activity["id"] == "test-2"
    assert activity["type"] == "uttanasana"
    assert activity["occurred_at"] == "2026-03-07T10:24:14.740Z"
    assert activity["duration_seconds"] == 60  # 1 minute span
    assert activity["goal_mapping"] == "Health"  # yoga maps to Health


def test_store_activities(test_db):
    """Test storing activities in database."""
    bridge = ActivitiesBridge(db_path=test_db)
    
    activities = [
        {
            "id": "act-1",
            "type": "gym",
            "occurred_at": "2026-03-07T08:00:00Z",
            "duration_seconds": 3600,
            "note": "Heavy legs",
            "tags": json.dumps(["workout"]),
            "measurements": json.dumps([]),
            "goal_mapping": "Health",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        },
        {
            "id": "act-2",
            "type": "coffee",
            "occurred_at": "2026-03-07T09:00:00Z",
            "duration_seconds": None,
            "note": None,
            "tags": json.dumps([]),
            "measurements": json.dumps([]),
            "goal_mapping": "Health",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    ]
    
    inserted = bridge.store_activities(activities)
    
    assert inserted == 2
    
    # Verify in database
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM activities")
    count = cursor.fetchone()[0]
    assert count == 2
    
    cursor.execute("SELECT type, goal_mapping FROM activities ORDER BY occurred_at")
    rows = cursor.fetchall()
    assert rows[0] == ("gym", "Health")
    assert rows[1] == ("coffee", "Health")
    conn.close()


def test_store_activities_deduplication(test_db):
    """Test that duplicate activities (same ID) are not inserted twice."""
    bridge = ActivitiesBridge(db_path=test_db)
    
    activity = {
        "id": "duplicate-test",
        "type": "walking",
        "occurred_at": "2026-03-07T12:00:00Z",
        "duration_seconds": 1800,
        "note": "Beach walk",
        "tags": json.dumps([]),
        "measurements": json.dumps([]),
        "goal_mapping": "Health",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
    
    # Insert once
    inserted = bridge.store_activities([activity])
    assert inserted == 1
    
    # Try to insert again (should be deduplicated)
    inserted = bridge.store_activities([activity])
    assert inserted == 0  # No new inserts
    
    # Verify only 1 row in database
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM activities WHERE id = 'duplicate-test'")
    count = cursor.fetchone()[0]
    assert count == 1
    conn.close()


def test_activity_goal_mapping():
    """Test that all activity types map to correct goals."""
    assert ACTIVITY_GOAL_MAP["bumble"] == "GOAL-1"
    assert ACTIVITY_GOAL_MAP["tinder"] == "GOAL-1"
    assert ACTIVITY_GOAL_MAP["duo-lingo"] == "GOAL-3"
    assert ACTIVITY_GOAL_MAP["gym"] == "Health"
    assert ACTIVITY_GOAL_MAP["coffee"] == "Health"
    assert ACTIVITY_GOAL_MAP["uttanasana"] == "Health"


def test_is_first_run(test_db):
    """Test first run detection."""
    bridge = ActivitiesBridge(db_path=test_db)
    
    # Empty database = first run
    assert bridge.is_first_run() is True
    
    # Insert one activity
    activity = {
        "id": "test-first-run",
        "type": "coffee",
        "occurred_at": "2026-03-07T08:00:00Z",
        "duration_seconds": None,
        "note": None,
        "tags": json.dumps([]),
        "measurements": json.dumps([]),
        "goal_mapping": "Health",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
    bridge.store_activities([activity])
    
    # No longer first run
    assert bridge.is_first_run() is False


@patch('activities.bridge.requests.get')
def test_fetch_date_success(mock_get, test_db, mock_api_response_moment):
    """Test fetching activities for a specific date."""
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = mock_api_response_moment
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    bridge = ActivitiesBridge(db_path=test_db)
    occurrences = bridge.fetch_date("2026-03-07")
    
    assert len(occurrences) == 1
    assert occurrences[0]["activityType"] == "bumble"
    
    # Verify API was called with correct URL
    expected_url = f"{bridge.base_url}/shared/{bridge.share_token}/occurrences/dates/2026-03-07"
    mock_get.assert_called_once_with(expected_url, timeout=30)


@patch('activities.bridge.requests.get')
def test_fetch_date_api_error(mock_get, test_db):
    """Test handling of API errors."""
    import requests
    
    # Mock API error
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_get.return_value = mock_response
    
    bridge = ActivitiesBridge(db_path=test_db)
    
    with pytest.raises(requests.HTTPError):
        bridge.fetch_date("2026-03-07")


@patch('activities.bridge.requests.get')
def test_sync_today_success(mock_get, test_db, mock_api_response_moment):
    """Test syncing today's activities."""
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = mock_api_response_moment
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    bridge = ActivitiesBridge(db_path=test_db)
    stats = bridge.sync_today()
    
    assert stats["success"] is True
    assert stats["activities_fetched"] == 1
    assert stats["activities_new"] == 1
    assert stats["error"] is None
    assert "duration_seconds" in stats


@patch('activities.bridge.requests.get')
def test_sync_today_api_error(mock_get, test_db):
    """Test sync_today with API error."""
    import requests
    
    # Mock API error
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_get.return_value = mock_response
    
    bridge = ActivitiesBridge(db_path=test_db)
    stats = bridge.sync_today()
    
    assert stats["success"] is False
    assert stats["activities_fetched"] == 0
    assert stats["activities_new"] == 0
    assert "500 Server Error" in stats["error"]


@patch('activities.bridge.requests.get')
def test_backfill(mock_get, test_db, mock_api_response_span):
    """Test backfilling 30 days of activities."""
    # Create 10 unique activities (different IDs to avoid deduplication)
    activities = []
    for i in range(10):
        act = mock_api_response_span[0].copy()
        act["id"] = f"test-id-{i}"  # Unique ID for each
        activities.append(act)
    
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = activities
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    bridge = ActivitiesBridge(db_path=test_db)
    stats = bridge.backfill(days=30)
    
    assert stats["success"] is True
    assert stats["activities_fetched"] == 10
    assert stats["activities_new"] == 10
    assert "from_date" in stats
    assert "to_date" in stats
    assert "duration_seconds" in stats
