"""Tests for SkillsExtractor"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from analyzer import SkillsExtractor


@pytest.fixture
def config():
    return {
        'skill_synonyms': {
            'Python': ['python', 'python3', 'py'],
            'PyTorch': ['pytorch', 'torch'],
            'Kubernetes': ['kubernetes', 'k8s']
        },
        'required_patterns': ['required', 'must have', 'essential'],
        'nice_to_have_patterns': ['nice to have', 'preferred', 'bonus']
    }


@pytest.fixture
def extractor(config):
    return SkillsExtractor(config)


def test_extract_from_tech_stack(extractor):
    """Test extraction from explicit tech_stack field."""
    mentions = extractor.extract(
        job_description="",
        tech_stack=['Python', 'Docker', 'AWS']
    )
    
    assert len(mentions) == 3
    assert all(m.context == "required" for m in mentions)
    skills = [m.skill for m in mentions]
    assert 'Python' in skills


def test_extract_from_description(extractor):
    """Test extraction from description text."""
    description = """
    We're looking for an engineer with Python and PyTorch experience.
    Knowledge of Kubernetes is a plus.
    """
    
    mentions = extractor.extract(description)
    
    skills = [m.skill for m in mentions]
    assert 'Python' in skills
    assert 'PyTorch' in skills
    assert 'Kubernetes' in skills


def test_context_detection_required(extractor):
    """Test required vs nice-to-have context detection."""
    description = """
    Required skills:
    - Python
    - PyTorch
    
    Nice to have:
    - Kubernetes
    """
    
    mentions = extractor.extract(description)
    
    python_mention = next(m for m in mentions if m.skill == 'Python')
    k8s_mention = next(m for m in mentions if m.skill == 'Kubernetes')
    
    assert python_mention.context == "required"
    assert k8s_mention.context == "nice_to_have"


def test_synonym_normalization(extractor):
    """Test that synonyms are normalized to canonical names."""
    mentions = extractor.extract("Experience with python3 and k8s")
    
    skills = [m.skill for m in mentions]
    assert 'Python' in skills  # python3 -> Python
    assert 'Kubernetes' in skills  # k8s -> Kubernetes


def test_aggregate_stats(extractor):
    """Test aggregation of skill mentions."""
    mentions = [
        extractor.extract("Required: Python")[0],
        extractor.extract("Nice to have: Python")[0],
        extractor.extract("Required: PyTorch")[0]
    ]
    
    # Flatten list
    all_mentions = [m for sublist in mentions for m in (sublist if isinstance(sublist, list) else [sublist])]
    
    stats = extractor.aggregate(all_mentions)
    
    assert 'Python' in stats
    assert stats['Python']['total'] == 2
    assert stats['Python']['required_count'] == 1
    assert stats['Python']['nice_count'] == 1
    assert stats['Python']['required_pct'] == 0.5


def test_empty_description(extractor):
    """Test handling of empty description."""
    mentions = extractor.extract("")
    assert len(mentions) == 0


def test_no_matches(extractor):
    """Test description with no skill matches."""
    mentions = extractor.extract("Looking for a great communicator with passion")
    assert len(mentions) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
