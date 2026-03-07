"""
Tests for Activities Data Bridge
"""

import pytest
import json
import sqlite3
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from activities.bridge import ActivitiesBridge, ACTIVITY_GOAL_MAP


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create activities table
    conn.execute("""
        CREATE TABLE activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT UNIQUE NOT NULL,
            activity_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            occurred_date TEXT NOT NULL,
            duration_minutes INTEGER,
            note TEXT,
            tags TEXT,
            measurements TEXT,
            goal_mapping TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    
    return str(db_path)


@pytest.fixture
def bridge(test_db):
    """Create a bridge instance with test database."""
    return ActivitiesBridge(db_path=test_db)


@pytest.fixture
def mock_api_response():
    """Mock API response with sample activities."""
    return {
        "occurrences": [
            {
                "id": "activity-001",
                "activityType": {"id": "type-001", "name": "bumble"},
                "moment": "2026-03-07T10:00:00Z",
                "note": "no matches, every girl on lanzarote",
                "measurements": [
                    {"type": {"name": "swipes"}, "count": 49}
                ],
                "tags": []
            },
            {
                "id": "activity-002",
                "activityType": {"id": "type-002", "name": "gym"},
                "start": "2026-03-07T08:00:00Z",
                "finish": "2026-03-07T09:30:00Z",
                "note": "Upper body",
                "measurements": [
                    {"type": {"name": "intensity"}, "value": 4}
                ],
                "tags": [{"name": "strength"}]
            },
            {
                "id": "activity-003",
                "activityType": {"id": "type-003", "name": "duo-lingo"},
                "moment": "2026-03-07T07:00:00Z",
                "note": None,
                "measurements": [],
                "tags": [{"name": "spanish"}]
            }
        ]
    }


def test_parse_moment_activity(bridge):
    """Test parsing MOMENT activity (instant event)."""
    occ = {
        "id": "test-001",
        "activityType": {"name": "coffee"},
        "moment": "2026-03-07T09:00:00Z",
        "note": "Morning brew",
        "measurements": [],
        "tags": []
    }
    
    parsed = bridge.parse_occurrence(occ)
    
    assert parsed is not None
    assert parsed["activity_id"] == "test-001"
    assert parsed["activity_type"] == "coffee"
    assert parsed["occurred_at"] == "2026-03-07T09:00:00Z"
    assert parsed["occurred_date"] == "2026-03-07"
    assert parsed["duration_minutes"] is None
    assert parsed["note"] == "Morning brew"
    assert parsed["goal_mapping"] == "Health"


def test_parse_span_activity(bridge):
    """Test parsing SPAN activity (duration-based)."""
    occ = {
        "id": "test-002",
        "activityType": {"name": "gym"},
        "start": "2026-03-07T08:00:00Z",
        "finish": "2026-03-07T09:30:00Z",
        "note": "Leg day",
        "measurements": [
            {"type": {"name": "intensity"}, "value": 5}
        ],
        "tags": [{"name": "strength"}]
    }
    
    parsed = bridge.parse_occurrence(occ)
    
    assert parsed is not None
    assert parsed["duration_minutes"] == 90
    assert parsed["measurements"] == json.dumps({"intensity": 5})
    assert parsed["tags"] == json.dumps(["strength"])


def test_parse_unknown_activity_skipped(bridge):
    """Test that unknown activities are skipped."""
    occ = {
        "id": "test-003",
        "activityType": {"name": "unknown-activity"},
        "moment": "2026-03-07T10:00:00Z",
        "note": "",
        "measurements": [],
        "tags": []
    }
    
    parsed = bridge.parse_occurrence(occ)
    assert parsed is None


def test_goal_mapping(bridge):
    """Test activity-to-goal mapping."""
    activities = [
        ("bumble", "GOAL-1"),
        ("tinder", "GOAL-1"),
        ("duo-lingo", "GOAL-3"),
        ("gym", "Health"),
        ("sauna", "Health"),
    ]
    
    for activity_type, expected_goal in activities:
        occ = {
            "id": f"test-{activity_type}",
            "activityType": {"name": activity_type},
            "moment": "2026-03-07T10:00:00Z",
            "note": "",
            "measurements": [],
            "tags": []
        }
        parsed = bridge.parse_occurrence(occ)
        assert parsed["goal_mapping"] == expected_goal


def test_store_activities_deduplication(bridge, test_db):
    """Test that duplicate activities are not stored twice."""
    occurrences = [
        {
            "id": "dup-001",
            "activityType": {"name": "coffee"},
            "moment": "2026-03-07T09:00:00Z",
            "note": "",
            "measurements": [],
            "tags": []
        }
    ]
    
    # Store once
    count1 = bridge.store_activities(occurrences)
    assert count1 == 1
    
    # Store again (should be deduplicated)
    count2 = bridge.store_activities(occurrences)
    assert count2 == 0
    
    # Verify only 1 row in database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM activities")
    total = cursor.fetchone()[0]
    conn.close()
    assert total == 1


def test_is_first_run(bridge, test_db):
    """Test first run detection."""
    # Initially empty database
    assert bridge.is_first_run() is True
    
    # Add one activity
    conn = sqlite3.connect(test_db)
    conn.execute("""
        INSERT INTO activities (
            activity_id, activity_type, occurred_at, occurred_date, goal_mapping
        ) VALUES ('test-001', 'gym', '2026-03-07T10:00:00Z', '2026-03-07', 'Health')
    """)
    conn.commit()
    conn.close()
    
    # No longer first run
    assert bridge.is_first_run() is False


@patch('activities.bridge.requests.get')
def test_fetch_date_range_success(mock_get, bridge, mock_api_response):
    """Test successful API fetch."""
    mock_response = Mock()
    mock_response.json.return_value = mock_api_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    occurrences = bridge.fetch_date_range("2026-03-01", "2026-03-07")
    
    assert len(occurrences) == 3
    assert occurrences[0]["activityType"]["name"] == "bumble"


@patch('activities.bridge.requests.get')
def test_fetch_date_range_error_handling(mock_get, bridge):
    """Test API error handling."""
    mock_get.side_effect = Exception("Network error")
    
    occurrences = bridge.fetch_date_range("2026-03-01", "2026-03-07")
    
    assert occurrences == []


@patch('activities.bridge.requests.get')
def test_sync_first_run_backfill(mock_get, bridge, test_db, mock_api_response):
    """Test sync on first run does 30-day backfill."""
    mock_response = Mock()
    mock_response.json.return_value = mock_api_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    stats = bridge.sync()
    
    assert stats["new_count"] == 3
    assert "duration_seconds" in stats
    assert "timestamp" in stats
    
    # Verify API was called with 30-day range
    assert mock_get.called
    call_url = mock_get.call_args[0][0]
    assert "/dates/" in call_url


@patch('activities.bridge.requests.get')
def test_sync_subsequent_run_today_only(mock_get, bridge, test_db, mock_api_response):
    """Test sync on subsequent runs fetches only today."""
    # Seed database to mark it as not first run
    conn = sqlite3.connect(test_db)
    conn.execute("""
        INSERT INTO activities (
            activity_id, activity_type, occurred_at, occurred_date, goal_mapping
        ) VALUES ('seed-001', 'gym', '2026-03-01T10:00:00Z', '2026-03-01', 'Health')
    """)
    conn.commit()
    conn.close()
    
    mock_response = Mock()
    mock_response.json.return_value = mock_api_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    stats = bridge.sync()
    
    assert stats["new_count"] == 3
    
    # Verify API was called with today's date (from/to same date)
    call_url = mock_get.call_args[0][0]
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"/dates/{today}/{today}" in call_url
