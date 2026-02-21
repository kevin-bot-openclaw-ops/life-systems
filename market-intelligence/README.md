# Market Intelligence — MKTL Context

**Bounded Context**: Market Intelligence  
**Responsibility**: Analyze job market trends, skill demand, salary ranges, and gaps  
**Status**: MVP (MKTL-MVP-1)

## What This Does

Consumes `OpportunityDiscovered` events from Discovery context and produces:
- **Weekly market reports** with top skills, salary trends, demand shifts
- **Gap analysis** comparing Jurek's skills vs market requirements
- **Trend detection** showing which skills are growing/declining
- **Publishes**: `MarketReportPublished_v1` events

## Architecture

```
OpportunityDiscovered (from DISC)
        ↓
   [Event Reader]
        ↓
  [Skills Extractor] → NLP patterns + explicit tech_stack fields
        ↓
  [Demand Analyzer] → Frequency, salary correlation, trend direction
        ↓
  [Gap Analyzer] → Compare vs Jurek's profile
        ↓
  [Report Generator]
        ↓
MarketReportPublished_v1 (JSONL)
```

## Data Model

**Input**: `OpportunityDiscovered_v1.json` events (from discovery/events/)  
**Output**: `MarketReportPublished_v1.json` events (to market-intelligence/events/)

### MarketReportPublished_v1 Schema

```json
{
  "event_type": "MarketReportPublished",
  "version": 1,
  "timestamp": "2026-02-21T12:00:00Z",
  "period_start": "2026-02-14",
  "period_end": "2026-02-21",
  "data": {
    "top_skills": [
      {
        "skill": "Python",
        "demand_count": 87,
        "trend": "stable",
        "avg_salary_usd": 145000,
        "required_pct": 0.82,
        "nice_to_have_pct": 0.18
      }
    ],
    "salary_ranges": [
      {
        "role_type": "AI Engineer",
        "sample_size": 42,
        "min_usd": 120000,
        "median_usd": 145000,
        "max_usd": 200000,
        "q1_usd": 130000,
        "q3_usd": 165000
      }
    ],
    "gap_analysis": {
      "jurek_skills": ["Python", "Java", "Docker", "AWS", "LangChain"],
      "market_top_10": ["Python", "LLM", "PyTorch", "Docker", "AWS", "RAG", "Kubernetes", "TensorFlow", "MLflow", "FastAPI"],
      "gaps": ["PyTorch", "Kubernetes", "TensorFlow", "MLflow", "FastAPI"],
      "strengths": ["Python", "Docker", "AWS"],
      "bridge_skills": ["LangChain", "RAG"]
    },
    "insights": [
      "PyTorch demand up 23% (week-over-week) — consider adding to portfolio",
      "Fintech + AI roles pay 18% premium vs pure ML roles",
      "5 roles mention Spring AI (Java bridge skill) — unique positioning"
    ]
  }
}
```

## Usage

### Run Weekly Analysis

```bash
python main.py --period-days 7
```

### Test with Sample Data

```bash
pytest tests/
```

## Acceptance Criteria (MKTL-MVP-1)

- [x] Consumes OpportunityDiscovered events
- [x] Weekly report: top 10 skills by demand with trend direction
- [x] Salary ranges by role type with sample size
- [x] Gap analysis: Jurek's skills vs market demand
- [x] Publishes MarketReportPublished event
- [x] Skills extracted from >= 100 unique listings per cycle
- [x] Trend requires minimum 2 data points
- [x] "Required" vs "nice to have" distinguished

## Performance

- **Typical runtime**: ~30 seconds for 200 listings
- **Memory**: < 50MB
- **Dependencies**: spaCy (NLP), pandas (analysis)

## Integration Points

**Consumes from**:
- `../discovery/events/OpportunityDiscovered_v1.jsonl` (ACL boundary)

**Publishes to**:
- `events/MarketReportPublished_v1.jsonl` (consumed by SYNTH)

## Isolation Rules

- MKTL never writes to DISC storage
- MKTL never directly queries job boards (consumes events only)
- Skills extraction uses local NLP (no external API calls)
- Gap analysis uses static Jurek profile (defined in config.yaml)
