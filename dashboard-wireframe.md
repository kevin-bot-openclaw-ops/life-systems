# Life Systems Dashboard Wireframe

Version: 1.0
Updated: 2026-02-20

## Layout Overview

```
┌────────────────────────────────────────────────────────────────┐
│  Life Systems Dashboard                            ⚙️ Profile  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │   🎯 Career          │  │   ❤️ Dating          │           │
│  │                      │  │                      │           │
│  │  • 5 new jobs        │  │  • 3 matches this    │           │
│  │  • 2 drafts pending  │  │    week              │           │
│  │  • Apply to TopCo    │  │  • 2 conversations   │           │
│  │                      │  │  • 1 date scheduled  │           │
│  └──────────────────────┘  └──────────────────────┘           │
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │   🌍 Relocation      │  │   📊 Market Intel    │           │
│  │                      │  │                      │           │
│  │  • Corralejo: 85/100 │  │  • RAG: demand ↑ 7%  │           │
│  │  • Weather: 24°C ☀️  │  │  • Python: hot       │           │
│  │  • CoLiving avail    │  │  • Remote: 45 roles  │           │
│  │                      │  │                      │           │
│  └──────────────────────┘  └──────────────────────┘           │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  🚨 Alerts & Actions                                   │   │
│  │  ────────────────────────────────────────────────────  │   │
│  │  🔴 URGENT: Apollo.io application closes in 2 days     │   │
│  │  🟡 Medium: Portfolio needs GitHub README update       │   │
│  │  🟢 Low: Tech radar shows MLOps trending               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  📈 Synthesis View                                     │   │
│  │  ────────────────────────────────────────────────────  │   │
│  │  Career momentum: ████████▒▒ 80% ↑                    │   │
│  │  Dating momentum: ██████▒▒▒▒ 60% →                    │   │
│  │  Health:          ███████▒▒▒ 70% ↑                    │   │
│  │  Location fit:    ██████████ 100% ✓                   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Last updated: 2 minutes ago • Next update: 8 minutes          │
└────────────────────────────────────────────────────────────────┘
```

---

## Section Mappings to Contexts

| Dashboard Section | Data Sources (Contexts) |
|-------------------|-------------------------|
| **Career** | DISC (opportunities), APPL (drafts, decisions), CRST (strategy) |
| **Dating** | DATE (signals, reports) |
| **Relocation** | RELOC (location scores) |
| **Market Intel** | MKTL (market reports), CRST (trend analysis) |
| **Alerts & Actions** | SYNTH (AlertTriggered events) |
| **Synthesis View** | SYNTH (StateUpdated events) |

---

## Detailed Section Specs

### 1. Career Section

**Data Sources**:
- DISC: OpportunityScored events (top 5 by score)
- APPL: DraftGenerated + DecisionMade (pending drafts count)
- CRST: StrategyReportPublished (recommended actions)

**Visual Elements**:
- Card with colored border (green = opportunities, yellow = pending)
- Number badges (5 new jobs, 2 drafts)
- Top action (e.g., "Apply to TopCo" from CRST)

**Click Behavior**:
- Expand to show job list with scores
- Click job → open APPL draft approval UI

---

### 2. Dating Section

**Data Sources**:
- DATE: DatingReportPublished (weekly metrics)
- DATE: SignalCollected (today's activity count)

**Visual Elements**:
- Heart icon with match count
- Conversation/date stats
- Trend indicator (improving/stable/declining)

**Click Behavior**:
- Expand to detailed dating metrics
- Weekly chart (matches, messages, dates)

---

### 3. Relocation Section

**Data Sources**:
- RELOC: RelocationReportPublished (top scored locations)

**Visual Elements**:
- Location name + score (0-100)
- Weather icon + temp (from RELOC data)
- Key factor highlight (e.g., "CoLiving avail")

**Click Behavior**:
- Expand to location comparison table
- Factor breakdown chart

---

### 4. Market Intel Section

**Data Sources**:
- MKTL: MarketReportPublished (trending skills, demand)

**Visual Elements**:
- Skill name + trend arrow (↑ ↓ →)
- Remote job count
- Salary trend sparkline

**Click Behavior**:
- Expand to full market report
- Skill deep-dive with salary data

---

### 5. Alerts & Actions

**Data Sources**:
- SYNTH: AlertTriggered events (priority-sorted)

**Visual Elements**:
- Priority color: 🔴 URGENT, 🟡 MEDIUM, 🟢 LOW
- Alert message
- Action button (if `actionRequired=true`)

**Click Behavior**:
- Dismiss alert
- Take action (routes to relevant section)

---

### 6. Synthesis View

**Data Sources**:
- SYNTH: StateUpdated (synthesized metrics)

**Visual Elements**:
- Progress bars for each life domain
- Trend arrows (↑ improving, ↓ declining, → stable)
- Overall health indicator

**Click Behavior**:
- Expand to conflict view (if ConflictDetected events exist)
- Show detailed metrics

---

## Mobile Adaptation (iOS Widget — M2)

```
┌─────────────────┐
│ Life Systems    │
├─────────────────┤
│ 🎯 5 jobs       │
│ ❤️ 3 matches    │
│ 🚨 1 urgent     │
└─────────────────┘
```

**Widget Behavior**:
- Tap → open web dashboard
- Shows top 3 metrics only
- Red badge if urgent alerts exist

---

## Update Frequency

| Section | Update Interval | Trigger |
|---------|----------------|---------|
| Career | 1 hour | DISC scan completes |
| Dating | Manual + daily | User logs data or midnight |
| Relocation | Weekly | RELOC analysis runs |
| Market Intel | Weekly | MKTL report published |
| Alerts | Real-time | SYNTH detects alert condition |
| Synthesis | 10 minutes | SYNTH aggregation runs |

**Dashboard polling**: Every 30 seconds for alerts, every 5 minutes for data sections.

---

## API Endpoints (DASH consumes)

```
GET /api/dashboard/career        → CareerSectionVM
GET /api/dashboard/dating        → DatingSectionVM
GET /api/dashboard/relocation    → RelocationSectionVM
GET /api/dashboard/market        → MarketSectionVM
GET /api/dashboard/alerts        → Alert[]
GET /api/dashboard/synthesis     → SynthesisVM
```

Each endpoint reads latest events from SYNTH's StateUpdated and domain-specific events, applies ACL (ViewModelMapper), returns JSON.

---

## Next Steps

1. **DASH-SPIKE-1**: Build dashboard shell with mock data (validates wireframe)
2. **SYNTH-M2-1**: Implement synthesis engine (produces StateUpdated events)
3. **DASH-M2-1**: Wire real data sources to dashboard sections
