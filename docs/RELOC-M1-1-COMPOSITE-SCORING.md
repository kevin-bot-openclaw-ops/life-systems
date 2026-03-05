# RELOC-M1-1: Composite Scoring + Recommendation Engine

## Overview

City recommendation system with configurable weighted scoring across 5 dimensions. Delivers motivation-first recommendations with trade-off analysis.

**Status:** ✅ Complete  
**Epic:** EPIC-003 (Location Optimizer)  
**Milestone:** M1  
**Duration:** 90 minutes  
**Tests:** 7/7 passing

---

## Features

### 1. Composite Scoring Algorithm

Calculates weighted average of normalized dimensions:

```python
composite_score = Σ(weight_i × normalize(dimension_i))
```

**Normalization:**
- Each dimension normalized to 0-1 scale
- Min/max bounds defined in config
- Inverted for "lower is better" dimensions (e.g., cost)

**Scoring:**
- Output scaled to 0-10 for readability
- NULL values treated as 0 in calculations
- Weights must sum to 1.0

### 2. Configurable Weights

Located at: `config/location_scoring.json`

**Default weights (equal):**
```json
{
  "weights": {
    "dating_pool": 0.20,
    "ai_job_density": 0.20,
    "cost_index": 0.20,
    "lifestyle_score": 0.20,
    "community_score": 0.20
  }
}
```

**Custom example:**
```json
{
  "weights": {
    "dating_pool": 0.35,
    "ai_job_density": 0.30,
    "cost_index": 0.15,
    "lifestyle_score": 0.10,
    "community_score": 0.10
  }
}
```

### 3. Recommendation Endpoint

`GET /api/cities/recommendation`

**Returns:**
```json
{
  "one_liner": "Madrid doubles your dating pool and has 30x more AI jobs -- strongest candidate.",
  "recommended_city": { ... },
  "current_city": { ... },
  "top_3": [ ... ],
  "trade_offs": [
    "Cost of living is 40% higher (1.4x vs 1.0x baseline)",
    "Community score: 9.0/10 vs 5.0/10"
  ],
  "dimension_comparisons": [ ... ]
}
```

### 4. One-Liner Format

**Motivation-first structure:**
1. Identify top 2 improvements (>50% change or >2 point difference)
2. Generate natural language comparisons
3. End with "-- strongest candidate"

**Examples:**
- "Madrid doubles your dating pool and has 30x more AI jobs -- strongest candidate."
- "Barcelona increases your dating pool and lifestyle 9/10 -- strongest candidate."
- "Berlin scores highest overall (8.5/10 vs 5.2/10) -- strongest candidate."

### 5. Trade-Offs

Automatically detected when:
- Cost change > 10%
- Lifestyle/community score change > 1 point

**Format:**
- Cost: percentage + absolute (e.g., "40% higher (1.4x vs 1.0x)")
- Scores: absolute values (e.g., "Community score: 9.0/10 vs 5.0/10")

---

## API Endpoints

### GET /api/cities

List all cities with composite scores.

**Query params:**
- `sort_by`: Column name (default: `composite_score`)
- `order`: `asc` or `desc` (default: `desc`)

**Response:** Array of CityResponse objects

### GET /api/cities/compare

Side-by-side comparison table.

**Query params:**
- `sort_by`: Column name
- `order`: Sort order

**Response:** ComparisonResponse with current city highlighted

### GET /api/cities/recommendation

Top recommendation with motivation-first one-liner.

**Response:** RecommendationResponse (see above)

### POST /api/cities/recalculate

Manually trigger score recalculation for all cities.

**Response:**
```json
{
  "status": "success",
  "message": "Recalculated composite scores for 8 cities",
  "config_path": "/path/to/config/location_scoring.json"
}
```

---

## Usage Examples

### 1. Get Recommendation

```bash
curl http://localhost:8000/api/cities/recommendation
```

### 2. Change Weights

Edit `config/location_scoring.json`:
```json
{
  "weights": {
    "dating_pool": 0.40,
    "ai_job_density": 0.30,
    "cost_index": 0.10,
    "lifestyle_score": 0.10,
    "community_score": 0.10
  }
}
```

Then recalculate:
```bash
curl -X POST http://localhost:8000/api/cities/recalculate
```

### 3. Sort by Dimension

```bash
# Cheapest cities first
curl "http://localhost:8000/api/cities?sort_by=cost_index&order=asc"

# Most AI jobs
curl "http://localhost:8000/api/cities?sort_by=ai_job_density&order=desc"
```

---

## Testing

Run test suite:
```bash
pytest tests/test_location_scoring.py -v
```

**Coverage:**
- ✅ Normalization (including inverted dimensions)
- ✅ Composite score calculation
- ✅ Batch score updates
- ✅ One-liner generation
- ✅ Trade-off detection
- ✅ Config loading (defaults + custom)

---

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| AC-1 | Composite score = weighted average of 5 normalized dimensions | ✅ |
| AC-2 | Default weights: equal (20% each), configurable via config.json | ✅ |
| AC-3 | `/api/cities/recommendation` returns one-liner + table + top 3 | ✅ |
| AC-4 | One-liner format: motivation-first (e.g., "Madrid doubles your dating pool...") | ✅ |
| AC-5 | Trade-offs included (cost change, score changes) | ✅ |

---

## Architecture Notes

### Normalization Strategy

**Linear scaling:**
```python
normalized = (value - min) / (max - min)
```

**Inverted dimensions (cost_index):**
```python
normalized = 1.0 - ((value - min) / (max - min))
```

**NULL handling:**
- Treated as 0 in scoring
- Weight redistributed to non-NULL dimensions

### Score Calculation Frequency

- **On-demand:** Recalculated when `/recommendation` is called
- **Manual:** Via `/recalculate` endpoint
- **Future:** Could add cron job for daily updates

### One-Liner Logic

1. Calculate dimension comparisons vs current city
2. Filter significant improvements (>50% or >2 points)
3. Sort by magnitude
4. Generate natural language for top 2
5. Format: "{City} {improvement1} and {improvement2} -- strongest candidate."

---

## Future Enhancements

1. **Uncertainty bounds:** Show confidence intervals for each dimension
2. **Scenario analysis:** "If I value dating 2x more than jobs, then..."
3. **Time-based weighting:** Adjust for seasonal factors (e.g., summer dating pool)
4. **Multi-objective optimization:** Pareto frontier visualization
5. **Decision deadline countdown:** Days until May 1 decision

---

## Dependencies

- SQLite (cities table)
- FastAPI (routing)
- Pydantic (models)
- JSON config (weights + normalization)

---

## Deliverables

| File | LOC | Description |
|------|-----|-------------|
| `api/routes/cities.py` | +190 | Scoring logic + recommendation endpoint |
| `config/location_scoring.json` | 33 | Weight configuration |
| `tests/test_location_scoring.py` | 250 | 7 test cases (100% pass) |
| `docs/RELOC-M1-1-COMPOSITE-SCORING.md` | This file | Documentation |

---

**Completion:** 2026-03-05, 03:00 UTC  
**Next:** DASH-M1-2 (Location Section in Advisor View)
