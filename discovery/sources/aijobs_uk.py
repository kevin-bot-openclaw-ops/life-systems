"""
AIJobs.co.uk WordPress REST API source.
Fetches job listings via WordPress JSON API.
"""
import re
from typing import List
import requests
from ..models import JobListing, LocationType, SeniorityLevel, SalaryRange, Currency
from .base import JobSource


class AIJobsUKSource(JobSource):
    """Fetch AI jobs from AIJobs.co.uk WordPress API."""

    API_URL = "https://aijobs.co.uk/wp-json/wp/v2/job-listings"
    
    REMOTE_KEYWORDS = ["remote", "anywhere", "distributed", "work from home", "wfh"]
    
    SENIORITY_MAP = {
        SeniorityLevel.SENIOR: ["senior", "sr.", "lead", "staff", "principal"],
        SeniorityLevel.MID: ["mid-level", "mid", "intermediate"],
        SeniorityLevel.JUNIOR: ["junior", "jr.", "entry"],
    }

    def __init__(self):
        super().__init__("aijobs_uk")

    def fetch(self) -> List[JobListing]:
        """Fetch job listings from WordPress API."""
        params = {
            "per_page": 100,  # Max allowed
            "orderby": "date",
            "order": "desc",
        }
        
        response = requests.get(self.API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        listings = []
        for item in data:
            listing = self._parse_job(item)
            if listing:
                listings.append(listing)
        
        return self._tag_source(listings)

    def _parse_job(self, item: dict) -> JobListing | None:
        """Parse a WordPress job post."""
        # Extract title
        title = item.get("title", {}).get("rendered", "").strip()
        if not title:
            return None
        
        # Clean HTML from title
        title = re.sub(r'<[^>]+>', '', title)
        
        # Extract content/description
        content = item.get("content", {}).get("rendered", "")
        # Strip HTML tags for description
        description = re.sub(r'<[^>]+>', '', content).strip()[:500]
        
        # Extract meta fields (WordPress custom fields may vary)
        meta = item.get("meta", {}) or {}
        acf = item.get("acf", {}) or {}
        
        # Company name (may be in meta, acf, or extract from title)
        company = (
            meta.get("company") or 
            acf.get("company") or 
            acf.get("company_name") or
            self._extract_company_from_title(title)
        )
        
        # Location type
        location_text = (
            meta.get("location") or 
            acf.get("location") or 
            description
        ).lower()
        
        is_remote = any(kw in location_text for kw in self.REMOTE_KEYWORDS)
        location = LocationType.REMOTE if is_remote else LocationType.ONSITE
        
        # Only include remote jobs
        if location != LocationType.REMOTE:
            return None
        
        # Seniority
        seniority = self._extract_seniority(title + " " + description)
        
        # Salary
        salary = self._extract_salary(content + str(meta) + str(acf))
        
        # URL
        url = item.get("link", "")
        
        # Role (clean version of title)
        role = self._clean_role(title)
        
        return JobListing(
            company=company,
            role=role,
            description=description,
            location=location,
            seniority=seniority,
            salary_range=salary,
            url=url,
        )

    def _extract_company_from_title(self, title: str) -> str:
        """Extract company from title like 'Company Name - Job Title'."""
        # Try pattern: "Company - Role" or "Company | Role"
        match = re.search(r'^([A-Z][^-|]+)\s*[-|]\s*', title)
        if match:
            return match.group(1).strip()
        
        # Fallback
        return "AI Company"

    def _clean_role(self, title: str) -> str:
        """Clean role title by removing company prefix."""
        # Remove "Company - " or "Company | " prefix
        cleaned = re.sub(r'^[^-|]+[-|]\s*', '', title)
        return cleaned.strip()

    def _extract_seniority(self, text: str) -> SeniorityLevel:
        """Extract seniority level."""
        text_lower = text.lower()
        for level, keywords in self.SENIORITY_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return level
        return SeniorityLevel.UNKNOWN

    def _extract_salary(self, text: str) -> SalaryRange | None:
        """Extract salary range from text."""
        # UK roles often show GBP
        # Pattern: £50,000-£80,000 or $100k-$150k
        match = re.search(r'[£$€]([\d,]+)k?\s*-\s*[£$€]([\d,]+)k?', text, re.IGNORECASE)
        if match:
            min_sal = int(match.group(1).replace(',', ''))
            max_sal = int(match.group(2).replace(',', ''))
            
            currency = Currency.GBP  # Default for UK site
            if '$' in text:
                currency = Currency.USD
            elif '€' in text:
                currency = Currency.EUR
            
            # Handle "k" suffix
            if 'k' in text.lower():
                min_sal *= 1000
                max_sal *= 1000
            
            return SalaryRange(min=min_sal, max=max_sal, currency=currency)
        
        return None
