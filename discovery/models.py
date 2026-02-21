"""
Data models for job discovery system.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl


class LocationType(str, Enum):
    """Job location type."""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class Currency(str, Enum):
    """Supported currencies."""
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    PLN = "PLN"


class SeniorityLevel(str, Enum):
    """Job seniority levels."""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    UNKNOWN = "unknown"


class SalaryRange(BaseModel):
    """Salary range information."""
    min: Optional[float] = Field(None, ge=0)
    max: Optional[float] = Field(None, ge=0)
    currency: Currency = Currency.EUR


class JobListing(BaseModel):
    """Raw job listing from a source."""
    listing_id: UUID = Field(default_factory=uuid4)
    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    description: str = ""
    location: LocationType = LocationType.REMOTE
    salary_range: Optional[SalaryRange] = None
    tech_stack: List[str] = Field(default_factory=list)
    seniority: SeniorityLevel = SeniorityLevel.UNKNOWN
    sources: List[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    url: str = ""

    def dedup_key(self) -> str:
        """Generate deduplication key (company + role normalized)."""
        company_norm = self.company.lower().strip()
        role_norm = self.role.lower().strip()
        return f"{company_norm}::{role_norm}"


class OpportunityDiscoveredPayload(BaseModel):
    """Payload for OpportunityDiscovered event."""
    listing_id: UUID
    company: str
    role: str
    description: str
    location: LocationType
    salary_range: Optional[SalaryRange] = None
    tech_stack: List[str] = Field(default_factory=list)
    seniority: SeniorityLevel
    sources: List[str]
    discovered_at: datetime
    url: str


class OpportunityDiscoveredEvent(BaseModel):
    """Complete OpportunityDiscovered event."""
    event_type: str = "OpportunityDiscovered"
    version: str = "v1"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: str = "DISC"
    payload: OpportunityDiscoveredPayload

    @classmethod
    def from_listing(cls, listing: JobListing) -> "OpportunityDiscoveredEvent":
        """Create event from job listing."""
        return cls(
            payload=OpportunityDiscoveredPayload(
                listing_id=listing.listing_id,
                company=listing.company,
                role=listing.role,
                description=listing.description,
                location=listing.location,
                salary_range=listing.salary_range,
                tech_stack=listing.tech_stack,
                seniority=listing.seniority,
                sources=listing.sources,
                discovered_at=listing.discovered_at,
                url=listing.url,
            )
        )
