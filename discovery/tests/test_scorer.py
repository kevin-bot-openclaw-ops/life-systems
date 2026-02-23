"""
Tests for DISC-MVP-2: Job Scoring Engine
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from discovery.scorer import (
    JobScorer,
    ScoringConfig,
    ScoringWeights,
    HardFilters,
    ScoreBreakdown,
    ScoredOpportunity
)


@pytest.fixture
def default_scorer():
    """Scorer with default configuration."""
    return JobScorer()


@pytest.fixture
def custom_config_file():
    """Create temporary config file."""
    config = {
        'weights': {
            'remote_match': 0.50,
            'ai_ml_relevance': 0.25,
            'seniority_match': 0.15,
            'salary_match': 0.05,
            'fintech_bonus': 0.05
        },
        'hard_filters': {
            'require_remote': True,
            'salary_floor_eur': 100000
        },
        'ai_ml_keywords': ['ai', 'ml', 'llm'],
        'fintech_keywords': ['fintech', 'banking'],
        'target_seniority': ['senior', 'staff']
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        return Path(f.name)


def test_scorer_initialization_default():
    """Test scorer initializes with default config."""
    scorer = JobScorer()
    assert scorer.config.weights.remote_match == 0.40
    assert scorer.config.weights.ai_ml_relevance == 0.30
    assert scorer.config.hard_filters.require_remote is True
    assert scorer.config.hard_filters.salary_floor_eur == 120000


def test_scorer_initialization_custom(custom_config_file):
    """Test scorer initializes with custom config."""
    scorer = JobScorer(config_path=custom_config_file)
    assert scorer.config.weights.remote_match == 0.50
    assert scorer.config.weights.ai_ml_relevance == 0.25
    assert scorer.config.hard_filters.salary_floor_eur == 100000


def test_perfect_match_listing(default_scorer):
    """Test scoring of perfect-fit listing."""
    listing = {
        'listing_id': 'perfect-123',
        'company': 'Fintech AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build production LLM systems using Python, LangChain, and RAG pipelines for banking compliance',
        'location': 'remote',
        'salary_range': {'min': 150000, 'max': 180000, 'currency': 'EUR'},
        'tech_stack': ['Python', 'LangChain', 'OpenAI', 'Kubernetes'],
        'seniority': 'senior'
    }
    
    scored = default_scorer.score_listing(listing)
    
    assert scored.rejected is False
    assert scored.score > 75  # Should score very high (adjusted for realistic weights)
    assert scored.breakdown.remote_match == 100
    assert scored.breakdown.ai_ml_relevance >= 50  # Multiple AI/ML keywords
    assert scored.breakdown.seniority_match == 90  # Senior
    assert scored.breakdown.salary_match == 100  # €150k+
    assert scored.breakdown.fintech_bonus > 0  # Banking + fintech keywords


def test_hard_filter_not_remote(default_scorer):
    """Test hard filter rejection for non-remote role."""
    listing = {
        'listing_id': 'onsite-123',
        'company': 'AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build AI systems',
        'location': 'onsite',
        'seniority': 'senior'
    }
    
    scored = default_scorer.score_listing(listing)
    
    assert scored.rejected is True
    assert scored.rejection_reason == "Not remote"
    assert scored.score == 0


def test_hard_filter_salary_below_floor(default_scorer):
    """Test hard filter rejection for salary below floor."""
    listing = {
        'listing_id': 'lowpay-123',
        'company': 'Startup AI',
        'role': 'Senior ML Engineer',
        'description': 'Build AI systems with Python and TensorFlow',
        'location': 'remote',
        'salary_range': {'min': 80000, 'max': 100000, 'currency': 'EUR'},
        'seniority': 'senior'
    }
    
    scored = default_scorer.score_listing(listing)
    
    assert scored.rejected is True
    assert 'Salary below floor' in scored.rejection_reason
    assert scored.score == 0


def test_hybrid_location_scoring(default_scorer):
    """Test hybrid location gets lower score than remote."""
    # Temporarily disable hard filter for this test
    default_scorer.config.hard_filters.require_remote = False
    
    listing_remote = {
        'listing_id': 'remote-123',
        'company': 'AI Corp',
        'role': 'ML Engineer',
        'description': 'AI work',
        'location': 'remote',
        'seniority': 'mid'
    }
    
    listing_hybrid = {
        **listing_remote,
        'listing_id': 'hybrid-123',
        'location': 'hybrid'
    }
    
    scored_remote = default_scorer.score_listing(listing_remote)
    scored_hybrid = default_scorer.score_listing(listing_hybrid)
    
    assert scored_remote.breakdown.remote_match == 100
    assert scored_hybrid.breakdown.remote_match == 30
    assert scored_remote.score > scored_hybrid.score


def test_ai_ml_relevance_keyword_scoring(default_scorer):
    """Test AI/ML relevance scoring based on keywords."""
    listing_high = {
        'listing_id': 'high-123',
        'company': 'AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build LLM agents using RAG, embeddings, and transformers with LangChain',
        'location': 'remote',
        'tech_stack': ['Python', 'OpenAI', 'Anthropic'],
        'seniority': 'senior'
    }
    
    listing_low = {
        'listing_id': 'low-123',
        'company': 'Tech Corp',
        'role': 'Senior Software Engineer',
        'description': 'Build backend systems using Java and Spring Boot',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    scored_high = default_scorer.score_listing(listing_high)
    scored_low = default_scorer.score_listing(listing_low)
    
    assert scored_high.breakdown.ai_ml_relevance > scored_low.breakdown.ai_ml_relevance
    assert scored_high.breakdown.ai_ml_relevance >= 50  # Multiple keywords


def test_seniority_scoring(default_scorer):
    """Test seniority level scoring."""
    base_listing = {
        'company': 'AI Corp',
        'role': 'ML Engineer',
        'description': 'AI work',
        'location': 'remote'
    }
    
    # Principal
    scored_principal = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'principal-123',
        'seniority': 'principal'
    })
    
    # Staff
    scored_staff = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'staff-123',
        'seniority': 'staff'
    })
    
    # Senior
    scored_senior = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'senior-123',
        'seniority': 'senior'
    })
    
    # Mid
    scored_mid = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'mid-123',
        'seniority': 'mid'
    })
    
    assert scored_principal.breakdown.seniority_match == 100
    assert scored_staff.breakdown.seniority_match == 100
    assert scored_senior.breakdown.seniority_match == 90
    assert scored_mid.breakdown.seniority_match == 50


def test_salary_range_scoring(default_scorer):
    """Test salary range scoring."""
    base_listing = {
        'company': 'AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'AI work',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    # High salary (€150k+)
    scored_high = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'high-123',
        'salary_range': {'min': 150000, 'max': 180000, 'currency': 'EUR'}
    })
    
    # Medium salary (€130k-145k)
    scored_medium = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'medium-123',
        'salary_range': {'min': 130000, 'max': 145000, 'currency': 'EUR'}
    })
    
    # Lower salary (€120k-130k)
    scored_lower = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'lower-123',
        'salary_range': {'min': 120000, 'max': 130000, 'currency': 'EUR'}
    })
    
    assert scored_high.breakdown.salary_match == 100  # €150k+
    assert scored_medium.breakdown.salary_match == 85  # €130-150k
    assert scored_lower.breakdown.salary_match == 70  # €120-130k


def test_fintech_bonus_scoring(default_scorer):
    """Test fintech/banking bonus scoring."""
    listing_fintech = {
        'listing_id': 'fintech-123',
        'company': 'Banking AI Solutions',
        'role': 'Senior ML Engineer',
        'description': 'Build fraud detection systems for fintech using ML, compliance with Basel III and AML regulations',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    listing_nofintech = {
        'listing_id': 'nofintech-123',
        'company': 'Tech Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build AI systems',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    scored_fintech = default_scorer.score_listing(listing_fintech)
    scored_nofintech = default_scorer.score_listing(listing_nofintech)
    
    assert scored_fintech.breakdown.fintech_bonus > 0
    assert scored_nofintech.breakdown.fintech_bonus == 0


def test_currency_conversion(default_scorer):
    """Test salary currency conversion to EUR."""
    base_listing = {
        'company': 'AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'AI work',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    # USD salary (should convert to EUR)
    scored_usd = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'usd-123',
        'salary_range': {'min': 163000, 'max': 200000, 'currency': 'USD'}  # ~€150k
    })
    
    # GBP salary (should convert to EUR)
    scored_gbp = default_scorer.score_listing({
        **base_listing,
        'listing_id': 'gbp-123',
        'salary_range': {'min': 130000, 'max': 160000, 'currency': 'GBP'}  # ~€150k
    })
    
    # Both should score well after conversion
    assert scored_usd.breakdown.salary_match >= 70
    assert scored_gbp.breakdown.salary_match >= 70


def test_missing_salary_neutral_score(default_scorer):
    """Test missing salary gets neutral score, not rejection."""
    listing = {
        'listing_id': 'nosalary-123',
        'company': 'AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build AI systems',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    scored = default_scorer.score_listing(listing)
    
    assert scored.rejected is False  # Not rejected
    assert scored.breakdown.salary_match == 60  # Neutral score


def test_config_weight_change_affects_ranking(custom_config_file):
    """Test changing weights in config changes ranking."""
    scorer1 = JobScorer()  # Default weights
    scorer2 = JobScorer(config_path=custom_config_file)  # Custom weights (higher remote)
    
    listing = {
        'listing_id': 'test-123',
        'company': 'AI Corp',
        'role': 'ML Engineer',
        'description': 'AI work',
        'location': 'remote',
        'seniority': 'mid'
    }
    
    scored1 = scorer1.score_listing(listing)
    scored2 = scorer2.score_listing(listing)
    
    # Custom config has higher remote_match weight (0.50 vs 0.40)
    assert scored2.weights.remote_match == 0.50
    assert scored1.weights.remote_match == 0.40
    # Scores should differ due to weight change
    assert scored1.score != scored2.score


def test_batch_scoring(default_scorer):
    """Test scoring multiple listings at once."""
    listings = [
        {
            'listing_id': f'batch-{i}',
            'company': 'AI Corp',
            'role': 'ML Engineer',
            'description': 'AI work',
            'location': 'remote',
            'seniority': 'senior'
        }
        for i in range(5)
    ]
    
    scored_batch = default_scorer.score_batch(listings)
    
    assert len(scored_batch) == 5
    assert all(isinstance(s, ScoredOpportunity) for s in scored_batch)
    assert all(not s.rejected for s in scored_batch)


def test_event_publishing(default_scorer, tmp_path):
    """Test OpportunityScored event publishing."""
    listing = {
        'listing_id': 'event-123',
        'company': 'AI Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build AI systems',
        'location': 'remote',
        'seniority': 'senior'
    }
    
    scored = default_scorer.score_listing(listing)
    output_file = tmp_path / "scored_events.jsonl"
    
    default_scorer.publish_scored_event(scored, output_file)
    
    assert output_file.exists()
    
    import json
    with open(output_file, 'r') as f:
        event = json.loads(f.readline())
    
    assert event['event_type'] == 'OpportunityScored'
    assert event['version'] == 'v1'
    assert event['context'] == 'DISC'
    assert event['payload']['listing_id'] == 'event-123'
    assert 'score' in event['payload']
