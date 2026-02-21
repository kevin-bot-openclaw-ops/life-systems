"""Tests for job scoring engine - DISC-MVP-2."""

import pytest
from datetime import datetime
from scorer import JobScorer, ScoringWeights, ScoreBreakdown, ScoredJob


@pytest.fixture
def default_weights():
    """Default scoring weights."""
    return ScoringWeights(
        remote_match=0.35,
        ai_ml_relevance=0.30,
        seniority_match=0.20,
        salary_match=0.10,
        fintech_bonus=0.05
    )


@pytest.fixture
def scorer(default_weights):
    """Initialized scorer with default weights."""
    return JobScorer(weights=default_weights, salary_floor=100000)


def test_perfect_match(scorer):
    """TS-DISC-MVP-2a: Perfect-fit listing scores > 85."""
    listing = {
        'listing_id': 'test-1',
        'company': 'Deutsche Bank',
        'role': 'Senior AI/ML Engineer',
        'description': 'Build production LLM systems with RAG pipelines for financial services. Use Claude API, LangChain, and FastAPI.',
        'location': 'remote',
        'salary_range': {'min': 140000, 'max': 170000, 'currency': 'EUR'},
        'tech_stack': ['Python', 'LangChain', 'Claude', 'PyTorch', 'Docker'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    assert not result.rejected
    assert result.score > 85.0
    assert result.breakdown.remote_match == 100.0
    assert result.breakdown.ai_ml_relevance > 80.0
    assert result.breakdown.seniority_match == 100.0
    assert result.breakdown.salary_match == 100.0
    assert result.breakdown.fintech_bonus > 10.0


def test_bad_fit_rejection(scorer):
    """TS-DISC-MVP-2b: Bad-fit listing (office-only, junior) filtered or < 30."""
    listing = {
        'listing_id': 'test-2',
        'company': 'Local Startup',
        'role': 'Junior Data Analyst',
        'description': 'Work with Excel and SQL in our office.',
        'location': 'onsite',
        'salary_range': {'min': 40000, 'max': 50000, 'currency': 'EUR'},
        'tech_stack': ['Excel', 'SQL'],
        'seniority': 'junior',
        'sources': ['working_nomads'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    assert result.rejected
    assert result.score == 0.0
    assert result.rejection_reason == "Not remote (location=onsite)"


def test_weight_change_impact(default_weights):
    """TS-DISC-MVP-2c: Change weights in config, verify fintech roles rise."""
    # Original weights
    scorer1 = JobScorer(weights=default_weights, salary_floor=100000)

    # Boost fintech bonus
    boosted_weights = ScoringWeights(
        remote_match=0.30,
        ai_ml_relevance=0.25,
        seniority_match=0.20,
        salary_match=0.10,
        fintech_bonus=0.15  # Tripled from 0.05
    )
    scorer2 = JobScorer(weights=boosted_weights, salary_floor=100000)

    fintech_listing = {
        'listing_id': 'test-3',
        'company': 'JPMorgan Chase',
        'role': 'Senior ML Engineer - Fraud Detection',
        'description': 'Build ML models for fraud detection and AML in banking.',
        'location': 'remote',
        'salary_range': {'min': 140000, 'max': 170000, 'currency': 'EUR'},
        'tech_stack': ['Python', 'ML', 'PyTorch'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result1 = scorer1.score_listing(fintech_listing)
    result2 = scorer2.score_listing(fintech_listing)

    # With boosted fintech weight, fintech contribution to final score should be higher
    fintech_contribution1 = result1.breakdown.fintech_bonus * result1.weights.fintech_bonus
    fintech_contribution2 = result2.breakdown.fintech_bonus * result2.weights.fintech_bonus
    
    assert fintech_contribution2 > fintech_contribution1
    assert result2.breakdown.fintech_bonus > 0


def test_missing_salary_neutral(scorer):
    """TS-DISC-MVP-2d: Listing with no salary gets neutral score (not penalty)."""
    listing = {
        'listing_id': 'test-4',
        'company': 'Stealth Startup',
        'role': 'Senior AI Engineer',
        'description': 'Build LLM-powered applications.',
        'location': 'remote',
        'salary_range': None,
        'tech_stack': ['Python', 'LLM', 'FastAPI'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    assert not result.rejected
    assert result.breakdown.salary_match == 50.0  # Neutral


def test_hybrid_penalty(scorer):
    """Hybrid location gets rejection (remote-only filter)."""
    listing = {
        'listing_id': 'test-5',
        'company': 'Google',
        'role': 'Senior ML Engineer',
        'description': 'Build ML systems.',
        'location': 'hybrid',
        'salary_range': {'min': 150000, 'max': 200000, 'currency': 'USD'},
        'tech_stack': ['Python', 'TensorFlow'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    assert result.rejected
    assert result.rejection_reason == "Not remote (location=hybrid)"


def test_salary_floor_rejection(scorer):
    """Below salary floor gets rejected."""
    listing = {
        'listing_id': 'test-6',
        'company': 'Budget Corp',
        'role': 'Senior ML Engineer',
        'description': 'Build ML systems.',
        'location': 'remote',
        'salary_range': {'min': 60000, 'max': 80000, 'currency': 'EUR'},
        'tech_stack': ['Python', 'ML'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    assert result.rejected
    assert "Below salary floor" in result.rejection_reason


def test_ai_ml_relevance_tiers(scorer):
    """High-tier AI/ML keywords score higher than low-tier."""
    high_tier_listing = {
        'listing_id': 'test-7',
        'company': 'AI Startup',
        'role': 'Senior LLM Engineer',
        'description': 'Build LLM applications with RAG pipelines, Claude API, and embeddings.',
        'location': 'remote',
        'tech_stack': ['LangChain', 'GPT', 'BERT'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    low_tier_listing = {
        'listing_id': 'test-8',
        'company': 'Data Corp',
        'role': 'Senior Data Scientist',
        'description': 'Work with Python and statistics on data analytics.',
        'location': 'remote',
        'tech_stack': ['Python', 'Statistics'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result_high = scorer.score_listing(high_tier_listing)
    result_low = scorer.score_listing(low_tier_listing)

    assert result_high.breakdown.ai_ml_relevance > result_low.breakdown.ai_ml_relevance


def test_seniority_detection_from_role(scorer):
    """Seniority detected from role title even if seniority field is unknown."""
    listing = {
        'listing_id': 'test-9',
        'company': 'Tech Corp',
        'role': 'Staff ML Engineer',  # Seniority in title
        'description': 'Build ML systems.',
        'location': 'remote',
        'seniority': 'unknown',  # But unknown in field
        'tech_stack': ['Python', 'ML'],
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    assert result.breakdown.seniority_match == 100.0


def test_currency_conversion(scorer):
    """USD salary converted to EUR for floor check."""
    listing = {
        'listing_id': 'test-10',
        'company': 'US Company',
        'role': 'Senior ML Engineer',
        'description': 'Build ML systems.',
        'location': 'remote',
        'salary_range': {'min': 150000, 'max': 200000, 'currency': 'USD'},  # ~186k EUR
        'tech_stack': ['Python', 'ML'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    result = scorer.score_listing(listing)

    # 200k USD * 0.93 = 186k EUR > 150k floor
    assert not result.rejected
    assert result.breakdown.salary_match == 100.0


def test_weights_validation():
    """Weights sum validation."""
    valid_weights = ScoringWeights(
        remote_match=0.35,
        ai_ml_relevance=0.30,
        seniority_match=0.20,
        salary_match=0.10,
        fintech_bonus=0.05
    )

    assert valid_weights.validate_sum()

    invalid_weights = ScoringWeights(
        remote_match=0.50,
        ai_ml_relevance=0.30,
        seniority_match=0.20,
        salary_match=0.10,
        fintech_bonus=0.05
    )

    assert not invalid_weights.validate_sum()


def test_event_publishing(scorer):
    """OpportunityScored event format."""
    listing = {
        'listing_id': 'test-11',
        'company': 'Test Corp',
        'role': 'Senior AI Engineer',
        'description': 'Build AI systems.',
        'location': 'remote',
        'tech_stack': ['Python', 'AI'],
        'seniority': 'senior',
        'sources': ['hn_algolia'],
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'url': 'https://example.com'
    }

    scored_job = scorer.score_listing(listing)
    event = scorer.publish_event(scored_job)

    assert event.event_type == "OpportunityScored"
    assert event.version == "v1"
    assert event.context == "DISC"
    assert event.payload.listing_id == 'test-11'
    assert event.timestamp.endswith('Z')
