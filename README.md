# Life Systems — Shared Kernel

**Version**: 1.0  
**Created**: 2026-02-20  
**Status**: Foundation Complete

This repository contains the shared kernel for the Life Systems project — a Domain-Driven Design (DDD) based personal intelligence platform.

---

## What's Here

This is the **foundation** that all bounded contexts build against. No code yet — just contracts, schemas, and decisions.

| File | Purpose |
|------|---------|
| **ARCHITECTURE.md** | Complete system architecture overview |
| **context-map.mermaid** | Visual diagram of 9 bounded contexts + event flows |
| **schemas/** | 14 versioned JSON schemas for domain events |
| **acl-interfaces.md** | Anti-Corruption Layer specifications (7 ACLs) |
| **isolation-rules.md** | Context isolation enforcement rules |
| **tech-stack.md** | Technology decisions (SQLite, file-based events, Python/React) |
| **dashboard-wireframe.md** | UI mockup + section-to-context mappings |

---

## Quick Start

1. **Read ARCHITECTURE.md first** — 10-minute overview of the entire system
2. **Review context-map.mermaid** — see how the 9 contexts relate
3. **Check schemas/** — understand the 14 event types
4. **Read acl-interfaces.md** — see how contexts translate between each other's models

---

## Event Catalog

| Event | Publisher | Consumers | Purpose |
|-------|-----------|-----------|---------|
| OpportunityDiscovered | DISC | APPL | New job found |
| OpportunityScored | DISC | CRST, LEARN | Job scored |
| DraftGenerated | APPL | CRST | Application draft created |
| DecisionMade | APPL | SYNTH, LEARN | User approved/rejected |
| MarketReportPublished | MKTL | CRST, SYNTH | Market analysis |
| StrategyReportPublished | CRST | SYNTH, APPL | Career advice |
| SignalCollected | DATE | SYNTH | Dating/fitness signal |
| DatingReportPublished | DATE | SYNTH | Dating metrics |
| RelocationReportPublished | RELOC | SYNTH | Location score |
| StateUpdated | SYNTH | DASH | Synthesized state change |
| ConflictDetected | SYNTH | DASH | Domain conflict |
| AlertTriggered | SYNTH | DASH | Actionable alert |
| WeightsAdjusted | LEARN | DISC | Scoring model update |
| DriftDetected | LEARN | CRST | Model drift detected |

---

## Bounded Context List

| Context | Milestone | Status |
|---------|-----------|--------|
| **SHARED** | MVP | ✅ Complete (this repo) |
| **DISC** | SPIKE → MVP | Pending |
| **APPL** | SPIKE → M1 → M2 | Pending |
| **MKTL** | MVP → M1 | Pending |
| **CRST** | M1 | Pending |
| **DATE** | SPIKE → M2 | Pending |
| **RELOC** | SPIKE → M2 | Pending |
| **SYNTH** | M2 | Pending |
| **DASH** | SPIKE → M2 | Pending |
| **LEARN** | M3 | Pending |

---

## Architecture Principles

1. **Events are the only contract** — No direct DB queries between contexts
2. **ACLs prevent coupling** — Never import another context's types
3. **Each context owns its data** — One SQLite file per context
4. **Version everything** — Events, ACLs, context internals
5. **Deploy independently** — Update DISC without touching APPL

---

## Tech Stack Summary

- **Storage**: SQLite (per context)
- **Events**: File-based JSON (append-only)
- **Backend**: Python 3.11+ (FastAPI)
- **Frontend**: React + TypeScript
- **Deploy**: AWS EC2 (systemd services)

Rationale in [tech-stack.md](tech-stack.md).

---

## Next Steps

1. **DISC-SPIKE-1**: Job board API research (validates data sources)
2. **DISC-MVP-1**: Job scanner implementation (first context live)
3. **APPL-SPIKE-1**: Humanizer rules research (application quality)
4. **DASH-SPIKE-1**: Dashboard shell with mock data (UI validation)

See `JerzyPlocha/kevin-backlog` BACKLOG.md for full task queue.

---

## Test Scenarios

### TS-SHARED-1a: End-to-End Trace
**Goal**: Verify a job listing crosses exactly 3 ACL boundaries (DISC → APPL → CRST → SYNTH → DASH).

**Steps**:
1. Create mock OpportunityDiscovered event
2. APPL consumes via OpportunityQualifier ACL
3. CRST consumes OpportunityScored
4. SYNTH aggregates into StateUpdated
5. DASH renders via ViewModelMapper ACL

**Pass**: Event ID traceable through all 4 contexts, data transformed at each ACL, no direct type imports.

### TS-SHARED-1b: Isolation Violation Attempt
**Goal**: Verify MKTL schema cannot reference DATE schema.

**Steps**:
1. Attempt to create event schema with cross-context type reference
2. JSON Schema validator rejects
3. Code review checklist catches import violation

**Pass**: Violation prevented at schema design + code review.

### TS-SHARED-1c: Schema Validation
**Goal**: All 14 schemas validate against sample payloads.

**Steps**:
1. Create sample payload for each event type
2. Run JSON Schema validator
3. Verify 100% pass

**Pass**: All schemas valid, no structural errors.

---

## Questions?

See [ARCHITECTURE.md](ARCHITECTURE.md) for deep dive or check [isolation-rules.md](isolation-rules.md) for boundary enforcement details.

---

**Delivered by**: Kevin (OpenClaw)  
**BACKLOG Task**: SHARED-MVP-1  
**Next**: Await Jurek approval → implement first spike
