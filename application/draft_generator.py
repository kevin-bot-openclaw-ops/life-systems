"""
APPL-M1-1: Application Draft Generator

Generates role-specific cover letter drafts for qualified opportunities.

Features:
- 4 role-specific templates (fintech, ML research, platform, general)
- Automatic humanization (removes AI tells)
- Company + role personalization
- Jurek's authentic voice (direct, concise, technical)
- No em dashes, no LLM artifacts

Architecture:
  ApplicationCandidate → Template Selection → LLM Generation → Humanizer → DraftGenerated Event

Performance target: 10 drafts in <2 minutes
Quality target: 7/10 approved by Jurek with minor/no edits
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from application.acl_opportunity_qualifier import ApplicationCandidate
from application.humanizer import humanize, is_likely_ai, Humanizer

logger = logging.getLogger(__name__)


@dataclass
class DraftResult:
    """Result of draft generation."""

    listing_id: str
    company: str
    role: str
    draft_text: str
    word_count: int
    role_type: str
    ai_score: float  # 0-100, higher = more AI-like
    humanized: bool
    generated_at: datetime


class DraftGenerator:
    """
    Generates personalized cover letter drafts.
    
    Templates:
    - Fintech: Emphasizes banking experience, regulatory knowledge
    - ML Research: Emphasizes AI/ML depth, publication record
    - Platform: Emphasizes infrastructure, production systems
    - General: Balanced technical + domain experience
    """

    def __init__(self, humanize_enabled: bool = True):
        """
        Initialize draft generator.
        
        Args:
            humanize_enabled: Run humanizer on generated drafts (default True)
        """
        self.humanize_enabled = humanize_enabled
        self.humanizer = Humanizer()

    def generate(self, candidate: ApplicationCandidate) -> DraftResult:
        """
        Generate a cover letter draft for a candidate.
        
        Args:
            candidate: Qualified opportunity from OpportunityQualifier ACL
        
        Returns:
            DraftResult with generated text and metadata
        """
        # Select template based on role type
        template_func = {
            "fintech": self._generate_fintech_draft,
            "ml_research": self._generate_research_draft,
            "platform": self._generate_platform_draft,
            "general": self._generate_general_draft,
        }.get(candidate.role_type, self._generate_general_draft)

        # Generate draft
        draft_text = template_func(candidate)

        # Humanize if enabled
        if self.humanize_enabled:
            draft_text = humanize(draft_text)
            humanized = True
        else:
            humanized = False

        # Calculate AI score
        score_result = self.humanizer.score(draft_text)
        ai_score = score_result["score"]

        # Count words
        word_count = len(draft_text.split())

        result = DraftResult(
            listing_id=candidate.listing_id,
            company=candidate.company,
            role=candidate.role,
            draft_text=draft_text,
            word_count=word_count,
            role_type=candidate.role_type,
            ai_score=ai_score,
            humanized=humanized,
            generated_at=datetime.now(timezone.utc),
        )

        logger.info(
            f"Generated {candidate.role_type} draft for {candidate.company} "
            f"({word_count} words, AI score: {ai_score:.1f})"
        )

        return result

    def _generate_fintech_draft(self, candidate: ApplicationCandidate) -> str:
        """
        Fintech template: Banking + AI/ML bridge.
        
        Emphasis:
        - 15 years banking/fintech experience
        - Production systems at scale
        - Regulatory context (Basel III, AML, fraud)
        - AI/ML applied to real business problems
        """
        return f"""I'm applying for the {candidate.role} position at {candidate.company}.

I've spent 15 years building production systems for Tier 1 banks (Deutsche Bank, Credit Suisse, Citi). I know what production means in a regulated environment: auditable decisions, explainable models, zero downtime during trading hours.

Now I'm focused on AI/ML in financial services. I've built fraud detection systems with imbalanced datasets (99.8% legitimate transactions), RAG pipelines for regulatory document search (Basel III, IFRS 9), and agent orchestration for automated compliance checks.

The work I've done translates directly: production rigor, understanding risk, building systems that matter when they break. Banking taught me that 99% uptime isn't good enough. AI taught me that perfect accuracy isn't possible. The combination is rare.

My recent projects: ML fraud detection (XGBoost, 86% AUPRC), financial NLP sentiment analysis (FinBERT), and MLOps deployment pipelines. All production-grade, all tested, all documented.

I'm based in the Canary Islands, working remotely full-time. I can start immediately.

Portfolio: github.com/kevin-bot-openclaw-ops
"""

    def _generate_research_draft(self, candidate: ApplicationCandidate) -> str:
        """
        ML Research template: Cutting-edge AI focus.
        
        Emphasis:
        - Deep technical expertise (NLP, LLMs, RAG)
        - Research mindset (experiment, iterate, publish)
        - Modern ML stack (PyTorch, Transformers, LangChain)
        - Less banking, more AI depth
        """
        return f"""I'm interested in the {candidate.role} role at {candidate.company}.

My background is unconventional: 15 years in enterprise architecture, now building production AI systems. I come from a world where uptime and reliability matter more than state-of-the-art benchmarks. That foundation makes me effective at shipping research into production.

Recent work: RAG pipelines with FAISS vector search and sentence transformers, multi-agent orchestration using Claude API, financial NLP with FinBERT (sentiment classification + entity extraction), and MLOps deployment with MLflow model registry and drift monitoring.

I've reviewed for Springer (NLP conference track), which means I read papers and understand the theory. But I spend more time writing code than writing papers. I care about what works in production, not just what works in a notebook.

Tech stack: Python, PyTorch, LangChain, HuggingFace Transformers, FastAPI, Docker. Comfortable with academic rigor but focused on applied ML.

I work remotely from the Canary Islands. I can start immediately.

Portfolio: github.com/kevin-bot-openclaw-ops
"""

    def _generate_platform_draft(self, candidate: ApplicationCandidate) -> str:
        """
        Platform template: Infrastructure + ML.
        
        Emphasis:
        - Production deployment experience
        - Infrastructure (Docker, Kubernetes, CI/CD)
        - MLOps (experiment tracking, model registry, monitoring)
        - Enterprise background (scale, reliability)
        """
        return f"""I'm applying for the {candidate.role} position at {candidate.company}.

I've built production systems for 15 years—enterprise Java at scale for Tier 1 banks. That means: high availability, monitoring, CI/CD, incident response. I know what it takes to run systems that can't go down.

Now I'm doing that for ML systems. I've built MLOps pipelines with MLflow (experiment tracking, model registry, serving), drift monitoring with PSI (Population Stability Index), FastAPI model serving with <50ms p99 latency, and GitHub Actions CI/CD for automated testing and deployment.

My approach: treat ML like any other production system. Models need versioning, monitoring, rollback strategies, and A/B testing infrastructure. I've done this before with microservices. Doing it for ML isn't fundamentally different—just new failure modes.

Recent work: fraud detection model deployment (XGBoost in production), financial sentiment NLP API (FinBERT via FastAPI), and RAG pipeline with vector search (FAISS). All deployed, all monitored, all production-grade.

I work remotely from the Canary Islands. I can start immediately.

Portfolio: github.com/kevin-bot-openclaw-ops
"""

    def _generate_general_draft(self, candidate: ApplicationCandidate) -> str:
        """
        General template: Balanced approach.
        
        Emphasis:
        - Balanced banking + AI/ML background
        - Production focus
        - Portfolio highlights
        - Direct, no filler
        """
        return f"""I'm applying for the {candidate.role} position at {candidate.company}.

I've built production systems for 15 years in banking and fintech (Deutsche Bank, Credit Suisse, Citi). Now I'm focused on AI/ML engineering—applying those same standards to ML systems.

Recent projects: RAG pipeline with vector search (FAISS, sentence transformers), fraud detection ML (XGBoost, 86% AUPRC on imbalanced data), financial NLP (FinBERT sentiment + entity extraction), and MLOps deployment (MLflow, FastAPI, drift monitoring).

My strength is shipping AI into production. I know how to test probabilistic systems, monitor drift, version models, and deploy with confidence. Enterprise experience taught me that reliability matters more than novelty.

Tech stack: Python, PyTorch, LangChain, FastAPI, Docker, GitHub Actions. I write tests, document my work, and commit often.

I work remotely from the Canary Islands. I can start immediately.

Portfolio: github.com/kevin-bot-openclaw-ops
"""

    def generate_batch(self, candidates: List[ApplicationCandidate]) -> List[DraftResult]:
        """
        Generate drafts for multiple candidates.
        
        Args:
            candidates: List of qualified opportunities
        
        Returns:
            List of DraftResults
        """
        results = []
        
        for candidate in candidates:
            result = self.generate(candidate)
            results.append(result)
        
        logger.info(f"Generated {len(results)} drafts")
        return results

    def publish_event(self, result: DraftResult, output_path: str):
        """
        Publish DraftGenerated event to JSONL file.
        
        Args:
            result: DraftResult to publish
            output_path: Path to JSONL event file
        """
        event = {
            "event_type": "DraftGenerated",
            "version": "v1",
            "timestamp": result.generated_at.isoformat(),
            "context": "APPL",
            "payload": {
                "listing_id": result.listing_id,
                "company": result.company,
                "role": result.role,
                "draft_text": result.draft_text,
                "word_count": result.word_count,
                "role_type": result.role_type,
                "ai_score": round(result.ai_score, 1),
                "humanized": result.humanized,
                "generated_at": result.generated_at.isoformat(),
            },
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "a") as f:
            f.write(json.dumps(event) + "\n")

        logger.info(f"Published DraftGenerated event to {output_path}")


if __name__ == "__main__":
    # Example usage
    from application.acl_opportunity_qualifier import ApplicationCandidate
    from datetime import datetime

    # Sample candidate
    candidate = ApplicationCandidate(
        listing_id="test-001",
        company="FinML Bank",
        role="Senior ML Engineer - Fraud Detection",
        url="https://example.com/job",
        score=87.5,
        role_type="fintech",
        fintech_signals=["fraud", "banking"],
        aiml_signals=["ml", "machine learning", "python"],
        tech_stack=["Python", "PyTorch"],
        seniority="senior",
        salary_range=None,
        location="remote",
        qualified_at=datetime.now(),
        disc_context={},
    )

    generator = DraftGenerator()
    result = generator.generate(candidate)

    print(f"\n{'='*60}")
    print(f"Draft for: {result.company} - {result.role}")
    print(f"Type: {result.role_type} | Words: {result.word_count} | AI Score: {result.ai_score:.1f}")
    print(f"{'='*60}\n")
    print(result.draft_text)
    print(f"\n{'='*60}\n")
