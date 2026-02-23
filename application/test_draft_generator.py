"""
Tests for APPL-M1-1: Application Draft Generator

Test scenarios from BACKLOG.md:
- TS-APPL-M1-1a: Fintech AI role -> verify banking experience prominent
- TS-APPL-M1-1b: Pure ML research role -> verify AI/ML skills lead, not banking
- TS-APPL-M1-1c: 10 drafts through humanizer -> zero AI-tells detected
- TS-APPL-M1-1d: Two drafts for different companies -> substantially different
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from application.acl_opportunity_qualifier import OpportunityQualifier, ApplicationCandidate
from application.draft_generator import DraftGenerator, DraftResult


# Test Fixtures

@pytest.fixture
def sample_scored_event_fintech():
    """Sample OpportunityScored event for fintech role."""
    return {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-23T06:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "fintech-001",
            "company": "JPMorgan Chase",
            "role": "Senior ML Engineer - Fraud Detection",
            "url": "https://example.com/job/fintech",
            "score": 88.0,
            "dimensions": {
                "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                "ai_ml_relevance": {"score": 80, "weight": 0.35, "reason": "3 primary + 2 secondary keywords"},
                "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                "salary": {"score": 100, "weight": 0.10, "reason": "160000 EUR (>= target)"},
                "fintech_bonus": {"score": 60, "weight": 0.05, "reason": "2 fintech keywords: fraud, banking"},
            },
            "verdict": "accept",
        },
    }


@pytest.fixture
def sample_scored_event_research():
    """Sample OpportunityScored event for ML research role."""
    return {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-23T06:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "research-001",
            "company": "OpenAI",
            "role": "Research Scientist - NLP",
            "url": "https://example.com/job/research",
            "score": 85.0,
            "dimensions": {
                "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                "ai_ml_relevance": {"score": 95, "weight": 0.35, "reason": "5 primary + 4 secondary keywords"},
                "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                "salary": {"score": 100, "weight": 0.10, "reason": "180000 USD (>= target)"},
                "fintech_bonus": {"score": 0, "weight": 0.05, "reason": "No fintech signals"},
            },
            "verdict": "accept",
        },
    }


@pytest.fixture
def sample_scored_event_platform():
    """Sample OpportunityScored event for platform role."""
    return {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-23T06:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "platform-001",
            "company": "Databricks",
            "role": "Senior ML Platform Engineer",
            "url": "https://example.com/job/platform",
            "score": 86.0,
            "dimensions": {
                "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                "ai_ml_relevance": {"score": 85, "weight": 0.35, "reason": "4 primary + 3 secondary keywords"},
                "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                "salary": {"score": 100, "weight": 0.10, "reason": "170000 USD (>= target)"},
                "fintech_bonus": {"score": 0, "weight": 0.05, "reason": "No fintech signals"},
            },
            "verdict": "accept",
        },
    }


# OpportunityQualifier ACL Tests

def test_acl_filters_low_score():
    """Test ACL rejects listings below score threshold."""
    qualifier = OpportunityQualifier(score_threshold=70.0)
    
    low_score_event = {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-23T06:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "low-001",
            "company": "LowScore Inc",
            "role": "ML Engineer",
            "url": "https://example.com/job",
            "score": 65.0,
            "dimensions": {},
            "verdict": "accept",
        },
    }
    
    candidate = qualifier.qualify(low_score_event)
    assert candidate is None


def test_acl_filters_rejected_verdict():
    """Test ACL rejects listings with verdict='reject'."""
    qualifier = OpportunityQualifier()
    
    rejected_event = {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-23T06:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "rejected-001",
            "company": "Rejected Corp",
            "role": "ML Engineer",
            "url": "https://example.com/job",
            "score": 85.0,
            "dimensions": {},
            "verdict": "reject",
            "rejection_reason": "Hybrid location",
        },
    }
    
    candidate = qualifier.qualify(rejected_event)
    assert candidate is None


def test_acl_qualifies_good_listing(sample_scored_event_fintech):
    """Test ACL qualifies a good listing."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    assert candidate is not None
    assert candidate.company == "JPMorgan Chase"
    assert candidate.role == "Senior ML Engineer - Fraud Detection"
    assert candidate.score == 88.0


def test_acl_classifies_fintech_role(sample_scored_event_fintech):
    """Test ACL correctly classifies fintech role."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    assert candidate.role_type == "fintech"
    assert "fraud" in candidate.fintech_signals or "banking" in candidate.fintech_signals


def test_acl_classifies_research_role(sample_scored_event_research):
    """Test ACL correctly classifies research role."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_research)
    
    assert candidate.role_type == "ml_research"


def test_acl_classifies_platform_role(sample_scored_event_platform):
    """Test ACL correctly classifies platform role."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_platform)
    
    assert candidate.role_type == "platform"


def test_acl_extracts_seniority(sample_scored_event_fintech):
    """Test ACL extracts seniority from role title."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    assert candidate.seniority == "senior"


# DraftGenerator Tests

def test_draft_generator_fintech_template(sample_scored_event_fintech):
    """TS-APPL-M1-1a: Fintech role emphasizes banking experience."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    generator = DraftGenerator(humanize_enabled=False)  # Disable for easier testing
    result = generator.generate(candidate)
    
    draft_lower = result.draft_text.lower()
    
    # Should mention banking/fintech experience
    assert any(word in draft_lower for word in ["bank", "banking", "fintech", "financial"])
    
    # Should mention fraud detection (company-specific)
    assert "jpmorgan" in draft_lower
    
    # Should mention 15 years experience
    assert "15 years" in draft_lower
    
    # Should be under 250 words
    assert result.word_count <= 250


def test_draft_generator_research_template(sample_scored_event_research):
    """TS-APPL-M1-1b: Research role emphasizes AI/ML, not banking."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_research)
    
    generator = DraftGenerator(humanize_enabled=False)
    result = generator.generate(candidate)
    
    draft_lower = result.draft_text.lower()
    
    # Should mention AI/ML topics
    assert any(word in draft_lower for word in ["ai", "ml", "nlp", "research", "pytorch"])
    
    # Should mention company
    assert "openai" in draft_lower
    
    # Banking should be less prominent (mentioned but not emphasized)
    banking_mentions = draft_lower.count("bank")
    assert banking_mentions <= 2  # Background mention OK, but not emphasis
    
    # Should be under 250 words
    assert result.word_count <= 250


def test_draft_generator_platform_template(sample_scored_event_platform):
    """Test platform role emphasizes infrastructure."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_platform)
    
    generator = DraftGenerator(humanize_enabled=False)
    result = generator.generate(candidate)
    
    draft_lower = result.draft_text.lower()
    
    # Should mention infrastructure/MLOps
    assert any(word in draft_lower for word in ["infrastructure", "mlops", "production", "deploy"])
    
    # Should mention company
    assert "databricks" in draft_lower
    
    # Should be under 250 words
    assert result.word_count <= 250


def test_humanizer_removes_ai_tells(sample_scored_event_fintech):
    """TS-APPL-M1-1c: Drafts through humanizer have low AI score."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    generator = DraftGenerator(humanize_enabled=True)
    result = generator.generate(candidate)
    
    # AI score should be low after humanization
    assert result.ai_score < 20, f"AI score too high: {result.ai_score}"
    
    # Should have no em dashes
    assert "—" not in result.draft_text
    
    # Should use contractions
    assert any(contraction in result.draft_text for contraction in ["I'm", "I've", "don't", "can't", "isn't"])


def test_drafts_are_different(sample_scored_event_fintech, sample_scored_event_research):
    """TS-APPL-M1-1d: Drafts for different companies are substantially different."""
    qualifier = OpportunityQualifier()
    
    candidate1 = qualifier.qualify(sample_scored_event_fintech)
    candidate2 = qualifier.qualify(sample_scored_event_research)
    
    generator = DraftGenerator(humanize_enabled=False)
    result1 = generator.generate(candidate1)
    result2 = generator.generate(candidate2)
    
    # Calculate Jaccard similarity (word-level)
    words1 = set(result1.draft_text.lower().split())
    words2 = set(result2.draft_text.lower().split())
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    similarity = intersection / union if union > 0 else 0
    
    # Similarity should be low (< 0.5 = substantially different)
    assert similarity < 0.5, f"Drafts too similar: {similarity:.2f}"


def test_batch_generation(sample_scored_event_fintech, sample_scored_event_research, sample_scored_event_platform):
    """Test batch draft generation."""
    qualifier = OpportunityQualifier()
    
    candidates = [
        qualifier.qualify(sample_scored_event_fintech),
        qualifier.qualify(sample_scored_event_research),
        qualifier.qualify(sample_scored_event_platform),
    ]
    
    generator = DraftGenerator(humanize_enabled=True)
    results = generator.generate_batch(candidates)
    
    assert len(results) == 3
    assert all(isinstance(r, DraftResult) for r in results)
    assert all(r.word_count <= 250 for r in results)


def test_event_publishing(sample_scored_event_fintech, tmp_path):
    """Test DraftGenerated event publishing."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    generator = DraftGenerator()
    result = generator.generate(candidate)
    
    # Publish event
    output_file = tmp_path / "events.jsonl"
    generator.publish_event(result, str(output_file))
    
    # Verify file exists
    assert output_file.exists()
    
    # Verify event structure
    with open(output_file, "r") as f:
        event = json.loads(f.read())
    
    assert event["event_type"] == "DraftGenerated"
    assert event["version"] == "v1"
    assert event["context"] == "APPL"
    assert event["payload"]["listing_id"] == candidate.listing_id
    assert event["payload"]["company"] == candidate.company
    assert "draft_text" in event["payload"]


def test_performance_10_drafts(sample_scored_event_fintech, sample_scored_event_research, sample_scored_event_platform):
    """Test performance: 10 drafts in <2 minutes."""
    import time
    
    qualifier = OpportunityQualifier()
    
    # Create 10 candidates (repeat the 3 samples)
    events = [sample_scored_event_fintech, sample_scored_event_research, sample_scored_event_platform]
    candidates = []
    for i in range(10):
        event = events[i % 3].copy()
        event["payload"]["listing_id"] = f"perf-{i}"
        candidate = qualifier.qualify(event)
        candidates.append(candidate)
    
    generator = DraftGenerator(humanize_enabled=True)
    
    start_time = time.time()
    results = generator.generate_batch(candidates)
    elapsed = time.time() - start_time
    
    assert len(results) == 10
    assert elapsed < 120, f"Too slow: {elapsed:.1f}s (target: <120s)"
    
    # Log performance
    print(f"\n✅ Generated 10 drafts in {elapsed:.2f}s ({elapsed/10:.2f}s per draft)")


def test_no_em_dashes_in_output(sample_scored_event_fintech):
    """Test that drafts never contain em dashes."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    generator = DraftGenerator(humanize_enabled=True)
    result = generator.generate(candidate)
    
    assert "—" not in result.draft_text
    assert "–" not in result.draft_text  # en dash too


def test_company_and_role_mentioned(sample_scored_event_fintech):
    """Test that drafts mention company and role."""
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_scored_event_fintech)
    
    generator = DraftGenerator()
    result = generator.generate(candidate)
    
    draft_lower = result.draft_text.lower()
    
    # Company mentioned
    assert "jpmorgan" in draft_lower
    
    # Role mentioned (at least "fraud" from "Fraud Detection")
    assert "fraud" in draft_lower or "senior ml engineer" in draft_lower


def test_role_type_affects_content(sample_scored_event_fintech, sample_scored_event_research):
    """Test that different role types produce different emphasis."""
    qualifier = OpportunityQualifier()
    
    fintech_candidate = qualifier.qualify(sample_scored_event_fintech)
    research_candidate = qualifier.qualify(sample_scored_event_research)
    
    generator = DraftGenerator(humanize_enabled=False)
    
    fintech_result = generator.generate(fintech_candidate)
    research_result = generator.generate(research_candidate)
    
    # Fintech should mention banking more
    fintech_banking_count = fintech_result.draft_text.lower().count("bank")
    research_banking_count = research_result.draft_text.lower().count("bank")
    
    assert fintech_banking_count > research_banking_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
