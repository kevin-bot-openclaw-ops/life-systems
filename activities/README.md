# Activities Integration

Bridge between the external Activities app and Life Systems intelligence layer.

## Overview

Jurek logs ALL daily activities (gym, yoga, dating apps, coffee, Spanish learning, etc.) in a separate Activities app (Kotlin/http4k on AWS). This module provides read-only access to that behavioral data via a share token API.

**Why this matters:** Real behavioral data beats manual logging. The Activities app is Jurek's daily habit tracker. Life Systems uses this data to power intelligence rules that detect patterns across life domains.

## Architecture

```
Activities App (AWS)
       ↓
  Share Token API (read-only)
       ↓
  activities/bridge.py (fetch + parse + store)
       ↓
  SQLite activities table
       ↓
  SYNTH Rules Engine (R-ACT-01 through R-ACT-06)
```

## Activities API

**Base URL:** `https://xznxeho9da.execute-api.eu-central-1.amazonaws.com`  
**Share Token:** `a50ea3e50186487ca3ad094bc3e177ac` (read-only, expires ~May 6, 2026)  
**Auth:** No auth headers needed for share token endpoints

### Endpoints

- `GET /shared/{token}/occurrences/dates/{YYYY-MM-DD}` — all activities for a date
- `GET /shared/{token}/occurrences/dates/{from}/{to}` — date range
- `GET /shared/{token}/goals` — goal definitions
- `GET /shared/{token}/activity-types` — all activity type definitions

### Activity Types Tracked

| Activity | Goal Mapping | Key Measurements |
|----------|-------------|------------------|
| bumble, tinder | GOAL-1 (dating) | swipes, matches (in notes) |
| duo-lingo | GOAL-3 (Spanish for relocation) | tags: spanish |
| gym, walking, swimming, uttanasana, yoga | Health | intensity 1-5, duration |
| sauna, nerve-stimulus | Health (stress mgmt) | tags: anxiety, calm, stress |
| sun-exposure | Health (testosterone) | duration |
| coffee | Health (track overconsumption) | count |
| sleep, nap | Health (recovery) | duration |

## Database Schema

```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT UNIQUE NOT NULL,  -- External ID (deduplication)
    activity_type TEXT NOT NULL,       -- 'bumble', 'gym', 'duo-lingo', etc.
    occurred_at TEXT NOT NULL,         -- ISO 8601 timestamp
    occurred_date TEXT NOT NULL,       -- YYYY-MM-DD for date queries
    duration_minutes INTEGER,          -- For SPAN activities
    note TEXT,                         -- User notes
    tags TEXT,                         -- JSON array
    measurements TEXT,                 -- JSON object
    goal_mapping TEXT NOT NULL,        -- GOAL-1, GOAL-2, GOAL-3, Health
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Sync Behavior

- **First run:** Backfills last 30 days of data
- **Subsequent runs:** Fetches today's activities only
- **Cron:** Every 4 hours via systemd timer
- **Deduplication:** Activities with duplicate `activity_id` are skipped

## Usage

### Manual Sync

```bash
python -m activities.bridge /path/to/life.db
```

### Systemd Timer Setup

```bash
sudo cp systemd/life-systems-activities.service /etc/systemd/system/
sudo cp systemd/life-systems-activities.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable life-systems-activities.timer
sudo systemctl start life-systems-activities.timer

# Check status
sudo systemctl status life-systems-activities.timer
journalctl -u life-systems-activities.service -f
```

## Example API Response

### MOMENT Activity (instant event)

```json
{
  "id": "activity-001",
  "activityType": {"id": "type-001", "name": "bumble"},
  "moment": "2026-03-07T10:00:00Z",
  "note": "no matches, every girl on lanzarote",
  "measurements": [
    {"type": {"name": "swipes"}, "count": 49}
  ],
  "tags": []
}
```

### SPAN Activity (duration-based)

```json
{
  "id": "activity-002",
  "activityType": {"id": "type-002", "name": "gym"},
  "start": "2026-03-07T08:00:00Z",
  "finish": "2026-03-07T09:30:00Z",
  "note": "Upper body",
  "measurements": [
    {"type": {"name": "intensity"}, "value": 4}
  ],
  "tags": [{"name": "strength"}]
}
```

## Stored Format

```python
{
    "activity_id": "activity-001",
    "activity_type": "bumble",
    "occurred_at": "2026-03-07T10:00:00Z",
    "occurred_date": "2026-03-07",
    "duration_minutes": None,  # MOMENT activity
    "note": "no matches, every girl on lanzarote",
    "tags": "[]",
    "measurements": '{"swipes": 49}',
    "goal_mapping": "GOAL-1"
}
```

## Tests

```bash
pytest activities/test_bridge.py -v
```

11 tests covering:
- MOMENT vs SPAN activity parsing
- Goal mapping
- Deduplication
- First run detection
- API error handling
- Backfill vs incremental sync

## Integration with SYNTH Rules

The SYNTH rules engine (Layer 1 intelligence) queries the `activities` table to detect patterns:

- **R-ACT-01:** Dating pool exhaustion (0 matches over N sessions)
- **R-ACT-02:** Stress escalation (nerve-stimulus frequency spike)
- **R-ACT-03:** Exercise consistency (streak tracking)
- **R-ACT-04:** Testosterone protocol score (sun, cold, exercise, sauna, sleep, coffee)
- **R-ACT-05:** Morning routine adherence (yoga + walk + coffee before 11:00)
- **R-ACT-06:** Dating-activity correlation (date quality vs same-day activities)

See `synthesis/rules/rules_config.yaml` for full rule definitions.

## Token Expiry

Share token expires ~May 6, 2026. If expired, get a new one from Jurek or use Kevin's authenticated account (see ACT-M1-2 for JWT auth flow).

## Cost

$0. Share token API is read-only and has no rate limits.
