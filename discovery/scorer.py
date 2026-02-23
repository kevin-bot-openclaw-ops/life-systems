"""
DISC-MVP-2: Job Scoring Engine

Consumes OpportunityDiscovered events and publishes OpportunityScored events.
Scoring based on:
- Remote match (hard filter)
- AI/ML relevance (keywords in role + description + tech_stack)
- Seniority match (senior/staff/principal preferred)
- Salary match (floor + target range)
- Fintech bonus (banking/fintech keywords)

Weights configurable via scorer_config.yaml.
"""

import re
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
import yaml
from pathlib import Path

from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    """Configurable scoring weights."""
    remote_match: float = Field(default=0.40, ge=0, le=1, description="Weight for remote work requirement")
    ai_ml_relevance: float = Field(default=0.30, ge=0, le=1, description="Weight for AI/ML keyword match")
    seniority_match: float = Field(default=0.15, ge=0, le=1, description="Weight for seniority level")
    salary_match: float = Field(default=0.10, ge=0, le=1, description="Weight for salary range")
    fintech_bonus: float = Field(default=0.05, ge=0, le=1, description="Weight for fintech/banking bonus")


class HardFilters(BaseModel):
    """Hard rejection filters."""
    require_remote: bool = Field(default=True, description="Reject non-remote roles")
    salary_floor_eur: Optional[int] = Field(default=120000, description="Minimum salary in EUR (reject if below)")


class ScoringConfig(BaseModel):
    """Complete scoring configuration."""
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    hard_filters: HardFilters = Field(default_factory=HardFilters)
    ai_ml_keywords: List[str] = Field(
        default_factory=lambda: [
            "ai", "ml", "machine learning", "artificial intelligence", "llm", "nlp",
            "deep learning", "neural network", "transformer", "gpt", "bert", "rag",
            "retrieval", "embedding", "vector", "langchain", "openai", "anthropic",
            "agent", "automation", "generative", "computer vision", "reinforcement learning"
        ]
    )
    fintech_keywords: List[str] = Field(
        default_factory=lambda: [
            "fintech", "banking", "financial", "credit", "payment", "trading",
            "risk", "compliance", "fraud", "kyc", "aml", "basel", "dodd-frank",
            "hedge fund", "investment", "securities", "blockchain", "crypto"
        ]
    )
    target_seniority: List[str] = Field(
        default_factory=lambda: ["senior", "staff", "principal"]
    )


class ScoreBreakdown(BaseModel):
    """Per-dimension score breakdown."""
    remote_match: float = Field(ge=0, le=100)
    ai_ml_relevance: float = Field(ge=0, le=100)
    seniority_match: float = Field(ge=0, le=100)
    salary_match: float = Field(ge=0, le=100)
    fintech_bonus: float = Field(ge=0, le=20)


class ScoredOpportunity(BaseModel):
    """Scored job listing with breakdown."""
    listing_id: str
    score: float = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    weights: ScoringWeights
    rejected: bool
    rejection_reason: Optional[str] = None


class JobScorer:
    """Job scoring engine with configurable weights."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize scorer with configuration.
        
        Args:
            config_path: Path to YAML config file (defaults to discovery/scorer_config.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "scorer_config.yaml"
        
        self.config = self._load_config(config_path)
        self._compile_patterns()
    
    def _load_config(self, config_path: Path) -> ScoringConfig:
        """Load configuration from YAML file."""
        if not config_path.exists():
            # Create default config if missing
            config = ScoringConfig()
            self._save_config(config, config_path)
            return config
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return ScoringConfig(**data)
    
    def _save_config(self, config: ScoringConfig, config_path: Path):
        """Save configuration to YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False)
    
    def _compile_patterns(self):
        """Compile regex patterns for keyword matching."""
        self.ai_ml_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.config.ai_ml_keywords) + r')\b',
            re.IGNORECASE
        )
        self.fintech_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.config.fintech_keywords) + r')\b',
            re.IGNORECASE
        )
    
    def score_listing(self, listing: Dict) -> ScoredOpportunity:
        """
        Score a job listing.
        
        Args:
            listing: OpportunityDiscovered payload
        
        Returns:
            ScoredOpportunity with score breakdown
        """
        payload = listing.get('payload', listing)
        listing_id = payload.get('listing_id', str(uuid.uuid4()))
        
        # Hard filters
        if self.config.hard_filters.require_remote:
            if payload.get('location', '').lower() != 'remote':
                return ScoredOpportunity(
                    listing_id=listing_id,
                    score=0,
                    breakdown=ScoreBreakdown(
                        remote_match=0,
                        ai_ml_relevance=0,
                        seniority_match=0,
                        salary_match=0,
                        fintech_bonus=0
                    ),
                    weights=self.config.weights,
                    rejected=True,
                    rejection_reason="Not remote"
                )
        
        # Salary floor check
        salary_range = payload.get('salary_range', {})
        if salary_range and self.config.hard_filters.salary_floor_eur:
            min_salary = salary_range.get('min', 0)
            currency = salary_range.get('currency', 'EUR')
            
            # Convert to EUR (simplified - production would use real FX rates)
            eur_conversion = {'EUR': 1.0, 'USD': 0.92, 'GBP': 1.15, 'PLN': 0.23}
            min_salary_eur = min_salary * eur_conversion.get(currency, 1.0)
            
            if min_salary_eur > 0 and min_salary_eur < self.config.hard_filters.salary_floor_eur:
                return ScoredOpportunity(
                    listing_id=listing_id,
                    score=0,
                    breakdown=ScoreBreakdown(
                        remote_match=100,  # Passed remote filter
                        ai_ml_relevance=0,
                        seniority_match=0,
                        salary_match=0,
                        fintech_bonus=0
                    ),
                    weights=self.config.weights,
                    rejected=True,
                    rejection_reason=f"Salary below floor: €{int(min_salary_eur):,} < €{self.config.hard_filters.salary_floor_eur:,}"
                )
        
        # Score dimensions
        remote_score = self._score_remote(payload)
        ai_ml_score = self._score_ai_ml_relevance(payload)
        seniority_score = self._score_seniority(payload)
        salary_score = self._score_salary(payload)
        fintech_score = self._score_fintech_bonus(payload)
        
        # Weighted total
        total_score = (
            remote_score * self.config.weights.remote_match +
            ai_ml_score * self.config.weights.ai_ml_relevance +
            seniority_score * self.config.weights.seniority_match +
            salary_score * self.config.weights.salary_match +
            fintech_score * self.config.weights.fintech_bonus
        )
        
        return ScoredOpportunity(
            listing_id=listing_id,
            score=round(total_score, 2),
            breakdown=ScoreBreakdown(
                remote_match=round(remote_score, 2),
                ai_ml_relevance=round(ai_ml_score, 2),
                seniority_match=round(seniority_score, 2),
                salary_match=round(salary_score, 2),
                fintech_bonus=round(fintech_score, 2)
            ),
            weights=self.config.weights,
            rejected=False,
            rejection_reason=None
        )
    
    def _score_remote(self, payload: Dict) -> float:
        """Score remote work compatibility (0-100)."""
        location = payload.get('location', '').lower()
        if location == 'remote':
            return 100.0
        elif location == 'hybrid':
            return 30.0
        else:
            return 0.0
    
    def _score_ai_ml_relevance(self, payload: Dict) -> float:
        """Score AI/ML keyword relevance (0-100)."""
        text = ' '.join([
            payload.get('role', ''),
            payload.get('description', ''),
            ' '.join(payload.get('tech_stack', []))
        ]).lower()
        
        matches = self.ai_ml_pattern.findall(text)
        unique_matches = len(set(matches))
        
        # Score based on unique keyword matches (0-10+ keywords)
        score = min(100, unique_matches * 10)
        return float(score)
    
    def _score_seniority(self, payload: Dict) -> float:
        """Score seniority level match (0-100)."""
        seniority = payload.get('seniority', '').lower()
        
        if seniority in ['principal', 'staff']:
            return 100.0
        elif seniority == 'senior':
            return 90.0
        elif seniority == 'mid':
            return 50.0
        elif seniority == 'junior':
            return 20.0
        else:
            # Unknown - check role title
            role = payload.get('role', '').lower()
            if any(level in role for level in ['principal', 'staff']):
                return 100.0
            elif 'senior' in role or 'lead' in role:
                return 90.0
            else:
                return 60.0  # Neutral for unknown
    
    def _score_salary(self, payload: Dict) -> float:
        """Score salary range (0-100)."""
        salary_range = payload.get('salary_range')
        if not salary_range:
            return 60.0  # Neutral for missing salary
        
        min_salary = salary_range.get('min', 0)
        max_salary = salary_range.get('max', 0)
        currency = salary_range.get('currency', 'EUR')
        
        # Convert to EUR
        eur_conversion = {'EUR': 1.0, 'USD': 0.92, 'GBP': 1.15, 'PLN': 0.23}
        conversion_rate = eur_conversion.get(currency, 1.0)
        
        min_eur = min_salary * conversion_rate
        max_eur = max_salary * conversion_rate
        
        # Target range: €150k+ = 100, €130-150k = 85, €120-130k = 70, <€120k = filtered
        if max_eur >= 150000:
            return 100.0
        elif max_eur > 130000:  # €130-150k range
            return 85.0
        elif max_eur >= 120000:
            return 70.0
        else:
            return 50.0  # Below target but above floor
    
    def _score_fintech_bonus(self, payload: Dict) -> float:
        """Score fintech/banking bonus (0-20)."""
        text = ' '.join([
            payload.get('company', ''),
            payload.get('role', ''),
            payload.get('description', '')
        ]).lower()
        
        matches = self.fintech_pattern.findall(text)
        unique_matches = len(set(matches))
        
        # Bonus points: 0-20 based on fintech keyword density
        score = min(20, unique_matches * 5)
        return float(score)
    
    def score_batch(self, listings: List[Dict]) -> List[ScoredOpportunity]:
        """Score a batch of listings."""
        return [self.score_listing(listing) for listing in listings]
    
    def publish_scored_event(self, scored: ScoredOpportunity, output_path: Path):
        """Publish OpportunityScored event to JSONL file."""
        event = {
            "event_type": "OpportunityScored",
            "version": "v1",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "context": "DISC",
            "payload": scored.model_dump()
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'a') as f:
            import json
            f.write(json.dumps(event) + '\n')
