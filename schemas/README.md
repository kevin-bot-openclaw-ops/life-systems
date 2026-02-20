# Life Systems - Event Schemas

**Version**: 1.0.0  
**Created**: 2026-02-20  

---

## Overview

This directory contains JSON Schema definitions for all domain events in the Life Systems architecture. Every event published by a bounded context must validate against its schema.

## Schema Versioning

- **Format**: `{EventType}_v{N}.json`
- **Version in event**: `"version": "v1"`
- **Backward compatibility**: Adding optional fields is backward compatible (v1 → v1 extended)
- **Breaking changes**: Require new version (v1 → v2)

## Schema Catalog

| Event | Version | Publisher | Consumers | Description |
|-------|---------|-----------|-----------|-------------|
| OpportunityDiscovered | v1 | DISC | APPL (via ACL), MKTL | Job listing discovered from external sources |
| OpportunityScored | v1 | DISC | APPL (via ACL) | Job listing with calculated relevance score |
| DraftGenerated | v1 | APPL | CRST | Application draft generated and humanized |
| DecisionMade | v1 | APPL | CRST, LEARN | Human decision on application draft |
| MarketReportPublished | v1 | MKTL | SYNTH (via ACL) | Weekly market intelligence report |
| StrategyReportPublished | v1 | CRST | SYNTH (via ACL) | Weekly career strategy funnel analysis |
| DatingReportPublished | v1 | DATE | SYNTH (via ACL) | Weekly dating/social activity report |
| RelocationReportPublished | v1 | RELOC | SYNTH (via ACL) | City comparison and relocation analysis |
| StateUpdated | v1 | SYNTH | DASH (via ACL), LEARN | Synthesized state from all advisors |
| ConflictDetected | v1 | SYNTH | DASH | Advisor disagreement detected |
| AlertTriggered | v1 | SYNTH | DASH | Threshold breach or trend change |
| WeightsAdjusted | v1 | LEARN | DISC, SYNTH | Scoring weight adjustment |
| DriftDetected | v1 | LEARN | SYNTH | Preference or behavioral drift detected |

## Validation

### Python (jsonschema)

```python
import json
import jsonschema

# Load schema
with open('schemas/OpportunityDiscovered_v1.json') as f:
    schema = json.load(f)

# Validate event
event = {
    "event_type": "OpportunityDiscovered",
    "version": "v1",
    "timestamp": "2026-02-20T11:00:00Z",
    "context": "DISC",
    "payload": { ... }
}

jsonschema.validate(instance=event, schema=schema)
```

### Test Suite

All schemas validated in `tests/test_schemas.py`:
- Schema is valid JSON Schema (meta-validation)
- Sample events pass validation
- Invalid events fail validation with correct error messages

## Adding a New Event

1. Create schema file: `schemas/NewEvent_v1.json`
2. Add to catalog table above
3. Add sample event to `tests/fixtures/events/`
4. Add validation test to `tests/test_schemas.py`
5. Update ARCHITECTURE.md with event flow

## Schema Fields (Common)

Every event MUST have:
- `event_type` (string, const)
- `version` (string, const "v1")
- `timestamp` (string, ISO8601 format)
- `context` (string, one of: DISC|APPL|CRST|MKTL|DATE|RELOC|SYNTH|LEARN|DASH)
- `payload` (object, event-specific structure)

## ACL Translation Rules

**Critical**: ACLs consume events but NEVER expose the raw event schema to the consuming context.

Example:
- APPL context receives `OpportunityScored` event
- OpportunityQualifier ACL translates to `ApplicationCandidate` (APPL internal type)
- APPL code NEVER imports `OpportunityScored` schema

This prevents leaky abstractions and ensures context isolation.

## References

- **Architecture Doc**: `../docs/ARCHITECTURE.md`
- **ACL Specs**: See ARCHITECTURE.md "Anti-Corruption Layers" section
- **Context Map**: See ARCHITECTURE.md Mermaid diagram

---

**End of Schema README v1.0.0**
