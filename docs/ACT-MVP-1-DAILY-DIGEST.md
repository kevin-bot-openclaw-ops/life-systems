# ACT-MVP-1: Daily Activities Digest via Slack

**Status**: Complete ✅  
**Created**: 2026-03-07  
**Branch**: task/act-mvp-1-daily-digest

## Overview

Automated evening digest that summarizes Jurek's daily activities by goal and delivers via Slack DM. Runs at 21:00 CET (20:00 UTC) daily.

## Implementation

### Core Components

1. **Digest Generator** (`activities/digest.py`, 360 LOC)
   - Groups activities by goal (GOAL-1, GOAL-2, GOAL-3, Health)
   - Generates motivation-first one-liner summary
   - Creates data table (activity type | count | duration | goal | notes)
   - Detects anomalies (streaks, broken streaks, first occurrences, excessive coffee, dating app no-matches)
   - Formats output for Slack markdown

2. **Slack Delivery Script** (`scripts/send_evening_digest.py`, 90 LOC)
   - Fetches digest for today
   - Sends via Slack API to D0AFK240GBE
   - Logs to systemd journal

3. **Systemd Timer** (`systemd/evening-digest.timer`)
   - Runs at 20:00 UTC (21:00 CET winter, 22:00 CEST summer)
   - Persistent (catches up if system was offline)

4. **Tests** (`activities/test_digest.py`, 430 LOC)
   - 12 test cases covering all scenarios
   - 100% pass rate ✅

## Output Format

### One-Liner (Motivation-First)
```
Today: 13 activities. GOAL-1: 1 Bumble, 1 Tinder (0 matches). GOAL-3: 3 Spanish lessons. Health: 5 exercise, 1 wellness.
```

### Data Table
```
Activity Type  | Count | Duration | Goal   | Key Notes
----------------------------------------------------------
tinder         | 1     | 10m      | GOAL-1 | -
bumble         | 1     | -        | GOAL-1 | no matches, every girl on lanzarote
duo-lingo      | 3     | 30m      | GOAL-3 | -
walking        | 3     | 21m      | Health | -
coffee         | 2     | -        | Health | -
uttanasana     | 2     | 8m       | Health | -
nerve-stimulus | 1     | 15m      | Health | -
```

### Anomalies
- Exercise streaks: "4-day gym streak maintained"
- Broken streaks: "No gym today (streak broken at 3 days)"
- First occurrences: "First sauna in 10 days — nice!"
- Excessive coffee: "3 coffees today — might impact sleep"
- Dating app no-matches: "bumble: no matches, every girl on lanzarote"

## Deployment

### 1. Deploy Script
```bash
sudo cp scripts/send_evening_digest.py /opt/life-systems/scripts/
sudo chmod +x /opt/life-systems/scripts/send_evening_digest.py
```

### 2. Install Systemd Units
```bash
sudo cp systemd/evening-digest.service /etc/systemd/system/
sudo cp systemd/evening-digest.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

### 3. Enable Timer
```bash
sudo systemctl enable evening-digest.timer
sudo systemctl start evening-digest.timer
```

### 4. Verify
```bash
# Check timer status
sudo systemctl status evening-digest.timer

# Check next run time
systemctl list-timers evening-digest.timer

# Test manual run
sudo systemctl start evening-digest.service

# Check logs
journalctl -u evening-digest.service -n 50
```

### 5. Environment Variables
Ensure `/etc/life-systems/env` contains:
```bash
SLACK_BOT_TOKEN=xoxb-...your-token...
```

## Testing

### Run All Tests
```bash
cd /opt/life-systems
python3 -m pytest activities/test_digest.py -v
```

**Results**: 12/12 passing ✅

### Manual Test
```bash
cd /opt/life-systems
python3 scripts/send_evening_digest.py
```

## Goal Mappings

| Activity Type | Goal | Example |
|--------------|------|---------|
| bumble, tinder | GOAL-1 | Dating apps |
| duo-lingo | GOAL-3 | Spanish learning for relocation |
| gym, uttanasana, walking, swimming | Health | Exercise |
| sauna, sun-exposure, nerve-stimulus | Health | Wellness/stress mgmt |
| coffee, sleep, nap | Health | Recovery tracking |

## Acceptance Criteria

- [x] AC-1: Evening cron (21:00 CET) generates daily digest
- [x] AC-2: Groups activities by goal (GOAL-1, GOAL-2, GOAL-3, Health)
- [x] AC-3: One-liner summary matches motivation-first format (ADR-005)
- [x] AC-4: Data table: activity type | count | duration | goal | key notes
- [x] AC-5: Highlights anomalies (streaks, first occurrences, excessive coffee, dating no-matches)
- [x] AC-6: Delivers via Slack DM to D0AFK240GBE
- [x] AC-7: Empty state handled: "No activities logged today. Everything okay?"
- [x] AC-8: All tests pass (12/12 ✅)

## Performance

- **Execution time**: < 1 second for 30 days of data
- **Database queries**: 5 queries (activities fetch + 4 anomaly detections)
- **Memory**: < 10 MB
- **Cost**: $0 (no API calls, pure SQL)

## Impact

**Unblocks:**
- ACT-MVP-2 (Activities-Powered Rules for SYNTH Engine)
- ACT-M1-1 (Health & Attractiveness Dashboard Section)

**Provides:**
- Daily visibility into behavioral patterns
- Goal-aligned activity tracking
- Streak reinforcement for consistency
- Early detection of dating pool exhaustion ("no matches" pattern)
- Motivation-first feedback loop (ADR-005)

## Future Enhancements (M2)

1. **Correlations**: "Your best dates happen on days with morning exercise"
2. **T-Optimization Score**: Daily testosterone protocol adherence (0-10)
3. **Morning Routine Adherence**: Detect yoga + walk + coffee before 11:00
4. **Cross-domain insights**: Link activities to date quality, career productivity

---

**Deliverables:**
- `activities/digest.py` (360 LOC)
- `scripts/send_evening_digest.py` (90 LOC)
- `systemd/evening-digest.service` + `evening-digest.timer`
- `activities/test_digest.py` (430 LOC, 12 tests)
- `docs/ACT-MVP-1-DAILY-DIGEST.md` (this file)

**Tests**: 12/12 passing ✅  
**Ready for deployment**: Yes ✅
