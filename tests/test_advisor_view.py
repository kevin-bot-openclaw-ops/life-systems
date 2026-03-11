"""
Tests for Advisor View - ACT-M1-1
"""
import pytest
import sqlite3
from datetime import datetime, timedelta
from database.advisor_view import (
    build_health_optimizer_view,
    build_dating_intelligence_view,
    calculate_t_optimization_score,
    calculate_morning_routine_adherence,
    calculate_exercise_streak,
    calculate_stress_trend,
    get_advisor_view
)


@pytest.fixture
def test_db():
    """Create test database with sample data."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Create activities table
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
    
    # Create dates table
    conn.execute("""
        CREATE TABLE dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            who TEXT NOT NULL,
            source TEXT NOT NULL,
            quality INTEGER NOT NULL,
            went_well TEXT,
            improve TEXT,
            date_of TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create cities table
    conn.execute("""
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            is_current INTEGER DEFAULT 0,
            dating_pool INTEGER,
            ai_job_density INTEGER,
            cost_index REAL,
            lifestyle_score REAL,
            community_score REAL,
            composite_score REAL,
            data_source TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert sample activities
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    
    activities = [
        # Today: sun + gym + sauna (score = 2+2+1 = 5)
        ('act1', 'sun-exposure', f'{today}T12:00:00Z', 1200, '', '[]'),
        ('act2', 'gym', f'{today}T07:00:00Z', 2700, '', '[]'),
        ('act3', 'sauna', f'{today}T20:00:00Z', 1200, '', '[]'),
        # Yesterday: yoga + walk before 11am (complete morning routine)
        ('act4', 'yoga', f'{yesterday}T08:30:00Z', 900, '', '[]'),
        ('act5', 'walking', f'{yesterday}T09:00:00Z', 1200, '', '[]'),
    ]
    
    for act_id, act_type, occurred, duration, note, tags in activities:
        conn.execute("""
            INSERT INTO activities (id, type, occurred_at, duration_seconds, note, tags, goal_mapping, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Health', ?)
        """, (act_id, act_type, occurred, duration, note, tags, datetime.now().isoformat()))
    
    # Insert sample dates
    dates = [
        ('Alice', 'app', 8, today),
        ('Bob', 'social', 6, yesterday),
    ]
    
    for who, source, quality, date_of in dates:
        conn.execute("""
            INSERT INTO dates (who, source, quality, went_well, improve, date_of)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (who, source, quality, '', '', date_of))
    
    # Insert sample cities
    cities = [
        ('Berlin', 'Germany', 0, 12000, 150),
        ('Madrid', 'Spain', 0, 8000, 120),
        ('Fuerteventura', 'Spain', 1, 200, 2),
    ]
    
    for name, country, is_current, dating_pool, ai_jobs in cities:
        conn.execute("""
            INSERT INTO cities (name, country, is_current, dating_pool, ai_job_density)
            VALUES (?, ?, ?, ?, ?)
        """, (name, country, is_current, dating_pool, ai_jobs))
    
    conn.commit()
    yield conn
    conn.close()


def test_t_optimization_score_calculation(test_db):
    """Test T-optimization score calculation."""
    today = datetime.now().date().isoformat()
    result = calculate_t_optimization_score(test_db, today)
    
    assert result['score'] == 5  # sun(2) + gym(2) + sauna(1) = 5
    assert result['max_score'] == 10
    assert result['breakdown']['sun'] == 2
    assert result['breakdown']['exercise'] == 2
    assert result['breakdown']['sauna'] == 1
    assert 'cold' in result['missing_items']
    assert 'sleep' in result['missing_items']
    assert len(result['sparkline']) == 7


def test_morning_routine_adherence(test_db):
    """Test morning routine adherence calculation."""
    result = calculate_morning_routine_adherence(test_db)
    
    # Yesterday had complete routine (yoga + walk before 11am)
    assert result['complete_days'] >= 1
    assert result['total_days'] == 7
    assert result['adherence_pct'] >= 0
    assert 'yoga' in result['today_status']
    assert 'walk' in result['today_status']


def test_exercise_streak(test_db):
    """Test exercise streak calculation."""
    result = calculate_exercise_streak(test_db)
    
    assert 'current_streak' in result
    assert 'personal_best' in result
    assert result['personal_best'] >= result['current_streak']


def test_stress_trend(test_db):
    """Test stress trend calculation."""
    result = calculate_stress_trend(test_db)
    
    assert result['trend'] in ['stable', 'escalating', 'improving']
    assert len(result['chart_data']) == 14
    assert 'recommendations' in result


def test_health_optimizer_view(test_db):
    """Test complete health optimizer view."""
    result = build_health_optimizer_view(test_db)
    
    assert result['section'] == 'health_optimizer'
    assert result['goal_ref'] == 'Health (all goals)'
    assert 'one_liner' in result
    assert 't_score' in result
    assert 'morning_routine' in result
    assert 'exercise_streak' in result
    assert 'stress_trend' in result
    assert 'actions' in result
    assert len(result['actions']) <= 3  # Max 3 per ADR-005


def test_dating_intelligence_view(test_db):
    """Test dating intelligence view."""
    result = build_dating_intelligence_view(test_db)
    
    assert result['section'] == 'dating_intelligence'
    assert result['goal_ref'] == 'GOAL-1 (find partner)'
    assert 'one_liner' in result
    assert 'pool_status' in result
    assert 'actions' in result
    assert len(result['actions']) <= 3


def test_full_advisor_view(test_db):
    """Test complete advisor view (integration test)."""
    # Mock get_db to return test_db
    import database.advisor_view as av
    original_get_db = av.get_db
    av.get_db = lambda: test_db
    
    try:
        result = get_advisor_view()
        
        assert 'advisor' in result
        assert 'timestamp' in result
        assert 'health_optimizer' in result['advisor']
        assert 'dating_intelligence' in result['advisor']
        
        # Check health section
        health = result['advisor']['health_optimizer']
        assert health['t_score']['score'] == 5
        assert len(health['actions']) >= 1
        
        # Check dating section
        dating = result['advisor']['dating_intelligence']
        assert 'pool_status' in dating
        
    finally:
        av.get_db = original_get_db


def test_one_liner_format_adheres_to_adr005(test_db):
    """Test one-liner follows ADR-005 motivation-first format."""
    result = build_health_optimizer_view(test_db)
    
    one_liner = result['one_liner']
    
    # Should be concise (max 120 chars per ADR-005)
    assert len(one_liner) <= 120
    
    # Should reference a goal or metric
    assert any(word in one_liner.lower() for word in ['score', 't-', 'streak', 'consistent', 'day'])
    
    # Should not be generic motivational fluff
    assert 'keep going' not in one_liner.lower()
    assert 'you got this' not in one_liner.lower()


def test_empty_state_handling(test_db):
    """Test empty state when no data exists."""
    # Clear all activities
    test_db.execute("DELETE FROM activities")
    test_db.commit()
    
    result = build_health_optimizer_view(test_db)
    
    # Should still return valid structure
    assert result['t_score']['score'] == 0
    assert result['morning_routine']['adherence_pct'] == 0
    assert result['exercise_streak']['current_streak'] == 0
    
    # One-liner should be meaningful even with no data
    assert len(result['one_liner']) > 0
    assert 'prioritize' in result['one_liner'].lower() or 'missing' in result['one_liner'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
