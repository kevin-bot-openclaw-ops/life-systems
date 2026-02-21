"""Job scoring engine for DISC context."""

import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    """Configurable weights for scoring dimensions."""
    remote_match: float = Field(default=0.35, ge=0, le=1)
    ai_ml_relevance: float = Field(default=0.30, ge=0, le=1)
    seniority_match: float = Field(default=0.20, ge=0, le=1)
    salary_match: float = Field(default=0.10, ge=0, le=1)
    fintech_bonus: float = Field(default=0.05, ge=0, le=1)

    def validate_sum(self) -> bool:
        """Ensure weights sum to 1.0 (excluding bonus)."""
        base_sum = (
            self.remote_match + 
            self.ai_ml_relevance + 
            self.seniority_match + 
            self.salary_match + 
            self.fintech_bonus
        )
        return abs(base_sum - 1.0) < 0.01


class ScoreBreakdown(BaseModel):
    """Per-dimension scores."""
    remote_match: float = Field(ge=0, le=100)
    ai_ml_relevance: float = Field(ge=0, le=100)
    seniority_match: float = Field(ge=0, le=100)
    salary_match: float = Field(ge=0, le=100)
    fintech_bonus: float = Field(ge=0, le=20)


class ScoredJob(BaseModel):
    """Scored job listing."""
    listing_id: str
    score: float = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    weights: ScoringWeights
    rejected: bool
    rejection_reason: Optional[str] = None


class OpportunityScored(BaseModel):
    """OpportunityScored event (DISC context)."""
    event_type: str = "OpportunityScored"
    version: str = "v1"
    timestamp: str
    context: str = "DISC"
    payload: ScoredJob


class JobScorer:
    """Scores job listings based on configurable weights."""

    # AI/ML keywords for relevance scoring
    AI_ML_KEYWORDS = {
        'high': [
            'llm', 'large language model', 'gpt', 'claude', 'openai',
            'machine learning engineer', 'ml engineer', 'ai engineer',
            'deep learning', 'neural network', 'transformer',
            'rag', 'retrieval augmented generation',
            'langchain', 'llama', 'bert', 'embeddings',
            'mlops', 'model serving', 'ml platform'
        ],
        'medium': [
            'machine learning', 'ai', 'artificial intelligence',
            'nlp', 'natural language processing', 'computer vision',
            'data science', 'pytorch', 'tensorflow', 'scikit-learn',
            'hugging face', 'ml', 'model training', 'inference'
        ],
        'low': [
            'python', 'statistics', 'data', 'analytics',
            'algorithm', 'optimization', 'prediction'
        ]
    }

    # Fintech keywords for bonus scoring
    FINTECH_KEYWORDS = [
        'bank', 'banking', 'fintech', 'financial services',
        'payment', 'trading', 'credit', 'lending', 'insurance',
        'fraud detection', 'aml', 'kyc', 'compliance',
        'deutsche bank', 'jpmorgan', 'goldman sachs', 'credit suisse',
        'visa', 'mastercard', 'paypal', 'stripe', 'square'
    ]

    def __init__(self, weights: ScoringWeights, salary_floor: Optional[int] = 100000):
        """
        Initialize scorer.

        Args:
            weights: Scoring dimension weights
            salary_floor: Minimum acceptable salary in EUR (converted from other currencies)
        """
        self.weights = weights
        self.salary_floor = salary_floor

        # Exchange rates (approx, for filtering)
        self.exchange_rates = {
            'EUR': 1.0,
            'USD': 0.93,  # 1 USD = 0.93 EUR
            'GBP': 1.17,  # 1 GBP = 1.17 EUR
            'PLN': 0.23   # 1 PLN = 0.23 EUR
        }

    def score_listing(self, listing: Dict) -> ScoredJob:
        """
        Score a job listing.

        Args:
            listing: OpportunityDiscovered payload

        Returns:
            ScoredJob with calculated score and breakdown
        """
        # Hard filters first
        rejected, rejection_reason = self._apply_hard_filters(listing)

        if rejected:
            return ScoredJob(
                listing_id=listing['listing_id'],
                score=0.0,
                breakdown=ScoreBreakdown(
                    remote_match=0.0,
                    ai_ml_relevance=0.0,
                    seniority_match=0.0,
                    salary_match=0.0,
                    fintech_bonus=0.0
                ),
                weights=self.weights,
                rejected=True,
                rejection_reason=rejection_reason
            )

        # Calculate dimension scores
        remote_score = self._score_remote(listing.get('location', ''))
        ai_ml_score = self._score_ai_ml_relevance(listing.get('role', ''), listing.get('description', ''), listing.get('tech_stack', []))
        seniority_score = self._score_seniority(listing.get('seniority', 'unknown'), listing.get('role', ''))
        salary_score = self._score_salary(listing.get('salary_range'))
        fintech_score = self._score_fintech(listing.get('company', ''), listing.get('description', ''))

        breakdown = ScoreBreakdown(
            remote_match=remote_score,
            ai_ml_relevance=ai_ml_score,
            seniority_match=seniority_score,
            salary_match=salary_score,
            fintech_bonus=fintech_score
        )

        # Weighted final score
        final_score = (
            remote_score * self.weights.remote_match +
            ai_ml_score * self.weights.ai_ml_relevance +
            seniority_score * self.weights.seniority_match +
            salary_score * self.weights.salary_match +
            fintech_score * self.weights.fintech_bonus
        )

        return ScoredJob(
            listing_id=listing['listing_id'],
            score=round(final_score, 2),
            breakdown=breakdown,
            weights=self.weights,
            rejected=False,
            rejection_reason=None
        )

    def _apply_hard_filters(self, listing: Dict) -> Tuple[bool, Optional[str]]:
        """Apply hard rejection filters."""
        # Remote-only mandatory
        location = listing.get('location', '').lower()
        if location != 'remote':
            return True, f"Not remote (location={location})"

        # Salary floor (if provided)
        if self.salary_floor and listing.get('salary_range'):
            salary_eur = self._convert_salary_to_eur(listing['salary_range'])
            if salary_eur and salary_eur < self.salary_floor:
                return True, f"Below salary floor (€{salary_eur:,} < €{self.salary_floor:,})"

        return False, None

    def _convert_salary_to_eur(self, salary_range: Dict) -> Optional[float]:
        """Convert salary to EUR for comparison."""
        if not salary_range or 'max' not in salary_range:
            return None

        max_salary = salary_range['max']
        currency = salary_range.get('currency', 'EUR')
        rate = self.exchange_rates.get(currency, 1.0)

        return max_salary * rate

    def _score_remote(self, location: str) -> float:
        """Score remote work alignment (0-100)."""
        location_lower = location.lower()
        if location_lower == 'remote':
            return 100.0
        elif location_lower == 'hybrid':
            return 20.0  # Penalty for hybrid
        else:
            return 0.0

    def _score_ai_ml_relevance(self, role: str, description: str, tech_stack: List[str]) -> float:
        """Score AI/ML relevance (0-100)."""
        text = f"{role} {description} {' '.join(tech_stack)}".lower()

        # Count keyword matches by tier
        high_matches = sum(1 for kw in self.AI_ML_KEYWORDS['high'] if kw in text)
        medium_matches = sum(1 for kw in self.AI_ML_KEYWORDS['medium'] if kw in text)
        low_matches = sum(1 for kw in self.AI_ML_KEYWORDS['low'] if kw in text)

        # Weighted scoring
        score = (high_matches * 30) + (medium_matches * 15) + (low_matches * 5)

        # Cap at 100
        return min(score, 100.0)

    def _score_seniority(self, seniority: str, role: str) -> float:
        """Score seniority match (0-100)."""
        seniority_lower = seniority.lower()
        role_lower = role.lower()

        # Target: senior, staff, principal
        if seniority_lower in ['senior', 'staff', 'principal']:
            return 100.0
        
        # Check role title for seniority indicators
        if any(word in role_lower for word in ['senior', 'staff', 'principal', 'lead', 'architect']):
            return 100.0

        # Mid-level acceptable
        if seniority_lower == 'mid' or 'mid' in role_lower:
            return 60.0

        # Junior/unknown penalty
        if seniority_lower == 'junior' or 'junior' in role_lower:
            return 20.0

        # Unknown seniority - neutral
        return 50.0

    def _score_salary(self, salary_range: Optional[Dict]) -> float:
        """Score salary alignment (0-100)."""
        if not salary_range or 'max' not in salary_range:
            return 50.0  # Neutral for missing data

        salary_eur = self._convert_salary_to_eur(salary_range)
        if not salary_eur:
            return 50.0

        # Target: €150k+
        # Score curve: 100k=50, 130k=75, 150k=100, 200k+=100
        if salary_eur >= 150000:
            return 100.0
        elif salary_eur >= 130000:
            return 75.0
        elif salary_eur >= 100000:
            return 50.0
        else:
            return 25.0

    def _score_fintech(self, company: str, description: str) -> float:
        """Score fintech bonus (0-20)."""
        text = f"{company} {description}".lower()

        matches = sum(1 for kw in self.FINTECH_KEYWORDS if kw in text)

        # Bonus scoring (max 20 points)
        if matches >= 3:
            return 20.0
        elif matches >= 2:
            return 15.0
        elif matches >= 1:
            return 10.0
        else:
            return 0.0

    def publish_event(self, scored_job: ScoredJob) -> OpportunityScored:
        """Wrap scored job in OpportunityScored event."""
        return OpportunityScored(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            payload=scored_job
        )
