# Data Gaps: Missing Activity Types & Measurements
**Date:** 2026-03-09  
**Purpose:** Identify what data Kevin needs from Jurek to enable intelligence features  
**Current State:** 14 activity types tracked, but missing critical measurements for goal achievement

---

## Executive Summary

**GOOD NEWS:** Jurek is already logging 14 activity types consistently (gym, duo-lingo, red-light-therapy, nerve-stimulus, bumble, tinder, date, etc.)

**BAD NEWS:** Missing **7 critical measurements** that would enable:
- Pre-date activity optimization (GOAL1-04)
- Dating funnel analysis (GOAL1-03)  
- Sleep quality tracking (Readiness Score)
- Work productivity correlation

**PRIORITY:** Add **4 measurements to existing types** (5-10 min setup) before building new features.

---

## Current State: What's Being Logged

### ✅ **Well-Tracked Activities (No Changes Needed):**

1. **gym** - Count tracked ✓
2. **duo-lingo** - Count tracked ✓ (GOAL-3: Spanish learning)
3. **red-light-therapy** (rtl) - Count tracked ✓ (Health optimization)
4. **nerve-stimulus** - Count + intensity tracked ✓ (Stress management)
5. **bumble** - Swipes tracked ✓
6. **tinder** - Swipes tracked ✓
7. **cold-exposure** - Count tracked ✓ (T-optimization)
8. **sauna** - Count + duration tracked ✓
9. **swimming** - Count tracked ✓
10. **walking** - Count tracked ✓
11. **coffee** - Count tracked ✓ (Cortisol proxy)
12. **uttanasana** - Count tracked ✓ (Yoga)

### ⚠️ **Partially Tracked (Missing Key Measurements):**

13. **date** - Has touches, laughs, kiss, hold-hand ✓ BUT missing:
    - ❌ `chemistry_rating` (1-10 scale) - Needed for date outcome prediction
    - ❌ `second_date_interest` (yes/no) - Needed for correlation analysis
    - ❌ `conversation_depth` (1-10) - Needed for quality assessment
    - ❌ `physical_chemistry` (1-10) - Needed for attraction tracking
    - ❌ `location` tag (beach, cafe, restaurant, walk) - Needed for activity correlation

14. **sun-exposure** - Tracked BUT missing:
    - ❌ Duration not consistently logged (need ≥15 min for readiness score)

---

## GAP #1: Dating App Funnel Measurements (GOAL1-03 BLOCKER)

**Problem:** Can track swipes (49 total), but can't track conversion funnel:
- Swipes → Matches → Conversations → Dates

**Current Data:**
- ✅ Swipes: 49 (bumble: 29, tinder: 20)
- ❌ Matches: Not tracked
- ❌ Conversations started: Not tracked
- ❌ Conversations → Numbers exchanged: Not tracked
- ❌ Numbers → Dates scheduled: Not tracked

**Why This Matters:**
- **GOAL1-03** (Dating Funnel Tracker) requires this data to identify bottlenecks
- Example insight we CAN'T generate: "You're getting 0 matches, not 0 dates-from-matches. Problem = profile/photos, not conversation skills."

**Solution: Add 4 measurements to bumble/tinder activity types:**

**New activity type schema for `bumble` and `tinder`:**
```json
{
  "name": "bumble",  // or "tinder"
  "measurements": [
    {"name": "swipes", "kind": "COUNT"},            // ✅ Already tracked
    {"name": "matches", "kind": "COUNT"},           // 🆕 ADD THIS
    {"name": "conversations", "kind": "COUNT"},     // 🆕 ADD THIS
    {"name": "numbers_exchanged", "kind": "COUNT"}, // 🆕 ADD THIS
    {"name": "dates_scheduled", "kind": "COUNT"}    // 🆕 ADD THIS
  ]
}
```

**How to log (iPhone Shortcut or manual):**
- After each swipe session: "I swiped 20 profiles, got 0 matches"
- After each match: "Got 1 match from yesterday's swipes"
- After starting conversation: "Started 1 conversation"
- After getting number: "Exchanged numbers with 1 person"
- After scheduling date: "Scheduled 1 date"

**Time Investment:** 30 seconds per swipe session (sustainable)

**Impact:** Unblocks GOAL1-03, enables funnel bottleneck identification

---

## GAP #2: Date Outcome Measurements (GOAL1-04 BLOCKER)

**Problem:** Current `date` activity has physical escalation metrics (touches, laughs, kiss, hold-hand) but missing **outcome prediction** metrics.

**Current Data (date with Zsofie, Mar 8):**
- ✅ Touches: 3
- ✅ She-laughs: 10
- ✅ Kiss: 0
- ✅ Hold-hand: 1
- ❌ **Chemistry rating:** Not tracked
- ❌ **Second date interest:** Not tracked
- ❌ **Conversation depth:** Not tracked
- ❌ **Physical chemistry:** Not tracked

**Why This Matters:**
- **GOAL1-04** (Pre-Date Activity Optimizer) requires outcome data to correlate same-day activities with date success
- Example insight we CAN'T generate: "On days you do gym + sun before a date, chemistry_rating averages 8.2/10 vs 5.1/10 on sedentary days"
- **Correlation API** (US-131) needs ≥15 dates with outcome measurements before it can compute meaningful correlations

**Solution: Add 4 outcome measurements to `date` activity type:**

**Updated activity type schema for `date`:**
```json
{
  "name": "date",
  "measurements": [
    // ✅ Keep existing (physical escalation):
    {"name": "touches", "kind": "COUNT"},
    {"name": "she-laughs", "kind": "COUNT"},
    {"name": "kiss", "kind": "COUNT"},
    {"name": "hold-hand", "kind": "COUNT"},
    
    // 🆕 ADD THESE (outcome metrics):
    {"name": "chemistry_rating", "kind": "RATING", "maxValue": 10},
    {"name": "second_date_interest", "kind": "RATING", "maxValue": 10},
    {"name": "conversation_depth", "kind": "RATING", "maxValue": 10},
    {"name": "physical_chemistry", "kind": "RATING", "maxValue": 10}
  ],
  "tags": [
    "source:app",     // bumble, tinder, hinge
    "source:social",  // bachata, kizomba, beach, coworking
    "source:friend",  // introduced by friend
    "activity:coffee", "activity:drinks", "activity:dinner", "activity:walk", "activity:beach", "activity:dance",
    "location:corralejo", "location:madrid", "location:barcelona"
  ]
}
```

**How to log (iPhone Shortcut or manual):**
- **Immediately after date:** Rate 4 metrics on 1-10 scale
  - Chemistry rating: "Overall, how was the chemistry?" (1=awful, 10=amazing)
  - Second date interest: "Do you want to see her again?" (1=no, 10=absolutely)
  - Conversation depth: "How deep/engaging was the conversation?" (1=shallow, 10=profound)
  - Physical chemistry: "How strong was the physical attraction?" (1=none, 10=electric)
- **Add tags:** source (app/social/friend), activity (coffee/drinks/etc), location

**Time Investment:** 2 minutes per date (sustainable)

**Impact:** Unblocks GOAL1-04, enables pre-date activity optimization

**Data Accumulation Needed:** 15+ dates with these measurements before correlations are statistically meaningful

---

## GAP #3: Sleep Quality Measurements (Readiness Score)

**Problem:** Sleep is tracked occasionally but missing **duration** and **quality** metrics consistently.

**Current Data:**
- ✅ Sleep logged occasionally (1 occurrence found)
- ❌ Duration: Not consistently tracked
- ❌ Quality rating: Not tracked
- ❌ Wake-up feeling: Not tracked

**Why This Matters:**
- **Readiness Score** penalizes <7h sleep, rewards 7-8h sleep
- Currently showing "Not logged" for sleep component → missing +1.5 points
- Can't correlate sleep quality with next-day performance (gym, dates, work)

**Solution: Update `sleep` activity type schema:**

```json
{
  "name": "sleep",
  "temporalMark": {"type": "SPAN"},  // Start time + end time (auto-calculates duration)
  "measurements": [
    {"name": "quality_rating", "kind": "RATING", "maxValue": 10},  // 1=terrible, 10=perfect
    {"name": "wake_up_feeling", "kind": "RATING", "maxValue": 10}  // 1=groggy, 10=energized
  ],
  "tags": [
    "location:home", "location:hotel"
  ]
}
```

**How to log:**
- **Every morning (within 30 min of waking):**
  - Start time: When you went to bed last night (e.g., 23:00)
  - End time: When you woke up (e.g., 7:00)
  - Duration: Auto-calculated (8 hours)
  - Quality: Rate 1-10
  - Wake-up feeling: Rate 1-10

**Time Investment:** 30 seconds every morning (sustainable via iPhone Shortcut)

**Impact:** 
- Unlocks sleep component in Readiness Score (+1.5 points potential)
- Enables sleep-performance correlation analysis

---

## GAP #4: Work Productivity Measurements (GOAL-2 Support)

**Problem:** No tracking of work sessions, focus time, or productivity.

**Current Data:**
- ❌ Work sessions: Not tracked
- ❌ Deep work duration: Not tracked
- ❌ Productivity rating: Not tracked
- ❌ Distractions: Not tracked

**Why This Matters:**
- Can't correlate health optimization (readiness score) with work productivity
- Example insight we CAN'T generate: "On 5.0+ readiness days, your deep work sessions average 3.2h vs 1.8h on <3.5 days"
- Can't optimize work schedule around high-energy periods

**Solution: Create new `work-session` activity type:**

```json
{
  "name": "work-session",
  "temporalMark": {"type": "SPAN"},  // Start + end time
  "measurements": [
    {"name": "focus_rating", "kind": "RATING", "maxValue": 10},      // 1=distracted, 10=flow state
    {"name": "productivity", "kind": "RATING", "maxValue": 10},     // 1=unproductive, 10=highly productive
    {"name": "energy_level", "kind": "RATING", "maxValue": 10},     // 1=exhausted, 10=energized
    {"name": "tasks_completed", "kind": "COUNT"}                     // Number of tasks finished
  ],
  "tags": [
    "type:deep-work", "type:meetings", "type:admin",
    "project:fraud-detection", "project:rag-pipeline", "project:job-search"
  ]
}
```

**How to log:**
- After each work session (2-4h blocks): Rate focus, productivity, energy + count tasks
- **OR use Pomodoro app** that auto-logs sessions (e.g., Focus app integration)

**Time Investment:** 30 seconds per session (3-4x/day = 2 min/day)

**Impact:** Enables work-health correlation analysis, optimizes work schedule

---

## GAP #5: Bachata/Kizomba Social Events (GOAL-1 Primary Channel)

**Problem:** Social dance is Jurek's PRIMARY dating channel (per research), but no tracking exists.

**Current Data:**
- ❌ Bachata events: Not tracked
- ❌ Dance partners: Not tracked
- ❌ Numbers exchanged: Not tracked
- ❌ Social proof: Not tracked

**Why This Matters:**
- **Research finding:** Social dance = 2.5x better odds than apps, but can't measure ROI without data
- Can't track conversion: Bachata events → dance partners → numbers → dates
- Can't optimize: Which venues work best? Which nights? How many events to attend?

**Solution: Create `bachata` and `kizomba` activity types:**

```json
{
  "name": "bachata",  // or "kizomba"
  "temporalMark": {"type": "SPAN"},  // Arrival time + departure time
  "measurements": [
    {"name": "dance_partners", "kind": "COUNT"},          // How many people you danced with
    {"name": "new_people_met", "kind": "COUNT"},          // First-time dance partners
    {"name": "numbers_exchanged", "kind": "COUNT"},       // Phone numbers / Instagram
    {"name": "follow_up_planned", "kind": "COUNT"},       // "Let's practice sometime"
    {"name": "energy_rating", "kind": "RATING", "maxValue": 10},  // How fun was the event?
    {"name": "skill_improvement", "kind": "RATING", "maxValue": 10}  // Did you improve tonight?
  ],
  "tags": [
    "venue:tropical-house", "venue:the-host", "venue:salsipuedes",
    "location:madrid", "location:barcelona", "location:corralejo"
  ]
}
```

**How to log:**
- **After each social event:** Count dance partners, new people, numbers exchanged, rate energy/skill

**Time Investment:** 1-2 minutes per event (sustainable)

**Impact:** 
- Tracks social dance ROI (events → partners → numbers → dates)
- Optimizes venue selection, attendance frequency

---

## GAP #6: Location Tags (All Activities)

**Problem:** Many activities don't have location tags, making it impossible to compare Corralejo vs Madrid.

**Current Data:**
- ✅ Some activities have location in note field (manual text)
- ❌ No structured location tags

**Why This Matters:**
- **GOAL-3 analysis:** Can't compare "dating success in Corralejo vs Madrid" without location tags
- Can't segment data: "In Madrid, gym 3x/week = readiness 5.5/7.0 vs Corralejo 4.2/7.0"

**Solution: Add location tags to ALL activities:**

**Standard location tags:**
- `loc:corralejo`
- `loc:madrid`
- `loc:barcelona`
- `loc:warsaw`
- `loc:other`

**How to log:**
- **iPhone Shortcut:** Auto-detect location via GPS, suggest tag
- **OR manual:** Select location when logging activity

**Time Investment:** 0 seconds (auto) or 2 seconds (manual tap)

**Impact:** Enables location-based analysis, validates Madrid relocation hypothesis

---

## GAP #7: Sun Exposure Duration (Readiness Score Component)

**Problem:** Sun-exposure activity exists but duration isn't consistently logged.

**Current Data:**
- ✅ Sun-exposure count tracked occasionally
- ❌ Duration: Not consistently tracked (need ≥15 min for readiness points)

**Why This Matters:**
- **Readiness Score:** Sun exposure ≥15 min = +1.5 points (currently showing 0 points)
- Can't validate if Jurek is hitting threshold

**Solution: Update `sun-exposure` to require duration:**

```json
{
  "name": "sun-exposure",
  "temporalMark": {"type": "SPAN"},  // Start + end time
  "measurements": [
    {"name": "shirtless", "kind": "BOOLEAN"},  // true/false (matters for Vitamin D)
    {"name": "spf_used", "kind": "BOOLEAN"}     // Sunscreen? (affects optimization)
  ],
  "tags": [
    "time:morning", "time:midday", "time:afternoon",
    "location:beach", "location:park", "location:balcony"
  ]
}
```

**How to log:**
- Set timer for 20 min when starting sun exposure
- When timer ends, log activity with start/end time

**Time Investment:** 0 seconds (just press "Start" and "End")

**Impact:** Unlocks sun exposure points in Readiness Score (+1.5 potential)

---

## Summary: Priority Data Gaps (Ranked by Impact)

| # | Data Gap | Activity Type | Measurements to Add | Impact | Effort | Priority |
|---|----------|---------------|---------------------|--------|--------|----------|
| 1 | **Date outcomes** | `date` | chemistry_rating, second_date_interest, conversation_depth, physical_chemistry | 🔴 **CRITICAL** (blocks GOAL1-04) | Low | **P0** |
| 2 | **Dating app funnel** | `bumble`, `tinder` | matches, conversations, numbers_exchanged, dates_scheduled | 🔴 **CRITICAL** (blocks GOAL1-03) | Low | **P0** |
| 3 | **Sleep duration** | `sleep` | Change to SPAN, add quality_rating | 🟡 High (readiness score +1.5 points) | Low | **P1** |
| 4 | **Sun exposure duration** | `sun-exposure` | Change to SPAN, add shirtless/spf | 🟡 High (readiness score +1.5 points) | Low | **P1** |
| 5 | **Bachata/kizomba events** | NEW: `bachata`, `kizomba` | dance_partners, new_people_met, numbers_exchanged, follow_up_planned | 🟡 High (tracks primary dating channel) | Medium | **P1** |
| 6 | **Location tags** | ALL activities | Add loc: tags to existing activities | 🟢 Medium (enables location analysis) | Low | **P2** |
| 7 | **Work productivity** | NEW: `work-session` | focus_rating, productivity, energy_level, tasks_completed | 🟢 Medium (work-health correlation) | Medium | **P2** |

---

## Recommended Action Plan

**WEEK 1 (Mar 10-16): Add P0 Measurements**
1. ✅ Update `date` activity type schema → Add 4 outcome measurements
2. ✅ Update `bumble`/`tinder` schema → Add 4 funnel measurements
3. ✅ Create iPhone Shortcut for date logging (2 min post-date)

**WEEK 2 (Mar 17-23): Add P1 Measurements**
4. ✅ Update `sleep` schema → Change to SPAN, add quality_rating
5. ✅ Update `sun-exposure` schema → Change to SPAN, add shirtless/spf
6. ✅ Create `bachata` and `kizomba` activity types

**WEEK 3 (Mar 24-30): Add P2 Features**
7. ✅ Implement location tag auto-detection in iPhone Shortcut
8. ✅ Create `work-session` activity type (optional)

**WEEK 4 (Apr 1+): Start Logging Consistently**
9. ✅ Log ALL dates with 4 outcome measurements
10. ✅ Log sleep EVERY morning (30 seconds)
11. ✅ Log sun exposure when ≥15 min (track SPAN)
12. ✅ Log bachata events in Madrid (starting Apr 1)

---

## Impact: What Intelligence Features Unlock

**After 30 days of complete data:**
- ✅ **GOAL1-03:** Dating funnel tracker (identify bottlenecks: swipes → matches → dates)
- ✅ **Readiness Score:** Accurate sleep + sun components (+3.0 points potential)
- ✅ **Social dance ROI:** Track bachata → numbers → dates conversion

**After 60 days of complete data (15+ dates logged):**
- ✅ **GOAL1-04:** Pre-date activity optimizer ("gym + sun same day = 8.2/10 chemistry avg vs 5.1/10")
- ✅ **Location comparison:** Corralejo vs Madrid dating success rates
- ✅ **Work-health correlation:** Readiness score → productivity analysis

**After 90 days:**
- ✅ **Weekly AI synthesis:** "Your best weeks have this pattern: [X]"
- ✅ **Predictive recommendations:** "Date scheduled tonight. Do gym + sun before 18:00 for optimal chemistry."

---

**END OF DATA GAPS REPORT**

**Next:** Slack summary (top 3 findings)
