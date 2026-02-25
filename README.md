# Life Systems

Personal life operating system: Career, Dating, Fitness

**Version**: 1.0.0  
**Status**: Phase 1 Complete (FastAPI skeleton + SQLite schema + basic auth + all endpoint stubs)

## Quick Start

```bash
# 1. Initialize database
sudo mkdir -p /var/lib/life-systems
sudo chown ubuntu:ubuntu /var/lib/life-systems
python3 -m database.db

# 2. Set environment variables
export LS_USER=jurek
export LS_PASSWORD='LifeSystems2026!'

# 3. Run locally
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Test
curl -u jurek:LifeSystems2026! http://localhost:8000/api/health
```

## API Endpoints

### Core
- `GET /api/health` - Health check (no auth)
- `GET /api/widget` - iPhone widget data
- `GET /api/dashboard` - Full dashboard state

### Jobs (Career)
- `GET /api/jobs` - List scored jobs
- `GET /api/jobs/{id}` - Job details + draft
- `POST /api/jobs/{id}/draft` - Generate cover letter
- `POST /api/jobs/{id}/decide` - Approve/reject/defer

### Dating
- `GET /api/dates` - List date logs
- `POST /api/dates` - Create date log

### Fitness
- `GET /api/fitness` - Gym streak + stats
- `POST /api/fitness/log` - Log workout

### Intelligence
- `GET /api/market` - Market intelligence
- `GET /api/actions` - Today's action queue
- `GET /api/insights` - Patterns, accountability, optimization

## Database Schema

11 tables:
- `jobs` - Job listings
- `scores` - Job scores (5 dimensions)
- `drafts` - AI-generated cover letters
- `decisions` - User decisions
- `dates` - Dating CRM logs
- `fitness` - Gym streak tracking
- `social_events` - Bachata, meetups, etc
- `market_reports` - Market intelligence
- `scans` - Scanner execution logs
- `actions` - Daily action queue
- `scores_history` - Score trending

## Deployment (Caddy + systemd)

Coming in Phase 8. For now, run locally with uvicorn.

## Next Phases

- **Phase 2**: Job scanner (5+ sources) + scoring engine
- **Phase 3**: React SPA dashboard
- **Phase 4**: Dating CRM + Fitness tracker
- **Phase 5**: Cover letter drafter (Claude API)
- **Phase 6**: Score calculator + insights engine
- **Phase 7**: Slack notifications (morning/evening)
- **Phase 8**: Caddy + systemd + widget

## Architecture

```
Caddy (HTTPS, basic auth, reverse proxy)
  ↓
FastAPI (localhost:8000)
  ↓
SQLite (/var/lib/life-systems/life.db)
```

## Environment Variables

See `.env.example` for full list. Required:
- `LS_USER` - Username (default: jurek)
- `LS_PASSWORD` - Password
- `ANTHROPIC_API_KEY` - For cover letter generation (Phase 5)
- `SLACK_BOT_TOKEN` - For notifications (Phase 7)

## Development

```bash
# Activate venv
source venv/bin/activate

# Run with auto-reload
uvicorn api.main:app --reload

# Initialize/reset database
python3 -m database.db
```

## Status

✅ **Phase 1 Complete** (2 hours)
- FastAPI skeleton with 14 endpoint stubs
- All 11 SQLite tables defined
- Basic HTTP Auth implemented
- Caddy installed and configured
- Requirements.txt created

**Next**: Phase 2 (Job scanner + scoring engine)
