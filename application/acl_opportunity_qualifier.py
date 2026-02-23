"""
APPL-M1-1: OpportunityQualifier ACL

Anti-Corruption Layer between DISC and APPL contexts.

Input: OpportunityScored events from DISC-MVP-2
Output: ApplicationCandidate (APPL internal model)

Purpose:
- Filters scored listings above acceptance threshold
- Translates DISC domain model to APPL domain model
- Isolates APPL from DISC schema changes
- Enforces context boundary (APPL never sees raw OpportunityDiscovered)

Architecture:
  DISC-MVP-2 → OpportunityScored → [ACL] → ApplicationCandidate → Draft Generator
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ApplicationCandidate:
    """
    APPL context's internal representation of a qualified opportunity.
    
    Isolated from DISC schema changes. Only contains what draft generator needs.
    """

    listing_id: str
    company: str
    role: str
    url: str
    score: float
    
    # Role classification for template selection
    role_type: str  # "fintech", "ml_research", "platform", "general"
    
    # Signals for draft personalization
    fintech_signals: List[str]  # Detected fintech keywords from DISC
    aiml_signals: List[str]     # Detected AI/ML keywords
    tech_stack: List[str]       # Tech stack from listing
    seniority: str              # Role seniority level
    
    # Optional fields
    salary_range: Optional[str]
    location: str
    
    # Metadata
    qualified_at: datetime
    disc_context: Dict  # Opaque reference to original DISC event (for audit)


class OpportunityQualifier:
    """
    ACL: Translates DISC OpportunityScored → APPL ApplicationCandidate.
    
    Responsibilities:
    1. Filter by score threshold
    2. Classify role type (fintech, ML research, platform, general)
    3. Extract signals for personalization
    4. Translate schema
    """

    def __init__(self, score_threshold: float = 60.0):
        """
        Initialize ACL with score threshold.
        
        Args:
            score_threshold: Minimum score to qualify (default 60)
        """
        self.score_threshold = score_threshold

    def qualify(self, scored_event: Dict) -> Optional[ApplicationCandidate]:
        """
        Qualify an OpportunityScored event.
        
        Args:
            scored_event: Full OpportunityScored event dict
        
        Returns:
            ApplicationCandidate if qualified, None if rejected
        """
        payload = scored_event.get("payload", {})
        
        # Filter 1: Check verdict
        if payload.get("verdict") != "accept":
            logger.debug(f"Rejected by verdict: {payload.get('company')} - {payload.get('rejection_reason')}")
            return None
        
        # Filter 2: Check score threshold
        score = payload.get("score", 0)
        if score < self.score_threshold:
            logger.debug(f"Rejected by score: {payload.get('company')} (score: {score})")
            return None
        
        # Extract signals from dimensions
        dimensions = payload.get("dimensions", {})
        
        # Fintech signals
        fintech_dim = dimensions.get("fintech_bonus", {})
        fintech_reason = fintech_dim.get("reason", "")
        fintech_signals = self._extract_keywords_from_reason(fintech_reason)
        
        # AI/ML signals
        aiml_dim = dimensions.get("ai_ml_relevance", {})
        aiml_reason = aiml_dim.get("reason", "")
        aiml_signals = self._extract_keywords_from_reason(aiml_reason)
        
        # Classify role type
        role = payload.get("role", "")
        company = payload.get("company", "")
        role_type = self._classify_role_type(role, company, fintech_signals, aiml_signals)
        
        # Build ApplicationCandidate
        candidate = ApplicationCandidate(
            listing_id=payload.get("listing_id"),
            company=company,
            role=role,
            url=payload.get("url"),
            score=score,
            role_type=role_type,
            fintech_signals=fintech_signals,
            aiml_signals=aiml_signals,
            tech_stack=[],  # Tech stack not in OpportunityScored schema yet
            seniority=self._extract_seniority(role),
            salary_range=None,  # Not in OpportunityScored schema
            location="remote",  # Hard filter in DISC ensures this
            qualified_at=datetime.now(),
            disc_context={"event_id": scored_event.get("timestamp"), "score": score},
        )
        
        logger.info(f"Qualified: {company} - {role} (score: {score}, type: {role_type})")
        return candidate

    def _extract_keywords_from_reason(self, reason: str) -> List[str]:
        """
        Extract keywords from a dimension's reason field.
        
        Example: "3 fintech keywords: banking, fraud, payments" → ["banking", "fraud", "payments"]
        """
        if not reason or ":" not in reason:
            return []
        
        # Look for pattern: "X keywords: word1, word2, word3"
        if "keywords:" in reason.lower():
            parts = reason.split(":")
            if len(parts) >= 2:
                keywords_str = parts[1].strip()
                # Split by comma, strip whitespace
                keywords = [kw.strip() for kw in keywords_str.split(",")]
                return [kw for kw in keywords if kw]
        
        return []

    def _classify_role_type(
        self, role: str, company: str, fintech_signals: List[str], aiml_signals: List[str]
    ) -> str:
        """
        Classify role into type for template selection.
        
        Types:
        - fintech: Banking/fintech companies or fraud/payments in role
        - ml_research: Research-heavy, cutting-edge ML
        - platform: Infrastructure, MLOps, platform engineering
        - general: Default
        """
        role_lower = role.lower()
        company_lower = company.lower()
        
        # Fintech classification
        fintech_role_keywords = ["fraud", "payment", "banking", "financial", "trading", "aml", "kyc"]
        fintech_company_keywords = ["bank", "fintech", "stripe", "jpmorgan", "goldman", "revolut"]
        
        is_fintech_role = any(kw in role_lower for kw in fintech_role_keywords)
        is_fintech_company = any(kw in company_lower for kw in fintech_company_keywords)
        has_fintech_signals = len(fintech_signals) >= 2
        
        if is_fintech_role or is_fintech_company or has_fintech_signals:
            return "fintech"
        
        # ML Research classification
        research_keywords = ["research", "scientist", "phd", "nlp", "computer vision", "llm", "foundation model"]
        is_research = any(kw in role_lower for kw in research_keywords)
        
        if is_research:
            return "ml_research"
        
        # Platform classification
        platform_keywords = ["platform", "infrastructure", "mlops", "devops", "sre", "cloud"]
        is_platform = any(kw in role_lower for kw in platform_keywords)
        
        if is_platform:
            return "platform"
        
        # Default
        return "general"

    def _extract_seniority(self, role: str) -> str:
        """Extract seniority level from role title."""
        role_lower = role.lower()
        
        if any(kw in role_lower for kw in ["principal", "staff", "architect"]):
            return "principal"
        elif "senior" in role_lower or "sr" in role_lower:
            return "senior"
        elif any(kw in role_lower for kw in ["lead", "manager"]):
            return "lead"
        else:
            return "unknown"

    def qualify_batch(self, scored_events: List[Dict]) -> List[ApplicationCandidate]:
        """
        Qualify a batch of OpportunityScored events.
        
        Args:
            scored_events: List of OpportunityScored event dicts
        
        Returns:
            List of ApplicationCandidates (only qualified listings)
        """
        candidates = []
        
        for event in scored_events:
            candidate = self.qualify(event)
            if candidate:
                candidates.append(candidate)
        
        logger.info(f"Qualified {len(candidates)}/{len(scored_events)} opportunities")
        return candidates


if __name__ == "__main__":
    # Example usage
    import json
    
    # Sample OpportunityScored event
    sample_event = {
        "event_type": "OpportunityScored",
        "version": "v1",
        "timestamp": "2026-02-23T06:00:00Z",
        "context": "DISC",
        "payload": {
            "listing_id": "test-001",
            "company": "FinML Bank",
            "role": "Senior ML Engineer - Fraud Detection",
            "url": "https://example.com/job",
            "score": 87.5,
            "dimensions": {
                "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                "ai_ml_relevance": {"score": 85, "weight": 0.35, "reason": "4 primary + 3 secondary keywords"},
                "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                "salary": {"score": 100, "weight": 0.10, "reason": "150000 EUR (>= target)"},
                "fintech_bonus": {"score": 60, "weight": 0.05, "reason": "2 fintech keywords: fraud, banking"},
            },
            "verdict": "accept",
        },
    }
    
    qualifier = OpportunityQualifier()
    candidate = qualifier.qualify(sample_event)
    
    if candidate:
        print(f"✅ Qualified: {candidate.company} - {candidate.role}")
        print(f"   Score: {candidate.score}")
        print(f"   Type: {candidate.role_type}")
        print(f"   Fintech signals: {candidate.fintech_signals}")
        print(f"   AI/ML signals: {candidate.aiml_signals}")
    else:
        print("❌ Not qualified")
