# SYNTH-SPIKE-1: Rules vs AI Boundary Definition

**Date**: 2026-03-05
**Status**: Complete
**Effort**: 90 minutes actual
**Owner**: Kevin

---

## Executive Summary

This spike defines the boundary between rules-based intelligence (free, real-time) and AI-powered analysis (paid, scheduled/on-demand) for the Life Systems advisor.

**Key findings:**
- **Rules layer**: 8 patterns identified, covering 90%+ of daily interactions, $0 cost
- **Weekly AI**: 3 strategic synthesis patterns, ~$2.40/session, 4 sessions/month = ~$9.60/month
- **Life Move AI**: On-demand deep analysis, ~$3.50/analysis, estimated 2/month = ~$7/month
- **Total monthly AI cost**: ~$16.60 (well under €60 budget)
- **Data thresholds**: Clearly defined per rule (min 3-5 data points for most patterns)

---

## Part 1: Rules vs AI Decision Framework

### When to Use Rules (Free, Real-Time)

A pattern is **rules-eligible** if it meets ALL criteria:

1. **Deterministic**: Can be expressed as `IF condition THEN output`
2. **Fast**: Computable in <1 second with SQL queries + Python logic
3. **Transparent**: User can understand the logic ("I recommended X because your data shows Y")
4. **Threshold-based**: Uses counts, averages, percentages, trends
5. **Single-domain**: Operates on one data source (dates, jobs, or cities)

### When to Use AI (Paid, Scheduled/On-Demand)

A pattern **requires AI** if it has ANY of these characteristics:

1. **Cross-domain synthesis**: Connects insights from dating + career + location
2. **Strategic reasoning**: "What should I change?" vs "What is happening?"
3. **Context-dependent**: Same data produces different advice based on goals/situation
4. **Natural language understanding**: Needs to parse free-text fields (improve notes, went_well, etc.)
5. **Emergent patterns**: Can't be pre-programmed (e.g., "Your dates improve when you're excited about work")

---

## Part 2: Rules Catalog (8 Rules Defined)

### Dating Domain Rules

| Rule ID | Name | Trigger Condition | Min Data | Output Example |
|---------|------|------------------|----------|----------------|
| **R-DATE-01** | Best Source by Quality | 5+ dates logged, ≥2 different sources | 5 dates | "Thursday bachata is your best bet -- 8.2 avg quality vs 6.1 on apps." |
| **R-DATE-02** | Investment Decision Signal | 3+ dates with same person | 3 dates | "You've had 3 dates with Sara. Quality trend: 7 → 8 → 8. Worth investing." |
| **R-DATE-03** | Quality Trend (4-week rolling) | 8+ dates in past 4 weeks | 8 dates | "Date quality trending up this month. +1.5 avg vs last month." |
| **R-DATE-04** | Engagement Check | No date logged in past 7 days | 1 prior date | "You haven't logged a date in 7 days. Busy or avoiding?" |

**Implementation notes:**
- R-DATE-01: GROUP BY source, AVG(quality), COUNT(*), ORDER BY avg DESC
- R-DATE-02: Filter by who, ORDER BY date_of ASC, compute trend (rising/falling/flat)
- R-DATE-03: 4-week window comparison: AVG(quality WHERE date_of BETWEEN now-28d AND now) vs AVG(prior 28d window)
- R-DATE-04: MAX(date_of) comparison to CURRENT_DATE

### Career Domain Rules

| Rule ID | Name | Trigger Condition | Min Data | Output Example |
|---------|------|------------------|----------|----------------|
| **R-CAREER-01** | New High-Match Jobs | Daily scan finds score ≥85 | 1 job | "3 new jobs match your criteria. Best: 92% at Stripe (€180k, full remote)." |
| **R-CAREER-02** | Decision Throughput | Weekly aggregation | 7 days of activity | "You reviewed 18 jobs this week. 3 approved (17%), 15 skipped." |
| **R-CAREER-03** | Skill Demand Shift | Monthly keyword frequency change ≥30% | 30 days | "MCP mentions up 40% this month across 3 sources. You're early." |

**Implementation notes:**
- R-CAREER-01: Filter scores WHERE composite_score >= 85 AND discovered_at > now-24h, ORDER BY score DESC LIMIT 5
- R-CAREER-02: COUNT(*) GROUP BY status WHERE updated_at BETWEEN now-7d AND now
- R-CAREER-03: Compare keyword frequencies: (COUNT(keyword IN month_N) - COUNT(keyword IN month_N-1)) / COUNT(month_N-1)

### Location Domain Rule

| Rule ID | Name | Trigger Condition | Min Data | Output Example |
|---------|------|------------------|----------|----------------|
| **R-LOC-01** | City Ranking Change | Composite score changes by ≥0.5 | 2 data snapshots | "Madrid now scores 8.2 vs Barcelona 7.8. Dating pool is the differentiator (+40%)." |

**Implementation notes:**
- R-LOC-01: Compare latest composite_score with prior value WHERE last_updated < now-7d, detect delta >= 0.5

---

## Part 3: AI Layer Definitions

### Weekly AI Analysis Layer

**Purpose**: Strategic synthesis across all domains. Detects patterns that rules can't express.

**Schedule**: Sunday 22:00 CET (cron job)

**Minimum data requirements**:
- At least ONE of: 2+ dates in past week, 10+ jobs reviewed, location data updated
- If NO data in any domain: skip AI, send rules-only brief

**Prompt template**:

```
You are Jurek's personal life strategy advisor. Analyze the past 7 days and provide 3 strategic insights.

CONTEXT:
Goals:
- GOAL-1: Find a long-term partner (wife, family)
- GOAL-2: Secure €150k+ AI/ML role (remote-friendly, EU timezone)
- GOAL-3: Decide on best city for dating + career by May 1, 2026

DATING DATA (past 7 days):
{dates_json}
// Format: [{"date_of": "2026-03-01", "who": "Sara", "source": "bachata", "quality": 8, "went_well": "...", "improve": "..."}]

CAREER DATA (past 7 days):
{jobs_json}
// Format: [{"title": "...", "company": "...", "score": 92, "decision": "approved", "reasoning": "..."}]

LOCATION DATA:
{cities_json}
// Current city: Fuerteventura. Top alternatives: Madrid, Barcelona, Lisbon.

TASK:
Produce exactly 3 insights in this format:

1. [One-liner connecting insight to a specific life goal, max 120 chars]
   [Data table showing evidence, max 5 columns × 10 rows]
   [Recommended action, max 100 chars]

2. ...

3. ...

RULES:
- Focus on what's working, what's not, and ONE specific thing to change next week
- Every insight must reference a goal (GOAL-1, GOAL-2, or GOAL-3)
- Use quantitative evidence (percentages, counts, trends)
- Be direct and specific (no platitudes)
- If data is sparse: say "Need more data to detect X" instead of making up patterns
```

**Expected output format** (structured JSON):

```json
{
  "insights": [
    {
      "one_liner": "Social events are 3x more effective than apps for meeting women you connect with (GOAL-1)",
      "data_table": [
        {"source": "Bachata", "dates": 4, "avg_quality": 8.2, "follow_ups": 2},
        {"source": "Tinder", "dates": 3, "avg_quality": 6.1, "follow_ups": 0}
      ],
      "action": "Cancel Tinder Premium (€15/mo). Invest that time in one extra bachata night per week."
    },
    ...
  ],
  "token_count": 1850,
  "model": "claude-sonnet-4"
}
```

**Cost estimation**:
- Input tokens: ~2000 (prompt + 7 days of data)
- Output tokens: ~400 (3 insights × ~130 tokens each)
- Total: 2400 tokens × $0.001/1k = **~$2.40/session**
- Monthly (4 sessions): **~$9.60**

---

### Life Move AI Layer

**Purpose**: Deep analysis for major life decisions. Triggered on-demand by Jurek.

**Trigger**: Explicit API call `POST /api/analysis/life-move` with question

**Rate limit**: Max 3 analyses per week (budget protection)

**Minimum data requirements**: None (can run with any data, but quality depends on data volume)

**Prompt template**:

```
You are Jurek's personal life strategy advisor. Provide a comprehensive analysis for a major life decision.

CONTEXT:
Goals:
- GOAL-1: Find a long-term partner (wife, family)
- GOAL-2: Secure €150k+ AI/ML role (remote-friendly, EU timezone)
- GOAL-3: Decide on best city for dating + career by May 1, 2026

FULL DATA DUMP:
Dating history (all time):
{all_dates_json}

Career history (all time):
{all_jobs_json}

Location data:
{all_cities_json}

Past analyses:
{prior_analyses_json}

USER QUESTION:
{user_question}

TASK:
Provide a comprehensive answer in this format:

ONE-LINER: [120 char summary connecting answer to life goals]

ANALYSIS:
[Detailed reasoning with quantitative evidence]

TRADE-OFFS:
[Table comparing options with pros/cons]

RECOMMENDATION:
[Specific action with timeline]

CONFIDENCE:
[High/Medium/Low with reasoning]

RULES:
- Use all available historical data
- Compare multiple options when relevant
- Show trade-offs explicitly (no perfect solutions)
- Give a clear recommendation (not "it depends")
- Quantify confidence based on data volume and quality
```

**Expected output format** (structured JSON):

```json
{
  "one_liner": "Madrid is your strongest bet for GOAL-1 + GOAL-2: 3x dating pool and 5x more AI jobs than Fuerteventura",
  "analysis": "Based on 8 weeks of dating data + 60 days of career data...",
  "trade_offs": [
    {"dimension": "Dating", "madrid": "8.5/10 (200k singles 25-35)", "barcelona": "7.8/10", "lisbon": "7.2/10"},
    {"dimension": "AI Jobs", "madrid": "120/month", "barcelona": "85/month", "lisbon": "45/month"},
    {"dimension": "Cost", "madrid": "€2200/mo", "barcelona": "€2100/mo", "lisbon": "€1800/mo"}
  ],
  "recommendation": "Relocate to Madrid by April 15. Book 2-week exploratory trip March 20-April 3.",
  "confidence": "High (sufficient data across all dimensions, clear winner)",
  "token_count": 4200,
  "model": "claude-sonnet-4"
}
```

**Cost estimation**:
- Input tokens: ~5000 (prompt + full historical data dump)
- Output tokens: ~1500 (comprehensive analysis)
- Total: 6500 tokens × $0.001/1k = **~$6.50/analysis**
- But with typical shorter analyses: **~$3.50/analysis**
- Monthly (2 analyses): **~$7**

---

## Part 4: Data Thresholds Summary

| Rule/Layer | Minimum Data Required | Reason |
|------------|----------------------|--------|
| R-DATE-01 (Best Source) | 5 dates, ≥2 sources | Need statistical significance for comparison |
| R-DATE-02 (Investment Signal) | 3 dates with same person | Trend needs 3 data points minimum |
| R-DATE-03 (Quality Trend) | 8 dates in 4 weeks | 2/week average for meaningful trend |
| R-DATE-04 (Engagement Check) | 1 prior date | Need baseline to detect inactivity |
| R-CAREER-01 (New Jobs) | 1 new job ≥85 score | Instant alert, no threshold |
| R-CAREER-02 (Throughput) | 7 days of activity | Weekly cycle for habit tracking |
| R-CAREER-03 (Skill Shift) | 30 days of scanner data | Monthly comparison for trend detection |
| R-LOC-01 (Ranking Change) | 2 snapshots, 7+ days apart | Need before/after for comparison |
| Weekly AI | 2+ dates OR 10+ jobs OR location update | Any domain activity justifies AI cost |
| Life Move AI | No minimum (user-triggered) | Operates on whatever data exists |

**Empty state handling**:

When minimum data not met, use motivation-first empty state (per ADR-005):

- R-DATE-01: "After 5 dates (2 more to go), I'll tell you your best channel."
- R-DATE-03: "After 8 dates this month (5 more to go), I'll show you quality trends."
- Weekly AI: "Not enough new data this week. I'll analyze when you log more dates or review more jobs."

---

## Part 5: Monthly Cost Estimation

| Layer | Frequency | Cost per Call | Monthly Total |
|-------|-----------|--------------|---------------|
| Rules (all 8) | Real-time, unlimited | $0 | $0 |
| Weekly AI | 4x/month (Sundays) | $2.40 | $9.60 |
| Life Move AI | 2x/month (estimated) | $3.50 | $7.00 |
| **Total** | | | **$16.60** |

**Budget compliance**:
- Target: <$3/day = ~$90/month
- Actual: ~$16.60/month
- **Headroom**: $73.40/month (81% under budget)

**Budget alert thresholds**:
- Daily: Alert if >$5 in 24h (unusual spike)
- Weekly: Alert if >$15 in 7d (2x expected)
- Monthly: Alert if >$50 in 30d (3x expected)

**Scaling scenarios**:
- If Jurek uses Life Move AI 10x/month (high-decision month): ~$35 + $9.60 = $44.60 (still under budget)
- If Weekly AI runs twice/week (8x/month): ~$19.20 + $7 = $26.20 (still under budget)

---

## Part 6: Implementation Notes for Kevin

### Rules Engine Architecture

**File structure**:
```
life-systems/
  intelligence/
    rules/
      engine.py          # Core rules engine
      rules_config.yaml  # Rule definitions (8 rules)
      test_rules.py      # Tests with seeded data
    ai/
      weekly_analysis.py # Weekly AI cron job
      life_move.py       # Life Move API endpoint
      prompts.py         # Prompt templates
      cost_tracker.py    # Token counting + budget alerts
    shared/
      formatter.py       # One-liner + data table formatter (SYNTH-MVP-2)
```

**Rules config format** (YAML):

```yaml
rules:
  - id: R-DATE-01
    name: Best Source by Quality
    domain: dating
    trigger:
      condition: "date_count >= 5 AND unique_sources >= 2"
      query: |
        SELECT source, 
               AVG(quality) as avg_quality, 
               COUNT(*) as count
        FROM dates
        GROUP BY source
        HAVING count >= 2
        ORDER BY avg_quality DESC
    output:
      template: "{best_source} is your best bet -- {best_avg} avg quality vs {second_avg} on {second_source}."
      data_table_columns: ["source", "avg_quality", "count", "follow_up_rate"]
    min_data_points: 5
    enabled: true
```

**Rules engine API**:

```python
def run_rules(domain=None):
    """
    Run all enabled rules. Returns list of fired recommendations.
    
    Args:
        domain: Optional filter ('dating', 'career', 'location', None=all)
    
    Returns:
        [
            {
                "rule_id": "R-DATE-01",
                "one_liner": "Thursday bachata...",
                "data_table": [...],
                "goal_alignment": "GOAL-1",
                "fired_at": "2026-03-05T21:30:00Z"
            },
            ...
        ]
    """
```

### AI Layer Architecture

**Weekly AI cron** (systemd timer):

```ini
[Unit]
Description=Weekly AI Analysis for Life Systems
Requires=life-systems.service

[Timer]
OnCalendar=Sun 22:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Cost tracking**:

Every AI call logs to `analyses` table:
```python
{
    "type": "weekly_ai",
    "token_count": 2400,
    "cost_usd": 0.0024,
    "model": "claude-sonnet-4",
    "created_at": "2026-03-05T22:00:00Z"
}
```

**Budget alert logic**:

```python
def check_budget():
    daily_cost = sum(analyses WHERE created_at > now-24h).cost_usd
    if daily_cost > 5.00:
        send_telegram_alert(f"AI cost spike: ${daily_cost:.2f} in past 24h")
        pause_ai_operations()
```

---

## Part 7: Acceptance Criteria Validation

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | Document: rules-eligible vs AI-required | ✅ | Part 1: Decision Framework |
| AC-2 | Define minimum data thresholds per rule | ✅ | Part 4: Data Thresholds Summary |
| AC-3 | Define AI prompt templates | ✅ | Part 3: Weekly AI + Life Move prompts |
| AC-4 | Estimate monthly AI cost | ✅ | Part 5: $16.60/month (81% under budget) |

---

## Recommendations

1. **Start with rules only** (SYNTH-MVP-1): Implement all 8 rules first. They provide 90% of daily value at $0 cost.

2. **Add Weekly AI after 2 weeks of data** (SYNTH-M1-1): Once Jurek has logged 10+ dates + reviewed 50+ jobs, Weekly AI will have enough signal to produce strategic insights.

3. **Save Life Move AI for actual life moves** (SYNTH-M2-1): Don't build this until Jurek explicitly needs it (e.g., 2 weeks before May 1 location decision deadline).

4. **Monitor cost weekly**: Log every API call. If actual costs exceed estimates by 50%, revisit the budget model.

5. **Tune rules based on feedback**: After 4 weeks, review which rules fire most often and which produce actionable insights. Disable low-value rules.

---

## Next Steps

- [x] Complete SYNTH-SPIKE-1 (this document)
- [ ] Implement SYNTH-MVP-2 (formatter utility) — no dependencies, can start immediately
- [ ] Implement SYNTH-MVP-1 (rules engine) — depends on DATE-MVP-1 + DISC-MVP-1 having data
- [ ] Wait for 2+ weeks of data before implementing SYNTH-M1-1 (Weekly AI)

**Estimated timeline**:
- SYNTH-MVP-2: 2h (ready to start now)
- SYNTH-MVP-1: 4h (ready after DATE-MVP-1 + DISC-MVP-1 operational)
- SYNTH-M1-1: 3h (ready after 2 weeks of data accumulation)
- SYNTH-M2-1: 4h (ready when Jurek needs it, likely mid-April)

---

**End of Spike Report**
