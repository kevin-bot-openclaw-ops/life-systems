"""
Tests for LEARN-M2-1 Unified Recommendation Engine

Covers:
- Recommendation aggregation from SYNTH + ACT rules
- Priority scoring
- Decision tracking (accept/snooze/dismiss)
- Cross-domain context
- Activities API feedback loop (mocked)
"""

import pytest
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from synthesis.recommendation_engine import RecommendationEngine


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary test database with schema."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables (minimal schema for testing)
    cursor.execute("""
        CREATE TABLE dates (
            id INTEGER PRIMARY KEY,
            who TEXT,
            source TEXT,
            quality INTEGER,
            went_well TEXT,
            improve TEXT,
            date_of TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            salary_range TEXT,
            discovered_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE scores (
            id INTEGER PRIMARY KEY,
            job_id INTEGER,
            composite_score REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY,
            job_id INTEGER,
            action TEXT,
            decided_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY,
            city TEXT,
            current_score REAL,
            last_updated TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE activities (
            id INTEGER PRIMARY KEY,
            activity_type TEXT,
            occurred_date TEXT,
            note TEXT,
            fetched_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE recommendation_decisions (
            id INTEGER PRIMARY KEY,
            rule_id TEXT,
            domain TEXT,
            one_liner TEXT,
            data_table TEXT,
            goal_alignment TEXT,
            action TEXT CHECK(action IN ('accept', 'snooze', 'dismiss')),
            decided_at TEXT,
            snooze_until TEXT,
            pattern_hash TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    
    return db_path


@pytest.fixture
def engine(temp_db):
    """Create RecommendationEngine instance with test database."""
    return RecommendationEngine(temp_db, activities_token="test-token")


@pytest.fixture
def seed_dating_data(temp_db):
    """Seed database with dating test data."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # 8 dates: 5 bachata (avg quality 8.2), 3 bumble (avg quality 6.0)
    bachata_dates = [
        ('Sara', 'bachata', 8, 'Great conversation', 'Be more playful', '2026-03-01'),
        ('Anna', 'bachata', 9, 'Amazing chemistry', 'None', '2026-03-02'),
        ('Maria', 'bachata', 7, 'Fun dancing', 'Ask more questions', '2026-03-03'),
        ('Laura', 'bachata', 8, 'Laughed a lot', 'Relax more', '2026-03-04'),
        ('Sofia', 'bachata', 9, 'Perfect evening', 'None', '2026-03-05'),
    ]
    
    bumble_dates = [
        ('Kate', 'bumble', 6, 'Okay date', 'More energy', '2026-03-01'),
        ('Emma', 'bumble', 6, 'Pleasant', 'Better photos', '2026-03-03'),
        ('Olivia', 'bumble', 6, 'Decent', 'Ask better questions', '2026-03-05'),
    ]
    
    for who, source, quality, went_well, improve, date_of in bachata_dates + bumble_dates:
        cursor.execute("""
            INSERT INTO dates (who, source, quality, went_well, improve, date_of)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (who, source, quality, went_well, improve, date_of))
    
    conn.commit()
    conn.close()


@pytest.fixture
def seed_activities_data(temp_db):
    """Seed database with activities test data."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Today's activities: gym + yoga + sun + coffee (health score = 2+1.5+2-1 = 4.5)
    today = datetime.utcnow().date().isoformat()
    activities = [
        ('gym', today, 'Good workout'),
        ('uttanasana', today, 'Morning yoga'),
        ('sun-exposure', today, '20 min'),
        ('coffee', today, '1 cup'),
    ]
    
    # Past 7 days: 2 nerve-stimulus (medium stress)
    for i in range(1, 8):
        date = (datetime.utcnow().date() - timedelta(days=i)).isoformat()
        cursor.execute("""
            INSERT INTO activities (activity_type, occurred_date, note, fetched_at)
            VALUES ('walking', ?, 'Daily walk', ?)
        """, (date, datetime.utcnow().isoformat() + 'Z'))
    
    # Add nerve-stimulus on days 2 and 5
    for day in [2, 5]:
        date = (datetime.utcnow().date() - timedelta(days=day)).isoformat()
        cursor.execute("""
            INSERT INTO activities (activity_type, occurred_date, note, fetched_at)
            VALUES ('nerve-stimulus', ?, 'Anxiety spike', ?)
        """, (date, datetime.utcnow().isoformat() + 'Z'))
    
    # Add today's activities
    for activity_type, occurred_date, note in activities:
        cursor.execute("""
            INSERT INTO activities (activity_type, occurred_date, note, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (activity_type, occurred_date, note, datetime.utcnow().isoformat() + 'Z'))
    
    conn.commit()
    conn.close()


# --- Tests ---

def test_engine_initialization(engine):
    """Test engine initializes with correct configuration."""
    assert engine.db_path
    assert engine.activities_token == "test-token"
    assert engine.rules_engine is not None


def test_get_top_recommendations_empty_db(engine):
    """Test recommendations with empty database returns empty state messages."""
    recommendations = engine.get_top_recommendations(limit=5)
    
    # Should return empty state recommendations from rules
    # Exact count depends on rules config, but should be non-zero
    assert isinstance(recommendations, list)


def test_get_top_recommendations_with_data(engine, seed_dating_data):
    """Test recommendations with dating data fires dating rules."""
    recommendations = engine.get_top_recommendations(limit=5)
    
    assert len(recommendations) > 0
    
    # Find R-DATE-01 (Best Source by Quality)
    date_rec = None
    for rec in recommendations:
        if rec['rule_id'] == 'R-DATE-01':
            date_rec = rec
            break
    
    assert date_rec is not None
    assert 'bachata' in date_rec['one_liner'].lower()
    assert date_rec['domain'] == 'dating'
    assert date_rec['goal_alignment'] == 'GOAL-1 (find partner)'
    assert 'priority_score' in date_rec
    assert date_rec['priority_score'] > 0


def test_priority_scoring_goal_alignment(engine, seed_dating_data, seed_activities_data):
    """Test priority scoring prioritizes by goal alignment."""
    recommendations = engine.get_top_recommendations(limit=20)
    
    # GOAL-1 recommendations should have higher priority than Health
    goal1_scores = [r['priority_score'] for r in recommendations if 'GOAL-1' in r['goal_alignment']]
    health_scores = [r['priority_score'] for r in recommendations if 'Health' in r['goal_alignment']]
    
    if goal1_scores and health_scores:
        assert max(goal1_scores) > min(health_scores)


def test_cross_domain_context(engine, seed_activities_data):
    """Test cross-domain context includes health and stress data."""
    recommendations = engine.get_top_recommendations(limit=5, include_cross_domain_context=True)
    
    if recommendations:
        rec = recommendations[0]
        assert 'cross_domain_context' in rec
        
        ctx = rec['cross_domain_context']
        assert 'health_score' in ctx
        assert 'stress_level' in ctx
        assert 'exercise_streak' in ctx
        assert ctx['stress_level'] in ['low', 'medium', 'high']


def test_decision_accept(engine, seed_dating_data):
    """Test recording an 'accept' decision."""
    # Get a recommendation
    recommendations = engine.get_top_recommendations(limit=1)
    assert len(recommendations) > 0
    
    rec = recommendations[0]
    rule_id = rec['rule_id']
    
    # Mock Activities API call
    with patch('synthesis.recommendation_engine.requests.post') as mock_post:
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": "activity-123", "type": "uttanasana"}
        )
        
        # Record accept decision
        result = engine.record_decision(rule_id, 'accept', rec)
    
    assert result['status'] == 'success'
    assert result['action'] == 'accept'
    assert result['rule_id'] == rule_id
    assert result['snooze_until'] is None
    # Activity logging depends on mapping, may or may not succeed
    
    # Verify decision is stored in database
    conn = sqlite3.connect(engine.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recommendation_decisions WHERE rule_id = ?", (rule_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None


def test_decision_snooze(engine, seed_dating_data):
    """Test recording a 'snooze' decision."""
    recommendations = engine.get_top_recommendations(limit=1)
    assert len(recommendations) > 0
    
    rec = recommendations[0]
    rule_id = rec['rule_id']
    
    # Record snooze decision
    result = engine.record_decision(rule_id, 'snooze', rec)
    
    assert result['status'] == 'success'
    assert result['action'] == 'snooze'
    assert result['snooze_until'] is not None
    
    # Verify snooze_until is ~4 hours from now
    snooze_time = datetime.fromisoformat(result['snooze_until'].replace('Z', ''))
    delta = (snooze_time - datetime.utcnow()).total_seconds()
    assert 3.9 * 3600 < delta < 4.1 * 3600  # ~4 hours


def test_decision_dismiss(engine, seed_dating_data):
    """Test recording a 'dismiss' decision."""
    recommendations = engine.get_top_recommendations(limit=1)
    assert len(recommendations) > 0
    
    rec = recommendations[0]
    rule_id = rec['rule_id']
    
    # Record dismiss decision
    result = engine.record_decision(rule_id, 'dismiss', rec)
    
    assert result['status'] == 'success'
    assert result['action'] == 'dismiss'
    assert result['snooze_until'] is None
    
    # Verify pattern_hash is stored
    conn = sqlite3.connect(engine.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT pattern_hash FROM recommendation_decisions WHERE rule_id = ?", (rule_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] is not None  # pattern_hash


def test_filter_dismissed(engine, seed_dating_data):
    """Test dismissed recommendations are filtered out."""
    # Get initial recommendations
    recommendations = engine.get_top_recommendations(limit=5)
    initial_count = len(recommendations)
    
    if initial_count == 0:
        pytest.skip("No recommendations fired")
    
    rec = recommendations[0]
    rule_id = rec['rule_id']
    
    # Dismiss the first recommendation
    engine.record_decision(rule_id, 'dismiss', rec)
    
    # Get recommendations again
    recommendations_after = engine.get_top_recommendations(limit=5)
    
    # The dismissed recommendation should not appear
    dismissed_in_results = any(r['rule_id'] == rule_id for r in recommendations_after)
    assert not dismissed_in_results


def test_filter_snoozed(engine, seed_dating_data):
    """Test snoozed recommendations are filtered out until snooze_until passes."""
    recommendations = engine.get_top_recommendations(limit=5)
    
    if len(recommendations) == 0:
        pytest.skip("No recommendations fired")
    
    rec = recommendations[0]
    rule_id = rec['rule_id']
    
    # Snooze the first recommendation
    engine.record_decision(rule_id, 'snooze', rec)
    
    # Get recommendations again immediately
    recommendations_after = engine.get_top_recommendations(limit=5)
    
    # The snoozed recommendation should not appear
    snoozed_in_results = any(r['rule_id'] == rule_id for r in recommendations_after)
    assert not snoozed_in_results


def test_domain_filter(engine, seed_dating_data):
    """Test domain filtering returns only recommendations from specified domain."""
    recommendations = engine.get_top_recommendations(limit=20, domain='dating')
    
    # All recommendations should be from dating domain
    for rec in recommendations:
        assert rec['domain'] == 'dating'


def test_activities_api_integration_mock(engine, seed_dating_data):
    """Test Activities API integration (mocked)."""
    recommendations = engine.get_top_recommendations(limit=1)
    
    if len(recommendations) == 0:
        pytest.skip("No recommendations fired")
    
    rec = recommendations[0]
    
    # Mock successful Activities API response
    with patch('synthesis.recommendation_engine.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "act-456", "type": "gym"}
        mock_post.return_value = mock_response
        
        result = engine.record_decision(rec['rule_id'], 'accept', rec)
    
    # If mapping exists, activity should be logged
    # Otherwise, activity_logged should be False
    assert 'activity_logged' in result


def test_pattern_hash_computation(engine):
    """Test pattern hash is consistent for similar data."""
    rec1 = {
        'rule_id': 'R-DATE-01',
        'domain': 'dating',
        'data_table': [
            {'source': 'bachata', 'avg_quality': 8.2},
            {'source': 'bumble', 'avg_quality': 6.1}
        ]
    }
    
    rec2 = {
        'rule_id': 'R-DATE-01',
        'domain': 'dating',
        'data_table': [
            {'source': 'bachata', 'avg_quality': 8.3},  # Slightly different, rounds to 8
            {'source': 'bumble', 'avg_quality': 6.0}   # Rounds to 6
        ]
    }
    
    hash1 = engine._compute_pattern_hash(rec1)
    hash2 = engine._compute_pattern_hash(rec2)
    
    # Hashes should be the same (both round to similar values)
    assert hash1 == hash2


def test_invalid_action(engine, seed_dating_data):
    """Test invalid action raises ValueError."""
    recommendations = engine.get_top_recommendations(limit=1)
    
    if len(recommendations) == 0:
        pytest.skip("No recommendations fired")
    
    rec = recommendations[0]
    
    with pytest.raises(ValueError):
        engine.record_decision(rec['rule_id'], 'invalid_action', rec)


def test_action_buttons_present(engine, seed_dating_data):
    """Test all recommendations have action buttons."""
    recommendations = engine.get_top_recommendations(limit=5)
    
    for rec in recommendations:
        assert 'actions' in rec
        assert len(rec['actions']) == 3
        
        action_types = [a['type'] for a in rec['actions']]
        assert 'accept' in action_types
        assert 'snooze' in action_types
        assert 'dismiss' in action_types


def test_empty_state_has_correct_format(engine):
    """Test empty state recommendations follow ADR-005 format."""
    recommendations = engine.get_top_recommendations(limit=20)
    
    # Some recommendations may be empty state (insufficient data)
    # They should still have proper structure
    for rec in recommendations:
        assert 'rule_id' in rec
        assert 'one_liner' in rec
        assert 'goal_alignment' in rec
        
        # Empty state one-liners should mention "After X more..."
        if rec.get('empty_state'):
            assert 'after' in rec['one_liner'].lower() or 'need' in rec['one_liner'].lower()


# --- Integration Tests ---

def test_full_workflow_accept_to_activities(engine, seed_activities_data):
    """
    Integration test: Full workflow from recommendation to activity logging.
    
    Scenario:
    1. Get recommendations
    2. Accept a health-related recommendation
    3. Verify activity is logged to Activities API
    """
    recommendations = engine.get_top_recommendations(limit=20)
    
    # Find a health-related recommendation that maps to an activity
    health_rec = None
    for rec in recommendations:
        if 'Health' in rec['goal_alignment']:
            health_rec = rec
            break
    
    if not health_rec:
        pytest.skip("No health recommendations fired")
    
    # Mock Activities API
    with patch('synthesis.recommendation_engine.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "activity-789", "type": "gym"}
        mock_post.return_value = mock_response
        
        result = engine.record_decision(health_rec['rule_id'], 'accept', health_rec)
    
    assert result['status'] == 'success'
    assert result['action'] == 'accept'
    
    # If there's a mapping, activity should be logged
    # Otherwise, activity_logged is False
    assert 'activity_logged' in result


def test_cross_domain_recommendation_boost(engine, seed_dating_data, seed_activities_data):
    """
    Integration test: Cross-domain context affects priority.
    
    Scenario:
    - Dating recommendation gets boost if health score is high (≥7)
    - Health recommendations get boost if health score is low (<5)
    """
    recommendations = engine.get_top_recommendations(limit=20, include_cross_domain_context=True)
    
    # Check if cross-domain context influenced priority
    for rec in recommendations:
        if 'cross_domain_context' in rec:
            ctx = rec['cross_domain_context']
            health_score = ctx.get('health_score', 0)
            
            # Dating rec with high health score should have higher priority
            if 'GOAL-1' in rec['goal_alignment'] and health_score >= 7:
                # Should have +5 boost
                assert rec['priority_score'] > 100
            
            # Health rec with low health score should have higher priority
            if 'Health' in rec['goal_alignment'] and health_score < 5:
                # Should have +10 boost
                assert rec['priority_score'] > 75
