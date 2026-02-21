"""Tests for GapAnalyzer"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from analyzer import GapAnalyzer


@pytest.fixture
def config():
    return {
        'jurek_profile': {
            'skills': ['Python', 'Java', 'Docker', 'AWS', 'LangChain', 'RAG']
        }
    }


@pytest.fixture
def analyzer(config):
    return GapAnalyzer(config)


def test_strengths_identification(analyzer):
    """Test identification of Jurek's strengths."""
    top_skills = [
        {'skill': 'Python', 'demand_count': 50},
        {'skill': 'PyTorch', 'demand_count': 40},
        {'skill': 'Docker', 'demand_count': 30},
        {'skill': 'Kubernetes', 'demand_count': 25}
    ]
    
    gap_analysis = analyzer.analyze(top_skills, top_n=4)
    
    strengths = gap_analysis['strengths']
    assert 'Python' in strengths
    assert 'Docker' in strengths
    assert len(strengths) == 2  # Python and Docker from top 4


def test_gaps_identification(analyzer):
    """Test identification of skill gaps."""
    top_skills = [
        {'skill': 'Python', 'demand_count': 50},
        {'skill': 'PyTorch', 'demand_count': 40},
        {'skill': 'Kubernetes', 'demand_count': 30}
    ]
    
    gap_analysis = analyzer.analyze(top_skills, top_n=3)
    
    gaps = gap_analysis['gaps']
    assert 'PyTorch' in gaps
    assert 'Kubernetes' in gaps


def test_bridge_skills_identification(analyzer):
    """Test identification of bridge skills."""
    top_skills = [
        {'skill': 'Python', 'demand_count': 50},
        {'skill': 'LangChain', 'demand_count': 15},  # Bridge skill
        {'skill': 'RAG', 'demand_count': 12},  # Bridge skill
        {'skill': 'Java', 'demand_count': 10}
    ]
    
    gap_analysis = analyzer.analyze(top_skills, top_n=10)
    
    bridge_skills = gap_analysis['bridge_skills']
    assert 'LangChain' in bridge_skills
    assert 'RAG' in bridge_skills


def test_insights_generation(analyzer):
    """Test that insights are generated."""
    top_skills = [
        {
            'skill': 'PyTorch',
            'demand_count': 40,
            'trend': 'growing',
            'week_over_week_change': 0.25,
            'avg_salary_usd': 150000
        },
        {
            'skill': 'Python',
            'demand_count': 50,
            'trend': 'stable',
            'avg_salary_usd': 140000,
            'required_pct': 0.85
        }
    ]
    
    gap_analysis = analyzer.analyze(top_skills, top_n=2)
    
    insights = gap_analysis['insights']
    assert len(insights) > 0
    
    # Should mention PyTorch growth
    assert any('PyTorch' in insight for insight in insights)


def test_market_top_10_list(analyzer):
    """Test that market_top_10 is included in output."""
    top_skills = [
        {'skill': 'Python', 'demand_count': 50},
        {'skill': 'PyTorch', 'demand_count': 40}
    ]
    
    gap_analysis = analyzer.analyze(top_skills, top_n=2)
    
    assert 'market_top_10' in gap_analysis
    assert gap_analysis['market_top_10'] == ['Python', 'PyTorch']


def test_jurek_skills_included(analyzer):
    """Test that Jurek's skills list is included."""
    top_skills = [{'skill': 'Python', 'demand_count': 50}]
    
    gap_analysis = analyzer.analyze(top_skills, top_n=1)
    
    assert 'jurek_skills' in gap_analysis
    assert 'Python' in gap_analysis['jurek_skills']
    assert 'Java' in gap_analysis['jurek_skills']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
