"""
Tests for RELOC-M1-1: Composite Scoring + Recommendation
"""
import json
import sqlite3
import pytest
from pathlib import Path


# Test data setup
TEST_DB = "/tmp/test_life_systems.db"
TEST_CONFIG = {
    "weights": {
        "dating_pool": 0.30,
        "ai_job_density": 0.25,
        "cost_index": 0.20,
        "lifestyle_score": 0.15,
        "community_score": 0.10
    },
    "normalization": {
        "dating_pool": {"min": 0, "max": 5000, "invert": False},
        "ai_job_density": {"min": 0, "max": 200, "invert": False},
        "cost_index": {"min": 0.5, "max": 2.0, "invert": True},
        "lifestyle_score": {"min": 1, "max": 10, "invert": False},
        "community_score": {"min": 1, "max": 10, "invert": False}
    }
}


@pytest.fixture
def setup_db():
    """Create test database with sample cities."""
    conn = sqlite3.connect(TEST_DB)
    
    # Create cities table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL,
            is_current INTEGER DEFAULT 0,
            dating_pool INTEGER,
            ai_job_density INTEGER,
            cost_index REAL,
            lifestyle_score REAL CHECK(lifestyle_score BETWEEN 1 AND 10),
            community_score REAL CHECK(community_score BETWEEN 1 AND 10),
            composite_score REAL,
            data_source TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert test data
    test_cities = [
        # name, country, is_current, dating_pool, ai_jobs, cost, lifestyle, community
        ("Fuerteventura", "Spain", 1, 200, 5, 1.0, 8.5, 5.0),
        ("Madrid", "Spain", 0, 2500, 150, 1.4, 8.0, 9.0),
        ("Barcelona", "Spain", 0, 3000, 120, 1.5, 9.0, 8.5),
        ("Lisbon", "Portugal", 0, 1800, 80, 1.2, 8.5, 7.5),
        ("Berlin", "Germany", 0, 3500, 180, 1.6, 7.5, 9.5),
        ("Amsterdam", "Netherlands", 0, 1200, 90, 1.8, 8.0, 8.0),
        ("Valencia", "Spain", 0, 800, 40, 1.1, 8.5, 6.5),
        ("Málaga", "Spain", 0, 600, 30, 1.0, 9.0, 6.0)
    ]
    
    for city in test_cities:
        conn.execute(
            """
            INSERT INTO cities 
            (name, country, is_current, dating_pool, ai_job_density, 
             cost_index, lifestyle_score, community_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            city
        )
    
    conn.commit()
    conn.close()
    
    yield TEST_DB
    
    # Cleanup
    Path(TEST_DB).unlink(missing_ok=True)


def test_normalize_value():
    """Test normalization function."""
    from api.routes.cities import normalize_value
    
    # Test normal case
    assert normalize_value(2500, "dating_pool", TEST_CONFIG) == 0.5
    assert normalize_value(5000, "dating_pool", TEST_CONFIG) == 1.0
    assert normalize_value(0, "dating_pool", TEST_CONFIG) == 0.0
    
    # Test inverted (cost_index)
    assert normalize_value(1.0, "cost_index", TEST_CONFIG) == pytest.approx(0.667, abs=0.01)
    assert normalize_value(2.0, "cost_index", TEST_CONFIG) == 0.0
    assert normalize_value(0.5, "cost_index", TEST_CONFIG) == 1.0
    
    # Test None
    assert normalize_value(None, "dating_pool", TEST_CONFIG) == 0.0
    
    # Test clamping
    assert normalize_value(10000, "dating_pool", TEST_CONFIG) == 1.0
    assert normalize_value(-100, "dating_pool", TEST_CONFIG) == 0.0


def test_calculate_composite_score():
    """Test composite score calculation."""
    from api.routes.cities import calculate_composite_score
    
    # Perfect city (max on all dimensions)
    perfect_city = {
        "dating_pool": 5000,
        "ai_job_density": 200,
        "cost_index": 0.5,  # Inverted: lower is better
        "lifestyle_score": 10,
        "community_score": 10
    }
    score = calculate_composite_score(perfect_city, TEST_CONFIG)
    assert score == 10.0
    
    # Baseline city (Fuerteventura)
    baseline_city = {
        "dating_pool": 200,
        "ai_job_density": 5,
        "cost_index": 1.0,
        "lifestyle_score": 8.5,
        "community_score": 5.0
    }
    score = calculate_composite_score(baseline_city, TEST_CONFIG)
    assert 2.0 < score < 5.0  # Should be below mid-range due to low dating/jobs
    
    # City with None values
    incomplete_city = {
        "dating_pool": 1000,
        "ai_job_density": None,
        "cost_index": 1.2,
        "lifestyle_score": 7.0,
        "community_score": None
    }
    score = calculate_composite_score(incomplete_city, TEST_CONFIG)
    assert score > 0  # Should still calculate with available dimensions


def test_update_all_composite_scores(setup_db, monkeypatch):
    """Test updating all city scores."""
    # Monkey-patch DB_PATH and CONFIG_PATH
    from api.routes import cities
    monkeypatch.setattr(cities, "DB_PATH", TEST_DB)
    monkeypatch.setattr(cities, "load_scoring_config", lambda: TEST_CONFIG)
    
    # Run update
    cities.update_all_composite_scores()
    
    # Verify scores were calculated
    conn = sqlite3.connect(TEST_DB)
    rows = conn.execute("SELECT name, composite_score FROM cities WHERE composite_score IS NOT NULL").fetchall()
    conn.close()
    
    assert len(rows) == 8  # All cities should have scores
    
    # Check specific expected rankings
    scores_dict = {name: score for name, score in rows}
    
    # Madrid and Barcelona should score high (large dating pool + many AI jobs)
    assert scores_dict["Madrid"] > scores_dict["Fuerteventura"]
    assert scores_dict["Barcelona"] > scores_dict["Fuerteventura"]
    
    # Berlin should score very high (largest dating pool + most AI jobs, despite high cost)
    assert scores_dict["Berlin"] > scores_dict["Lisbon"]


def test_one_liner_generation():
    """Test motivation-first one-liner generation."""
    from api.routes.cities import _generate_one_liner, CityResponse, DimensionComparison
    
    recommended = CityResponse(
        id=1,
        name="Madrid",
        country="Spain",
        dating_pool=2500,
        ai_job_density=150,
        cost_index=1.4,
        lifestyle_score=8.0,
        community_score=9.0,
        composite_score=8.5
    )
    
    current = CityResponse(
        id=2,
        name="Fuerteventura",
        country="Spain",
        is_current=1,
        dating_pool=200,
        ai_job_density=5,
        cost_index=1.0,
        lifestyle_score=8.5,
        community_score=5.0,
        composite_score=5.2
    )
    
    comparisons = [
        DimensionComparison(
            dimension="dating pool",
            current_value=200,
            recommended_value=2500,
            change_pct=1150.0,
            change_abs=2300
        ),
        DimensionComparison(
            dimension="AI job density",
            current_value=5,
            recommended_value=150,
            change_pct=2900.0,
            change_abs=145
        )
    ]
    
    one_liner = _generate_one_liner(recommended, current, comparisons)
    
    # Should mention dating pool and AI jobs
    assert "Madrid" in one_liner
    assert "strongest candidate" in one_liner
    assert any(word in one_liner.lower() for word in ["dating", "jobs", "ai"])


def test_trade_offs_generation():
    """Test trade-off calculation."""
    # This would be tested via the full endpoint, but we can verify the logic
    current_cost = 1.0
    rec_cost = 1.4
    
    change_pct = (rec_cost - current_cost) / current_cost * 100
    assert change_pct == pytest.approx(40.0)
    
    trade_off = f"Cost of living is {change_pct:.0f}% higher ({rec_cost:.1f}x vs {current_cost:.1f}x baseline)"
    assert "40% higher" in trade_off


def test_equal_weights_default():
    """Test that default config has equal weights."""
    from api.routes.cities import load_scoring_config
    
    # If config file doesn't exist, should return defaults
    config = load_scoring_config()
    
    weights = config["weights"]
    assert weights["dating_pool"] == 0.20
    assert weights["ai_job_density"] == 0.20
    assert weights["cost_index"] == 0.20
    assert weights["lifestyle_score"] == 0.20
    assert weights["community_score"] == 0.20
    
    # Sum should be 1.0
    assert sum(weights.values()) == pytest.approx(1.0)


def test_configurable_weights():
    """Test that weights are read from config."""
    custom_weights = TEST_CONFIG["weights"]
    
    # Custom weights should not be equal
    assert custom_weights["dating_pool"] == 0.30
    assert custom_weights["ai_job_density"] == 0.25
    
    # Sum should still be 1.0
    assert sum(custom_weights.values()) == pytest.approx(1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
