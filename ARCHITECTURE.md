# Life Systems Architecture

Version: 1.0
Created: 2026-02-20
Status: Shared Kernel Established

## Executive Summary

Life Systems is a Domain-Driven Design (DDD) based personal intelligence platform for managing career, dating, and relocation decisions through autonomous data collection, scoring, and synthesis.

**Core Concept**: Nine bounded contexts, each owning a specific domain, communicate via versioned domain events through Anti-Corruption Layers (ACLs). A synthesis engine aggregates signals into a unified dashboard.

---

## System Context

```
External Data Sources → DISC/MKTL/DATE/RELOC → Advisory Contexts → SYNTH → DASH
                                    ↓
                                  APPL (human-in-loop)
                                    ↓
                                  LEARN (feedback)
```

**User Interaction Points**:
1. **Dashboard (DASH)**: Primary UI — web + iOS widget
2. **Approval Queue (APPL)**: Review/approve AI-generated job applications
3. **Manual Input (DATE)**: Log dating/fitness data

**Autonomous Components**: Everything else runs without human intervention.

---

## Bounded Context Catalog

### 1. SHARED (Kernel)
**Purpose**: Event schemas, ACL interfaces, shared types  
**Owns**: JSON schemas, this architecture doc  
**Publishes**: (none — documentation only)  
**Dependencies**: (none)

### 2. DISC (Discovery)
**Purpose**: Job scanning + opportunity scoring  
**Owns**: Job listings, scoring models, opportunity IDs  
**Publishes**: OpportunityDiscovered, OpportunityScored  
**Consumes**: WeightsAdjusted (from LEARN)  
**Run Frequency**: Hourly (systemd timer)

### 3. APPL (Application)
**Purpose**: Generate job application drafts + approval queue  
**Owns**: Drafts, user decisions  
**Publishes**: DraftGenerated, DecisionMade  
**Consumes**: OpportunityDiscovered (DISC), StrategyReportPublished (CRST)  
**Run Frequency**: Event-driven (when opportunity arrives)

### 4. MKTL (Market)
**Purpose**: Track AI/ML job market trends  
**Owns**: Market snapshots, trend analyses  
**Publishes**: MarketReportPublished  
**Consumes**: (none — pull external data)  
**Run Frequency**: Weekly

### 5. CRST (Career Strategy)
**Purpose**: Career advice based on opportunities + market  
**Owns**: Strategy models, recommendation engine  
**Publishes**: StrategyReportPublished  
**Consumes**: OpportunityScored (DISC), DraftGenerated (APPL), MarketReportPublished (MKTL), DriftDetected (LEARN)  
**Run Frequency**: Daily or on-demand

### 6. DATE (Dating Intelligence)
**Purpose**: Track dating/fitness metrics  
**Owns**: Dating signals, fitness data  
**Publishes**: SignalCollected, DatingReportPublished  
**Consumes**: (none — manual input + external APIs)  
**Run Frequency**: Manual + daily aggregation

### 7. RELOC (Relocation)
**Purpose**: Score relocation destinations  
**Owns**: Location data, scoring models  
**Publishes**: RelocationReportPublished  
**Consumes**: (none — pull external data)  
**Run Frequency**: Weekly or on-demand

### 8. SYNTH (Synthesis)
**Purpose**: Aggregate all domains into unified state  
**Owns**: Synthesized state, conflict detection, alert rules  
**Publishes**: StateUpdated, ConflictDetected, AlertTriggered  
**Consumes**: ALL advisory context reports + decision events  
**Run Frequency**: Every 10 minutes

### 9. DASH (Dashboard)
**Purpose**: Present synthesized view to user  
**Owns**: View models, UI state, user preferences  
**Publishes**: (none)  
**Consumes**: StateUpdated, ConflictDetected, AlertTriggered (SYNTH)  
**Run Frequency**: Real-time web app, polling backend every 30s

### 10. LEARN (Learning)
**Purpose**: Feedback loops for scoring + strategy  
**Owns**: Model weights, drift thresholds  
**Publishes**: WeightsAdjusted, DriftDetected  
**Consumes**: OpportunityScored (DISC), DecisionMade (APPL)  
**Run Frequency**: Weekly analysis

---

## Event Flow Diagram

See [context-map.mermaid](context-map.mermaid) for visual representation.

**Key Flows**:

**Job Application Flow**:
```
DISC (scan job boards)
  → OpportunityDiscovered
  → OpportunityScored
APPL (read OpportunityDiscovered)
  → DraftGenerated
CRST (read OpportunityScored + DraftGenerated)
  → StrategyReportPublished
SYNTH (read DecisionMade + StrategyReportPublished)
  → StateUpdated
DASH (read StateUpdated)
  → Display to user
```

**Learning Loop**:
```
User approves/rejects draft in APPL
  → DecisionMade
LEARN (correlate with OpportunityScored)
  → WeightsAdjusted
DISC (apply new weights to next scan)
  → Improved scoring
```

---

## Anti-Corruption Layers (ACLs)

See [acl-interfaces.md](acl-interfaces.md) for full specifications.

**Purpose**: Prevent coupling by translating between context-specific models.

**Example**: APPL reads `OpportunityDiscovered` from DISC but never imports DISC's internal types. Instead:

```python
# DISC publishes (internal model)
class DiscoveredOpportunity:
    opportunity_id: str
    source_url: str
    raw_data: dict

# ACL translates to APPL's expected format
def qualify_opportunity(event: OpportunityDiscoveredEvent) -> QualifiedOpportunity:
    return QualifiedOpportunity(
        id=generate_appl_id(),  # APPL owns its IDs
        source_ref=event.data.opportunity_id,  # Opaque ref to DISC
        title=event.data.raw_data['title'],
        priority=map_score_to_priority(event.data.score)
    )
```

**All ACLs live in**: `/shared/acls/` directory, versioned alongside event schemas.

---

## Technology Stack

See [tech-stack.md](tech-stack.md) for decision rationale.

| Component | Technology |
|-----------|-----------|
| Storage | SQLite (one DB per context) |
| Event Transport | File-based JSON (append-only) |
| Backend | Python 3.11+ (FastAPI) |
| Frontend | React + TypeScript |
| Deployment | AWS EC2 (systemd services) |
| Scheduling | systemd timers |

**Why File-Based Events?**
- No message queue infrastructure
- Git-trackable (audit trail)
- Replayable (delete consumer state, replay from files)
- Simple debugging (just open JSON file)

---

## Data Isolation Rules

See [isolation-rules.md](isolation-rules.md) for complete specification.

**Core Principle**: A context NEVER directly queries another context's database or references its internal IDs.

**Enforcement**:
1. Each context has its own SQLite file (physical separation)
2. Event files are the ONLY inter-context interface
3. ACLs enforce type boundaries
4. Code reviews check for cross-context imports

**Example Violation**:
```python
# ❌ WRONG: APPL importing DISC's models
from disc.models import DiscoveredOpportunity

# ✓ CORRECT: APPL reading event via ACL
event = read_event('OpportunityDiscovered.v1.json')
qualified = OpportunityQualifier.translate(event)
```

---

## Event Schema Versioning

All events follow this structure:

```json
{
  "eventId": "uuid-v4",
  "timestamp": "2026-02-20T14:30:00Z",
  "version": "v1",
  "source": "DISC",
  "data": { ... }
}
```

**Versioning Rules**:
1. Add new fields freely (backward compatible)
2. Breaking changes require new version (v2)
3. Both versions coexist for 30+ days
4. Consumers declare required version in their ACL

**Schema Location**: `/shared/schemas/*.v1.json` (JSON Schema format)

---

## Testing Strategy

### Unit Tests (per context)
- Mock all inbound events
- Verify outbound events match schema
- No cross-context dependencies

### Integration Tests (ACLs)
- Real event payloads → ACL → verify output
- Schema validation on both sides

### End-to-End Tests
- Trace job listing: DISC → APPL → CRST → SYNTH → DASH
- Verify data transformations at each boundary
- Check dashboard displays correct data

**Test Scenarios**: See SHARED-MVP-1 acceptance criteria (TS-SHARED-1a/b/c).

---

## Deployment Architecture

```
/opt/life-systems/
  contexts/
    disc/              # DISC context (Python package)
      disc.sqlite      # DISC-owned data
      scanner.py
      scorer.py
    appl/              # APPL context
      appl.sqlite
      generator.py
    ...
  shared/              # Shared kernel
    schemas/           # Event JSON schemas
    acls/              # ACL implementations
  data/
    events/            # Event transport directory
      2026-02-20/
        001-opportunity-discovered.json
        002-opportunity-scored.json
  dashboard/           # React build output
    index.html
    assets/
```

**Systemd Services**:
```
life-systems-disc.service      # Job scanner (hourly)
life-systems-appl.service      # Draft generator (event-driven)
life-systems-crst.service      # Strategist (daily)
life-systems-synth.service     # Synthesis (every 10 min)
life-systems-dashboard.service # Web server
```

---

## Monitoring & Observability

**Metrics to Track**:
- Events published per context per day
- Event processing latency (time from publish to consumed)
- ACL translation errors
- Dashboard API response times

**Logging**:
- Each context logs to `/var/log/life-systems/{context}.log`
- Event files provide audit trail

**Alerts**:
- SYNTH publishes AlertTriggered events → DASH displays
- systemd failures → email notification (journalctl integration)

---

## Security & Privacy

**Data Ownership**: All data owned by Jurek, stored locally on EC2.

**Secrets**:
- API keys (job boards, dating apps) → systemd environment files
- No secrets in code or event files

**Access Control**:
- Dashboard requires login (session-based)
- No public endpoints (EC2 security group: SSH + HTTPS only)

**Audit Trail**:
- All events immutable (append-only event files)
- User decisions logged (DecisionMade events)

---

## Migration & Evolution

**Phase 1: Shared Kernel** ✓ (this document)
- Event schemas defined
- ACL interfaces spec'd
- Tech stack decided

**Phase 2: Core Loop (MVP)**
- DISC → APPL → DASH
- First job application generated end-to-end

**Phase 3: Advisory Layer**
- MKTL + CRST + SYNTH
- Intelligence synthesis working

**Phase 4: Life Domains**
- DATE + RELOC
- Full multi-domain synthesis

**Phase 5: Learning**
- LEARN context
- Feedback loops active

---

## Open Questions

1. **Event retention**: Keep 30 days hot, archive 1 year, then delete?
2. **Backup strategy**: Daily rsync to S3 or manual?
3. **Dashboard auth**: OAuth or simple password?

---

## Approvals

| Role | Name | Status |
|------|------|--------|
| Architect | Kevin (OpenClaw) | Approved |
| Product Owner | Jurek | Pending |
| Executor | Kevin | Approved |

**Next Step**: Get Jurek's approval, then implement DISC-SPIKE-1.

---

## References

- [Context Map](context-map.mermaid) — Visual diagram
- [Event Schemas](schemas/) — 14 JSON Schema files
- [ACL Interfaces](acl-interfaces.md) — 7 ACL specifications
- [Isolation Rules](isolation-rules.md) — Context boundaries enforcement
- [Tech Stack](tech-stack.md) — Technology decisions + rationale
- [Dashboard Wireframe](dashboard-wireframe.md) — UI mockup + section mappings
