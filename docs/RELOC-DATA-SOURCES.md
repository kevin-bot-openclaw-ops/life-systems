# RELOC-SPIKE-1: Location Data Source Report

**Created**: 2026-03-04
**Context**: EPIC-003 Location Optimizer
**Deadline**: Data sources identified by March 10 (ADR-006)
**Candidate Cities**: Madrid, Barcelona, Lisbon, Berlin, Amsterdam, Vienna, Warsaw, Fuerteventura

---

## Executive Summary

**Automation Score**: 3/5 dimensions can be fully automated
**Manual Research Required**: 2/5 dimensions (Lifestyle fit, Community quality)
**Data Freshness**: Monthly for automated sources, quarterly for manual

---

## Dimension 1: Dating Pool Size

### Best Source: **City Population Data (Age 25-40 filter)**

**Rationale**: Tinder Insights API is not publicly available. Dating app "users nearby" counts are unreliable and change rapidly. Best proxy: city population in target age range.

**Data Source**:
- **Primary**: City-Data.com population statistics (free, no API)
- **Secondary**: National statistics offices (manual lookup per country)
- **Format**: Manual web scraping or one-time research

**Measurement**:
- Total population aged 25-40 in metro area
- Apply dating pool multiplier: ~5% actively dating at any time
- Example: Barcelona metro ~1.6M, age 25-40 ~25% = 400k → ~20k active daters

**Automation**: ❌ Manual (one-time research per city)
**Frequency**: Annual (population changes slowly)
**Effort**: ~30 minutes per city (8 cities = 4 hours)

---

## Dimension 2: AI/ML Job Density

### Best Source: **Remotive API + Manual LinkedIn Search**

**Data Sources**:
1. **Remotive API** (https://remotive.com/api)
   - Format: JSON
   - Rate limits: Public (no auth), reasonable limits
   - Filters: Category "Software Dev", keyword "AI" or "ML"
   - Free: ✅
   - Returns: Job listings with location tags

2. **LinkedIn Job Search** (manual fallback)
   - Search: "AI engineer" OR "ML engineer" + location filter + "remote"
   - Manual count of results per city
   - Frequency: Monthly

**Measurement**:
- Count of remote-friendly AI/ML jobs mentioning city in last 30 days
- Weight by company quality (tier-1 companies 2x multiplier)

**Automation**: ✅ Partial (Remotive API automated, LinkedIn manual)
**Frequency**: Monthly
**Effort**: 15 minutes per city per month (automated scraping script)

---

## Dimension 3: Cost of Living

### Best Source: **Numbeo Cost of Living API**

**Data Source**:
- **URL**: https://www.numbeo.com/cost-of-living/
- **API**: https://www.numbeo.com/api/ (requires paid subscription $50/month)
- **Alternative**: Web scraping (terms of service unclear)
- **Free option**: Manual lookup via website

**Measurement**:
- Cost of Living Index (relative to NYC = 100)
- Convert to relative index with Fuerteventura as baseline (1.0)
- Key metrics: rent, groceries, restaurants, transportation

**Automation**: ⚠️ Possible with API ($50/month) OR manual scraping (legal risk)
**Frequency**: Quarterly (CoL changes slowly)
**Effort**: 
  - With API: Automated, 5 minutes setup
  - Manual: 15 minutes per city (8 cities = 2 hours quarterly)

**Recommendation**: Start manual, upgrade to API if used frequently

---

## Dimension 4: Lifestyle Fit

### Best Source: **Manual Research (Kevin + Web Search)**

**Data Sources**:
- Climate data: weather.com, climate-data.org
- Nightlife: Tripadvisor, Timeout city guides
- Sports/Activities: Local tourism board websites
- Expat community: Internations.org, expat forums
- Beach/surf access: Surfline, Magicseaweed

**Measurement**:
- Score 1-10 based on fit to Jurek's preferences:
  - Warm weather year-round (Fuerteventura baseline = 10)
  - Beach/surf access (important)
  - Bachata dance scene
  - Tech/startup culture
  - English-speaking expat community

**Automation**: ❌ Manual (requires qualitative judgment)
**Frequency**: One-time (with quarterly updates)
**Effort**: 1 hour per city (8 cities = 8 hours)

**Process**:
1. Kevin researches each dimension per city
2. Drafts initial scores with reasoning
3. Jurek validates and adjusts based on personal preferences

---

## Dimension 5: Community Quality

### Best Source: **Meetup.com + Internations.org**

**Data Sources**:
1. **Meetup.com**
   - Search: "tech" + city name
   - Count: Active tech/AI/startup meetups in last 3 months
   - Free: ✅
   - Format: Manual web scraping

2. **Internations.org**
   - Expat community size per city
   - Event frequency
   - Requires free account

3. **Facebook Groups**
   - Search: "[City] Expats", "[City] Tech Community"
   - Member count as proxy for community size

**Measurement**:
- Tech meetup count (last 3 months)
- Expat community size
- Score 1-10 based on:
  - Event frequency
  - Community engagement (comments, RSVPs)
  - Diversity of events

**Automation**: ⚠️ Partial (Meetup can be scraped, Facebook requires manual)
**Frequency**: Quarterly
**Effort**: 30 minutes per city (8 cities = 4 hours)

---

## Summary Table

| Dimension | Automation | Data Source | Frequency | Effort (per city) |
|-----------|-----------|-------------|-----------|-------------------|
| **1. Dating Pool** | ❌ Manual | City population stats | Annual | 30 min |
| **2. AI Job Density** | ✅ Automated | Remotive API + manual LinkedIn | Monthly | 15 min |
| **3. Cost of Living** | ⚠️ Possible | Numbeo (manual or $50/mo API) | Quarterly | 15 min |
| **4. Lifestyle Fit** | ❌ Manual | Web research | One-time | 1 hour |
| **5. Community Quality** | ⚠️ Partial | Meetup + Internations | Quarterly | 30 min |

**Total Initial Research Effort**: ~20 hours (8 cities × 2.5 hours avg)
**Ongoing Maintenance**: ~2 hours/quarter

---

## Recommendations

### Phase 1 (MVP, March 10 deadline):
1. **Manual research for all 5 dimensions** across 3 cities (Madrid, Barcelona, Lisbon)
2. Populate `cities` table with baseline data
3. Build comparison table UI
4. **Total effort**: ~7.5 hours

### Phase 2 (M1, April 1):
5. Expand to 8 cities (add Berlin, Amsterdam, Vienna, Warsaw, Fuerteventura)
6. **Total effort**: +12.5 hours

### Phase 3 (M2, ongoing):
7. Automate Remotive API scraping
8. Consider Numbeo API subscription if quarterly updates needed
9. Set up quarterly re-evaluation cron

---

## Data Freshness

| Dimension | How Often Does It Change? |
|-----------|---------------------------|
| Dating Pool | Slow (annual population shifts) |
| AI Job Density | Fast (monthly market changes) |
| Cost of Living | Moderate (quarterly inflation) |
| Lifestyle Fit | Very slow (city culture stable) |
| Community Quality | Moderate (quarterly event cycle) |

**Implication**: Initial research sufficient for May 1 deadline. Quarterly updates reasonable for long-term tracking.

---

## Next Steps

1. ✅ **RELOC-SPIKE-1 complete** — data sources identified
2. Start RELOC-MVP-1: Manual research for 3 cities (Madrid, Barcelona, Lisbon)
3. Populate `cities` table with data
4. Build comparison endpoint + UI

**Estimated timeline to working city comparison**: 10 hours across 3 tasks
