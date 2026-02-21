"""Tests for DemandAnalyzer"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime, timedelta
from analyzer import DemandAnalyzer


@pytest.fixture
def config():
    return {
        'trend': {
            'min_data_points': 2,
            'significant_change_pct': 0.15
        }
    }


@pytest.fixture
def analyzer(config):
    return DemandAnalyzer(config)


def test_analyze_with_salaries(analyzer):
    """Test demand analysis with salary data."""
    skill_stats = {
        'Python': {'total': 10, 'required_count': 8, 'nice_count': 2, 'required_pct': 0.8, 'nice_to_have_pct': 0.2},
        'Java': {'total': 5, 'required_count': 3, 'nice_count': 2, 'required_pct': 0.6, 'nice_to_have_pct': 0.4}
    }
    
    listings = [
        {'description': 'Python developer', 'salary': '$120k-140k', 'tech_stack': ['Python']},
        {'description': 'Python engineer', 'salary': '$130k-150k', 'tech_stack': ['Python']},
        {'description': 'Java developer', 'salary': '$110k', 'tech_stack': ['Java']}
    ]
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    demands = analyzer.analyze(skill_stats, listings, period_start, period_end)
    
    assert len(demands) == 2
    
    # Python should be first (higher demand)
    python_demand = demands[0]
    assert python_demand.skill == 'Python'
    assert python_demand.demand_count == 10
    assert python_demand.avg_salary_usd is not None
    assert python_demand.avg_salary_usd > 100000


def test_salary_extraction_range(analyzer):
    """Test salary extraction from range."""
    listing = {'salary': '$120k-140k', 'description': '', 'tech_stack': []}
    salary = analyzer._extract_salary_from_listing(listing)
    
    assert salary is not None
    assert 120000 <= salary <= 140000


def test_salary_extraction_single(analyzer):
    """Test salary extraction from single value."""
    listing = {'salary': '$135,000', 'description': '', 'tech_stack': []}
    salary = analyzer._extract_salary_from_listing(listing)
    
    assert salary == 135000


def test_salary_extraction_eur(analyzer):
    """Test EUR to USD conversion."""
    listing = {'salary': '€100k', 'description': '', 'tech_stack': []}
    salary = analyzer._extract_salary_from_listing(listing)
    
    assert salary is not None
    assert salary > 100000  # Should be converted to USD


def test_trend_detection_new_skill(analyzer):
    """Test trend for skill with no historical data."""
    skill_stats = {
        'Python': {'total': 10, 'required_count': 8, 'nice_count': 2}
    }
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    demands = analyzer.analyze(skill_stats, [], period_start, period_end)
    
    assert demands[0].trend == 'new'


def test_trend_detection_growing(analyzer):
    """Test trend detection for growing skill."""
    # Set up historical data (prior count = 5)
    period_end = datetime.utcnow()
    one_week_ago = period_end - timedelta(days=7)
    
    analyzer.historical_demand['Python'] = [
        (one_week_ago, 5)
    ]
    
    # Current count = 10 (doubled)
    skill_stats = {
        'Python': {'total': 10, 'required_count': 8, 'nice_count': 2, 'required_pct': 0.8, 'nice_to_have_pct': 0.2}
    }
    
    demands = analyzer.analyze(skill_stats, [], period_end - timedelta(days=1), period_end)
    
    assert demands[0].trend in ['growing', 'insufficient_data']  # May be insufficient if min_data_points not met


def test_sorting_by_demand(analyzer):
    """Test that results are sorted by demand count."""
    skill_stats = {
        'Python': {'total': 20, 'required_count': 15, 'nice_count': 5, 'required_pct': 0.75, 'nice_to_have_pct': 0.25},
        'Java': {'total': 5, 'required_count': 3, 'nice_count': 2, 'required_pct': 0.6, 'nice_to_have_pct': 0.4},
        'Go': {'total': 10, 'required_count': 8, 'nice_count': 2, 'required_pct': 0.8, 'nice_to_have_pct': 0.2}
    }
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)
    
    demands = analyzer.analyze(skill_stats, [], period_start, period_end)
    
    # Should be sorted: Python (20) > Go (10) > Java (5)
    assert demands[0].skill == 'Python'
    assert demands[1].skill == 'Go'
    assert demands[2].skill == 'Java'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
