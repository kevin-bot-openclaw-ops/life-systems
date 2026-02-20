# Life Systems - Tech Stack Decision Record

**Version**: 1.0.0  
**Created**: 2026-02-20  
**Status**: APPROVED  

---

## Decision Summary

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Storage** | SQLite (per-context) | Simplicity, isolation, version control friendly, sufficient for single-user |
| **Event Transport** | File-based (MVP) → RabbitMQ (M2+) | Inspectable, debuggable, zero infrastructure (MVP); scalable (M2+) |
| **API** | FastAPI | Async support, auto OpenAPI docs, lightweight, Python ecosystem |
| **Background Jobs** | Systemd timers | Native to deployment host (AWS EC2), no cron complexity, service management |
| **Web Dashboard** | GitHub Pages (static) | Free hosting, CDN, version-controlled, zero backend |
| **iOS Widget** | Scriptable | Native iOS widgets, JavaScript (reuse logic), no App Store submission |
| **Observability** | JSON logs + trace IDs | Structured, parseable, grep-friendly, trace across contexts |

---

## Storage: SQLite Per-Context

### Decision
Each bounded context gets its own SQLite database (`disc.db`, `appl.db`, etc.).

### Rationale
- **Isolation**: No accidental cross-context queries (physical boundary enforces DDD rules)
- **Simplicity**: No database server, no connection pooling, no clustering complexity
- **Backup**: `cp data/*.db backup/` = full backup
- **Version control**: Schema migrations per context (Alembic), independent evolution
- **Sufficient scale**: Single-user system, <10k records per context, <1 query/second

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| PostgreSQL (shared DB, schemas per context) | Over-engineered for single-user; shared DB invites coupling |
| PostgreSQL (separate DBs per context) | Infrastructure overhead (connection pooling, backups, auth) |
| MongoDB | Overkill for structured data; SQL is better for relational queries |
| In-memory only | Data loss on restart; need persistence |

### Migration Path
If scale requires:
1. Extract high-volume context (e.g., DISC with 100k+ listings) → PostgreSQL
2. Keep low-volume contexts on SQLite (CRST, LEARN, SYNTH)
3. Events remain file-based or message queue (transport layer is independent of storage)

---

## Event Transport: File-Based (MVP)

### Decision
Events written as JSON files: `events/{event_type}/{timestamp}_{uuid}.json`

### Rationale
- **Inspectable**: `cat events/OpportunityDiscovered/*.json | jq`
- **Debuggable**: Add a file, replay the event, test consumer behavior
- **Version-controlled**: Events can be committed to Git for tests (anonymized samples)
- **Zero infrastructure**: No message broker, no service management
- **Sufficient**: Single producer per event type, low volume (<100 events/day)

### Event Flow
1. Context publishes event: writes JSON file to `events/{event_type}/`
2. Consumer polls directory (systemd timer every 5 min) or watches with inotify
3. Consumer processes file, marks as processed (move to `events/processed/` or delete)

### Alternatives Considered
| Alternative | Why Rejected (MVP) | When to Reconsider |
|-------------|--------------------|--------------------|
| RabbitMQ | Overhead (service, auth, queues); overkill for <100 events/day | Multi-consumer patterns, >1k events/day |
| Redis Pub/Sub | Ephemeral (no persistence); need event replay | Real-time requirements, event streams |
| Kafka | Extreme overkill; designed for millions of events/day | Never for this use case |
| Database table as queue | Coupling via shared DB; breaks isolation | Never (violates DDD) |

### M2+ Migration Path
When file-based becomes limiting (multi-consumer race conditions, >1k events/day):
1. Introduce RabbitMQ or Redis Streams
2. Contexts publish to message broker instead of files
3. Schema validation unchanged (events still JSON, same schemas)
4. ACLs unchanged (still translate events to internal types)

---

## API: FastAPI

### Decision
REST API per context: `/api/disc/...`, `/api/appl/...`, etc.

### Rationale
- **Async**: Native async/await for non-blocking I/O (job scraping, LLM calls)
- **Auto docs**: OpenAPI/Swagger UI generated automatically
- **Lightweight**: No Django ORM overhead, no Spring Boot startup time
- **Python ecosystem**: Integrates with existing Claude API client, Slack SDK, Brave Search

### API Design
- **Context-scoped**: Each context exposes its own endpoints (no cross-context API calls)
- **Events-first**: APIs are secondary (primary communication is events)
- **Read-only mostly**: Most endpoints are GET (write operations via events)

Example:
```python
# DISC context API
@app.get("/api/disc/listings")
async def list_listings(limit: int = 20, scored_only: bool = False):
    # Returns listings from disc.db, never queries appl.db
    ...
```

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Flask | Synchronous by default; async support is bolted-on |
| Django | Too heavy; brings ORM, admin panel, migrations we don't need |
| Express.js (Node) | Introduces second language; Python ecosystem preferred |
| No API (events only) | Dashboard needs data access; API simplifies that |

---

## Background Jobs: Systemd Timers

### Decision
Systemd timers instead of cron.

### Rationale
- **Service management**: `systemctl status life-systems-disc` shows last run, logs, failures
- **Logging**: journalctl captures all output
- **Dependencies**: Can declare dependencies (e.g., synthesis runs after all advisors complete)
- **Environment**: Easier to manage secrets, Python virtualenv paths

### Example Timer

```ini
# /etc/systemd/system/life-systems-disc.timer
[Unit]
Description=Life Systems - Discovery Scanner (every 4h)

[Timer]
OnCalendar=*-*-* 00,04,08,12,16,20:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/life-systems-disc.service
[Unit]
Description=Life Systems - Discovery Scanner

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/.openclaw/workspace/life-systems
ExecStart=/home/ubuntu/.openclaw/workspace/life-systems/venv/bin/python -m disc.scanner
```

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Cron | Less observability, harder to manage dependencies, environment vars tricky |
| Celery | Overkill; introduces Redis/RabbitMQ dependency, complex for simple periodic tasks |
| APScheduler | In-process scheduler; requires long-running daemon (systemd is simpler) |

---

## Presentation: GitHub Pages + Scriptable

### Decision
- **Web dashboard**: Static HTML + vanilla JS, hosted on GitHub Pages
- **iOS widget**: Scriptable app (JavaScript widget framework)

### Rationale (Web Dashboard)
- **Free hosting**: GitHub Pages = CDN + HTTPS
- **Version control**: HTML/JS/CSS committed to repo, rollback trivial
- **Zero backend**: Fetches `synthesized_state.json` from EC2 API or static JSON (no server-side rendering)
- **Fast**: Static site loads in <1s, works offline after first load

### Rationale (iOS Widget)
- **No App Store**: Scriptable widgets = instant deployment (edit JS, refresh widget)
- **Reuse logic**: JavaScript for both web dashboard and widget (share view model code)
- **Native widgets**: Home screen, Lock Screen, StandBy mode

### Data Flow
1. SYNTH publishes `StateUpdated` event → writes `synthesized_state.json` to EC2 `/var/www/life-systems/data/`
2. Dashboard fetches `https://ec2.openclaw.ai/life-systems/data/synthesized_state.json`
3. Widget fetches same JSON, displays on iOS Home Screen

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| React SPA | Build step complexity, npm dependencies, overkill for simple dashboard |
| Native iOS app (Swift) | Requires App Store submission, Xcode setup, Swift learning curve |
| Telegram bot as UI | Not visual enough; dashboard is richer (charts, tables, trends) |

---

## Observability: JSON Logs + Trace IDs

### Decision
Structured JSON logs, one log file per context per day, trace IDs propagate across events.

### Rationale
- **Parseable**: `cat logs/disc/2026-02-20.log | jq '.level == "ERROR"'`
- **Contextual**: Every log line includes `context`, `event_type`, `trace_id`
- **Traceable**: Follow a job listing from discovery → scoring → draft → decision via trace_id
- **Grep-friendly**: Still plain text, no log aggregation service required

### Log Format
```json
{
  "timestamp": "2026-02-20T11:00:00Z",
  "level": "INFO",
  "context": "DISC",
  "event_type": "OpportunityDiscovered",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Discovered 23 listings from LinkedIn Jobs",
  "data": {"source": "linkedin", "count": 23}
}
```

### Trace ID Propagation
1. DISC creates `trace_id` when discovering listing
2. `OpportunityDiscovered` event includes `trace_id`
3. APPL reads event, uses same `trace_id` in logs
4. All logs for that listing share the same `trace_id`

### Query Examples
```bash
# All errors today
cat logs/*/2026-02-20.log | jq 'select(.level == "ERROR")'

# Trace a specific listing
grep "a1b2c3d4-e5f6-7890-abcd-ef1234567890" logs/*/*.log

# Count events by type
cat logs/disc/*.log | jq -r '.event_type' | sort | uniq -c
```

### Alternatives Considered
| Alternative | Why Rejected (MVP) | When to Reconsider |
|-------------|--------------------|--------------------|
| ELK Stack | Elasticsearch + Kibana = heavy infrastructure | Multi-user, >10k events/day |
| Datadog / New Relic | Cost for single-user system | Production SaaS deployment |
| CloudWatch Logs | AWS lock-in, query syntax less familiar than jq | AWS-native deployment |

---

## Dependencies

| Context | External Dependencies |
|---------|----------------------|
| DISC | Brave Search API, job board APIs (LinkedIn, Upwork, etc.) |
| APPL | Claude API (draft generation), Slack SDK (approval queue) |
| MKTL | None (consumes DISC events only) |
| CRST | None (consumes APPL events only) |
| DATE | Apple Health API (optional), event discovery APIs (Meetup, Eventbrite) |
| RELOC | Cost of living APIs, tax calculators (external data sources) |
| SYNTH | None (consumes advisor events only) |
| DASH | None (consumes SYNTH events only) |
| LEARN | scikit-learn (logistic regression) |

---

## Deployment Architecture

```
AWS EC2 (existing OpenClaw instance)
├── /home/ubuntu/.openclaw/workspace/life-systems/
│   ├── disc/          (Python module)
│   ├── appl/          (Python module)
│   ├── crst/          (Python module)
│   ├── mktl/          (Python module)
│   ├── date/          (Python module)
│   ├── reloc/         (Python module)
│   ├── synth/         (Python module)
│   ├── learn/         (Python module)
│   ├── data/          (SQLite DBs: disc.db, appl.db, ...)
│   ├── events/        (JSON event files)
│   ├── logs/          (JSON log files)
│   └── venv/          (Python virtualenv)
├── /etc/systemd/system/
│   ├── life-systems-disc.timer
│   ├── life-systems-disc.service
│   ├── life-systems-advisors.timer
│   ├── life-systems-advisors.service
│   ├── life-systems-synth.timer
│   └── life-systems-synth.service
└── /var/www/life-systems/
    └── data/
        └── synthesized_state.json  (served via nginx)
```

---

**End of Tech Stack Decision Record v1.0.0**
