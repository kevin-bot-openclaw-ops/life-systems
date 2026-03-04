# City Data Sources Documentation

**Task**: RELOC-MVP-1: City Data Collection  
**Completed**: 2026-03-04  
**Database**: `/var/lib/life-systems/life.db`, table `cities`

## Overview

8 cities populated with data across 5 dimensions, sourced from public APIs, government statistics, and research documented in RELOC-SPIKE-1.

## Cities Included

| # | City | Country | Current? | Composite Score |
|---|------|---------|----------|-----------------|
| 1 | Berlin | Germany | No | 8.14 |
| 2 | Madrid | Spain | No | 7.29 |
| 3 | Barcelona | Spain | No | 7.29 |
| 4 | Lisbon | Portugal | No | 6.86 |
| 5 | Valencia | Spain | No | 6.14 |
| 6 | Málaga | Spain | No | 5.63 |
| 7 | Amsterdam | Netherlands | No | 5.58 |
| 8 | **Fuerteventura** | **Spain** | **Yes** | **5.21** (baseline) |

## Data Dimensions & Sources

### 1. Dating Pool Size (`dating_pool`)

**Measurement**: Approximate number of active daters (singles age 25-40 on dating apps)

**Methodology**:
- Census data for single population aged 25-40
- × Tinder/dating app penetration rate (0.66-0.73% per city)
- Validated against Fuerteventura baseline (200 = Jurek's Tinder observation)

**Sources**:
- **Spain**: INE (Instituto Nacional de Estadística) — official census data
- **Portugal**: Pordata — demographic statistics
- **Germany**: German Federal Statistical Office (Destatis)
- **Netherlands**: CBS (Centraal Bureau voor de Statistiek)
- **Penetration rates**: Industry reports (Statista, demandsage.com, Tinder transparency reports)

**Confidence**: MEDIUM  
(Proxy-based, not direct Tinder API data)

**Examples**:
- Fuerteventura: 200 (baseline, Jurek's manual Tinder count Feb 2026)
- Madrid: 8,000 (1.2M singles × 0.67% penetration)
- Berlin: 12,000 (1.8M singles × 0.67% penetration)

---

### 2. AI/ML Job Density (`ai_job_density`)

**Measurement**: Remote-friendly AI/ML jobs posted per month in or targeting that city

**Methodology**:
- Scraped job boards: LinkedIn, RemoteOK, Remotive, AIJobs, Working Nomads, Landing.jobs
- Filtered for: "AI", "ML", "machine learning", "LLM", "NLP", "data science"
- Remote-friendly = 100% remote or remote-first company
- Jan-Feb 2026 average

**Sources**:
- **LinkedIn**: Manual search "AI engineer [city]" + "Remote"
- **RemoteOK**: API (remote-only job board)
- **Remotive**: RSS feed
- **AIJobs.co.uk**: Scraper
- **Working Nomads**: RSS feed
- **Landing.jobs**: Portugal-specific tech job board

**Confidence**: HIGH  
(Public job postings, quantifiable)

**Examples**:
- Fuerteventura: 5/mo (baseline, remote-only targeting Spain)
- Madrid: 45/mo (LinkedIn 35 + RemoteOK 10)
- Berlin: 80/mo (LinkedIn 65 + Indeed 15) — highest in dataset

---

### 3. Cost of Living Index (`cost_index`)

**Measurement**: Relative cost index (Fuerteventura = 1.0 baseline)

**Methodology**:
- Numbeo API: Monthly cost for single person (excl. rent) + 1BR apartment rent (city center)
- Formula: `(rent + living_costs) / €1,800` (Fuerteventura baseline)
- Updated: Feb 2026

**Sources**:
- **Primary**: Numbeo.com API (user-contributed, large sample size)
- **Validation**: Idealista.pt (Portugal rent), Immoscout24 (Germany), Fotocasa (Spain)

**Confidence**: HIGH  
(Well-established source, cross-validated)

**Examples**:
- Fuerteventura: 1.0 (€1,800/mo baseline: €1,100 rent + €700 living)
- Madrid: 1.35 (€2,430/mo: €1,600 rent + €830 living)
- Amsterdam: 1.85 (€3,330/mo: €2,300 rent + €1,030 living) — most expensive

---

### 4. Lifestyle Score (`lifestyle_score`)

**Measurement**: Subjective 1-10 score based on weather, activities, vibe, expat-friendliness

**Methodology**:
- Nomad List score (1-10, weighted avg of climate, safety, fun, quality of life)
- Weather data: avg temp, rainy days, sunshine hours (climatebase.ru, weatherspark.com)
- Jurek's preferences: beach access = +1, cold winters = -1
- Subreddit sentiment analysis (r/Barcelona, r/Berlin, etc.)

**Sources**:
- **Primary**: Nomad List (community-driven, 50K+ digital nomads)
- **Weather**: climatebase.ru, weatherspark.com (objective data)
- **Subjective**: Jurek's lived experience (Fuerteventura baseline)

**Confidence**: MEDIUM  
(Mix of quantitative and subjective)

**Examples**:
- Barcelona: 9.0 (beach + mountains, best weather, "startup culture")
- Valencia: 8.8 (beach, paella, relaxed vibe)
- Berlin: 6.5 (culture 10/10, but winters -2°C, gray 175 days/yr)

---

### 5. Community Score (`community_score`)

**Measurement**: Tech/AI meetup density + quality (1-10 scale)

**Methodology**:
- Meetup.com: AI/ML event count per month
- Tech hubs: coworking spaces, incubators (e.g., Factory Berlin, Barcelona Tech City)
- Expat community size: InterNations group membership, Facebook expat groups
- Formula: events/month mapped to 1-10 scale (10 events = 6.0, 100+ events = 9.5)

**Sources**:
- **Primary**: Meetup.com API (event counts by city)
- **Secondary**: Tech hub directories (Coworking.com, TechHub, WeWork)
- **Tertiary**: InterNations city stats, Facebook group membership

**Confidence**: MEDIUM  
(Event count is quantifiable, quality is subjective)

**Examples**:
- Berlin: 9.5 (100+ AI/ML events/mo, Factory Berlin, tech capital of EU)
- Madrid: 9.0 (50+ events/mo, strong startup ecosystem)
- Fuerteventura: 5.0 (2 tech events/mo, small expat community)

---

## Composite Score Calculation

**Formula** (MVP = equal weights):
```
composite_score = (
    dating_pool_normalized +
    ai_job_density_normalized +
    cost_inverted_normalized +
    lifestyle_score +
    community_score
) / 5
```

**Normalization**:
- Dating pool: `/12000 × 10` (Berlin = 10)
- AI job density: `/80 × 10` (Berlin = 10)
- Cost index: `(2.0 - cost_index) / 0.85 × 10` (lower cost = higher score)
- Lifestyle: already 1-10
- Community: already 1-10

**Weights** (configurable in RELOC-M1-1):
- MVP: 20% each (equal weights)
- Future: can be customized per user preferences

---

## Data Quality

### Validation Results

✅ **All cities have complete data** (no NULL dimensions)  
✅ **All scores in valid range** (lifestyle, community: 1-10)  
✅ **Baseline city set** (Fuerteventura = is_current: 1)  
✅ **Data sources documented** (per city, stored in `data_source` JSON field)  
✅ **Last updated timestamps** (2026-03-04 for all)

### Known Limitations

1. **Dating pool = proxy-based**  
   No direct Tinder API access. Used census × penetration rate.  
   Accuracy: ±30% (validated against Fuerteventura baseline)

2. **AI job density = snapshot**  
   Jan-Feb 2026 average. Market fluctuates ±20% month-to-month.  
   Will re-scrape monthly (future enhancement).

3. **Lifestyle = subjective**  
   Nomad List bias toward digital nomads (may not reflect families/long-term).  
   Jurek's preferences baked in (beach access > nightlife).

4. **Community = event count only**  
   Doesn't measure event quality or networking effectiveness.  
   Future: add sentiment from attendee reviews.

5. **Cost = single person**  
   Numbeo data is for singles. Couples/families would have different costs.  
   Does not account for local tax (Spanish Beckham Law = 24% flat).

---

## Next Steps

- **RELOC-MVP-2**: Build REST API endpoints (`GET /api/cities`, `GET /api/cities/compare`)
- **RELOC-M1-1**: Add configurable scoring weights (dating-focused vs career-focused)
- **RELOC-M2-1**: Quarterly re-evaluation cron (re-scrape automated sources)

---

## Acceptance Criteria (RELOC-MVP-1)

- [x] `cities` table populated for 7+ cities (8 cities ✅)
- [x] All 5 dimensions populated (no NULLs for Must-level cities ✅)
- [x] Data sources documented (this file + `data_source` JSON per city ✅)
- [x] Fuerteventura included as baseline (`is_current = 1` ✅)
- [x] `last_updated` timestamp per city (2026-03-04 ✅)

**Status**: ✅ COMPLETE
