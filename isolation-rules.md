# Context Isolation Rules

Version: 1.0
Updated: 2026-02-20

## Core Principle

**Bounded contexts are independently deployable, testable, and evolvable.**

Each context owns its data, logic, and internal models. Inter-context communication happens ONLY through published domain events and ACL adapters.

---

## Event Visibility Matrix

| Consumer Context | Can Read Events From |
|------------------|---------------------|
| DISC | LEARN (WeightsAdjusted) |
| APPL | DISC (OpportunityDiscovered), CRST (StrategyReportPublished) |
| MKTL | (none — pull-based external data) |
| CRST | DISC (OpportunityScored), APPL (DraftGenerated, DecisionMade), MKTL (MarketReportPublished), LEARN (DriftDetected) |
| DATE | (none — manual data entry + external APIs) |
| RELOC | (none — pull-based external data) |
| SYNTH | APPL (DecisionMade), MKTL (MarketReportPublished), CRST (StrategyReportPublished), DATE (SignalCollected, DatingReportPublished), RELOC (RelocationReportPublished) |
| DASH | SYNTH (StateUpdated, ConflictDetected, AlertTriggered) |
| LEARN | APPL (DecisionMade), DISC (OpportunityScored) |

**Rule**: A context may ONLY consume events explicitly listed in its row. Any other event is invisible to it.

---

## Data Ownership

| Context | Owns |
|---------|------|
| DISC | Job listings, scoring models, opportunity IDs |
| APPL | Application drafts, approval queue, user decisions |
| MKTL | Market data snapshots, trend analyses |
| CRST | Career strategies, recommendation logic |
| DATE | Dating signals, fitness data, dating reports |
| RELOC | Location data, relocation scores |
| SYNTH | Synthesized state, conflict detection logic |
| DASH | View models, UI state, user preferences |
| LEARN | Model weights, drift detection thresholds |

**Rule**: A context's owned data is NEVER directly queried by another context. All reads happen via published events.

---

## Schema Isolation Violations (Examples)

### ❌ VIOLATION: Direct ID Reference
```json
// In APPL's internal model
{
  "draftId": "draft-123",
  "discOpportunityId": "opp-456" // ❌ references DISC's internal ID
}
```

**Fix**: Use ACL to translate DISC's `opportunityId` into APPL's own foreign key.

```json
{
  "draftId": "draft-123",
  "sourceOpportunityRef": "opp-456" // ✓ stored as opaque ref, never queried
}
```

---

### ❌ VIOLATION: Shared Type Definition
```typescript
// Shared across DISC and APPL
interface Opportunity {
  id: string;
  title: string;
  company: string;
}
```

**Fix**: Each context defines its own model. ACL translates between them.

```typescript
// DISC's model
interface DiscoveredOpportunity { ... }

// APPL's model (different!)
interface ApplicationTarget { ... }

// ACL translates DISC → APPL
function qualifyOpportunity(disc: DiscoveredOpportunity): ApplicationTarget { ... }
```

---

## Deployment Independence

Each context can be:
- **Deployed separately**: Update DISC without touching APPL
- **Versioned independently**: DISC v2.3, APPL v1.8, etc.
- **Tested in isolation**: APPL tests use mocked OpportunityDiscovered events
- **Scaled independently**: Run 3 DISC workers, 1 APPL worker

**Rule**: A context deployment NEVER requires coordinated deploys of other contexts (except when event schema versions change — handled by versioning + deprecation).

---

## Event Versioning & Deprecation

When an event schema changes:
1. Publish new version (e.g., `OpportunityDiscovered.v2`)
2. Both versions coexist for 30 days minimum
3. Consumer contexts upgrade at their own pace
4. Old version deprecated after all consumers migrated

**Rule**: A context may publish multiple event versions simultaneously. Consumers declare which version they expect.

---

## Testing Isolation

### Unit Tests (per context)
- Mock all inbound events
- Verify outbound events match schema
- No cross-context imports

### Integration Tests (ACLs)
- Test ACL adapters with real event payloads
- Verify schema compliance on both sides

### End-to-End Tests (full flow)
- Trace a job listing from DISC → APPL → CRST → SYNTH → DASH
- Verify data transformations at each ACL boundary

---

## Conflict Resolution

If two contexts need to share logic (e.g., both DISC and CRST score opportunities):
1. **Don't**: Extract to SHARED kernel if truly shared
2. **Duplicate**: Each context implements independently if logic differs
3. **Publish**: One context publishes the result as an event

**Default: Duplicate.** Shared code creates coupling. Duplicate when in doubt.

---

## Summary Rules

1. ✅ **Events are the only contract** between contexts
2. ✅ **ACLs prevent coupling** — never import another context's types
3. ✅ **Each context owns its data** — no cross-context queries
4. ✅ **Deploy independently** — no coordinated releases
5. ✅ **Version everything** — events, ACLs, context internals
6. ❌ **Never** directly reference another context's database or IDs
7. ❌ **Never** share code between contexts (unless in SHARED kernel)
8. ❌ **Never** skip the ACL — even if it feels redundant
