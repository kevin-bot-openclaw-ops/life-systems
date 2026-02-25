# Anti-Corruption Layer (ACL) Interface Specifications

Version: 1.0
Updated: 2026-02-20

## Purpose

ACLs prevent context coupling by translating between domain-specific models. Each ACL is a single-purpose adapter that converts data from one bounded context's format into another's expected format.

---

## ACL Catalog

### 1. OpportunityQualifier

**Purpose**: Translates raw OpportunityDiscovered events into APPL's internal opportunity model.

**Input**: `OpportunityDiscovered.v1` (from DISC)
**Output**: APPL internal `QualifiedOpportunity` model

```typescript
interface QualifiedOpportunity {
  id: string;
  sourceOpportunityId: string; // DISC's opportunityId
  title: string;
  company: string;
  matchScore: number; // derived from DISC's scoring signals
  applicationDeadline?: Date;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
}
```

**Transformation Rules**:
- Extract required fields from `rawData`
- Map DISC's score (0-100) to priority buckets
- Infer deadline from `postedDate` if not explicit

---

### 2. SignalNormalizer

**Purpose**: Converts raw dating/fitness signals from DATE into standardized metrics for SYNTH.

**Input**: `SignalCollected.v1` (from DATE)
**Output**: SYNTH internal `NormalizedSignal` model

```typescript
interface NormalizedSignal {
  domain: 'DATING' | 'FITNESS';
  metric: string;
  value: number; // normalized to 0-1 scale
  timestamp: Date;
  confidence: number; // 0-1
}
```

**Transformation Rules**:
- Normalize different signal types to common 0-1 scale
- Map signal types to metric names
- Calculate confidence based on data completeness

---

### 3. MarketAdvisorAdapter

**Purpose**: Translates market reports into career strategy inputs.

**Input**: `MarketReportPublished.v1` (from MKTL)
**Output**: CRST internal `MarketContext` model

```typescript
interface MarketContext {
  trendingSkills: Array<{skill: string, demand: number}>;
  salaryBenchmarks: Record<string, {min: number, max: number, median: number}>;
  demandRegions: string[];
  updatedAt: Date;
}
```

---

### 4. StrategyAdvisorAdapter

**Purpose**: Translates strategy reports into synthesis inputs.

**Input**: `StrategyReportPublished.v1` (from CRST)
**Output**: SYNTH internal `StrategyInsight` model

```typescript
interface StrategyInsight {
  recommendations: Array<{
    action: string;
    priority: number; // 0-1
    domain: 'CAREER' | 'RELOCATION' | 'DATING';
    timeframe: 'IMMEDIATE' | 'SHORT_TERM' | 'LONG_TERM';
  }>;
  confidence: number;
}
```

---

### 5. RelocationAdvisorAdapter

**Purpose**: Translates relocation reports into synthesis inputs.

**Input**: `RelocationReportPublished.v1` (from RELOC)
**Output**: SYNTH internal `RelocationInsight` model

```typescript
interface RelocationInsight {
  location: string;
  overallScore: number; // 0-100
  factorBreakdown: Record<string, number>;
  recommendation: 'STRONGLY_RECOMMEND' | 'CONSIDER' | 'AVOID';
}
```

---

### 6. DatingAdvisorAdapter

**Purpose**: Translates dating reports into synthesis inputs.

**Input**: `DatingReportPublished.v1` (from DATE)
**Output**: SYNTH internal `DatingInsight` model

```typescript
interface DatingInsight {
  period: {start: Date, end: Date};
  metrics: Record<string, number>;
  trend: 'IMPROVING' | 'STABLE' | 'DECLINING';
  actionableInsights: string[];
}
```

---

### 7. ViewModelMapper

**Purpose**: Transforms synthesized state into dashboard view models.

**Input**: `StateUpdated.v1` (from SYNTH)
**Output**: DASH internal `DashboardViewModel`

```typescript
interface DashboardViewModel {
  sections: {
    career: CareerSectionVM;
    dating: DatingSectionVM;
    relocation: RelocationSectionVM;
    alerts: AlertsSectionVM;
  };
  lastUpdated: Date;
}
```

**Transformation Rules**:
- Flatten nested synthesis state into section-specific VMs
- Apply display formatting (dates, percentages)
- Filter sensitive data based on user preferences

---

## Implementation Constraints

1. **One-way only**: ACLs translate in one direction (input context → consuming context)
2. **Stateless**: ACLs don't persist data; they're pure transformations
3. **Versioned**: Each ACL versioned alongside its input event schema
4. **No cross-context references**: Output models never reference input context's IDs directly
5. **Error handling**: Invalid input → log + emit fallback or skip (never crash)

---

## Testing Requirements

Each ACL must have unit tests covering:
- Happy path transformation
- Missing optional fields
- Invalid input (malformed JSON, wrong schema version)
- Edge cases (empty arrays, null values)
