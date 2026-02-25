"""
SQLite database layer for Life Systems.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path


class Database:
    """SQLite database manager."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_jobs(
        self,
        limit: int = 10,
        offset: int = 0,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get scored job listings."""
        query = """
            SELECT 
                j.id, j.title, j.company, j.location, j.remote,
                s.score, j.discovered_at, j.sources
            FROM jobs j
            LEFT JOIN scores s ON j.id = s.job_id
            WHERE 1=1
        """
        params = []
        
        if min_score is not None:
            query += " AND s.score >= ?"
            params.append(min_score)
        
        query += " ORDER BY s.score DESC, j.discovered_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        jobs = []
        for row in rows:
            job = dict(row)
            job['sources'] = json.loads(job['sources']) if job['sources'] else []
            jobs.append(job)
        
        return jobs
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single job with full details."""
        query = """
            SELECT 
                j.*, s.score, s.score_breakdown
            FROM jobs j
            LEFT JOIN scores s ON j.id = s.job_id
            WHERE j.id = ?
        """
        cursor = self.conn.execute(query, (job_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        job = dict(row)
        job['sources'] = json.loads(job['sources']) if job['sources'] else []
        job['tech_stack'] = json.loads(job['tech_stack']) if job['tech_stack'] else []
        if job.get('score_breakdown'):
            job['score_breakdown'] = json.loads(job['score_breakdown'])
        
        return job
    
    def get_draft(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get existing draft for a job."""
        query = "SELECT * FROM drafts WHERE job_id = ? ORDER BY created_at DESC LIMIT 1"
        cursor = self.conn.execute(query, (job_id,))
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def save_draft(self, job_id: str, text: str) -> str:
        """Save a draft cover letter."""
        draft_id = f"draft_{job_id}_{int(datetime.utcnow().timestamp())}"
        query = """
            INSERT INTO drafts (id, job_id, text, created_at)
            VALUES (?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (draft_id, job_id, text, datetime.utcnow().isoformat())
        )
        self.conn.commit()
        return draft_id
    
    def save_decision(self, job_id: str, action: str, reason: Optional[str] = None):
        """Record a decision on a job."""
        decision_id = f"dec_{job_id}_{int(datetime.utcnow().timestamp())}"
        query = """
            INSERT INTO decisions (id, job_id, action, reason, decided_at)
            VALUES (?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (decision_id, job_id, action, reason, datetime.utcnow().isoformat())
        )
        self.conn.commit()
    
    def get_dashboard_state(self) -> Dict[str, Any]:
        """Get synthesized dashboard state."""
        # Get job counts
        cursor = self.conn.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]
        
        # Get today's jobs
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE discovered_at >= ?",
            (yesterday,)
        )
        jobs_today = cursor.fetchone()[0]
        
        # Get pending drafts
        cursor = self.conn.execute("""
            SELECT COUNT(DISTINCT j.id)
            FROM jobs j
            LEFT JOIN drafts d ON j.id = d.job_id
            LEFT JOIN decisions dec ON j.id = dec.job_id
            WHERE d.id IS NULL AND dec.id IS NULL
        """)
        drafts_pending = cursor.fetchone()[0]
        
        # Get career metrics
        cursor = self.conn.execute("SELECT COUNT(*) FROM jobs")
        discovered = cursor.fetchone()[0]
        
        cursor = self.conn.execute("""
            SELECT COUNT(DISTINCT job_id) FROM decisions WHERE action = 'approve'
        """)
        applied = cursor.fetchone()[0]
        
        # Get top opportunities
        top_jobs = self.get_jobs(limit=10, min_score=70.0)
        
        # Get last scan time
        cursor = self.conn.execute(
            "SELECT MAX(timestamp) FROM scans"
        )
        last_scan_row = cursor.fetchone()
        last_scan = last_scan_row[0] if last_scan_row[0] else None
        
        if last_scan:
            last_scan_dt = datetime.fromisoformat(last_scan)
            ago_seconds = (datetime.utcnow() - last_scan_dt).total_seconds()
            if ago_seconds < 3600:
                last_scan_ago = f"{int(ago_seconds / 60)} minutes ago"
            elif ago_seconds < 86400:
                last_scan_ago = f"{int(ago_seconds / 3600)} hours ago"
            else:
                last_scan_ago = f"{int(ago_seconds / 86400)} days ago"
        else:
            last_scan_ago = "never"
        
        # Calculate career score (simple heuristic)
        career_score = min(100, int(
            (applied / max(1, discovered) * 50) +  # Application rate
            (jobs_today * 5)  # Recent activity
        ))
        
        return {
            "career_score": career_score,
            "jobs_today": jobs_today,
            "drafts_pending": drafts_pending,
            "market_summary": f"{total_jobs} jobs discovered, {applied} applications sent",
            "last_scan": last_scan,
            "last_scan_ago": last_scan_ago,
            "career_metrics": {
                "discovered": discovered,
                "applied": applied,
                "responded": 0,  # TODO: integrate with email tracking
                "interviewing": 0,
                "offered": 0
            },
            "top_opportunities": top_jobs,
            "top_skills": [],  # TODO: integrate market intelligence
            "alerts": []
        }
    
    def get_latest_market_report(self) -> Optional[Dict[str, Any]]:
        """Get the most recent market report."""
        query = "SELECT * FROM market_reports ORDER BY generated_at DESC LIMIT 1"
        cursor = self.conn.execute(query)
        row = cursor.fetchone()
        
        if not row:
            return None
        
        report = dict(row)
        report['top_skills'] = json.loads(report['top_skills'])
        report['salary_ranges'] = json.loads(report['salary_ranges'])
        report['gap_analysis'] = json.loads(report['gap_analysis'])
        
        return report
    
    def save_scan_result(self, job_data: Dict[str, Any], score_data: Dict[str, Any]):
        """Save a scanned job and its score."""
        # Insert job
        job_query = """
            INSERT OR IGNORE INTO jobs (
                id, title, company, location, remote, description,
                salary_min, salary_max, currency, tech_stack, url,
                discovered_at, sources
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(job_query, (
            job_data['id'],
            job_data['title'],
            job_data['company'],
            job_data['location'],
            job_data.get('remote', True),
            job_data.get('description', ''),
            job_data.get('salary_min'),
            job_data.get('salary_max'),
            job_data.get('currency', 'EUR'),
            json.dumps(job_data.get('tech_stack', [])),
            job_data.get('url', ''),
            datetime.utcnow().isoformat(),
            json.dumps(job_data.get('sources', []))
        ))
        
        # Insert score
        score_query = """
            INSERT OR REPLACE INTO scores (
                job_id, score, score_breakdown, scored_at
            ) VALUES (?, ?, ?, ?)
        """
        self.conn.execute(score_query, (
            job_data['id'],
            score_data['score'],
            json.dumps(score_data.get('breakdown', {})),
            datetime.utcnow().isoformat()
        ))
        
        self.conn.commit()
    
    def record_scan(self, source: str, jobs_found: int):
        """Record a scan event."""
        query = """
            INSERT INTO scans (id, source, jobs_found, timestamp)
            VALUES (?, ?, ?, ?)
        """
        scan_id = f"scan_{source}_{int(datetime.utcnow().timestamp())}"
        self.conn.execute(
            query,
            (scan_id, source, jobs_found, datetime.utcnow().isoformat())
        )
        self.conn.commit()


def init_db(db_path: str):
    """Initialize database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            remote BOOLEAN NOT NULL,
            description TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            currency TEXT DEFAULT 'EUR',
            tech_stack TEXT,  -- JSON array
            url TEXT,
            discovered_at TEXT NOT NULL,
            sources TEXT  -- JSON array
        )
    """)
    
    # Scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            job_id TEXT PRIMARY KEY,
            score REAL NOT NULL,
            score_breakdown TEXT,  -- JSON object
            scored_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    
    # Drafts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    
    # Decisions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('approve', 'reject', 'defer')),
            reason TEXT,
            decided_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    
    # Market reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_reports (
            id TEXT PRIMARY KEY,
            generated_at TEXT NOT NULL,
            top_skills TEXT NOT NULL,  -- JSON array
            salary_ranges TEXT NOT NULL,  -- JSON object
            gap_analysis TEXT NOT NULL,  -- JSON array
            weekly_summary TEXT NOT NULL
        )
    """)
    
    # Scans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            jobs_found INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON jobs(discovered_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_action ON decisions(action)")
    
    conn.commit()
    conn.close()
