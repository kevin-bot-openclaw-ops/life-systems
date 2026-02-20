"""
Schema Validation Tests
Tests that all event schemas are valid and sample events pass validation.
"""

import json
import jsonschema
from pathlib import Path
import pytest

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"

def load_schema(event_type: str, version: str = "v1") -> dict:
    """Load a JSON schema file."""
    schema_path = SCHEMA_DIR / f"{event_type}_{version}.json"
    with open(schema_path) as f:
        return json.load(f)

def test_schema_files_exist():
    """All documented schemas exist as files."""
    expected_schemas = [
        "OpportunityDiscovered_v1.json",
        "OpportunityScored_v1.json",
        "DraftGenerated_v1.json",
        "DecisionMade_v1.json",
        "MarketReportPublished_v1.json",
        "StateUpdated_v1.json",
        "WeightsAdjusted_v1.json",
    ]
    
    for schema_file in expected_schemas:
        assert (SCHEMA_DIR / schema_file).exists(), f"Missing schema: {schema_file}"

def test_opportunitydiscovered_valid():
    """OpportunityDiscovered schema validates correct event."""
    schema = load_schema("OpportunityDiscovered")
    
    event = {
        "event_type": "OpportunityDiscovered",
        "version": "v1",
        "timestamp": "2026-02-20T11:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "company": "Anthropic",
            "role": "Senior AI Engineer",
            "description": "Build production AI systems...",
            "location": "remote",
            "salary_range": {"min": 150000, "max": 200000, "currency": "EUR"},
            "tech_stack": ["Python", "LangChain", "FastAPI"],
            "seniority": "senior",
            "sources": ["linkedin"],
            "discovered_at": "2026-02-20T11:00:00Z",
            "url": "https://example.com/job/123"
        }
    }
    
    # Should not raise
    jsonschema.validate(instance=event, schema=schema)

def test_opportunitydiscovered_missing_required():
    """OpportunityDiscovered schema rejects event missing required field."""
    schema = load_schema("OpportunityDiscovered")
    
    event = {
        "event_type": "OpportunityDiscovered",
        "version": "v1",
        "timestamp": "2026-02-20T11:00:00Z",
        "context": "DISC",
        "payload": {
            # Missing listing_id (required)
            "company": "Anthropic",
            "role": "Senior AI Engineer",
            "description": "Build production AI systems...",
            "location": "remote",
            "discovered_at": "2026-02-20T11:00:00Z",
            "url": "https://example.com/job/123"
        }
    }
    
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=event, schema=schema)

def test_opportunityscored_valid():
    """OpportunityScored schema validates correct event."""
    schema = load_schema("OpportunityScored")
    
    event = {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-20T11:05:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "score": 87.5,
            "breakdown": {
                "remote_match": 100,
                "ai_ml_relevance": 95,
                "seniority_match": 90,
                "salary_match": 85,
                "fintech_bonus": 0
            },
            "weights": {
                "remote_match": 0.4,
                "ai_ml_relevance": 0.3,
                "seniority_match": 0.2,
                "salary_match": 0.1,
                "fintech_bonus": 0.0
            },
            "rejected": False,
            "rejection_reason": None
        }
    }
    
    jsonschema.validate(instance=event, schema=schema)

def test_opportunityscored_score_bounds():
    """OpportunityScored schema enforces score bounds (0-100)."""
    schema = load_schema("OpportunityScored")
    
    event = {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-20T11:05:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "score": 150,  # Invalid: > 100
            "breakdown": {
                "remote_match": 100,
                "ai_ml_relevance": 95,
                "seniority_match": 90,
                "salary_match": 85,
                "fintech_bonus": 0
            },
            "weights": {
                "remote_match": 0.4,
                "ai_ml_relevance": 0.3,
                "seniority_match": 0.2,
                "salary_match": 0.1,
                "fintech_bonus": 0.0
            },
            "rejected": False
        }
    }
    
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=event, schema=schema)

def test_draftgenerated_valid():
    """DraftGenerated schema validates correct event."""
    schema = load_schema("DraftGenerated")
    
    event = {
        "event_type": "DraftGenerated",
        "version": "v1",
        "timestamp": "2026-02-20T11:10:00Z",
        "context": "APPL",
        "payload": {
            "draft_id": "d1e2f3g4-h5i6-7890-jklm-nopqr1234567",
            "listing_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "company": "Anthropic",
            "role": "Senior AI Engineer",
            "draft_text": "I'm reaching out about the Senior AI Engineer role...",
            "humanizer_pass": True,
            "ai_tells_detected": 0,
            "word_count": 187,
            "variant": "ml_research"
        }
    }
    
    jsonschema.validate(instance=event, schema=schema)

def test_decisionmade_valid():
    """DecisionMade schema validates correct event."""
    schema = load_schema("DecisionMade")
    
    event = {
        "event_type": "DecisionMade",
        "version": "v1",
        "timestamp": "2026-02-20T11:15:00Z",
        "context": "APPL",
        "payload": {
            "draft_id": "d1e2f3g4-h5i6-7890-jklm-nopqr1234567",
            "listing_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "decision": "approved",
            "reason": None,
            "applied_at": "2026-02-20T11:20:00Z",
            "response_received": False,
            "response_at": None
        }
    }
    
    jsonschema.validate(instance=event, schema=schema)

def test_marketreportpublished_valid():
    """MarketReportPublished schema validates correct event."""
    schema = load_schema("MarketReportPublished")
    
    event = {
        "event_type": "MarketReportPublished",
        "version": "v1",
        "timestamp": "2026-02-20T12:00:00Z",
        "context": "MKTL",
        "payload": {
            "week": "2026-W08",
            "top_skills": [
                {
                    "skill": "LangChain",
                    "demand_count": 42,
                    "trend": "rising",
                    "required_vs_nice": {"required": 28, "nice_to_have": 14}
                }
            ],
            "salary_ranges": [
                {
                    "role_type": "Senior AI Engineer",
                    "min": 120000,
                    "max": 180000,
                    "median": 150000,
                    "currency": "EUR",
                    "sample_size": 23
                }
            ],
            "gap_analysis": {
                "jurek_has": ["Python", "Java", "Spring Boot"],
                "market_wants": ["Python", "LangChain", "FastAPI"],
                "gaps": ["LangChain"]
            },
            "sample_size": 156
        }
    }
    
    jsonschema.validate(instance=event, schema=schema)

def test_stateupdated_valid():
    """StateUpdated schema validates correct event."""
    schema = load_schema("StateUpdated")
    
    event = {
        "event_type": "StateUpdated",
        "version": "v1",
        "timestamp": "2026-02-20T12:05:00Z",
        "context": "SYNTH",
        "payload": {
            "sections": {
                "career": {"funnel": {"discovered": 23, "applied": 8}},
                "market": {"top_skills": ["LangChain", "FastAPI"]},
                "dating": {"hours_this_week": 8},
                "relocation": {"top_city": "Lisbon"}
            },
            "conflicts": [
                {
                    "conflict_type": "advisor_disagreement",
                    "advisors": ["CRST", "MKTL"],
                    "summary": "CRST says pause Upwork, MKTL says Upwork demand rising",
                    "perspectives": [
                        {
                            "advisor": "CRST",
                            "recommendation": "Pause Upwork (low response rate)",
                            "confidence": 0.7
                        },
                        {
                            "advisor": "MKTL",
                            "recommendation": "Upwork fintech+AI demand up 15%",
                            "confidence": 0.85
                        }
                    ]
                }
            ],
            "alerts": [
                {
                    "alert_type": "threshold_breach",
                    "severity": "warning",
                    "message": "Social hours below target for 2 consecutive weeks",
                    "context_data": {"actual": 6, "target": 10}
                }
            ]
        }
    }
    
    jsonschema.validate(instance=event, schema=schema)

def test_weightsadjusted_valid():
    """WeightsAdjusted schema validates correct event."""
    schema = load_schema("WeightsAdjusted")
    
    event = {
        "event_type": "WeightsAdjusted",
        "version": "v1",
        "timestamp": "2026-02-20T13:00:00Z",
        "context": "LEARN",
        "payload": {
            "dimension": "fintech_bonus",
            "old_weight": 0.15,
            "new_weight": 0.22,
            "reason": "Fintech roles approved at 85% rate (12 of 14 decisions)",
            "confidence": 0.78,
            "decisions_analyzed": 52
        }
    }
    
    jsonschema.validate(instance=event, schema=schema)

def test_all_schemas_are_valid_json_schema():
    """Meta-validation: all schema files are valid JSON Schema."""
    schema_files = list(SCHEMA_DIR.glob("*_v1.json"))
    assert len(schema_files) >= 7, "Missing schema files"
    
    for schema_file in schema_files:
        with open(schema_file) as f:
            schema = json.load(f)
        
        # JSON Schema Draft 7 meta-schema validation
        jsonschema.Draft7Validator.check_schema(schema)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
