# DATE-M1-1: Rules-Based Quality Trend Analysis

## Overview

This module analyzes dating quality trends from Activities API data. It provides actionable insights following ADR-005 (motivation-first UX).

**Status:** ✅ COMPLETE  
**Branch:** `task/date-m1-1-quality-trends`  
**Created:** 2026-03-15  

## Features

### 1. Quality Trend Detection
- Compares last 2 weeks vs previous 2 weeks
- Detects: UP (>10% improvement), DOWN (>10% decline), FLAT (stable)
- Confidence level based on sample size

### 2. Source Performance Analysis
- Ranks sources (tinder, bumble, dance, real, etc.) by quality-weighted conversion
- Conversion score = avg_quality × √(date_count)
- Identifies best performing channel

### 3. Timing Analysis
- Best day of week for dates
- Best time range (evening 18-22, afternoon 14-18, night 22+)
- Sample size requirements for reliability

### 4. Quality Score Computation
Dates are scored 1-10 based on measurements from Activities API:

| Component | Points | Max |
|-----------|--------|-----|
| Base score | 5.0 | — |
| Touches | +0.5 each | +2.0 |
| She laughs | +0.3 each | +1.5 |
| Kisses | +1.5 each | +3.0 |
| Hand holds | +0.3 each | +1.0 |
| Duration >90min | +0.5 | — |
| Duration >120min | +1.0 | — |
| Positive note keywords | +0.5 | — |
| Negative note keywords | -0.5 | — |

## API Endpoint

```
GET /api/dates/quality-trends
```

### Response Format (ADR-005 Compliant)

```json
{
  "section": "date_quality_trends",
  "goal_ref": "GOAL-1",
  "one_liner": "Your dating quality is IMPROVING (+25% in 2 weeks)! Tinder is your best channel (8.5/10 avg, 3 dates).",
  "data_table": {
    "type": "quality_trends",
    "trend_summary": {
      "direction": "up",
      "recent_avg": 8.2,
      "previous_avg": 6.5,
      "change_pct": 26.2,
      "confidence": "high",
      "total_dates": 8
    },
    "sources": [
      {
        "source": "tinder",
        "dates": 3,
        "avg_quality": 8.5,
        "score": 14.7,
        "best": "9.5/10, 2 kiss(es)"
      },
      {
        "source": "bumble",
        "dates": 2,
        "avg_quality": 7.0,
        "score": 9.9,
        "best": "7.5/10"
      }
    ],
    "timing": {
      "best_day": "Saturday",
      "best_day_quality": 8.8,
      "best_time": "evening (18-22)",
      "best_time_quality": 8.2
    },
    "recent_dates": [
      {
        "date": "2026-03-12",
        "source": "tinder",
        "quality": 8.5,
        "highlights": "2💋 3🤝 8😂"
      }
    ]
  },
  "actions": [
    {
      "action": "optimize_source",
      "label": "Focus on Tinder",
      "description": "Your Tinder dates average 8.5/10 vs Bumble at 7.0/10. Double down on what works."
    },
    {
      "action": "optimize_timing",
      "label": "Schedule Saturday evening (18-22)",
      "description": "Your best dates happen on Saturday evening (18-22) (8.8/10 avg)."
    }
  ],
  "generated_at": "2026-03-15T09:47:00Z"
}
```

### Empty State Response

When fewer than 5 dates are logged:

```json
{
  "section": "date_quality_trends",
  "goal_ref": "GOAL-1",
  "one_liner": "After 3 more date(s), I'll show you quality patterns. Current: 2 logged.",
  "data_table": {
    "type": "empty_state",
    "message": "Log 3 more dates to unlock trend analysis.",
    "current_dates": 2,
    "required_dates": 5
  },
  "actions": [
    {
      "action": "log_date",
      "label": "Log a Date",
      "description": "Open Activities app and log your next date."
    }
  ],
  "generated_at": "2026-03-15T09:47:00Z"
}
```

## Data Sources

### Activities API Endpoints Used
- `GET /shared/{token}/occurrences/dates/{from}/{to}` - Fetch date occurrences
- Activity type: `date`

### Measurements Parsed
- `touches` (COUNT) - Physical escalation
- `she-laughs` (COUNT) - Rapport indicator
- `kiss` (COUNT) - Romantic progression
- `hold-hand` (COUNT) - Physical connection
- `minutes` (COUNT) - Date duration
- SELECT measurement for source (tinder/bumble/real/dance)

### Source Inference
Sources are determined by (in order):
1. SELECT measurement in occurrence
2. Tags (tinder, bumble, dance, etc.)
3. Note text keywords

## Testing

```bash
cd /home/ubuntu/.openclaw/workspace/life-systems-app
python3 -m pytest tests/test_date_quality_trends.py -v
```

**Tests:** 24/24 passing ✅

Test coverage:
- Date occurrence parsing (4 tests)
- Quality trend analysis (4 tests)
- Source analysis (3 tests)
- Timing analysis (3 tests)
- Output format (5 tests)
- Full analysis workflow (2 tests)
- Edge cases (3 tests)

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Rules engine detects: quality trending up/down/flat over 4 weeks | ✅ |
| 2 | Rules engine detects: best source by quality-weighted conversion | ✅ |
| 3 | Rules engine detects: best day/time for dates | ✅ |
| 4 | Output in motivation-first format (one-liner + data table) | ✅ |
| 5 | Empty state: "After N more dates, I'll show you patterns" | ✅ |

## Files

| File | Lines | Description |
|------|-------|-------------|
| `database/date_quality_trends.py` | 642 | Core analysis module |
| `tests/test_date_quality_trends.py` | 486 | Comprehensive test suite |
| `api/routes/dates.py` | +25 | API endpoint |
| `docs/DATE-M1-1-QUALITY-TRENDS.md` | 200 | This documentation |
| **Total** | **1,353** | |

## Integration

### Dashboard Integration
Call from advisor view:
```python
from database.date_quality_trends import build_date_quality_trends_view
result = build_date_quality_trends_view()
```

### CLI Testing
```bash
cd /home/ubuntu/.openclaw/workspace/life-systems-app
python3 -m database.date_quality_trends
```

## Interview Talking Points

1. **Multi-source data aggregation**: Fetches from Activities API, parses complex nested JSON, computes quality scores
2. **Trend detection algorithm**: Compares time windows with statistical confidence
3. **Quality-weighted ranking**: Balances quality and volume with conversion score formula
4. **ADR-005 compliance**: Motivation-first UX with one-liner + data table + actions
5. **Comprehensive testing**: 24 tests covering parsing, analysis, output format, edge cases

## Impact

- **Completes:** DATE-M1-1 (Rules-Based Quality Trend Analysis)
- **Unblocks:** DASH-M1-1 (Dating Section in Advisor View)
- **Portfolio value:** Real-world data analysis, rule-based intelligence, ADR compliance
