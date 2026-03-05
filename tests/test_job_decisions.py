"""
Test job decision tracking (APPL-MVP-1).
"""
import pytest
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app

# Set up client with basic auth
client = TestClient(app)
# Use default credentials from main.py
auth = ("admin", "changeme")

@pytest.fixture
def setup_test_db():
    """Set up test database with sample data."""
    conn = sqlite3.connect("database/life.db")
    cursor = conn.cursor()
    
    # Clean up any existing test data
    cursor.execute("DELETE FROM decisions")
    cursor.execute("DELETE FROM scores")
    cursor.execute("DELETE FROM jobs")
    
    # Insert test jobs
    test_jobs = [
        ("job-1", "remotive", "Senior AI Engineer", "TechCorp", "https://example.com/job1", 
         "Remote", 1, 120000, 150000, "EUR", "Great AI role", "2026-03-01", "2026-03-01T10:00:00", "new"),
        ("job-2", "linkedin", "ML Platform Engineer", "DataCo", "https://example.com/job2",
         "Hybrid", 0, 100000, 130000, "EUR", "ML platform", "2026-03-02", "2026-03-02T10:00:00", "new"),
        ("job-3", "hn", "AI Research Scientist", "ResearchLab", "https://example.com/job3",
         "Remote", 1, 140000, 180000, "EUR", "Research role", "2026-03-03", "2026-03-03T10:00:00", "new"),
    ]
    
    for job in test_jobs:
        cursor.execute("""
            INSERT INTO jobs (external_id, source, title, company, url, location, remote, 
                            salary_min, salary_max, salary_currency, description, posted_date, 
                            discovered_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, job)
    
    # Insert test scores
    test_scores = [
        (1, 85, 8, 10, 9, 7, 8),  # job 1
        (2, 70, 7, 5, 7, 8, 7),   # job 2
        (3, 92, 9, 10, 10, 8, 9), # job 3
    ]
    
    for score in test_scores:
        cursor.execute("""
            INSERT INTO scores (job_id, total_score, role_match, remote_score, salary_fit, tech_overlap, company_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, score)
    
    conn.commit()
    conn.close()
    
    yield
    
    # Cleanup after test
    conn = sqlite3.connect("database/life.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM decisions")
    cursor.execute("DELETE FROM scores")
    cursor.execute("DELETE FROM jobs")
    conn.commit()
    conn.close()

def test_list_jobs_no_filter(setup_test_db):
    """Test listing all jobs without filters."""
    response = client.get("/api/jobs", auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 3
    assert len(data["jobs"]) == 3
    assert data["jobs"][0]["title"] == "AI Research Scientist"  # Latest first

def test_list_jobs_with_min_score(setup_test_db):
    """Test listing jobs with minimum score filter."""
    response = client.get("/api/jobs?min_score=80", auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 2
    assert len(data["jobs"]) == 2
    assert all(job["total_score"] >= 80 for job in data["jobs"])

def test_list_jobs_with_status_filter(setup_test_db):
    """Test listing jobs with status filter."""
    # First approve a job
    client.post("/api/jobs/1/decide", json={"action": "approve"}, auth=auth)
    
    # Then filter by approved status
    response = client.get("/api/jobs?status=approved", auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["jobs"][0]["status"] == "approved"

def test_decide_on_job_approve(setup_test_db):
    """Test approving a job."""
    response = client.post("/api/jobs/1/decide", json={
        "action": "approve",
        "reasoning": "Perfect match for my skills"
    }, auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert data["job_id"] == 1
    assert data["action"] == "approve"
    assert data["status"] == "approved"
    
    # Verify job status updated
    response = client.get("/api/jobs/1", auth=auth)
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "approved"
    assert job["action"] == "approve"
    assert job["decision_notes"] == "Perfect match for my skills"

def test_decide_on_job_skip(setup_test_db):
    """Test skipping a job."""
    response = client.post("/api/jobs/2/decide", json={
        "action": "skip",
        "reasoning": "Not remote enough"
    }, auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert data["action"] == "skip"
    assert data["status"] == "skipped"
    
    # Verify job status updated
    response = client.get("/api/jobs/2", auth=auth)
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "skipped"

def test_decide_on_job_save(setup_test_db):
    """Test saving a job for later."""
    response = client.post("/api/jobs/3/decide", json={
        "action": "save"
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["action"] == "save"
    assert data["status"] == "saved"
    
    # Verify job status updated
    response = client.get("/api/jobs/3")
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "saved"

def test_decide_on_nonexistent_job(setup_test_db):
    """Test decision on job that doesn't exist."""
    response = client.post("/api/jobs/999/decide", json={
        "action": "approve"
    }, auth=auth)
    assert response.status_code == 404

def test_decide_with_invalid_action(setup_test_db):
    """Test decision with invalid action."""
    response = client.post("/api/jobs/1/decide", json={
        "action": "reject"  # Not in allowed list
    }, auth=auth)
    assert response.status_code == 422  # Validation error

def test_filter_by_status_combinations(setup_test_db):
    """Test various status filter combinations."""
    # Approve one, skip one, save one
    client.post("/api/jobs/1/decide", json={"action": "approve"}, auth=auth)
    client.post("/api/jobs/2/decide", json={"action": "skip"}, auth=auth)
    client.post("/api/jobs/3/decide", json={"action": "save"}, auth=auth)
    
    # Test approved filter
    response = client.get("/api/jobs?status=approved", auth=auth)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    
    # Test skipped filter
    response = client.get("/api/jobs?status=skipped", auth=auth)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    
    # Test saved filter
    response = client.get("/api/jobs?status=saved", auth=auth)
    assert response.status_code == 200
    assert response.json()["total"] == 1

def test_pagination(setup_test_db):
    """Test pagination of job list."""
    response = client.get("/api/jobs?limit=2", auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["jobs"]) == 2
    assert data["total"] == 3
    
    # Test offset
    response = client.get("/api/jobs?limit=2&skip=2", auth=auth)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["jobs"]) == 1
    assert data["total"] == 3

def test_decision_count_trackable(setup_test_db):
    """Test that decision count is trackable for CAREER-2 metric."""
    # Make several decisions
    client.post("/api/jobs/1/decide", json={"action": "approve"}, auth=auth)
    client.post("/api/jobs/2/decide", json={"action": "skip"}, auth=auth)
    client.post("/api/jobs/3/decide", json={"action": "save"}, auth=auth)
    
    # Query decisions table directly
    conn = sqlite3.connect("database/life.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM decisions")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
