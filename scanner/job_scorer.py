#!/usr/bin/env python3
"""
Life Systems v5 Job Scorer (DISC-MVP-2)
5-dimension scoring engine for job relevance.

Dimensions:
1. role_match: keyword matching (1-10)
2. remote_friendly: remote vs hybrid vs onsite (1-10)
3. salary_fit: distance from EUR 150k target (1-10)
4. tech_overlap: % match with Jurek's tech stack (1-10)
5. company_quality: known companies score higher (1-10)
"""
import sqlite3
import json
import re
import yaml
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass


# Database path
DB_PATH = Path("/var/lib/life-systems/life.db")

# Configuration file path
CONFIG_PATH = Path(__file__).parent / "scoring_config.yaml"


@dataclass
class ScoringConfig:
    """Scoring configuration."""
    # Target keywords (prioritized by importance)
    target_keywords_tier1: List[str] = None  # 3 points each
    target_keywords_tier2: List[str] = None  # 2 points each
    target_keywords_tier3: List[str] = None  # 1 point each
    
    # Jurek's skills (for tech_overlap calculation)
    skills: List[str] = None
    
    # Salary target
    target_salary_eur: int = 150000
    
    # Composite score weights (must sum to 1.0)
    weights: Dict[str, float] = None
    
    # Known quality companies (case-insensitive)
    known_companies: List[str] = None
    
    def __post_init__(self):
        # Defaults (used if YAML config not found)
        if self.target_keywords_tier1 is None:
            self.target_keywords_tier1 = [
                "mcp", "model context protocol", "llm", "large language model",
                "rag", "retrieval augmented generation", "ai engineer", "ml engineer"
            ]
        
        if self.target_keywords_tier2 is None:
            self.target_keywords_tier2 = [
                "mlops", "machine learning", "nlp", "deep learning",
                "python", "pytorch", "tensorflow", "langchain",
                "banking", "financial services", "fintech"
            ]
        
        if self.target_keywords_tier3 is None:
            self.target_keywords_tier3 = [
                "java", "spring", "kubernetes", "docker", "aws",
                "data science", "analytics", "sql", "api"
            ]
        
        if self.skills is None:
            self.skills = [
                "python", "java", "spring", "llm", "rag", "mcp",
                "langchain", "fastapi", "docker", "kubernetes",
                "sql", "postgresql", "banking", "financial services",
                "rest api", "microservices", "aws", "mlops"
            ]
        
        if self.weights is None:
            self.weights = {
                "role_match": 0.30,
                "remote_friendly": 0.25,
                "salary_fit": 0.20,
                "tech_overlap": 0.15,
                "company_quality": 0.10
            }
        
        if self.known_companies is None:
            self.known_companies = [
                "google", "microsoft", "amazon", "meta", "apple",
                "openai", "anthropic", "cohere", "mistral",
                "databricks", "hugging face", "scale ai",
                "stripe", "revolut", "wise", "n26",
                "jpmorgan", "goldman sachs", "morgan stanley",
                "deutsche bank", "citi", "hsbc"
            ]
    
    @classmethod
    def load_from_yaml(cls, config_path: Path = CONFIG_PATH) -> "ScoringConfig":
        """Load configuration from YAML file."""
        if not config_path.exists():
            print(f"Warning: Config file not found at {config_path}, using defaults")
            return cls()
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        return cls(
            target_keywords_tier1=data.get("target_keywords", {}).get("tier1", None),
            target_keywords_tier2=data.get("target_keywords", {}).get("tier2", None),
            target_keywords_tier3=data.get("target_keywords", {}).get("tier3", None),
            skills=data.get("skills", None),
            target_salary_eur=data.get("target_salary_eur", 150000),
            weights=data.get("weights", None),
            known_companies=data.get("known_companies", None)
        )


class JobScorer:
    """5-dimension job scoring engine."""
    
    def __init__(self, config: Optional[ScoringConfig] = None):
        self.config = config or ScoringConfig.load_from_yaml()
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
    
    def score_all_unscored_jobs(self) -> Dict:
        """Score all jobs that don't have scores yet."""
        cursor = self.conn.cursor()
        
        # Find unscored jobs
        cursor.execute("""
            SELECT j.* FROM jobs j
            LEFT JOIN scores s ON j.id = s.job_id
            WHERE s.id IS NULL
        """)
        
        jobs = cursor.fetchall()
        stats = {
            "jobs_scored": 0,
            "jobs_skipped": 0
        }
        
        for job in jobs:
            try:
                score = self._score_job(job)
                self._save_score(job["id"], score)
                stats["jobs_scored"] += 1
            except Exception as e:
                print(f"Error scoring job {job['id']}: {e}")
                stats["jobs_skipped"] += 1
        
        self.conn.commit()
        return stats
    
    def score_job_by_id(self, job_id: int) -> Dict[str, float]:
        """Score a specific job by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        score = self._score_job(job)
        self._save_score(job_id, score)
        self.conn.commit()
        
        return score
    
    def _score_job(self, job: sqlite3.Row) -> Dict[str, float]:
        """Calculate all 5 dimension scores for a job."""
        text = self._get_searchable_text(job)
        
        scores = {
            "role_match": self._score_role_match(text),
            "remote_friendly": self._score_remote_friendly(job),
            "salary_fit": self._score_salary_fit(job),
            "tech_overlap": self._score_tech_overlap(text),
            "company_quality": self._score_company_quality(job)
        }
        
        # Calculate composite score
        scores["composite"] = sum(
            scores[dim] * self.config.weights[dim]
            for dim in self.config.weights
        )
        
        return scores
    
    def _get_searchable_text(self, job: sqlite3.Row) -> str:
        """Combine title + description + requirements for keyword matching."""
        parts = [
            job["title"] or "",
            job["description"] or "",
            job["requirements"] or ""
        ]
        return " ".join(parts).lower()
    
    def _score_role_match(self, text: str) -> float:
        """Score 1-10 based on keyword matching (weighted by tier)."""
        points = 0.0
        max_points = 30.0  # Tier1: 3pts × 10 keywords = 30 max
        
        # Tier 1 keywords: 3 points each
        for keyword in self.config.target_keywords_tier1:
            if keyword.lower() in text:
                points += 3.0
        
        # Tier 2 keywords: 2 points each
        for keyword in self.config.target_keywords_tier2:
            if keyword.lower() in text:
                points += 2.0
        
        # Tier 3 keywords: 1 point each
        for keyword in self.config.target_keywords_tier3:
            if keyword.lower() in text:
                points += 1.0
        
        # Normalize to 1-10 scale
        score = min(10.0, 1.0 + (points / max_points) * 9.0)
        return round(score, 2)
    
    def _score_remote_friendly(self, job: sqlite3.Row) -> float:
        """Score remote friendliness: 10 = fully remote, 5 = hybrid, 1 = onsite."""
        location = (job["location"] or "").lower()
        title = (job["title"] or "").lower()
        description = (job["description"] or "").lower()
        
        # Check explicit remote flag from scanner
        if job["remote"] == 1:
            return 10.0
        
        # Keywords for fully remote
        remote_keywords = ["remote", "anywhere", "worldwide", "work from home", "wfh"]
        if any(kw in location or kw in title or kw in description for kw in remote_keywords):
            return 10.0
        
        # Keywords for hybrid
        hybrid_keywords = ["hybrid", "flexible", "2 days", "3 days", "office optional"]
        if any(kw in location or kw in description for kw in hybrid_keywords):
            return 5.0
        
        # Keywords for onsite
        onsite_keywords = ["onsite", "on-site", "office", "in-person", "relocate"]
        if any(kw in location or kw in description for kw in onsite_keywords):
            return 1.0
        
        # Default: assume hybrid if unclear
        return 5.0
    
    def _score_salary_fit(self, job: sqlite3.Row) -> float:
        """Score salary fit against EUR 150k target (1-10)."""
        target = self.config.target_salary_eur
        salary_min = job["salary_min"]
        salary_max = job["salary_max"]
        currency = job["salary_currency"] if job["salary_currency"] else "EUR"
        
        # If no salary data, return neutral score
        if not salary_min and not salary_max:
            return 5.0
        
        # Convert to EUR if needed (simple approximation)
        conversion_rates = {
            "EUR": 1.0,
            "USD": 0.92,
            "GBP": 1.17,
            "PLN": 0.23
        }
        rate = conversion_rates.get(currency, 1.0)
        
        # Use max salary if available, otherwise min
        salary_eur = (salary_max or salary_min) * rate
        
        # Score based on distance from target
        if salary_eur >= target:
            return 10.0
        elif salary_eur >= target * 0.8:  # 120k+
            return 8.0
        elif salary_eur >= target * 0.6:  # 90k+
            return 6.0
        elif salary_eur >= target * 0.4:  # 60k+
            return 4.0
        else:
            return 2.0
    
    def _score_tech_overlap(self, text: str) -> float:
        """Score % overlap between job requirements and Jurek's skills."""
        matches = 0
        for skill in self.config.skills:
            if skill.lower() in text:
                matches += 1
        
        overlap_pct = matches / len(self.config.skills)
        
        # Map percentage to 1-10 scale
        score = 1.0 + (overlap_pct * 9.0)
        return round(score, 2)
    
    def _score_company_quality(self, job: sqlite3.Row) -> float:
        """Basic heuristic: known companies score 8-10, others 5."""
        company = (job["company"] or "").lower()
        
        for known in self.config.known_companies:
            if known.lower() in company:
                return 9.0
        
        # Default: assume average quality
        return 5.0
    
    def _save_score(self, job_id: int, scores: Dict[str, float]):
        """Persist scores to database."""
        cursor = self.conn.cursor()
        
        # Delete existing score if any
        cursor.execute("DELETE FROM scores WHERE job_id = ?", (job_id,))
        
        # Insert new score
        cursor.execute("""
            INSERT INTO scores (
                job_id, total_score, role_match, remote_score,
                salary_fit, tech_overlap, company_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            int(scores["composite"] * 10),  # Scale to 100
            int(scores["role_match"] * 10),
            int(scores["remote_friendly"] * 10),
            int(scores["salary_fit"] * 10),
            int(scores["tech_overlap"] * 10),
            int(scores["company_quality"] * 10)
        ))
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """CLI entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--job-id":
        job_id = int(sys.argv[2])
        scorer = JobScorer()
        scores = scorer.score_job_by_id(job_id)
        print(f"Scored job {job_id}:")
        for dim, score in scores.items():
            print(f"  {dim}: {score:.2f}")
        scorer.close()
    else:
        scorer = JobScorer()
        stats = scorer.score_all_unscored_jobs()
        print(f"Scoring complete:")
        print(f"  Jobs scored: {stats['jobs_scored']}")
        print(f"  Jobs skipped: {stats['jobs_skipped']}")
        scorer.close()


if __name__ == "__main__":
    main()
