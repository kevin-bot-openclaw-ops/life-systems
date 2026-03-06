-- Life Systems SQLite Schema
-- Version: 1.0
-- Created: 2026-02-25

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
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

-- Scores table
CREATE TABLE IF NOT EXISTS scores (
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

-- Drafts table (AI-generated cover letters)
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    variant TEXT NOT NULL, -- ai_engineer, ml_platform, agent_architect, custom
    content TEXT NOT NULL,
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    edited_at TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Decisions table (user approvals/rejections)
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    action TEXT NOT NULL, -- approve, reject, defer
    decided_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Dates table (dating CRM)
CREATE TABLE IF NOT EXISTS dates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date_when TEXT NOT NULL,
    how_met TEXT NOT NULL, -- app, bachata, event, friends, other
    venue TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    attraction INTEGER CHECK(attraction >= 1 AND attraction <= 5),
    intellectual INTEGER CHECK(intellectual >= 1 AND intellectual <= 5),
    notes TEXT,
    next_step TEXT NOT NULL, -- see_again, maybe, no, scheduled
    follow_up_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Fitness table (gym streak tracking)
CREATE TABLE IF NOT EXISTS fitness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    completed BOOLEAN NOT NULL DEFAULT 0,
    rest_day BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Social events table (bachata, meetups, etc)
CREATE TABLE IF NOT EXISTS social_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL, -- bachata, meetup, expat_event, other
    venue TEXT NOT NULL,
    date_when TEXT NOT NULL,
    people_met INTEGER DEFAULT 0,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Market reports table
CREATE TABLE IF NOT EXISTS market_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    top_skills TEXT NOT NULL, -- JSON array
    salary_trends TEXT, -- JSON object
    demand_hotspots TEXT, -- JSON array
    gap_analysis TEXT, -- JSON object
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Scans table (job scanner execution log)
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    jobs_found INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT DEFAULT 'running', -- running, completed, failed
    error_message TEXT
);

-- Actions table (daily action queue)
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL, -- review_job, approve_draft, log_date, log_gym
    reference_id INTEGER, -- job_id, draft_id, etc
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending', -- pending, done, skipped
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

-- Scores history table (for trending)
CREATE TABLE IF NOT EXISTS scores_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score_type TEXT NOT NULL, -- career, dating, fitness
    score_value INTEGER NOT NULL,
    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    details TEXT -- JSON object with breakdown
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_remote ON jobs(remote);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON jobs(discovered_at);
CREATE INDEX IF NOT EXISTS idx_scores_job ON scores(job_id);
CREATE INDEX IF NOT EXISTS idx_dates_when ON dates(date_when);
CREATE INDEX IF NOT EXISTS idx_fitness_date ON fitness(date);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS idx_scans_started ON scans(started_at);
