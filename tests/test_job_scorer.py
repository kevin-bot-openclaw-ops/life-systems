#!/usr/bin/env python3
"""
Tests for DISC-MVP-2: Job Scoring Engine
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path
import sys

# Add scanner directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scanner"))

from job_scorer import JobScorer, ScoringConfig


@pytest.fixture
def test_db():
    """Create a temporary test database with schema."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(db_path)
    
    # Create schema
    conn.executescript("""
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            url TEXT NOT NULL,
            location TEXT,
            remote BOOLEAN DEFAULT 0,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_currency TEXT DEFAULT 'EUR',
            description TEXT,
            requirements TEXT,
            posted_date TEXT,
            discovered_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            total_score INTEGER NOT NULL,
            role_match INTEGER,
            remote_score INTEGER,
            salary_fit INTEGER,
            tech_overlap INTEGER,
            company_size INTEGER,
            scored_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
    """)
    
    conn.commit()
    conn.close()
    
    # Patch DB_PATH
    import job_scorer
    original_db_path = job_scorer.DB_PATH
    job_scorer.DB_PATH = Path(db_path)
    
    yield db_path
    
    # Cleanup
    job_scorer.DB_PATH = original_db_path
    Path(db_path).unlink()


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "mcp_job": {
            "external_id": "mcp-001",
            "source": "test",
            "title": "Senior MCP Engineer - AI/ML",
            "company": "Anthropic",
            "url": "https://example.com/job1",
            "location": "Remote - Worldwide",
            "remote": 1,
            "salary_min": 140000,
            "salary_max": 180000,
            "salary_currency": "EUR",
            "description": "Build Model Context Protocol servers with LLM integration",
            "requirements": "Python, LangChain, RAG, banking domain experience",
            "discovered_at": "2026-03-05T00:00:00"
        },
        "hybrid_job": {
            "external_id": "hybrid-001",
            "source": "test",
            "title": "Machine Learning Engineer",
            "company": "Local Startup",
            "url": "https://example.com/job2",
            "location": "Warsaw - Hybrid 3 days/week",
            "remote": 0,
            "salary_min": 80000,
            "salary_max": 100000,
            "salary_currency": "EUR",
            "description": "ML models for fintech. Office 3 days/week.",
            "requirements": "Python, TensorFlow, SQL",
            "discovered_at": "2026-03-05T00:00:00"
        },
        "low_salary_job": {
            "external_id": "low-001",
            "source": "test",
            "title": "Junior Data Scientist",
            "company": "SmallCo",
            "url": "https://example.com/job3",
            "location": "Remote",
            "remote": 1,
            "salary_min": 40000,
            "salary_max": 50000,
            "salary_currency": "EUR",
            "description": "Entry-level data science role",
            "requirements": "Python, Pandas, basic ML",
            "discovered_at": "2026-03-05T00:00:00"
        },
        "perfect_match": {
            "external_id": "perfect-001",
            "source": "test",
            "title": "Staff AI Engineer - Banking AI",
            "company": "Goldman Sachs",
            "url": "https://example.com/job4",
            "location": "Remote - EU",
            "remote": 1,
            "salary_min": 150000,
            "salary_max": 200000,
            "salary_currency": "EUR",
            "description": "Build LLM-powered RAG systems for banking. MCP integration required. Work with financial services AI team on NLP and MLOps.",
            "requirements": "Python, Java, Spring, LangChain, banking domain, financial services, Kubernetes, AWS, MLOps",
            "discovered_at": "2026-03-05T00:00:00"
        }
    }


def insert_job(db_path: str, job_data: dict) -> int:
    """Helper to insert a job and return its ID."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO jobs (
            external_id, source, title, company, url, location, remote,
            salary_min, salary_max, salary_currency, description, requirements,
            discovered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data["external_id"], job_data["source"], job_data["title"],
        job_data["company"], job_data["url"], job_data["location"],
        job_data["remote"], job_data["salary_min"], job_data["salary_max"],
        job_data["salary_currency"], job_data["description"],
        job_data["requirements"], job_data["discovered_at"]
    ))
    
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return job_id


class TestJobScorer:
    """Test suite for job scoring engine."""
    
    def test_role_match_scoring(self, test_db, sample_job_data):
        """Test role_match dimension scoring."""
        job_id = insert_job(test_db, sample_job_data["mcp_job"])
        
        scorer = JobScorer()
        scores = scorer.score_job_by_id(job_id)
        scorer.close()
        
        # MCP job should score high on role_match (has tier1 keywords)
        assert scores["role_match"] >= 6.0, f"Expected role_match >= 6.0, got {scores['role_match']}"
        assert scores["role_match"] <= 10.0
    
    def test_remote_friendly_scoring(self, test_db, sample_job_data):
        """Test remote_friendly dimension scoring."""
        # Test fully remote job
        remote_id = insert_job(test_db, sample_job_data["mcp_job"])
        scorer = JobScorer()
        remote_scores = scorer.score_job_by_id(remote_id)
        
        # Test hybrid job
        hybrid_id = insert_job(test_db, sample_job_data["hybrid_job"])
        hybrid_scores = scorer.score_job_by_id(hybrid_id)
        scorer.close()
        
        assert remote_scores["remote_friendly"] == 10.0, "Remote job should score 10.0"
        assert hybrid_scores["remote_friendly"] == 5.0, "Hybrid job should score 5.0"
    
    def test_salary_fit_scoring(self, test_db, sample_job_data):
        """Test salary_fit dimension scoring."""
        # High salary job (180k EUR)
        high_id = insert_job(test_db, sample_job_data["mcp_job"])
        scorer = JobScorer()
        high_scores = scorer.score_job_by_id(high_id)
        
        # Low salary job (50k EUR)
        low_id = insert_job(test_db, sample_job_data["low_salary_job"])
        low_scores = scorer.score_job_by_id(low_id)
        scorer.close()
        
        assert high_scores["salary_fit"] >= 8.0, "180k job should score >= 8.0"
        assert low_scores["salary_fit"] <= 4.0, "50k job should score <= 4.0"
    
    def test_tech_overlap_scoring(self, test_db, sample_job_data):
        """Test tech_overlap dimension scoring."""
        # Perfect match job has many overlapping skills
        perfect_id = insert_job(test_db, sample_job_data["perfect_match"])
        scorer = JobScorer()
        perfect_scores = scorer.score_job_by_id(perfect_id)
        
        # Low match job has few overlapping skills
        low_id = insert_job(test_db, sample_job_data["low_salary_job"])
        low_scores = scorer.score_job_by_id(low_id)
        scorer.close()
        
        assert perfect_scores["tech_overlap"] >= 7.0, "Perfect match should have high tech overlap"
        assert low_scores["tech_overlap"] <= 5.0, "Low match should have low tech overlap"
    
    def test_company_quality_scoring(self, test_db, sample_job_data):
        """Test company_quality dimension scoring."""
        # Known company (Goldman Sachs)
        known_id = insert_job(test_db, sample_job_data["perfect_match"])
        scorer = JobScorer()
        known_scores = scorer.score_job_by_id(known_id)
        
        # Unknown company
        unknown_id = insert_job(test_db, sample_job_data["low_salary_job"])
        unknown_scores = scorer.score_job_by_id(unknown_id)
        scorer.close()
        
        assert known_scores["company_quality"] >= 8.0, "Known company should score high"
        assert unknown_scores["company_quality"] == 5.0, "Unknown company should score 5.0"
    
    def test_composite_score_calculation(self, test_db, sample_job_data):
        """Test composite score is weighted average."""
        job_id = insert_job(test_db, sample_job_data["perfect_match"])
        
        scorer = JobScorer()
        scores = scorer.score_job_by_id(job_id)
        scorer.close()
        
        # Calculate expected composite manually
        expected = (
            scores["role_match"] * 0.30 +
            scores["remote_friendly"] * 0.25 +
            scores["salary_fit"] * 0.20 +
            scores["tech_overlap"] * 0.15 +
            scores["company_quality"] * 0.10
        )
        
        assert abs(scores["composite"] - expected) < 0.01, "Composite should be weighted average"
    
    def test_perfect_match_job(self, test_db, sample_job_data):
        """Test that perfect match job scores very high overall."""
        job_id = insert_job(test_db, sample_job_data["perfect_match"])
        
        scorer = JobScorer()
        scores = scorer.score_job_by_id(job_id)
        scorer.close()
        
        # Perfect match should score >= 9.0 composite
        assert scores["composite"] >= 9.0, f"Perfect match should score >= 9.0, got {scores['composite']}"
        
        # All dimensions should be strong
        assert scores["role_match"] >= 8.0
        assert scores["remote_friendly"] == 10.0
        assert scores["salary_fit"] == 10.0
        assert scores["tech_overlap"] >= 7.0
        assert scores["company_quality"] >= 8.0
    
    def test_score_all_unscored_jobs(self, test_db, sample_job_data):
        """Test batch scoring of multiple jobs."""
        # Insert 3 jobs
        insert_job(test_db, sample_job_data["mcp_job"])
        insert_job(test_db, sample_job_data["hybrid_job"])
        insert_job(test_db, sample_job_data["low_salary_job"])
        
        scorer = JobScorer()
        stats = scorer.score_all_unscored_jobs()
        scorer.close()
        
        assert stats["jobs_scored"] == 3, "Should score all 3 jobs"
        assert stats["jobs_skipped"] == 0, "Should skip 0 jobs"
        
        # Verify scores were persisted
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scores")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 3, "Should have 3 score records in database"
    
    def test_score_persistence(self, test_db, sample_job_data):
        """Test that scores are correctly saved to database."""
        job_id = insert_job(test_db, sample_job_data["mcp_job"])
        
        scorer = JobScorer()
        scores = scorer.score_job_by_id(job_id)
        scorer.close()
        
        # Verify scores in database
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scores WHERE job_id = ?", (job_id,))
        db_score = cursor.fetchone()
        conn.close()
        
        assert db_score is not None, "Score should be saved"
        assert db_score["job_id"] == job_id
        assert db_score["total_score"] == int(scores["composite"] * 10)
        assert db_score["role_match"] == int(scores["role_match"] * 10)
        assert db_score["remote_score"] == int(scores["remote_friendly"] * 10)
    
    def test_custom_weights(self, test_db, sample_job_data):
        """Test that custom weights affect composite score."""
        job_id = insert_job(test_db, sample_job_data["mcp_job"])
        
        # Default weights
        scorer_default = JobScorer()
        scores_default = scorer_default.score_job_by_id(job_id)
        scorer_default.close()
        
        # Custom weights (prioritize remote heavily)
        custom_config = ScoringConfig()
        custom_config.weights = {
            "role_match": 0.10,
            "remote_friendly": 0.60,  # 60% weight on remote
            "salary_fit": 0.10,
            "tech_overlap": 0.10,
            "company_quality": 0.10
        }
        
        # Delete existing score
        conn = sqlite3.connect(test_db)
        conn.execute("DELETE FROM scores WHERE job_id = ?", (job_id,))
        conn.commit()
        conn.close()
        
        scorer_custom = JobScorer(config=custom_config)
        scores_custom = scorer_custom.score_job_by_id(job_id)
        scorer_custom.close()
        
        # Composite scores should differ
        assert scores_default["composite"] != scores_custom["composite"], "Different weights should produce different composites"
        
        # Remote job with 60% remote weight should score very high
        assert scores_custom["composite"] >= 8.9, "Remote job with 60% remote weight should score very high"
    
    def test_no_salary_data_handling(self, test_db):
        """Test that jobs without salary data get neutral salary_fit score."""
        job_data = {
            "external_id": "no-salary-001",
            "source": "test",
            "title": "ML Engineer",
            "company": "TestCo",
            "url": "https://example.com/job",
            "location": "Remote",
            "remote": 1,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "EUR",
            "description": "ML role with no salary info",
            "requirements": "Python",
            "discovered_at": "2026-03-05T00:00:00"
        }
        
        job_id = insert_job(test_db, job_data)
        
        scorer = JobScorer()
        scores = scorer.score_job_by_id(job_id)
        scorer.close()
        
        assert scores["salary_fit"] == 5.0, "No salary data should result in neutral score of 5.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
