"""Tests for job scanner."""
import pytest
from pathlib import Path
import tempfile
import json
from ..models import JobListing, LocationType
from ..scanner import JobScanner
from ..sources.base import JobSource


class MockSource(JobSource):
    """Mock job source for testing."""
    
    def __init__(self, name: str, listings: list):
        super().__init__(name)
        self.listings = listings
    
    def fetch(self):
        return self._tag_source(self.listings)


class FailingSource(JobSource):
    """Mock source that always fails."""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def fetch(self):
        raise Exception("Simulated fetch failure")


def test_scanner_basic():
    """Test basic scanner functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock source
        listings = [
            JobListing(company="CompanyA", role="ML Engineer"),
            JobListing(company="CompanyB", role="Data Scientist"),
        ]
        source = MockSource("test_source", listings)
        
        # Run scanner
        scanner = JobScanner([source], Path(tmpdir))
        summary = scanner.scan()
        
        assert summary["sources_succeeded"] == 1
        assert summary["sources_failed"] == 0
        assert summary["total_fetched"] == 2
        assert summary["new_listings"] == 2
        assert summary["events_published"] == 2


def test_scanner_deduplication():
    """Test deduplication across sources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Same job from two sources
        listing1 = JobListing(company="CompanyA", role="ML Engineer")
        listing2 = JobListing(company="CompanyA", role="ML Engineer")
        
        source1 = MockSource("source1", [listing1])
        source2 = MockSource("source2", [listing2])
        
        scanner = JobScanner([source1, source2], Path(tmpdir))
        summary = scanner.scan()
        
        # Should deduplicate to 1 listing
        assert summary["total_fetched"] == 2
        assert summary["after_dedup"] == 1
        assert summary["new_listings"] == 1
        
        # Check event file
        event_files = list(Path(tmpdir).glob("events_*.jsonl"))
        assert len(event_files) == 1
        
        with open(event_files[0]) as f:
            events = [json.loads(line) for line in f]
        
        assert len(events) == 1
        # Should have both sources listed
        assert len(events[0]["payload"]["sources"]) == 2


def test_scanner_seen_tracking():
    """Test seen listings are not re-published."""
    with tempfile.TemporaryDirectory() as tmpdir:
        listing = JobListing(company="CompanyA", role="ML Engineer")
        source = MockSource("test_source", [listing])
        
        scanner = JobScanner([source], Path(tmpdir))
        
        # First scan
        summary1 = scanner.scan()
        assert summary1["new_listings"] == 1
        
        # Second scan with same listing
        scanner2 = JobScanner([source], Path(tmpdir))
        summary2 = scanner2.scan()
        
        # Should not re-publish
        assert summary2["new_listings"] == 0


def test_scanner_partial_failure():
    """Test scanner continues on partial source failures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        good_listing = JobListing(company="CompanyA", role="ML Engineer")
        good_source = MockSource("good_source", [good_listing])
        bad_source = FailingSource("bad_source")
        
        scanner = JobScanner([good_source, bad_source], Path(tmpdir))
        summary = scanner.scan()
        
        # One succeeded, one failed
        assert summary["sources_succeeded"] == 1
        assert summary["sources_failed"] == 1
        assert len(summary["failures"]) == 1
        assert summary["failures"][0]["source"] == "bad_source"
        
        # Should still publish good results
        assert summary["new_listings"] == 1


def test_event_file_format():
    """Test published event files are valid JSONL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        listings = [
            JobListing(company="CompanyA", role="ML Engineer"),
            JobListing(company="CompanyB", role="Data Scientist"),
        ]
        source = MockSource("test", listings)
        
        scanner = JobScanner([source], Path(tmpdir))
        scanner.scan()
        
        # Check event file
        event_files = list(Path(tmpdir).glob("events_*.jsonl"))
        assert len(event_files) == 1
        
        with open(event_files[0]) as f:
            events = [json.loads(line) for line in f]
        
        assert len(events) == 2
        
        # Validate event structure
        for event in events:
            assert event["event_type"] == "OpportunityDiscovered"
            assert event["version"] == "v1"
            assert event["context"] == "DISC"
            assert "payload" in event
            assert "company" in event["payload"]
            assert "role" in event["payload"]
