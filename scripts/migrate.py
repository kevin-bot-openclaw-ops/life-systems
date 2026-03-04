#!/usr/bin/env python3
"""
Life Systems v5 Database Migration Script
Idempotent, version-tracked schema management.

Usage:
    python scripts/migrate.py
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path("/var/lib/life-systems/life.db")
DB_VERSION = "v5.0.0"

# Schema definitions from EPIC-001 through EPIC-004
SCHEMA_SQL = """
-- EPIC-001: Dating Module
CREATE TABLE IF NOT EXISTS dates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    who TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('app', 'event', 'social')),
    quality INTEGER NOT NULL CHECK(quality BETWEEN 1 AND 10),
    went_well TEXT,
    improve TEXT,
    date_of DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dates_date_of ON dates(date_of);
CREATE INDEX IF NOT EXISTS idx_dates_who ON dates(who);
CREATE INDEX IF NOT EXISTS idx_dates_source ON dates(source);

-- EPIC-002: Career Advisor
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    salary_range TEXT,
    description TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'new' CHECK(status IN ('new', 'reviewed', 'approved', 'skipped', 'saved', 'applied', 'interviewing', 'offered', 'rejected', 'archived')),
    archived INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS job_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    role_match REAL CHECK(role_match BETWEEN 0 AND 10),
    remote_friendly REAL CHECK(remote_friendly BETWEEN 0 AND 10),
    salary_fit REAL CHECK(salary_fit BETWEEN 0 AND 10),
    tech_overlap REAL CHECK(tech_overlap BETWEEN 0 AND 10),
    company_quality REAL CHECK(company_quality BETWEEN 0 AND 10),
    composite REAL,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    action TEXT NOT NULL CHECK(action IN ('approve', 'skip', 'save')),
    reasoning TEXT,
    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE NOT NULL,
    top_skills TEXT,
    avg_salaries TEXT,
    remote_pct REAL,
    jobs_this_period INTEGER,
    one_liner TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON jobs(discovered_at);
CREATE INDEX IF NOT EXISTS idx_scores_composite ON job_scores(composite DESC);

-- EPIC-003: Location Optimizer
CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    is_current INTEGER DEFAULT 0,
    dating_pool INTEGER,
    ai_job_density INTEGER,
    cost_index REAL,
    lifestyle_score REAL CHECK(lifestyle_score BETWEEN 1 AND 10),
    community_score REAL CHECK(community_score BETWEEN 1 AND 10),
    composite_score REAL,
    data_source TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS city_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER NOT NULL REFERENCES cities(id),
    dimension TEXT NOT NULL,
    note TEXT NOT NULL,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- EPIC-004: Intelligence Layer
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('rules', 'weekly_ai', 'life_move')),
    domain TEXT,
    one_liner TEXT NOT NULL,
    data_table TEXT,
    actions TEXT,
    source_rule_ids TEXT,
    token_count INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    trigger_condition TEXT NOT NULL,
    min_data_points INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    last_fired TIMESTAMP,
    fire_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER REFERENCES analyses(id),
    rule_id TEXT REFERENCES rules(id),
    one_liner TEXT NOT NULL,
    data_table TEXT,
    goal_alignment TEXT,
    priority INTEGER,
    time_sensitive INTEGER DEFAULT 0,
    acted_on INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analyses_type ON analyses(type);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_recommendations_priority ON recommendations(priority);

-- Migration metadata table
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    """Initialize database with v5 schema."""
    # Ensure parent directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect and enable WAL mode
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Check if we need to migrate from old schema
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
    )
    existing_jobs = cursor.fetchone()
    
    if existing_jobs:
        print("⚠️  Found existing v4 tables - archiving as *_v4...")
        
        # Archive old tables
        old_tables = ['jobs', 'dates', 'decisions', 'job_scores', 'market_reports', 
                      'drafts', 'scans', 'scores']
        for table in old_tables:
            try:
                conn.execute(f"ALTER TABLE {table} RENAME TO {table}_v4")
                print(f"   ✅ Archived {table} → {table}_v4")
            except sqlite3.OperationalError:
                # Table doesn't exist, skip
                pass
        
        conn.commit()
    
    # Execute v5 schema
    conn.executescript(SCHEMA_SQL)
    
    # Record version
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
        (DB_VERSION,)
    )
    
    conn.commit()
    
    # Verify tables created
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"✅ Database initialized: {DB_PATH}")
    print(f"✅ Schema version: {DB_VERSION}")
    print(f"✅ WAL mode enabled")
    print(f"✅ Tables created ({len(tables)}):")
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   - {table}: {count} rows")
    
    conn.close()


def get_db_info():
    """Get current database version and table counts."""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # Get version
    try:
        version = conn.execute(
            "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        version = version[0] if version else "unknown"
    except sqlite3.OperationalError:
        version = "legacy"
    
    # Get table counts
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'schema_version' ORDER BY name"
    )
    tables = {}
    for row in cursor.fetchall():
        table_name = row[0]
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        tables[table_name] = count
    
    conn.close()
    
    return {
        "version": version,
        "tables": tables
    }


if __name__ == "__main__":
    print("Life Systems v5 Migration")
    print("=" * 50)
    
    # Check current state
    info = get_db_info()
    if info:
        print(f"Current version: {info['version']}")
        print(f"Existing tables: {len(info['tables'])}")
    else:
        print("Database does not exist yet")
    
    # Run migration
    print("\nRunning migration...")
    init_db()
    
    print("\n✅ Migration complete!")

# Add scans table for job scanner logging
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sources INTEGER NOT NULL,
    jobs_found INTEGER NOT NULL,
    jobs_new INTEGER NOT NULL,
    duration_seconds REAL,
    errors TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
