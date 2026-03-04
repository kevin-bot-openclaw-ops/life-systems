#!/usr/bin/env python3
"""
Life Systems v5 Job Scanner (DISC-MVP-1)
Multi-source job discovery for AI/ML roles.
"""
import sqlite3
import requests
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


# Database path
DB_PATH = Path("/var/lib/life-systems/life.db")

# Target keywords for AI/ML jobs
TARGET_KEYWORDS = [
    "machine learning", "ml engineer", "ai engineer", "mlops",
    "llm", "nlp", "deep learning", "data scientist", "ai",
    "artificial intelligence", "mcp", "rag", "python", "pytorch",
    "tensorflow"
]


class JobScanner:
    """Multi-source job scanner."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.stats = {
            "sources_scanned": 0,
            "jobs_found": 0,
            "jobs_new": 0,
            "duplicates_skipped": 0,
            "errors": []
        }
    
    def scan_all_sources(self) -> Dict:
        """Scan all configured job sources."""
        start_time = time.time()
        
        print(f"[{datetime.now().isoformat()}] Starting job scan...")
        
        # Source 1: Remotive API
        try:
            self._scan_remotive()
        except Exception as e:
            self.stats["errors"].append(f"Remotive: {str(e)}")
            print(f"  ❌ Remotive error: {e}")
        
        # Source 2: RemoteOK API
        try:
            self._scan_remoteok()
        except Exception as e:
            self.stats["errors"].append(f"RemoteOK: {str(e)}")
            print(f"  ❌ RemoteOK error: {e}")
        
        # Source 3: HN Algolia (Who is Hiring)
        try:
            self._scan_hn_algolia()
        except Exception as e:
            self.stats["errors"].append(f"HN Algolia: {str(e)}")
            print(f"  ❌ HN Algolia error: {e}")
        
        duration = time.time() - start_time
        self.stats["duration_seconds"] = round(duration, 2)
        
        # Log to database
        self._log_scan_run()
        
        self.conn.close()
        
        print(f"[{datetime.now().isoformat()}] Scan complete:")
        print(f"  Sources: {self.stats['sources_scanned']}")
        print(f"  Jobs found: {self.stats['jobs_found']}")
        print(f"  New jobs: {self.stats['jobs_new']}")
        print(f"  Duplicates: {self.stats['duplicates_skipped']}")
        print(f"  Duration: {duration:.1f}s")
        
        return self.stats
    
    def _scan_remotive(self):
        """Scan Remotive API for remote AI/ML jobs."""
        print("  Scanning Remotive API...")
        self.stats["sources_scanned"] += 1
        
        url = "https://remotive.com/api/remote-jobs?category=software-dev"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        jobs = data.get("jobs", [])
        
        for job in jobs:
            # Filter for AI/ML keywords in title
            title = job.get("title", "").lower()
            if not any(kw in title for kw in TARGET_KEYWORDS):
                continue
            
            self._store_job({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("candidate_required_location", "Remote"),
                "salary_range": job.get("salary", ""),
                "description": job.get("description", ""),
                "source": "remotive",
                "source_url": job.get("url", "")
            })
        
        print(f"    ✓ Remotive: {len(jobs)} jobs checked")
    
    def _scan_remoteok(self):
        """Scan RemoteOK API for remote AI/ML jobs."""
        print("  Scanning RemoteOK API...")
        self.stats["sources_scanned"] += 1
        
        url = "https://remoteok.com/api"
        headers = {"User-Agent": "LifeSystems/1.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        jobs = response.json()
        
        # First item is metadata, skip it
        if jobs and isinstance(jobs[0], dict) and "legalnotice" in jobs[0]:
            jobs = jobs[1:]
        
        for job in jobs:
            # Filter for AI/ML keywords
            title = job.get("position", "").lower()
            tags = " ".join(job.get("tags", [])).lower()
            
            if not any(kw in title or kw in tags for kw in TARGET_KEYWORDS):
                continue
            
            # Parse salary if available
            salary_str = ""
            if job.get("salary_min") and job.get("salary_max"):
                salary_str = f"${job['salary_min']//1000}k-${job['salary_max']//1000}k"
            
            self._store_job({
                "title": job.get("position"),
                "company": job.get("company"),
                "location": job.get("location", "Remote"),
                "salary_range": salary_str,
                "description": job.get("description", ""),
                "source": "remoteok",
                "source_url": job.get("url", f"https://remoteok.com/remote-jobs/{job.get('id', '')}")
            })
        
        print(f"    ✓ RemoteOK: {len(jobs)} jobs checked")
    
    def _scan_hn_algolia(self):
        """Scan HN Algolia for 'Who is Hiring' posts."""
        print("  Scanning HN Algolia...")
        self.stats["sources_scanned"] += 1
        
        # Search for recent "Who is Hiring" threads
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": "who is hiring",
            "tags": "story",
            "hitsPerPage": 5
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        threads = data.get("hits", [])
        
        if not threads:
            print("    ⚠ No recent 'Who is Hiring' threads found")
            return
        
        # Get comments from most recent thread
        latest_thread = threads[0]
        thread_id = latest_thread.get("objectID")
        
        comments_url = f"https://hn.algolia.com/api/v1/items/{thread_id}"
        response = requests.get(comments_url, timeout=30)
        response.raise_for_status()
        
        thread_data = response.json()
        comments = thread_data.get("children", [])
        
        for comment in comments[:50]:  # Limit to first 50 comments
            text = comment.get("text", "").lower()
            
            # Filter for AI/ML keywords and "remote" indicator
            if not any(kw in text for kw in TARGET_KEYWORDS):
                continue
            if "remote" not in text and "anywhere" not in text:
                continue
            
            # Parse company name (usually in first line or starts with company name)
            lines = comment.get("text", "").split("\n")
            company = lines[0][:50] if lines else "HN Company"
            
            self._store_job({
                "title": f"AI/ML Position (HN: {comment.get('id')})",
                "company": company,
                "location": "Remote",
                "salary_range": "",
                "description": comment.get("text", "")[:500],  # Truncate long descriptions
                "source": "hn_algolia",
                "source_url": f"https://news.ycombinator.com/item?id={comment.get('id')}"
            })
        
        print(f"    ✓ HN Algolia: {len(comments)} comments checked")
    
    def _store_job(self, job_data: Dict):
        """Store job in database with deduplication."""
        self.stats["jobs_found"] += 1
        
        # Normalize for deduplication check
        normalized_title = job_data["title"].lower().strip()
        normalized_company = (job_data["company"] or "").lower().strip()
        
        # Check if job with same title+company already exists (within last 30 days)
        existing = self.conn.execute("""
            SELECT id FROM jobs 
            WHERE LOWER(TRIM(title)) = ? 
              AND LOWER(TRIM(COALESCE(company, ''))) = ?
              AND discovered_at >= datetime('now', '-30 days')
            LIMIT 1
        """, (normalized_title, normalized_company)).fetchone()
        
        if existing:
            self.stats["duplicates_skipped"] += 1
            return
        
        # Insert new job (let SQLite auto-increment the ID)
        try:
            self.conn.execute("""
                INSERT INTO jobs (title, company, location, salary_range, description, source, source_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                job_data["title"],
                job_data["company"],
                job_data["location"],
                job_data["salary_range"],
                job_data["description"],
                job_data["source"],
                job_data["source_url"]
            ))
            self.conn.commit()
            self.stats["jobs_new"] += 1
        except sqlite3.IntegrityError as e:
            # Duplicate caught by DB constraint
            self.stats["duplicates_skipped"] += 1
            print(f"    ⚠ Duplicate or constraint error: {e}")
    
    def _log_scan_run(self):
        """Log scan run to scans table (if exists, else skip)."""
        try:
            self.conn.execute("""
                INSERT INTO scans (sources, jobs_found, jobs_new, duration_seconds, errors)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.stats["sources_scanned"],
                self.stats["jobs_found"],
                self.stats["jobs_new"],
                self.stats["duration_seconds"],
                " | ".join(self.stats["errors"]) if self.stats["errors"] else None
            ))
            self.conn.commit()
        except sqlite3.OperationalError:
            # scans table doesn't exist (optional feature)
            pass


if __name__ == "__main__":
    scanner = JobScanner()
    stats = scanner.scan_all_sources()
    
    # Exit with error code if scan failed completely
    if stats["sources_scanned"] == 0:
        print("ERROR: No sources scanned successfully")
        exit(1)
    
    exit(0)
