"""Tests for data models."""
import pytest
from datetime import datetime
from uuid import UUID
from ..models import (
    JobListing,
    LocationType,
    SeniorityLevel,
    SalaryRange,
    Currency,
    OpportunityDiscoveredEvent,
)


def test_job_listing_defaults():
    """Test JobListing default values."""
    listing = JobListing(
        company="TestCo",
        role="ML Engineer",
    )
    
    assert isinstance(listing.listing_id, UUID)
    assert listing.company == "TestCo"
    assert listing.role == "ML Engineer"
    assert listing.location == LocationType.REMOTE
    assert listing.seniority == SeniorityLevel.UNKNOWN
    assert listing.sources == []
    assert listing.tech_stack == []
    assert isinstance(listing.discovered_at, datetime)


def test_dedup_key():
    """Test deduplication key generation."""
    listing1 = JobListing(company="TestCo", role="ML Engineer")
    listing2 = JobListing(company="testco", role="ml engineer")
    listing3 = JobListing(company="TestCo", role="Data Scientist")
    
    # Same company + role (normalized) should have same key
    assert listing1.dedup_key() == listing2.dedup_key()
    
    # Different role should have different key
    assert listing1.dedup_key() != listing3.dedup_key()


def test_salary_range():
    """Test salary range model."""
    salary = SalaryRange(min=100000, max=150000, currency=Currency.EUR)
    
    assert salary.min == 100000
    assert salary.max == 150000
    assert salary.currency == Currency.EUR


def test_opportunity_discovered_event():
    """Test event creation from listing."""
    listing = JobListing(
        company="TestCo",
        role="Senior ML Engineer",
        description="Build ML systems",
        location=LocationType.REMOTE,
        seniority=SeniorityLevel.SENIOR,
        sources=["test_source"],
        url="https://example.com/job",
    )
    
    event = OpportunityDiscoveredEvent.from_listing(listing)
    
    assert event.event_type == "OpportunityDiscovered"
    assert event.version == "v1"
    assert event.context == "DISC"
    assert event.payload.company == "TestCo"
    assert event.payload.role == "Senior ML Engineer"
    assert event.payload.seniority == SeniorityLevel.SENIOR
    assert "test_source" in event.payload.sources
    assert isinstance(event.timestamp, datetime)


def test_event_serialization():
    """Test event can be serialized to JSON."""
    listing = JobListing(company="TestCo", role="ML Engineer", sources=["test"])
    event = OpportunityDiscoveredEvent.from_listing(listing)
    
    # Should serialize without errors
    json_str = event.model_dump_json()
    assert "OpportunityDiscovered" in json_str
    assert "TestCo" in json_str
