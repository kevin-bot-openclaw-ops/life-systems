-- Migration: Add status column to jobs table
-- Version: 001
-- Created: 2026-03-05
-- Context: APPL-MVP-1 job decision tracking

-- Add status column if it doesn't exist
ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'new' CHECK(status IN ('new', 'reviewed', 'approved', 'skipped', 'saved', 'applied', 'interviewing', 'offered', 'rejected', 'archived'));

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Update existing jobs to 'new' status (if any exist without status)
UPDATE jobs SET status = 'new' WHERE status IS NULL;
