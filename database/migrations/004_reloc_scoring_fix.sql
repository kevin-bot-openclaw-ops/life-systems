-- Migration 004: Fix RELOC scoring model
-- Created: 2026-03-07
-- Purpose: Add missing dimensions, split remote jobs, fix dating pool numbers

-- Add new columns for corrected model
ALTER TABLE cities ADD COLUMN remote_ai_jobs INTEGER DEFAULT 0;
ALTER TABLE cities ADD COLUMN onsite_hybrid_ai_jobs INTEGER DEFAULT 0;
ALTER TABLE cities ADD COLUMN dating_pool_verified INTEGER DEFAULT 0;
ALTER TABLE cities ADD COLUMN language_advantage REAL DEFAULT 0;
ALTER TABLE cities ADD COLUMN dating_culture_fit REAL DEFAULT 0;
ALTER TABLE cities ADD COLUMN social_dance_scene REAL DEFAULT 0;
ALTER TABLE cities ADD COLUMN visa_ease REAL DEFAULT 0;

-- Create index on new composite score
CREATE INDEX IF NOT EXISTS idx_cities_composite_v2 ON cities(composite_score);
