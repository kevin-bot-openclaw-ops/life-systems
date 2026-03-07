-- Migration 003: Add activities table for real behavioral data from Activities app
-- Created: 2026-03-07

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT UNIQUE NOT NULL,  -- External ID from Activities app (for deduplication)
    activity_type TEXT NOT NULL,       -- e.g., 'bumble', 'tinder', 'gym', 'duo-lingo', 'sauna', etc.
    occurred_at TEXT NOT NULL,         -- ISO 8601 timestamp when activity occurred
    occurred_date TEXT NOT NULL,       -- YYYY-MM-DD for date-based queries
    duration_minutes INTEGER,          -- For SPAN activities (gym, sleep, etc.)
    note TEXT,                         -- User notes about the activity
    tags TEXT,                         -- JSON array of tags (e.g., ["anxiety", "calm"])
    measurements TEXT,                 -- JSON object with activity-specific measurements
    goal_mapping TEXT NOT NULL,        -- GOAL-1, GOAL-2, GOAL-3, or Health
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(occurred_date);
CREATE INDEX IF NOT EXISTS idx_activities_goal ON activities(goal_mapping);
CREATE INDEX IF NOT EXISTS idx_activities_occurred ON activities(occurred_at);

-- Index for date range queries (used by rules engine)
CREATE INDEX IF NOT EXISTS idx_activities_date_type ON activities(occurred_date, activity_type);
