# 🚀 Life Systems v5 - Production Deployment Guide

**Deployed:** March 11, 2026 at 07:38 UTC  
**Status:** ✅ ALL MODULES LIVE  
**URL:** https://life.plocha.eu

---

## ✅ What's Deployed

### 1. **Advisor View Dashboard** (MAIN INTERFACE)

**URL:** https://life.plocha.eu/advisor-view.html

**What it shows:**
- **Health & Attractiveness Optimizer** - Your daily T-score (testosterone/energy), exercise streak, stress trend
- **Dating Intelligence** - Dating pool status, source comparison (apps vs social), activity correlations
- **Career Intelligence** - New AI/ML job matches, scoring, application tracking
- **Location Comparison** - Madrid, Barcelona, Lisbon scores across dating pool, jobs, cost of living

**How to use:**
1. Open https://life.plocha.eu/advisor-view.html
2. Login: `jurek` / `LifeSystems2026!`
3. Dashboard auto-refreshes with latest data

**Key features:**
- One-liner summaries (motivation-first format)
- Data tables (sortable, filterable)
- Action buttons (log activities, review jobs, etc.)
- Cross-goal recommendations

---

### 2. **Readiness Score Engine** (GOAL1-02)

**API Endpoint:** `GET /api/readiness/score`

**What it calculates:**
- Daily readiness score out of 7.0 (testosterone/attractiveness proxy)
- Components: gym (+2.0), sun (+1.5), sleep (+1.5), cold/heat (+1.0), coffee (+0.5), movement (+0.5)
- Color zones: 🟢≥5.0 READY, 🟡3.5-4.9 MODERATE, 🔴<3.5 LOW

**Example response:**
```json
{
  "score": 3.5,
  "max_score": 7.0,
  "breakdown": {
    "gym": 2.0,
    "sun": 0.0,
    "sleep": 0.0,
    "cold_heat": 1.0,
    "coffee": 0.5,
    "movement": 0.0
  },
  "status": "MODERATE",
  "recommendations": [
    "Get 20+ min sun exposure before lunch",
    "Log 7-8h sleep tonight",
    "Add 20min walk or swim"
  ]
}
```

**How to test:**
```bash
curl -u jurek:LifeSystems2026! https://life.plocha.eu/api/readiness/score | jq
```

**Dashboard view:** Included in Advisor View → Health Optimizer section

---

### 3. **Dating Pool Monitor** (GOAL1-01)

**API Endpoint:** `GET /api/advisor/dating`

**What it tracks:**
- Dating app activity (Bumble, Tinder, Hinge)
- Date quality scores and outcomes
- Source comparison (apps vs social vs events)
- Pool exhaustion detection

**Example response:**
```json
{
  "one_liner": "Social is your strongest channel — 9.0/10 average quality across 1 dates.",
  "data_table": [
    {"source": "Social", "dates": 1, "avg_quality": 9.0, "best": 9},
    {"source": "Event", "dates": 1, "avg_quality": 8.0, "best": 8},
    {"source": "App", "dates": 1, "avg_quality": 7.0, "best": 7}
  ],
  "pool_status": {
    "exhausted": false,
    "exhausted_apps": [],
    "current_location": "Fuerteventura",
    "alternative_cities": [
      {"name": "Berlin", "pool_size": 12000},
      {"name": "Madrid", "pool_size": 8000}
    ]
  }
}
```

**How to log dates:**
- Via iPhone Shortcut (see `docs/IPHONE-SHORTCUT-GUIDE.md`)
- Via API: `POST /api/dates`
- Via dashboard action button

**Dashboard view:** Advisor View → Dating Intelligence section

---

### 4. **Job Scanner & Tracker** (GOAL2-01, DISC-MVP-1/2)

**API Endpoints:**
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{id}` - Get specific job details
- `POST /api/jobs/{id}/decide` - Mark job decision (pass/review/applied/interview)
- `POST /api/jobs/{id}/draft` - Generate cover letter draft

**What it does:**
- Scans 3 sources: Remotive, HackerNews (Who's Hiring), LinkedIn
- Auto-scores jobs based on your criteria (remote-only, EU-friendly, €100k+, fintech/banking domain)
- Tracks application funnel (saw → reviewed → applied → interview → offer)
- Generates cover letter drafts

**Scoring criteria:**
- ✅ Fully remote: +25 points
- ✅ EU-friendly: +20 points
- ✅ Salary €100k+: +20 points
- ✅ Fintech/banking domain: +15 points
- ✅ Senior/Staff/Principal title: +10 points
- ✅ MLOps/ML platform keywords: +10 points

**How to use:**
```bash
# List jobs
curl -u jurek:LifeSystems2026! 'https://life.plocha.eu/api/jobs?limit=10' | jq

# Get job details
curl -u jurek:LifeSystems2026! 'https://life.plocha.eu/api/jobs/30' | jq

# Mark job as reviewed
curl -u jurek:LifeSystems2026! -X POST 'https://life.plocha.eu/api/jobs/30/decide' \
  -H 'Content-Type: application/json' \
  -d '{"decision": "review", "notes": "Strong match, need to research company"}'
```

**Dashboard view:** Advisor View → Career section

**Auto-scan:** Every 4 hours via systemd timer

---

### 5. **Location Comparison Engine** (RELOC-MVP-1/2)

**API Endpoints:**
- `GET /api/cities` - List all cities with scores
- `GET /api/cities/{city_id}` - Get detailed city breakdown
- `GET /api/cities/recommendation` - Get top recommendation

**What it compares:**
- Dating pool size (verified counts from research)
- AI/ML job market (remote + onsite)
- Cost of living (rent, food, transport)
- Social scene (bachata/kizomba nights per week)
- Visa ease
- Language advantage

**Scoring model:**
- Dating: 40% (2x weight of other dimensions)
- Jobs: 20%
- Cost of living: 15%
- Social scene: 15%
- Other: 10%

**Top cities (as of March 11):**
1. **Madrid** - 8.92/10 (400k dating pool, 10 local AI jobs, 35 remote)
2. **Barcelona** - 8.65/10 (350k dating pool, 12 local AI jobs, 38 remote)
3. **Lisbon** - 6.25/10 (120k dating pool, 10 local AI jobs, 30 remote)

**How to test:**
```bash
curl -u jurek:LifeSystems2026! https://life.plocha.eu/api/cities | jq
```

**Dashboard view:** Advisor View → Location section

---

### 6. **Activities Integration** (ACT-MVP-1/2, ACT-M1-1)

**What's syncing:**
- ✅ Auto-sync every 4 hours from Activities API
- ✅ 13+ activity types tracked (gym, sun, sleep, cold-exposure, dating apps, dates, etc.)
- ✅ Named measurements (US-145 compatible)
- ✅ Behavioral rules engine (14 rules active)

**Behavioral rules examples:**
- "2+ gym sessions per week" → readiness score boost
- "Sun exposure <15 min for 3 days" → low energy warning
- "0 dates in 14 days" → pool exhaustion check
- "Coffee >3/day" → stress indicator

**Storage:**
- Local cache: `/var/lib/life-systems/life.db` (SQLite)
- Source of truth: Activities API (read-only share token)

**How to verify sync:**
```bash
# Check recent activities
curl -u jurek:LifeSystems2026! 'https://life.plocha.eu/api/dashboard' | jq '.advisor.health.t_score.sparkline'
```

---

### 7. **Recommendation Engine** (SYNTH-MVP-1/2)

**What it does:**
- Cross-goal recommendations (e.g., "Madrid scores high for both dating AND jobs")
- Priority-sorted actions (P0 = today, P1 = this week)
- Decision tracking (what you decided + why)

**Example recommendations:**
```json
{
  "recommendations": [
    {
      "one_liner": "Log your next date within 24 hours to build consistent tracking habits.",
      "priority": 1,
      "goal": "GOAL-1",
      "action": {"type": "primary", "label": "Log date", "href": "/api/dates"}
    },
    {
      "one_liner": "Review new job matches before they get stale (most posted <48h ago).",
      "priority": 2,
      "goal": "GOAL-2",
      "action": {"type": "primary", "label": "Review jobs", "href": "/api/jobs"}
    }
  ]
}
```

**Dashboard view:** Advisor View → Recommendations section (bottom)

---

## 📊 What You Can Do NOW

### Immediate Actions

1. **View Dashboard**
   - Open https://life.plocha.eu/advisor-view.html
   - Login: `jurek` / `LifeSystems2026!`
   - See all 3 goal sections + recommendations

2. **Check Readiness Score**
   - Included in Health Optimizer section
   - Shows your current T-score/energy level
   - Recommendations for improvement

3. **Review Job Matches**
   - 30 jobs already scanned and scored
   - Click "Review all jobs" button
   - Mark decisions (pass/review/applied)

4. **Compare Locations**
   - Madrid, Barcelona, Lisbon comparison
   - Full breakdown: dating pool, jobs, cost, social scene
   - 50 days until May 1 decision deadline

5. **Log Activities**
   - Use iPhone Shortcut for dates, gym, sun, etc.
   - Auto-syncs to dashboard every 4 hours
   - Builds your behavioral intelligence

---

## 🔧 Technical Details

### Service Status

**Main API:**
```bash
sudo systemctl status life-systems.service
```

**Activities Sync:**
```bash
sudo systemctl status life-systems-activities.timer
sudo systemctl status life-systems-activities.service
```

**Logs:**
```bash
# API logs
sudo journalctl -u life-systems.service -f

# Activities sync logs
sudo journalctl -u life-systems-activities.service -f
```

### Database

**Location:** `/var/lib/life-systems/life.db` (SQLite WAL mode)

**Tables:**
- `dates` - Dating activity tracking
- `jobs` - Job listings + decisions
- `cities` - Location comparison data
- `activities` - Local cache of Activities API data
- `decisions` - User decisions + rationale
- `recommendations` - Generated recommendations

**Backup:** (Not yet configured - TODO: S3 backup)

### API Authentication

**Method:** HTTP Basic Auth  
**Username:** `jurek`  
**Password:** `LifeSystems2026!`

**Change password:**
```bash
# Edit systemd service
sudo systemctl edit life-systems.service

# Add:
[Service]
Environment="LS_PASSWORD=YourNewPasswordHere"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart life-systems.service
```

### HTTPS

**Certificate:** Let's Encrypt (via Caddy)  
**Auto-renewal:** Yes (Caddy handles automatically)  
**Config:** `/etc/caddy/Caddyfile`

---

## 📈 Data Requirements

Some features need more data to unlock full intelligence:

### Dating Intelligence (GOAL1-04)
- **Minimum:** 5+ dates logged
- **Optimal:** 15+ dates
- **Unlocks:** Activity correlations (gym → better dates?), pre-date optimizer

**Current status:** 3 dates logged (need 2 more for correlations)

### Job Intelligence (GOAL2-01)
- **Minimum:** 10+ job decisions
- **Optimal:** 30+ days of data
- **Unlocks:** Application funnel analysis, time-to-interview predictions

**Current status:** 30 jobs scanned, 0 decisions logged (start deciding!)

### Location Intelligence (GOAL3-01)
- **Minimum:** 14+ days system usage
- **Optimal:** 30+ days
- **Unlocks:** Personal fit scoring (which city matches YOUR behavior patterns)

**Current status:** 7 days (need 1 more week)

---

## 🚧 Known Limitations

### Not Yet Available

1. **Write-scoped Activities token** (US-147)
   - Can READ activities, cannot WRITE yet
   - Auto-logging blocked (sprint completions, system events)
   - **Workaround:** Use iPhone Shortcut to log manually

2. **MCP Client** (US-148)
   - Read-only wrapper built (TASK-055 complete)
   - Real MCP client not deployed yet
   - **No impact:** Current wrapper works fine

3. **Correlation Analysis** (GOAL1-04)
   - Need 15+ dates to unlock
   - Requires US-131 (correlations API) deployment
   - **Current status:** 3 dates logged, need 12 more

4. **Social/Job Activity Types**
   - Need to create `bachata`, `kizomba`, `surfing` types in Activities
   - Need `job-application`, `interview`, `offer` types
   - **Impact:** Can't log these activities yet

### Known Bugs

- None currently identified 🎉

---

## 🔄 What Gets Updated Automatically

### Every 4 Hours
- Activities sync from API
- Job scanner runs
- Readiness score recalculated
- Recommendations refreshed

### Every Page Load
- Dashboard data (real-time from database)
- Advisor view (cached for 5 minutes)

---

## 📱 Mobile Access

**Dashboard is mobile-optimized** (375px width)

**How to add to iPhone home screen:**
1. Open https://life.plocha.eu/advisor-view.html in Safari
2. Tap Share button
3. Tap "Add to Home Screen"
4. Name it "Life Systems"
5. Tap "Add"

Now you have a full-screen app icon!

---

## 🎯 Next Steps

### Your Action Items

1. **Start logging dates** (need 5+ for correlations)
   - Use iPhone Shortcut
   - Include chemistry rating, conversation quality
   - Log within 24h of date

2. **Review job matches** (30 waiting for you)
   - Mark as: pass, review, applied, interview
   - Add notes on why you decided
   - Builds your decision intelligence

3. **Create social activity types** (5 min setup)
   - `bachata`, `kizomba`, `surfing`, `beach-volleyball`
   - Then start logging via iPhone Shortcut

4. **Professional photo shoot** (highest ROI: 21x)
   - Research showed €300 photo shoot → 17 matches
   - Best investment for dating ROI

5. **Book Madrid trial** (Apr 1-30)
   - Malasaña neighborhood
   - €1200-1500/month AirBnb
   - Test bachata scene + dating pool

### My Action Items (Blocked)

1. **Build US-147** (write-scoped share tokens)
   - Enables auto-logging from sprint loop
   - You must implement this on Activities API

2. **Deploy US-148** (MCP server)
   - Enables cleaner integrations
   - Not blocking any features

3. **Accumulate data** (ongoing)
   - 15+ dates for correlations
   - 30+ days for location intelligence
   - 30+ job decisions for funnel analysis

---

## 🆘 Troubleshooting

### Dashboard not loading
```bash
# Check service
sudo systemctl status life-systems.service

# Check logs
sudo journalctl -u life-systems.service -n 50

# Restart if needed
sudo systemctl restart life-systems.service
```

### Activities not syncing
```bash
# Check timer
sudo systemctl status life-systems-activities.timer

# Manually trigger sync
sudo systemctl start life-systems-activities.service

# Check logs
sudo journalctl -u life-systems-activities.service -n 50
```

### Login not working
- Username: `jurek` (lowercase, no capital)
- Password: `LifeSystems2026!` (exact case, include !)

### API returns 401
- Use HTTP Basic Auth
- Example: `curl -u jurek:LifeSystems2026! https://life.plocha.eu/api/health`

---

## 📞 Support

**For urgent issues:** Send Telegram message to Kevin
**For bugs:** Create issue in `kevin-bot-openclaw-ops/life-systems` repo
**For questions:** Slack DM to Kevin

---

**END OF DEPLOYMENT GUIDE**

*Last updated: March 11, 2026 at 07:38 UTC*
