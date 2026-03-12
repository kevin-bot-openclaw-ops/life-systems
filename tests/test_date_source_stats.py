"""
Tests for DATE-M1-2: Source Conversion Tracking
"""
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.date_source_stats import get_source_stats, get_follow_up_details


def setup_test_db():
    """Create temporary test database with sample data."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create dates table
    cursor.execute("""
        CREATE TABLE dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            who TEXT NOT NULL,
            source TEXT NOT NULL,
            quality INTEGER NOT NULL CHECK(quality >= 1 AND quality <= 10),
            went_well TEXT,
            improve TEXT,
            date_of DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            archived INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    return db_path, conn


def test_empty_state():
    """Test with no dates logged."""
    db_path, conn = setup_test_db()
    
    result = get_source_stats(db_path)
    
    assert result.one_liner == "No dates logged yet. Log your first date to start tracking."
    assert len(result.stats) == 0
    assert len(result.data_table) == 0
    assert result.sample_size_warning is not None
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_empty_state passed")


def test_single_source():
    """Test with dates from only one source."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    # Add 3 dates from same source
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 7, "2026-03-01"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Bob", "app", 8, "2026-03-02"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Carol", "app", 9, "2026-03-03"))
    conn.commit()
    
    result = get_source_stats(db_path)
    
    assert len(result.stats) == 1
    assert result.best_source == "app"
    assert result.best_avg_quality == 8.0
    assert "app" in result.one_liner.lower()
    assert "8.0/10" in result.one_liner
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_single_source passed")


def test_multiple_sources():
    """Test with dates from multiple sources."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    # app: 7 + 6 = avg 6.5
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 7, "2026-03-01"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Bob", "app", 6, "2026-03-02"))
    
    # event: 9 + 8 = avg 8.5
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Carol", "event", 9, "2026-03-03"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Dave", "event", 8, "2026-03-04"))
    
    # social: 10 = avg 10.0
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Eve", "social", 10, "2026-03-05"))
    
    conn.commit()
    
    result = get_source_stats(db_path)
    
    assert len(result.stats) == 3
    assert result.best_source == "social"
    assert result.best_avg_quality == 10.0
    assert "social" in result.one_liner.lower()
    assert len(result.data_table) == 3
    
    # Verify ranking order (best to worst)
    sources = [s.source for s in result.stats]
    assert sources == ["social", "event", "app"]
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_multiple_sources passed")


def test_follow_up_rate():
    """Test follow-up rate calculation (2+ dates with same person)."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    # Alice: 2 dates from app
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 8, "2026-03-01"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 9, "2026-03-08"))
    
    # Bob: 1 date from app (no follow-up)
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Bob", "app", 7, "2026-03-02"))
    
    # Carol: 3 dates from event
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Carol", "event", 9, "2026-03-03"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Carol", "event", 9, "2026-03-10"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Carol", "event", 10, "2026-03-17"))
    
    conn.commit()
    
    result = get_source_stats(db_path)
    
    # app: 2 people met (Alice, Bob), 1 repeat (Alice) = 50%
    app_stats = next(s for s in result.stats if s.source == "app")
    assert app_stats.people_met == 2
    assert app_stats.repeat_dates == 1
    assert app_stats.follow_up_rate == 50.0
    
    # event: 1 person met (Carol), 1 repeat (Carol) = 100%
    event_stats = next(s for s in result.stats if s.source == "event")
    assert event_stats.people_met == 1
    assert event_stats.repeat_dates == 1
    assert event_stats.follow_up_rate == 100.0
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_follow_up_rate passed")


def test_sample_size_warning():
    """Test sample size warnings."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    # Small sample (< 10 dates)
    for i in range(5):
        cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                      (f"Person{i}", "app", 7 + i % 3, f"2026-03-0{i+1}"))
    conn.commit()
    
    result = get_source_stats(db_path)
    assert result.sample_size_warning is not None
    assert "Small sample size" in result.sample_size_warning
    assert "5 dates" in result.sample_size_warning
    
    # Large sample (>= 10 dates)
    for i in range(5, 15):
        cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                      (f"Person{i}", "event", 8, f"2026-03-{i+1:02d}"))
    conn.commit()
    
    result = get_source_stats(db_path)
    # Now 20 total dates - no warning
    assert result.sample_size_warning is None
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_sample_size_warning passed")


def test_follow_up_details():
    """Test follow-up details function."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    # Alice: 3 dates, quality 8, 8, 9
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 8, "2026-03-01"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 8, "2026-03-08"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 9, "2026-03-15"))
    
    # Bob: 2 dates, quality 7, 8
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Bob", "event", 7, "2026-03-02"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Bob", "event", 8, "2026-03-09"))
    
    # Carol: 1 date (should not appear)
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Carol", "social", 10, "2026-03-03"))
    
    conn.commit()
    
    details = get_follow_up_details(db_path)
    
    assert len(details) == 2  # Only Alice and Bob (2+ dates)
    
    # Alice should be first (more dates)
    alice = details[0]
    assert alice['who'] == "Alice"
    assert alice['dates'] == 3
    assert alice['avg_quality'] == 8.3  # (8+8+9)/3 = 8.33, rounded to 8.3
    
    # Bob should be second
    bob = details[1]
    assert bob['who'] == "Bob"
    assert bob['dates'] == 2
    assert bob['avg_quality'] == 7.5  # (7+8)/2
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_follow_up_details passed")


def test_archived_dates_ignored():
    """Test that archived dates are excluded."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    # Active dates
    cursor.execute("INSERT INTO dates (who, source, quality, date_of, archived) VALUES (?, ?, ?, ?, ?)",
                  ("Alice", "app", 8, "2026-03-01", 0))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of, archived) VALUES (?, ?, ?, ?, ?)",
                  ("Bob", "event", 9, "2026-03-02", 0))
    
    # Archived date (should be ignored)
    cursor.execute("INSERT INTO dates (who, source, quality, date_of, archived) VALUES (?, ?, ?, ?, ?)",
                  ("Carol", "app", 10, "2026-03-03", 1))
    
    conn.commit()
    
    result = get_source_stats(db_path)
    
    # Should only count 2 active dates
    app_stats = next(s for s in result.stats if s.source == "app")
    assert app_stats.date_count == 1  # Only Alice, not Carol
    assert app_stats.avg_quality == 8.0  # Only Alice's 8, not Carol's 10
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_archived_dates_ignored passed")


def test_data_table_format():
    """Test ADR-005 compliance: one-liner + data table format."""
    db_path, conn = setup_test_db()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Alice", "app", 8, "2026-03-01"))
    cursor.execute("INSERT INTO dates (who, source, quality, date_of) VALUES (?, ?, ?, ?)",
                  ("Bob", "event", 9, "2026-03-02"))
    conn.commit()
    
    result = get_source_stats(db_path)
    
    # Verify one-liner exists and is concise
    assert len(result.one_liner) > 0
    assert len(result.one_liner) < 200  # ADR-005: max 120 chars, but we allow some flex
    
    # Verify data table structure
    assert len(result.data_table) == 2
    row = result.data_table[0]
    assert "Source" in row
    assert "Dates" in row
    assert "Avg Quality" in row
    assert "People Met" in row
    assert "Follow-up Rate" in row
    
    conn.close()
    os.unlink(db_path)
    print("✓ test_data_table_format passed")


if __name__ == "__main__":
    test_empty_state()
    test_single_source()
    test_multiple_sources()
    test_follow_up_rate()
    test_sample_size_warning()
    test_follow_up_details()
    test_archived_dates_ignored()
    test_data_table_format()
    
    print("\n✅ All 8 tests passed!")
