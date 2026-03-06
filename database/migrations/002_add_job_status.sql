-- Migration 002: Add status column to jobs table
-- Created: 2026-03-05
-- For: CRST-M1-1 Pipeline Funnel tracking

-- Add status column to jobs table
ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'new' 
CHECK(status IN ('new', 'reviewed', 'approved', 'skipped', 'saved', 'applied', 'interviewing', 'offered', 'rejected', 'archived'));

-- Create index on status for fast filtering
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Update existing jobs to 'new' status (default already applied via ALTER)
-- No additional UPDATE needed since DEFAULT handles it
