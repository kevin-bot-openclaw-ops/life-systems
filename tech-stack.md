# Technology Stack Decisions

Version: 1.0
Updated: 2026-02-20
Status: Proposed

## Decision Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Storage** | SQLite (per context) | Simplicity, no ops overhead, sufficient for single-user system |
| **Event Transport** | File-based (JSON events directory) | No message queue infrastructure needed, git-trackable |
| **Backend** | Python 3.11+ | Existing OpenClaw ecosystem, ML/AI library support |
| **API** | FastAPI | Async support, auto-docs, type safety |
| **Web Dashboard** | React + TypeScript | Component isolation, type safety, wide adoption |
| **iOS Widget** | SwiftUI (later milestone) | Native iOS, declarative UI |
| **Deployment** | AWS EC2 (existing) | Already running OpenClaw, no new infra |
| **Scheduling** | systemd timers | Already used in OpenClaw, OS-level reliability |
| **Testing** | pytest + React Testing Library | Industry standard, good tooling |

---

## Detailed Decisions

### 1. Storage: SQLite per Context

**Decision**: Each bounded context gets its own SQLite database file.

**Pros**:
- Zero ops: no PostgreSQL/MySQL server to manage
- File-based: easy backup, version control friendly
- Sufficient performance for single-user workload
- Perfect isolation: one DB file per context = hard boundaries
- Portable: entire system state in `/data/*.sqlite` directory

**Cons**:
- Not multi-user (acceptable — Jurek is the only user)
- No built-in replication (acceptable — simple file backups)

**Alternative Considered**: Shared PostgreSQL
**Why Rejected**: Overkill for single user, adds deployment complexity, requires always-on server

**File Structure**:
```
/data/
  disc.sqlite          # DISC context data
  appl.sqlite          # APPL context data
  crst.sqlite          # CRST context data
  ...
  events/              # Event transport directory
    2026-02-20/
      001-opportunity-discovered.json
      002-opportunity-scored.json
```

---

### 2. Event Transport: File-Based JSON

**Decision**: Domain events published as JSON files in a shared `/data/events/` directory.

**Mechanism**:
- Context publishes event → writes `{timestamp}-{eventType}-{uuid}.json` to today's events folder
- Consumers poll events directory (or use inotify for real-time)
- Event files are append-only, never deleted (audit trail)

**Pros**:
- No message queue (Kafka/RabbitMQ) infrastructure
- Git-friendly: events can be versioned
- Debuggable: just open JSON file to see what happened
- Replayable: delete consumer state, replay events from directory
- Simple: no network calls, no authentication

**Cons**:
- Not real-time (polling latency ~5-10 seconds)
- Manual cleanup needed (archive old events monthly)

**Alternative Considered**: Redis Streams / RabbitMQ
**Why Rejected**: Infrastructure overhead, network calls, auth complexity. File-based is sufficient for batch-oriented workflows (job scanning is hourly, not millisecond-critical).

**Event File Example**:
```json
// /data/events/2026-02-20/142035-opportunity-discovered-a3f2b1c0.json
{
  "eventId": "a3f2b1c0-1234-5678-90ab-cdef12345678",
  "timestamp": "2026-02-20T14:20:35Z",
  "version": "v1",
  "source": "DISC",
  "data": { ... }
}
```

---

### 3. Backend: Python 3.11+

**Decision**: All contexts implemented in Python.

**Pros**:
- Consistency with OpenClaw (already Python)
- Rich AI/ML libraries (transformers, scikit-learn, pandas)
- FastAPI for async REST APIs
- Type hints (mypy) for safety

**Cons**:
- Slower than Go/Rust (acceptable — not CPU-bound)

**Alternative Considered**: TypeScript (Node.js)
**Why Rejected**: Python has better ML ecosystem, OpenClaw integration smoother.

---

### 4. Web Dashboard: React + TypeScript

**Decision**: Browser-based dashboard using React + TypeScript + Vite.

**Pros**:
- Type safety (catch UI bugs early)
- Component reuse across sections
- Wide hiring pool (if this becomes a product)
- Dev tools (React DevTools, hot reload)

**Cons**:
- Build step required

**Alternative Considered**: Vanilla JS + Tailwind
**Why Rejected**: TypeScript's type safety worth the build step. React's component model fits dashboard sections well.

**Architecture**:
```
/dashboard/
  src/
    sections/
      CareerSection.tsx    # Consumes CRST + DISC events
      DatingSection.tsx    # Consumes DATE events
      AlertsSection.tsx    # Consumes SYNTH alerts
    api/
      client.ts            # Calls backend API
```

---

### 5. Deployment: Monorepo on EC2

**Decision**: Single EC2 instance runs all contexts + dashboard.

**Structure**:
```
/opt/life-systems/
  contexts/
    disc/         # DISC context code
    appl/         # APPL context code
    ...
  dashboard/      # React build output
  data/           # SQLite DBs + events
  shared/         # Event schemas, ACLs
```

**Systemd Services**:
```
life-systems-disc.service      # DISC job scanner (cron: every hour)
life-systems-appl.service      # APPL draft generator (event-driven)
life-systems-synth.service     # SYNTH synthesis (every 10 min)
life-systems-dashboard.service # FastAPI serving React build
```

**Pros**:
- Reuses existing OpenClaw EC2
- Simple: one machine, no orchestration
- Cost: no additional infrastructure

**Cons**:
- Not horizontally scalable (acceptable — single user)

**Alternative Considered**: Docker Compose
**Why Rejected**: Systemd already proven in OpenClaw, less overhead.

---

### 6. Scheduling: systemd Timers

**Decision**: Use systemd timers (not cron) for periodic tasks.

**Example** (DISC job scanner):
```ini
# /etc/systemd/system/life-systems-disc.timer
[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

**Pros**:
- More reliable than cron (guaranteed execution, even after reboot)
- Logs in journalctl (easier debugging)
- Resource control (CPU/memory limits)

---

## Migration Path

### Phase 1: Shared Kernel (Current)
- Event schemas published
- ACL interfaces defined
- Tech stack decided

### Phase 2: MVP Contexts
- DISC + APPL + DASH
- File-based events working
- First end-to-end flow (job → draft → dashboard)

### Phase 3: Advisory Contexts
- MKTL + CRST + SYNTH
- Intelligence layer working

### Phase 4: Life Contexts
- DATE + RELOC
- Full synthesis working

### Phase 5: Learning
- LEARN context
- Feedback loops active

---

## Open Questions

1. **Event retention policy**: How long to keep event files? (Proposal: 30 days hot, 1 year archive, then delete)
2. **Backups**: Manual or automated? (Proposal: daily rsync to S3)
3. **Secrets management**: Where to store API keys? (Proposal: systemd environment files, same as OpenClaw)

---

## Approvals

| Role | Name | Status |
|------|------|--------|
| Architect | Kevin (OpenClaw) | Proposed |
| Product Owner | Jurek | Pending |
| Executor | Kevin | Approved (self) |

**Next Step**: Get Jurek's approval on storage + event transport decisions before implementing DISC-SPIKE-1.
