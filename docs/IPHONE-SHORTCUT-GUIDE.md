# iPhone Shortcuts Integration Guide

**Life Systems v5 - Dating Module**  
**Created:** 2026-03-04  
**Context:** EPIC-001 Dating Module - DATE-MVP-2

---

## Quick Start

Life Systems dating endpoints can be called directly from iPhone Shortcuts using the **"Get Contents of URL"** action.

**Base URL:** `https://life.plocha.eu`  
**Authentication:** HTTP Basic Auth (username: `jurek`, password: `LifeSystems2026!`)

---

## 1. Log a Date (POST /api/dates)

### Curl Example

```bash
curl -X POST \
  -u jurek:LifeSystems2026! \
  -H "Content-Type: application/json" \
  -d '{
    "who": "Anna",
    "source": "event",
    "quality": 8,
    "went_well": "Great conversation about AI",
    "improve": "Be more direct about intentions",
    "date_of": "2026-03-04"
  }' \
  https://life.plocha.eu/api/dates
```

### iPhone Shortcut Configuration

**Action:** Get Contents of URL

- **URL:** `https://life.plocha.eu/api/dates`
- **Method:** POST
- **Headers:**
  - `Content-Type`: `application/json`
  - `Authorization`: `Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==` (base64 of "jurek:LifeSystems2026!")
- **Request Body:** JSON

**Example Shortcut JSON Body:**

```json
{
  "who": "<Ask for Input: Who was the date with?>",
  "source": "<Choose from Menu: app, event, social>",
  "quality": "<Ask for Number: Rate quality 1-10>",
  "went_well": "<Ask for Text: What went well?>",
  "improve": "<Ask for Text: What to improve?>",
  "date_of": "<Current Date: YYYY-MM-DD format>"
}
```

**Expected Response (201 Created):**

```json
{
  "id": 1,
  "who": "Anna",
  "source": "event",
  "quality": 8,
  "went_well": "Great conversation about AI",
  "improve": "Be more direct about intentions",
  "date_of": "2026-03-04",
  "created_at": "2026-03-04T16:30:00",
  "archived": 0
}
```

---

## 2. List Recent Dates (GET /api/dates)

### Curl Example

```bash
curl -u jurek:LifeSystems2026! \
  "https://life.plocha.eu/api/dates?limit=10"
```

### iPhone Shortcut Configuration

**Action:** Get Contents of URL

- **URL:** `https://life.plocha.eu/api/dates?limit=10`
- **Method:** GET
- **Headers:**
  - `Authorization`: `Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==`

**Expected Response (200 OK):**

```json
[
  {
    "id": 3,
    "who": "Sophie",
    "source": "social",
    "quality": 9,
    "went_well": "Amazing chemistry",
    "improve": "Nothing",
    "date_of": "2026-03-03",
    "created_at": "2026-03-04T12:42:24",
    "archived": 0
  },
  {
    "id": 2,
    "who": "Maria",
    "source": "app",
    "quality": 7,
    ...
  }
]
```

---

## 3. Get Dating Stats (GET /api/dates/stats)

### Curl Example

```bash
curl -u jurek:LifeSystems2026! \
  https://life.plocha.eu/api/dates/stats
```

### iPhone Shortcut Configuration

**Action:** Get Contents of URL

- **URL:** `https://life.plocha.eu/api/dates/stats`
- **Method:** GET
- **Headers:**
  - `Authorization`: `Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==`

**Expected Response (200 OK):**

```json
{
  "by_source": {
    "app": {
      "count": 5,
      "avg_quality": 7.2,
      "max_quality": 9,
      "min_quality": 5
    },
    "event": {
      "count": 3,
      "avg_quality": 8.3,
      "max_quality": 9,
      "min_quality": 7
    },
    "social": {
      "count": 2,
      "avg_quality": 8.5,
      "max_quality": 9,
      "min_quality": 8
    }
  },
  "total_dates": 10
}
```

**Insight:** Shows which source produces best quality dates.

---

## 4. Get Quality Trends (GET /api/dates/trends)

### Curl Example

```bash
curl -u jurek:LifeSystems2026! \
  https://life.plocha.eu/api/dates/trends
```

### iPhone Shortcut Configuration

**Action:** Get Contents of URL

- **URL:** `https://life.plocha.eu/api/dates/trends`
- **Method:** GET
- **Headers:**
  - `Authorization`: `Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==`

**Expected Response (200 OK):**

```json
{
  "weeks": [
    {
      "week": "2026-08",
      "avg_quality": 7.5,
      "count": 3
    },
    {
      "week": "2026-09",
      "avg_quality": 8.2,
      "count": 5
    }
  ],
  "trend": "up",
  "four_week_avg": 7.9
}
```

**Insight:** Quality trending up = you're improving!

---

## Error Handling

### 401 Unauthorized

**Response:**
```json
{
  "detail": "Incorrect username or password"
}
```

**Fix:** Check your Authorization header. Make sure it's `Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==`

### 422 Unprocessable Entity (Validation Error)

**Example Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "quality"],
      "msg": "ensure this value is less than or equal to 10",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**Fix:** Check your input values:
- `quality` must be 1-10
- `source` must be one of: "app", "event", "social"
- `who` is required (can't be empty)
- `date_of` must be YYYY-MM-DD format

### 500 Internal Server Error

**Response:**
```json
{
  "detail": "Internal server error"
}
```

**Fix:** Contact admin (this shouldn't happen). Check server logs.

---

## Complete Shortcut Example

**Shortcut Name:** "Log Date"

1. **Ask for Input:** "Who was the date with?"
   - Variable: `who`

2. **Choose from Menu:** "How did you meet?"
   - Options: App, Event, Social
   - Variable: `source` (lowercase)

3. **Ask for Number:** "Rate quality 1-10"
   - Variable: `quality`

4. **Ask for Text:** "What went well?"
   - Variable: `went_well`

5. **Ask for Text:** "What to improve?"
   - Variable: `improve`

6. **Current Date**
   - Format: Custom "YYYY-MM-DD"
   - Variable: `date_of`

7. **Dictionary:**
   ```json
   {
     "who": "<who>",
     "source": "<source>",
     "quality": <quality>,
     "went_well": "<went_well>",
     "improve": "<improve>",
     "date_of": "<date_of>"
   }
   ```

8. **Get Contents of URL:**
   - URL: `https://life.plocha.eu/api/dates`
   - Method: POST
   - Headers: 
     - `Content-Type`: `application/json`
     - `Authorization`: `Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==`
   - Request Body: JSON (from Dictionary)

9. **Show Notification:**
   - Title: "Date logged!"
   - Body: "Thanks for tracking. Check stats at life.plocha.eu"

---

## Tips for Fast Logging

**Target:** Log a date in under 2 minutes (NEED-4 acceptance criterion)

1. **Pre-fill common values:**
   - If you always meet at bachata events, default `source` to "event"
   - Skip optional fields (`went_well`, `improve`) if in a hurry

2. **Use Siri:**
   - "Hey Siri, log a date"
   - Follow voice prompts

3. **Minimal flow:**
   - Who: 1 tap (name from recent)
   - Source: 1 tap (default to most common)
   - Quality: 1 tap (slider 1-10)
   - Save: 1 tap
   - **Total: 4 taps, ~30 seconds**

4. **Log same day:**
   - Best compliance: log within 24 hours (DATE-1 Must metric)
   - Set reminder: "Log date after getting home"

---

## Base64 Auth Header Generation

If you need to regenerate the Authorization header:

```bash
echo -n "jurek:LifeSystems2026!" | base64
# Output: anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==
```

Use in header: `Authorization: Basic anVyZWs6TGlmZVN5c3RlbXMyMDI2IQ==`

---

## Next Steps

Once you've logged 5+ dates:
- Check `/api/dates/stats` to see which source is best
- Check `/api/dates/trends` to see if quality is improving
- Dashboard at `https://life.plocha.eu` will show dating insights

**Questions?** Check the main README or API docs at `/docs`
