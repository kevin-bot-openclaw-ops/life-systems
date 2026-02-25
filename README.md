# Life Systems

**Personal intelligence platform for career, dating, and relocation.**

---

## Overview

Life Systems is a FastAPI web application that aggregates job listings, generates application drafts, provides market intelligence, and synthesizes insights into a unified dashboard.

**Live URL:** https://life.plocha.eu (via Cloudflare Tunnel)

---

## Architecture

```
┌─────────────────┐
│  Job Sources    │  HN Algolia, Working Nomads, AIJobs.co.uk
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scanner Cron   │  Every 4 hours (systemd timer)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │  Jobs, Scores, Drafts, Decisions
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI App    │  REST API + Static Dashboard
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dashboard UI   │  React-style SPA (vanilla JS)
└─────────────────┘
```

### Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Database:** SQLite (single file, no external DB)
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **AI:** Claude API (Anthropic) for cover letter generation
- **Deployment:** systemd, Cloudflare Tunnel
- **Hosting:** AWS EC2

---

## API Endpoints

### Health & Status

- `GET /api/health` → `{"status": "ok", "version": "0.1.0"}`
- `GET /api/dashboard` → Synthesized state (jobs, metrics, summary)
- `GET /api/widget` → Minimal data for iPhone widget

### Jobs

- `GET /api/jobs` → List of scored job listings (paginated)
  - Query params: `limit`, `offset`, `min_score`
- `GET /api/jobs/{id}` → Full job details + generated draft
- `POST /api/jobs/{id}/draft` → Generate new cover letter draft
  - Body: `{"variant": "fintech|ml_research|platform|general"}`
- `POST /api/jobs/{id}/decide` → Record decision (approve/reject/defer)
  - Body: `{"action": "approve", "reason": "..."}`

### Market Intelligence

- `GET /api/market` → Latest market report (top skills, salary ranges, gaps)

### Admin

- `POST /api/scan` → Manually trigger job scan (requires auth)

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- pip
- systemd (for service management)
- Cloudflare Tunnel (cloudflared)

### Installation

1. **Clone the repo:**

```bash
cd /home/ubuntu/.openclaw/workspace/life-systems
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure environment:**

```bash
sudo mkdir -p /etc/life-systems
sudo cp .env.example /etc/life-systems/env
sudo nano /etc/life-systems/env
```

Edit `/etc/life-systems/env`:
- Set `ANTHROPIC_API_KEY` (required for draft generation)
- Set `LS_USER` and `LS_PASSWORD` (basic auth credentials)
- Set `CLOUDFLARE_TUNNEL_TOKEN` (from Cloudflare Zero Trust dashboard)
- Set `DB_PATH` (default: `/var/lib/life-systems/life.db`)

4. **Initialize database:**

```bash
python3 -c "from api.database import init_db; init_db('/var/lib/life-systems/life.db')"
```

5. **Install systemd services:**

```bash
sudo cp systemd/life-systems.service /etc/systemd/system/
sudo cp systemd/life-systems-scanner.service /etc/systemd/system/
sudo cp systemd/life-systems-scanner.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable life-systems
sudo systemctl enable life-systems-scanner.timer
```

6. **Start services:**

```bash
sudo systemctl start life-systems
sudo systemctl start life-systems-scanner.timer
```

7. **Check status:**

```bash
sudo systemctl status life-systems
sudo journalctl -u life-systems -f
```

---

## Cloudflare Tunnel Setup

1. **Create a tunnel:**

```bash
cloudflared tunnel create life-systems
```

2. **Configure DNS:**

Add a CNAME record in Route 53:
```
life.plocha.eu → <tunnel-id>.cfargotunnel.com
```

3. **Create tunnel config:**

```yaml
# /etc/cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /home/ubuntu/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: life.plocha.eu
    service: http://localhost:8000
  - service: http_status:404
```

4. **Run tunnel:**

```bash
cloudflared tunnel run life-systems
```

Or install as a systemd service:

```bash
sudo cloudflared service install
sudo systemctl start cloudflared
```

---

## Development

### Run locally:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export LS_USER="admin"
export LS_PASSWORD="test"
export DB_PATH="./life.db"

python -m uvicorn api.main:app --reload --port 8000
```

Open: http://localhost:8000

### Run scanner manually:

```bash
python -c "import asyncio; from api.database import Database, init_db; from api.scanner import run_scan; init_db('./life.db'); db=Database('./life.db'); print(asyncio.run(run_scan(db)))"
```

### API docs:

Open: http://localhost:8000/docs (FastAPI auto-generated Swagger UI)

---

## Database Schema

### Tables

- **jobs** → Job listings (title, company, location, description, tech_stack, url, etc.)
- **scores** → Job scores with breakdown (score, dimensions)
- **drafts** → Generated cover letters (job_id, text, created_at)
- **decisions** → User decisions (job_id, action=approve/reject/defer, reason)
- **market_reports** → Market intelligence (top_skills, salary_ranges, gap_analysis)
- **scans** → Scan events (source, jobs_found, timestamp)

---

## Scanner Sources

Currently integrated (from DISC-MVP-1):

1. **HN Algolia** → Hacker News "Who's Hiring" threads
2. **Working Nomads** → Remote job board (AI/ML filter)
3. **AIJobs.co.uk** → UK-based AI jobs site

Adding new sources:

1. Implement source class in `discovery/sources/`
2. Add to `api/scanner.py` sources list
3. Source must return standardized job dict (see `discovery/models.py`)

---

## Cover Letter Generation

Uses Claude API (anthropic python SDK).

### Variants:

- **fintech** → Emphasize banking systems + AI/ML
- **ml_research** → Lead with AI/ML projects
- **platform** → Emphasize MLOps and infrastructure
- **general** → Balanced approach

### Fallback:

If Claude API fails or no API key, uses template-based generation.

---

## Monitoring

### Logs:

```bash
sudo journalctl -u life-systems -f
sudo journalctl -u life-systems-scanner -f
```

### Check scanner timer:

```bash
systemctl list-timers | grep life-systems
```

### Database size:

```bash
ls -lh /var/lib/life-systems/life.db
```

---

## iPhone Scriptable Widget

Minimal widget showing career score, jobs today, and top job.

**Endpoint:** `/api/widget`

**Example response:**
```json
{
  "career_score": 72,
  "jobs_today": 8,
  "top_job_title": "Senior AI Engineer at Mistral AI",
  "last_scan_ago": "2 hours ago"
}
```

Script location: `dashboard/scriptable-widget.js`

---

## Security

- **Basic Auth:** All endpoints require HTTP Basic Authentication
- **Environment Variables:** Secrets stored in `/etc/life-systems/env` (not in code)
- **Cloudflare Tunnel:** HTTPS with zero-trust access policies
- **Database:** SQLite file with restrictive permissions (chmod 600)

---

## Troubleshooting

### Service won't start:

```bash
sudo journalctl -u life-systems -n 50
```

Common issues:
- Missing `ANTHROPIC_API_KEY` in `/etc/life-systems/env`
- Database path not writable
- Port 8000 already in use

### Scanner not running:

```bash
sudo systemctl status life-systems-scanner.timer
systemctl list-timers | grep life-systems
```

Force run:

```bash
sudo systemctl start life-systems-scanner.service
```

### Dashboard shows "Failed to load":

- Check API is running: `curl http://localhost:8000/api/health`
- Check basic auth credentials
- Check browser console for CORS errors

---

## Contributing

### Code structure:

```
life-systems/
├── api/
│   ├── main.py           ← FastAPI app
│   ├── models.py         ← Pydantic models
│   ├── database.py       ← SQLite layer
│   ├── scanner.py        ← Job scanner integration
│   ├── draft_generator.py ← Claude API integration
│   └── static/
│       └── index.html    ← Dashboard UI
├── discovery/            ← Job discovery (from DISC-MVP-1)
├── application/          ← Draft generation (from APPL-M1-1)
├── career/               ← Strategy analysis (from CRST-M1-1)
├── market-intelligence/  ← Market reports (from MKTL-MVP-1)
├── systemd/              ← Service files
├── requirements.txt
└── README.md             ← This file
```

### Testing:

Run discovery tests:
```bash
cd discovery && pytest
```

Run application tests:
```bash
cd application && pytest
```

---

## License

Private project. Not open source.

---

## Contact

For questions: jerzy.plocha@gmail.com
