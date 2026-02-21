"""
Base interface for job sources.
"""
from abc import ABC, abstractmethod
from typing import List
from ..models import JobListing


class JobSource(ABC):
    """Abstract base for job listing sources."""

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def fetch(self) -> List[JobListing]:
        """
        Fetch job listings from this source.
        
        Returns:
            List of JobListing objects
        
        Raises:
            Exception on fetch failure (caller handles partial failures)
        """
        pass

    def _tag_source(self, listings: List[JobListing]) -> List[JobListing]:
        """Tag all listings with this source name."""
        for listing in listings:
            if self.source_name not in listing.sources:
                listing.sources.append(self.source_name)
        return listings
