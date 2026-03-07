-- Migration 003: Add activities table for Activities app integration
-- Created: 2026-03-07
-- Purpose: Store behavioral data from Jurek's Activities app (share token)

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,  -- UUID from Activities app
    type TEXT NOT NULL,   -- Activity type (bumble, gym, coffee, etc.)
    occurred_at TEXT NOT NULL,  -- ISO timestamp when activity happened
    duration_seconds INTEGER,  -- For SPAN activities, NULL for MOMENT
    note TEXT,  -- Free text notes
    tags TEXT,  -- JSON array of tags
    measurements TEXT,  -- JSON array of measurements (kind + value)
    goal_mapping TEXT,  -- GOAL-1, GOAL-2, GOAL-3, or Health
    fetched_at TEXT NOT NULL,  -- When we fetched from API
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(type);
CREATE INDEX IF NOT EXISTS idx_activities_occurred_at ON activities(occurred_at);
CREATE INDEX IF NOT EXISTS idx_activities_goal ON activities(goal_mapping);
CREATE INDEX IF NOT EXISTS idx_activities_fetched_at ON activities(fetched_at);

-- Unique constraint: same activity ID from source
CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_id ON activities(id);
