"""
Working Nomads job board scraper.
Parses HTML listings from workingnomads.com.
"""
import re
from typing import List
import requests
from bs4 import BeautifulSoup
from ..models import JobListing, LocationType, SeniorityLevel, SalaryRange, Currency
from .base import JobSource


class WorkingNomadsSource(JobSource):
    """Scrape jobs from WorkingNomads."""

    BASE_URL = "https://www.workingnomads.com/jobs"
    
    # AI/ML category filter
    AI_ML_KEYWORDS = [
        "ai", "ml", "machine learning", "data science",
        "artificial intelligence", "nlp", "deep learning",
        "mlops", "llm", "neural", "model"
    ]
    
    SENIORITY_MAP = {
        "senior": SeniorityLevel.SENIOR,
        "sr.": SeniorityLevel.SENIOR,
        "lead": SeniorityLevel.SENIOR,
        "staff": SeniorityLevel.STAFF,
        "principal": SeniorityLevel.PRINCIPAL,
        "mid": SeniorityLevel.MID,
        "junior": SeniorityLevel.JUNIOR,
        "jr.": SeniorityLevel.JUNIOR,
    }

    def __init__(self):
        super().__init__("working_nomads")

    def fetch(self) -> List[JobListing]:
        """Fetch and parse job listings."""
        # Fetch development/programming category (most likely to have AI/ML)
        params = {"category": "development"}
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = []
        
        # Find all job listing cards
        job_cards = soup.select('.job-list li, article.job')
        
        for card in job_cards:
            listing = self._parse_job_card(card)
            if listing:
                listings.append(listing)
        
        return self._tag_source(listings)

    def _parse_job_card(self, card) -> JobListing | None:
        """Parse a single job card."""
        # Extract title/role
        title_elem = card.select_one('h3, .job-title, a.job-link')
        if not title_elem:
            return None
        role = title_elem.get_text(strip=True)
        
        # Filter for AI/ML roles only
        role_lower = role.lower()
        if not any(kw in role_lower for kw in self.AI_ML_KEYWORDS):
            return None
        
        # Extract company
        company_elem = card.select_one('.company, .company-name, h4')
        company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
        
        # Extract description
        desc_elem = card.select_one('.description, .job-description, p')
        description = desc_elem.get_text(strip=True)[:500] if desc_elem else ""
        
        # Extract URL
        link_elem = card.select_one('a')
        url = link_elem.get('href', '') if link_elem else ""
        if url and not url.startswith('http'):
            url = f"https://www.workingnomads.com{url}"
        
        # Determine seniority
        seniority = self._extract_seniority(role)
        
        # Extract salary if available
        salary = self._extract_salary(card)
        
        return JobListing(
            company=company,
            role=role,
            description=description,
            location=LocationType.REMOTE,  # Working Nomads is remote-only
            seniority=seniority,
            salary_range=salary,
            url=url,
        )

    def _extract_seniority(self, role: str) -> SeniorityLevel:
        """Extract seniority from role title."""
        role_lower = role.lower()
        for keyword, level in self.SENIORITY_MAP.items():
            if keyword in role_lower:
                return level
        return SeniorityLevel.UNKNOWN

    def _extract_salary(self, card) -> SalaryRange | None:
        """Extract salary range if present."""
        salary_elem = card.select_one('.salary, .compensation')
        if not salary_elem:
            return None
        
        salary_text = salary_elem.get_text(strip=True)
        
        # Try to parse salary ranges like "$100k-$150k" or "€80,000-€120,000"
        match = re.search(r'[\$€£]?([\d,]+)k?\s*-\s*[\$€£]?([\d,]+)k?', salary_text, re.IGNORECASE)
        if match:
            min_sal = int(match.group(1).replace(',', ''))
            max_sal = int(match.group(2).replace(',', ''))
            
            # Detect currency
            currency = Currency.USD  # default
            if '€' in salary_text:
                currency = Currency.EUR
            elif '£' in salary_text:
                currency = Currency.GBP
            
            # If values look like "100k", multiply by 1000
            if 'k' in salary_text.lower():
                min_sal *= 1000
                max_sal *= 1000
            
            return SalaryRange(min=min_sal, max=max_sal, currency=currency)
        
        return None
