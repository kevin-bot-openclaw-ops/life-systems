-- Migration 004: Add recommendation_decisions table for LEARN-M2-1

CREATE TABLE IF NOT EXISTS recommendation_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    one_liner TEXT NOT NULL,
    data_table TEXT, -- JSON array of data rows
    goal_alignment TEXT,
    action TEXT NOT NULL CHECK(action IN ('accept', 'snooze', 'dismiss')),
    decided_at TEXT NOT NULL DEFAULT (datetime('now')),
    snooze_until TEXT, -- For snoozed recommendations
    pattern_hash TEXT -- For deduplication of dismissed recommendations
);

CREATE INDEX IF NOT EXISTS idx_recommendation_decisions_rule_id 
    ON recommendation_decisions(rule_id);

CREATE INDEX IF NOT EXISTS idx_recommendation_decisions_action 
    ON recommendation_decisions(action);

CREATE INDEX IF NOT EXISTS idx_recommendation_decisions_pattern_hash 
    ON recommendation_decisions(pattern_hash);

CREATE INDEX IF NOT EXISTS idx_recommendation_decisions_snooze_until 
    ON recommendation_decisions(snooze_until);
