"""
Hacker News Algolia API source.
Searches "Ask HN: Who is hiring?" threads for job listings.
"""
import re
from datetime import datetime
from typing import List
import requests
from ..models import JobListing, LocationType, SeniorityLevel
from .base import JobSource


class HNAlgoliaSource(JobSource):
    """Fetch jobs from HN Who is Hiring via Algolia API."""

    API_URL = "http://hn.algolia.com/api/v1/search"
    
    # Keywords for filtering AI/ML roles
    AI_ML_KEYWORDS = [
        "ai", "ml", "machine learning", "deep learning",
        "nlp", "llm", "gpt", "claude", "openai",
        "artificial intelligence", "neural", "model",
        "data science", "mlops", "langchain"
    ]
    
    # Remote indicators
    REMOTE_KEYWORDS = ["remote", "anywhere", "distributed", "wfh", "work from home"]
    
    # Seniority keywords
    SENIORITY_MAP = {
        SeniorityLevel.SENIOR: ["senior", "sr.", "lead", "staff", "principal"],
        SeniorityLevel.MID: ["mid-level", "intermediate"],
        SeniorityLevel.JUNIOR: ["junior", "jr.", "entry"],
    }

    def __init__(self):
        super().__init__("hn_algolia")

    def fetch(self) -> List[JobListing]:
        """Fetch recent Who is Hiring threads and extract listings."""
        # Search for "Ask HN: Who is hiring?" threads from last 60 days
        params = {
            "query": "Ask HN: Who is hiring?",
            "tags": "story",
            "numericFilters": f"created_at_i>{int((datetime.utcnow().timestamp() - 60*24*3600))}",
            "hitsPerPage": 5,
        }
        
        response = requests.get(self.API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        listings = []
        for hit in data.get("hits", []):
            story_id = hit.get("objectID")
            if story_id:
                listings.extend(self._fetch_thread_comments(story_id))
        
        return self._tag_source(listings)

    def _fetch_thread_comments(self, story_id: str) -> List[JobListing]:
        """Fetch comments from a Who is Hiring thread."""
        url = f"http://hn.algolia.com/api/v1/items/{story_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        listings = []
        for comment in data.get("children", []):
            listing = self._parse_comment(comment)
            if listing:
                listings.append(listing)
        
        return listings

    def _parse_comment(self, comment: dict) -> JobListing | None:
        """Parse a HN comment into a JobListing."""
        text = comment.get("text", "")
        if not text:
            return None
        
        # Check if it mentions AI/ML
        text_lower = text.lower()
        if not any(kw in text_lower for kw in self.AI_ML_KEYWORDS):
            return None
        
        # Extract company name (usually first line or bold text)
        company = self._extract_company(text)
        if not company:
            return None
        
        # Check if remote
        is_remote = any(kw in text_lower for kw in self.REMOTE_KEYWORDS)
        if not is_remote:
            return None  # Filter to remote-only
        
        # Extract role title
        role = self._extract_role(text)
        
        # Determine seniority
        seniority = self._extract_seniority(text)
        
        # Extract URL
        url = self._extract_url(text, comment.get("id"))
        
        return JobListing(
            company=company,
            role=role or "AI/ML Engineer",  # Default role
            description=text[:500],  # Truncate for storage
            location=LocationType.REMOTE,
            seniority=seniority,
            url=url,
        )

    def _extract_company(self, text: str) -> str | None:
        """Extract company name from HN comment."""
        # Try to find company in format "Company Name | Role"
        match = re.search(r'^([A-Z][A-Za-z0-9\s&\.]+?)\s*\|', text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Try bold text (first occurrence)
        match = re.search(r'<b>([^<]+)</b>', text)
        if match:
            return match.group(1).strip()
        
        # Fallback: first capitalized word sequence
        match = re.search(r'^([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})', text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        return None

    def _extract_role(self, text: str) -> str | None:
        """Extract role title from HN comment."""
        # Look for "Role:" or similar
        match = re.search(r'(?:Role|Position|Title):\s*([^\n<]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Look for common role patterns
        match = re.search(r'\b((?:Senior|Staff|Principal|Lead)?\s*(?:ML|AI|Machine Learning|Data Science|MLOps)\s*Engineer)\b', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None

    def _extract_seniority(self, text: str) -> SeniorityLevel:
        """Extract seniority level from text."""
        text_lower = text.lower()
        for level, keywords in self.SENIORITY_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return level
        return SeniorityLevel.UNKNOWN

    def _extract_url(self, text: str, comment_id: str) -> str:
        """Extract application URL or construct HN comment URL."""
        # Try to find https://... URLs
        match = re.search(r'https?://[^\s<>"]+', text)
        if match:
            return match.group(0)
        
        # Fallback: HN comment permalink
        return f"https://news.ycombinator.com/item?id={comment_id}"
