"""
Tests for Daily Activities Digest Generator
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import date, datetime, timedelta
from activities.digest import DailyDigest


@pytest.fixture
def temp_db():
    """Create temporary database with activities table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    db_path = Path(path)
    
    # Create schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
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
        )
    """)
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    db_path.unlink()


def insert_activity(db_path, activity_id, activity_type, occurred_at, goal_mapping, 
                   duration_seconds=None, note=None):
    """Helper to insert test activity."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO activities (id, type, occurred_at, duration_seconds, note, 
                               goal_mapping, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (activity_id, activity_type, occurred_at, duration_seconds, note, 
          goal_mapping, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def test_empty_digest(temp_db):
    """Test digest with no activities."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    assert one_liner == "No activities logged today. Everything okay?"
    assert len(data_table) == 1  # Header only
    assert data_table[0] == ["Activity Type", "Count", "Duration", "Goal", "Key Notes"]
    assert len(anomalies) == 0


def test_single_activity_digest(temp_db):
    """Test digest with single activity."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    
    # Insert single activity
    insert_activity(
        temp_db,
        "act-001",
        "gym",
        target_date.isoformat() + "T10:30:00Z",
        "Health",
        duration_seconds=3600,
        note="Heavy squats"
    )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    assert "1 activities" in one_liner
    assert "Health" in one_liner
    assert len(data_table) == 2  # Header + 1 row
    assert data_table[1][0] == "gym"
    assert data_table[1][1] == "1"  # Count
    assert data_table[1][2] == "60m"  # Duration
    assert data_table[1][3] == "Health"


def test_mixed_goals_digest(temp_db):
    """Test digest with activities across multiple goals."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    base_time = target_date.isoformat()
    
    # Insert activities for different goals
    insert_activity(temp_db, "act-001", "bumble", f"{base_time}T09:00:00Z", "GOAL-1", 
                   note="no matches")
    insert_activity(temp_db, "act-002", "tinder", f"{base_time}T09:15:00Z", "GOAL-1", 
                   note="2 matches")
    insert_activity(temp_db, "act-003", "gym", f"{base_time}T10:00:00Z", "Health", 
                   duration_seconds=3600)
    insert_activity(temp_db, "act-004", "duo-lingo", f"{base_time}T14:00:00Z", "GOAL-3")
    insert_activity(temp_db, "act-005", "duo-lingo", f"{base_time}T20:00:00Z", "GOAL-3")
    insert_activity(temp_db, "act-006", "walking", f"{base_time}T18:00:00Z", "Health", 
                   duration_seconds=1800)
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should mention all goals
    assert "6 activities" in one_liner
    assert "GOAL-1" in one_liner
    assert "GOAL-3" in one_liner
    assert "Health" in one_liner
    
    # Should have 5 rows (header + bumble, tinder, gym, duo-lingo, walking)
    assert len(data_table) == 6
    
    # Verify grouping (duo-lingo should be count=2)
    duo_lingo_row = [row for row in data_table if row[0] == "duo-lingo"][0]
    assert duo_lingo_row[1] == "2"  # Count


def test_dating_app_summary(temp_db):
    """Test dating app activity summary."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    base_time = target_date.isoformat()
    
    # Insert dating app activities
    insert_activity(temp_db, "act-001", "bumble", f"{base_time}T09:00:00Z", "GOAL-1", 
                   note="no matches, every girl on lanzarote")
    insert_activity(temp_db, "act-002", "tinder", f"{base_time}T09:30:00Z", "GOAL-1", 
                   note="3 swipes")
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should include app counts and match status
    assert "GOAL-1" in one_liner
    assert "Bumble" in one_liner or "bumble" in one_liner.lower()
    assert "Tinder" in one_liner or "tinder" in one_liner.lower()
    assert "0 matches" in one_liner or "no match" in anomalies[0].lower()


def test_spanish_learning_summary(temp_db):
    """Test Spanish learning (GOAL-3) summary."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    base_time = target_date.isoformat()
    
    # Insert 3 duo-lingo sessions
    for i in range(3):
        insert_activity(
            temp_db, 
            f"act-00{i+1}", 
            "duo-lingo", 
            f"{base_time}T{10+i*2:02d}:00:00Z", 
            "GOAL-3"
        )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should mention Spanish lessons
    assert "GOAL-3" in one_liner
    assert "3 Spanish lesson" in one_liner


def test_exercise_streak_detection(temp_db):
    """Test detection of exercise streaks."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    
    # Insert gym sessions for past 4 days (including today)
    for i in range(4):
        day = target_date - timedelta(days=i)
        insert_activity(
            temp_db,
            f"gym-{i}",
            "gym",
            f"{day.isoformat()}T10:00:00Z",
            "Health",
            duration_seconds=3600
        )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should detect streak
    assert any("gym streak" in a.lower() for a in anomalies)
    assert any("4-day" in a for a in anomalies)


def test_broken_streak_detection(temp_db):
    """Test detection of broken streaks."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    
    # Insert gym sessions for past 3 days (NOT including today)
    for i in range(1, 4):
        day = target_date - timedelta(days=i)
        insert_activity(
            temp_db,
            f"gym-{i}",
            "gym",
            f"{day.isoformat()}T10:00:00Z",
            "Health",
            duration_seconds=3600
        )
    
    # Add non-gym activity today
    insert_activity(
        temp_db,
        "walk-today",
        "walking",
        f"{target_date.isoformat()}T10:00:00Z",
        "Health",
        duration_seconds=1800
    )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should detect broken streak
    assert any("No gym" in a and "streak broken" in a for a in anomalies)


def test_first_occurrence_detection(temp_db):
    """Test detection of first occurrence after long gap."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    
    # Insert sauna 10 days ago
    past_date = target_date - timedelta(days=10)
    insert_activity(
        temp_db,
        "sauna-past",
        "sauna",
        f"{past_date.isoformat()}T18:00:00Z",
        "Health",
        duration_seconds=1800
    )
    
    # Insert sauna today
    insert_activity(
        temp_db,
        "sauna-today",
        "sauna",
        f"{target_date.isoformat()}T18:00:00Z",
        "Health",
        duration_seconds=1800
    )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should detect first occurrence after gap
    assert any("First sauna" in a and "10 days" in a for a in anomalies)


def test_excessive_coffee_warning(temp_db):
    """Test warning for excessive coffee consumption."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    base_time = target_date.isoformat()
    
    # Insert 3 coffee activities
    for i in range(3):
        insert_activity(
            temp_db,
            f"coffee-{i+1}",
            "coffee",
            f"{base_time}T{8+i*2:02d}:00:00Z",
            "Health"
        )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Should warn about coffee
    assert any("coffee" in a.lower() and "sleep" in a.lower() for a in anomalies)


def test_slack_formatting(temp_db):
    """Test Slack markdown formatting."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    base_time = target_date.isoformat()
    
    # Insert some activities
    insert_activity(temp_db, "act-001", "gym", f"{base_time}T10:00:00Z", "Health", 
                   duration_seconds=3600)
    insert_activity(temp_db, "act-002", "duo-lingo", f"{base_time}T14:00:00Z", "GOAL-3")
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    slack_message = digest.format_for_slack(one_liner, data_table, anomalies)
    
    # Should have bold one-liner
    assert one_liner in slack_message
    assert "*" in slack_message  # Slack bold formatting
    
    # Should have code block for table
    assert "```" in slack_message
    
    # Should have Activity Type header
    assert "Activity Type" in slack_message


def test_duration_aggregation(temp_db):
    """Test duration aggregation for same activity type."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    base_time = target_date.isoformat()
    
    # Insert 2 walking sessions with durations
    insert_activity(temp_db, "walk-1", "walking", f"{base_time}T08:00:00Z", "Health", 
                   duration_seconds=1800)  # 30 min
    insert_activity(temp_db, "walk-2", "walking", f"{base_time}T18:00:00Z", "Health", 
                   duration_seconds=2400)  # 40 min
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Find walking row
    walking_row = [row for row in data_table if row[0] == "walking"][0]
    
    assert walking_row[1] == "2"  # Count
    assert walking_row[2] == "70m"  # Total duration (30 + 40)


def test_note_truncation(temp_db):
    """Test that long notes are truncated."""
    digest = DailyDigest(temp_db)
    target_date = date.today()
    
    long_note = "This is a very long note that should be truncated because it exceeds forty characters"
    
    insert_activity(
        temp_db,
        "act-001",
        "bumble",
        f"{target_date.isoformat()}T09:00:00Z",
        "GOAL-1",
        note=long_note
    )
    
    one_liner, data_table, anomalies = digest.generate_digest(target_date)
    
    # Find bumble row
    bumble_row = [row for row in data_table if row[0] == "bumble"][0]
    note_cell = bumble_row[4]
    
    # Note should be truncated to 40 chars
    assert len(note_cell) <= 40


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
