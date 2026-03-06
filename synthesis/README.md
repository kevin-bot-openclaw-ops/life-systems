# SYNTHESIS Module - Motivation-First Formatter

**Status**: SYNTH-MVP-2 Complete ✅  
**Owner**: Kevin (kevin-bot-openclaw-ops)  
**Created**: 2026-03-06  
**ADRs**: ADR-005 (motivation-first UX), ADR-001 (intelligence layers)

---

## Overview

The Synthesis module provides cross-cutting utilities for formatting recommendations in the motivation-first paradigm. Every insight, alert, and screen element follows a consistent structure:

```
[One-liner connecting action to life goal]
[Data table showing evidence]
[Action buttons: approve/skip/details]
```

This module is used by all domain contexts (DATE, DISC, APPL, CRST, RELOC) to ensure consistent UX across the system.

---

## Quick Start

```python
from synthesis import (
    format_recommendation_html,
    format_recommendation_slack,
    format_dating_recommendation
)

# Create a recommendation
rec = format_dating_recommendation(
    one_liner="Thursday bachata is your best bet -- 3x more quality vs apps.",
    source_data=[
        {"Source": "Bachata", "Dates": 4, "Avg Quality": 7.8},
        {"Source": "Tinder", "Dates": 8, "Avg Quality": 5.2}
    ]
)

# Render for dashboard
html = format_recommendation_html(rec)

# Render for Slack notification
slack = format_recommendation_slack(rec)
```

---

## Core Components

### 1. Recommendation Object

The main data structure for a recommendation:

```python
from synthesis import Recommendation, ActionButton, GoalReference

rec = Recommendation(
    one_liner="This role could be your bridge to AI leadership.",  # Max 120 chars
    data_rows=[  # Max 10 rows, max 5 columns
        {"Dimension": "Role match", "Score": "9/10"},
        {"Dimension": "Remote", "Score": "10/10"}
    ],
    actions=[  # Max 3 buttons
        ActionButton(label="Apply", action="approve", primary=True),
        ActionButton(label="Skip", action="skip")
    ],
    goal=GoalReference.CAREER  # Required: connects to life goal
)
```

**Validation rules:**
- `one_liner`: max 120 characters (enforced)
- `data_rows`: max 10 rows, max 5 columns per row (enforced)
- `actions`: max 3 buttons (enforced)
- `goal`: must reference a life goal (PARTNER, CAREER, LOCATION, FAMILY, FINANCIAL)

### 2. Empty State

When there's not enough data for insights:

```python
from synthesis import EmptyState, format_empty_state_html

empty = EmptyState(
    count_needed=5,
    data_type="dates",
    insight_type="quality trends and best sources",
    goal=GoalReference.PARTNER
)

# Generates: "After 5 more dates, I'll show you quality trends and best sources."
message = empty.to_message()
html = format_empty_state_html(empty)
```

### 3. Action Buttons

Clickable actions for recommendations:

```python
from synthesis import ActionButton

# Simple button
btn = ActionButton(label="Apply", action="approve")

# Primary action (highlighted)
primary = ActionButton(label="Apply", action="approve", primary=True)

# Button with URL (renders as link)
link = ActionButton(
    label="Full analysis",
    action="details",
    url="/location/compare"
)
```

---

## Formatting Functions

### HTML Output (Dashboard)

```python
from synthesis import format_recommendation_html

html = format_recommendation_html(rec)
```

**Output structure:**
```html
<div class="recommendation" data-goal="career">
  <div class="one-liner">This role could be your bridge to AI leadership.</div>
  <table class="data-table">
    <thead>
      <tr>
        <th>Dimension</th>
        <th>Score</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Role match</td>
        <td>9/10</td>
      </tr>
    </tbody>
  </table>
  <div class="actions">
    <button class="btn btn-primary" data-action="approve">Apply</button>
    <button class="btn btn-secondary" data-action="skip">Skip</button>
  </div>
</div>
```

**CSS classes:**
- `.recommendation`: Outer container
- `.one-liner`: The sharp insight text
- `.data-table`: Evidence table
- `.actions`: Button container
- `.btn-primary`: Primary action button
- `.btn-secondary`: Secondary action buttons

### Slack Markdown Output

```python
from synthesis import format_recommendation_slack

slack = format_recommendation_slack(rec)
```

**Output structure:**
```
*This role could be your bridge to AI leadership.*

```
Dimension | Score
-------------------
Role match | 9/10
Remote | 10/10
```

▶️ _Apply_ | • _Skip_
```

**Formatting:**
- Bold one-liner
- Code-block table with pipe separators
- Primary actions marked with ▶️ emoji
- Secondary actions marked with • bullet
- URLs wrapped in `(<url>)` format

---

## Domain-Specific Helpers

Convenience functions for common recommendation types:

### Dating Recommendations

```python
from synthesis import format_dating_recommendation

rec = format_dating_recommendation(
    one_liner="Thursday bachata is your best bet.",
    source_data=[
        {"Source": "Bachata", "Dates": 4, "Avg Quality": 7.8},
        {"Source": "Tinder", "Dates": 8, "Avg Quality": 5.2}
    ],
    primary_action="View details"  # Optional, defaults to "View details"
)
```

**Defaults:**
- Goal: `GoalReference.PARTNER`
- Actions: "View details" (primary) + "Dismiss"

### Career Recommendations

```python
from synthesis import format_career_recommendation

rec = format_career_recommendation(
    one_liner="This role could be your bridge to AI leadership.",
    job_data=[
        {"Dimension": "Role match", "Score": "9/10"},
        {"Dimension": "Remote", "Score": "10/10"}
    ],
    job_id="job_123"  # Optional
)
```

**Defaults:**
- Goal: `GoalReference.CAREER`
- Actions: "Apply" (primary) + "Skip" + "Save"

### Location Recommendations

```python
from synthesis import format_location_recommendation

rec = format_location_recommendation(
    one_liner="Madrid doubles your dating pool and has 3x more AI jobs.",
    city_data=[
        {"City": "Madrid", "Dating Pool": "~2,000", "AI Jobs/mo": 45},
        {"City": "Barcelona", "Dating Pool": "~1,800", "AI Jobs/mo": 38}
    ]
)
```

**Defaults:**
- Goal: `GoalReference.LOCATION`
- Actions: "Full analysis" (primary) + "Dismiss"

---

## Usage Examples

### Example 1: Dating Insight (from ADR-005)

```python
from synthesis import Recommendation, ActionButton, GoalReference
from synthesis import format_recommendation_html, format_recommendation_slack

rec = Recommendation(
    one_liner="Thursday bachata is your best bet -- 3x more quality connections than apps.",
    data_rows=[
        {"Source": "Bachata", "Dates": 4, "Avg Quality": 7.8, "Follow-up Rate": "75%"},
        {"Source": "Tinder", "Dates": 8, "Avg Quality": 5.2, "Follow-up Rate": "25%"},
        {"Source": "Social", "Dates": 2, "Avg Quality": 8.0, "Follow-up Rate": "50%"}
    ],
    actions=[
        ActionButton(label="View details", action="details", primary=True),
        ActionButton(label="Dismiss", action="dismiss")
    ],
    goal=GoalReference.PARTNER
)

# For dashboard
html = format_recommendation_html(rec)

# For Slack notification
slack = format_recommendation_slack(rec)
```

### Example 2: Career Morning Brief (from ADR-005)

```python
rec = Recommendation(
    one_liner="This role could be your bridge to AI leadership -- 95% match, fully remote.",
    data_rows=[
        {"Dimension": "Role match", "Score": "9/10", "Why": "MCP + financial services"},
        {"Dimension": "Remote", "Score": "10/10", "Why": "Fully remote, no office visits"},
        {"Dimension": "Salary", "Score": "8/10", "Why": "EUR 140-160k range"},
        {"Dimension": "Tech overlap", "Score": "9/10", "Why": "Java + Python + LLM"}
    ],
    actions=[
        ActionButton(label="Apply", action="approve", primary=True),
        ActionButton(label="Skip", action="skip"),
        ActionButton(label="Save for later", action="save")
    ],
    goal=GoalReference.CAREER
)
```

### Example 3: Location Comparison (from ADR-005)

```python
rec = Recommendation(
    one_liner="Madrid doubles your dating pool and has 3x more AI jobs -- strongest candidate.",
    data_rows=[
        {"City": "Madrid", "Dating Pool": "~2,000", "AI Jobs/mo": 45, "Cost Index": 0.85, "Lifestyle": "8/10"},
        {"City": "Fuerteventura", "Dating Pool": "~200", "AI Jobs/mo": 2, "Cost Index": 0.70, "Lifestyle": "9/10"},
        {"City": "Barcelona", "Dating Pool": "~1,800", "AI Jobs/mo": 38, "Cost Index": 0.90, "Lifestyle": "8/10"}
    ],
    actions=[
        ActionButton(label="Full analysis", action="details", primary=True),
        ActionButton(label="Dismiss", action="dismiss")
    ],
    goal=GoalReference.LOCATION
)
```

### Example 4: Empty State

```python
from synthesis import EmptyState, format_empty_state_html, GoalReference

empty = EmptyState(
    count_needed=5,
    data_type="dates",
    insight_type="quality trends and best sources",
    goal=GoalReference.PARTNER
)

# Message: "After 5 more dates, I'll show you quality trends and best sources."
html = format_empty_state_html(empty)
slack = format_empty_state_slack(empty)
```

---

## Testing

Run the full test suite:

```bash
cd life-systems
pytest synthesis/tests/test_formatter.py -v
```

**Test coverage:**
- ✅ Validation constraints (120 chars, 10 rows, 5 columns, 3 actions)
- ✅ HTML formatting (structure, headers, tables, buttons)
- ✅ Slack formatting (markdown, tables, action prompts)
- ✅ Empty state formatting
- ✅ Domain-specific helpers
- ✅ Edge cases (empty data, Unicode, missing values)
- ✅ Real-world examples from ADR-005

**Total: 40+ test cases**

---

## Integration with Domain Contexts

### In DATE (Dating Module)

```python
from synthesis import format_dating_recommendation

def generate_source_insight(dates: List[Date]) -> Recommendation:
    """Rules engine: detect best source by quality"""
    # Calculate source performance
    source_stats = calculate_source_performance(dates)
    
    # Format as recommendation
    return format_dating_recommendation(
        one_liner=f"{best_source} is your best bet -- {multiplier}x quality vs apps.",
        source_data=source_stats
    )
```

### In DISC (Discovery Module)

```python
from synthesis import format_career_recommendation

def generate_job_alert(job: Job, score: JobScore) -> Recommendation:
    """Rules engine: alert on high-match jobs"""
    return format_career_recommendation(
        one_liner=f"This role could be your bridge to AI leadership -- {score.composite}% match.",
        job_data=[
            {"Dimension": "Role match", "Score": f"{score.role_match}/10"},
            {"Dimension": "Remote", "Score": f"{score.remote_friendly}/10"}
        ],
        job_id=job.id
    )
```

### In RELOC (Location Optimizer)

```python
from synthesis import format_location_recommendation

def generate_city_comparison(cities: List[City]) -> Recommendation:
    """Generate city comparison recommendation"""
    top_city = cities[0]
    
    return format_location_recommendation(
        one_liner=f"{top_city.name} doubles your dating pool and has 3x more AI jobs.",
        city_data=[
            {
                "City": city.name,
                "Dating Pool": city.dating_pool_size,
                "AI Jobs/mo": city.ai_jobs_per_month
            }
            for city in cities[:5]
        ]
    )
```

---

## Design Principles (from ADR-005)

### 1. Motivation-First
Every recommendation MUST answer: "How does this move me closer to my life goals?"

**Good:**
> "Thursday bachata is your best bet -- 3x more quality connections than apps."

**Bad:**
> "You have 4 dates from bachata events." (so what?)

### 2. Data-Backed
Every one-liner MUST be supported by evidence in the data table.

### 3. Actionable
Every recommendation MUST have clear next steps (action buttons).

### 4. Concise
- One-liner: max 120 chars (scan quickly)
- Data table: max 10 rows, 5 columns (avoid overwhelming)
- Actions: max 3 buttons (reduce decision fatigue)

### 5. Goal-Connected
Every recommendation MUST reference a life goal (partner, career, location, family, financial).

---

## Anti-Patterns (Never Do These)

❌ **Raw numbers without context**
```python
# BAD
one_liner = "50 jobs found"
```

✅ **Context + impact**
```python
# GOOD
one_liner = "3 new jobs match your criteria -- best is 95% match at Stripe."
```

---

❌ **Metric without goal connection**
```python
# BAD
one_liner = "Your career score is 72"
```

✅ **Goal-connected insight**
```python
# GOOD
one_liner = "This role could be your bridge to AI leadership -- 95% match."
```

---

❌ **Generic motivation**
```python
# BAD
one_liner = "Keep going!"
```

✅ **Data-backed encouragement**
```python
# GOOD
one_liner = "Date quality trending up this month -- +1.5 avg vs last month."
```

---

❌ **Long paragraph explanations**
```python
# BAD
one_liner = "Based on analysis of your past 4 weeks of dating activity..."
```

✅ **Sharp one-liner**
```python
# GOOD
one_liner = "Thursday bachata is your best bet -- 3x quality vs apps."
```

---

## Acceptance Criteria (All Met ✅)

| # | Criterion | Status |
|---|-----------|--------|
| AC-1 | Shared function: `format_recommendation(one_liner, data_rows, actions)` -> HTML + Slack markdown | ✅ |
| AC-2 | One-liner: max 120 chars, includes goal reference | ✅ |
| AC-3 | Data table: max 5 columns, max 10 rows | ✅ |
| AC-4 | Actions: max 3 buttons per recommendation | ✅ |
| AC-5 | Works in both dashboard HTML and Slack markdown | ✅ |
| AC-6 | Empty state template: "After [N] more [data_type], I'll show you [insight_type]." | ✅ |

---

## Future Enhancements

- [ ] **SYNTH-MVP-1**: Rules engine integration (Layer 1 from ADR-001)
- [ ] **SYNTH-M1-1**: Weekly AI synthesis (Layer 2 from ADR-001)
- [ ] **SYNTH-M2-1**: Life Move AI (Layer 3 from ADR-001)
- [ ] **LEARN-M3-1**: Track which recommendations Jurek acts on (self-learning)

---

## Dependencies

- Python 3.9+
- pytest (for tests)
- No external dependencies for formatter (pure Python)

---

## Files

```
synthesis/
├── __init__.py              # Module exports
├── formatter.py             # Core formatting logic (11KB)
├── README.md                # This file
└── tests/
    ├── __init__.py
    └── test_formatter.py    # Comprehensive test suite (20KB, 40+ tests)
```

---

## Demo

Run the demo to see examples:

```bash
cd life-systems
python -m synthesis.formatter
```

**Output:**
```
=== MOTIVATION-FIRST FORMATTER DEMO ===

HTML OUTPUT:
<div class="recommendation" data-goal="partner">
  <div class="one-liner">Thursday bachata is your best bet -- 3x more quality connections than apps.</div>
  ...
</div>

==================================================

SLACK OUTPUT:
*Thursday bachata is your best bet -- 3x more quality connections than apps.*

```
Source | Dates | Avg Quality | Follow-up Rate
------------------------------------------------
Bachata | 4 | 7.8 | 75%
Tinder | 8 | 5.2 | 25%
Social | 2 | 8.0 | 50%
```

▶️ _View details_ | • _Dismiss_

==================================================
```

---

## Contact

**Author**: Kevin (kevin-bot-openclaw-ops)  
**Epic**: EPIC-004 (Intelligence Layer)  
**Task**: SYNTH-MVP-2 (One-Liner + Data Table Formatter)  
**Status**: Complete ✅  
**Completion Date**: 2026-03-06
