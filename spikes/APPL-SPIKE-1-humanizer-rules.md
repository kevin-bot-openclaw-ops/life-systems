# APPL-SPIKE-1: Humanizer Rules Research

**Status:** in_progress
**Started:** 2026-02-20 16:01 UTC
**Assignee:** kevin-bot
**Context:** APPL (Application Pipeline)
**Milestone:** SPIKE
**Effort:** 4-6h

## Objective

Catalog AI writing tells and build a tested ruleset for humanizing LLM-generated cover letters and applications. The draft generator (APPL-M1-1) must produce text indistinguishable from human writing.

## Research Questions

1. What are the most common AI tells in 2026? (not 2023 lists)
2. How does Jurek's authentic writing differ from LLM output?
3. Can we build a regex/pattern library that catches 80%+ of tells?
4. What's a reliable test harness for validation?

## AI Tell Catalog (Target: 30+ patterns)

### Overused Phrases (LLM artifacts)

| Tell | Pattern | Severity | Example |
|------|---------|----------|---------|
| "I'd be happy to" | `I'd be happy to \w+` | High | "I'd be happy to discuss" |
| "Delve" | `\bdelve\b` | Critical | "Let's delve into..." |
| "Game-changer" | `\bgame[- ]changer\b` | High | "This is a game-changer" |
| "Leverage" | `\bleverage\b` (as verb) | Medium | "Leverage my expertise" |
| "Excited to" | `excited to \w+` | Medium | "Excited to contribute" |
| "Utilize" | `\butilize\b` | Medium | "Utilize best practices" |
| "In conclusion" | `in conclusion` | Critical | "In conclusion, I..." |
| "Furthermore" | `\bfurthermore\b` | Medium | Starting sentences |
| "Moreover" | `\bmoreover\b` | Medium | Transition overuse |
| "Additionally" | `\badditionally\b` | Medium | Every other paragraph |
| "Robust" | `\brobust\b` (overused) | Low | "Robust solution" |
| "Holistic" | `\bholistic\b` | Medium | "Holistic approach" |
| "Cutting-edge" | `\bcutting[- ]edge\b` | Medium | "Cutting-edge technology" |
| "State-of-the-art" | `\bstate[- ]of[- ]the[- ]art\b` | Medium | "State-of-the-art ML" |
| "Synergy" | `\bsynergy\b` | Low | Corporate jargon |
| "Paradigm shift" | `\bparadigm shift\b` | High | Buzzword |
| "Circle back" | `\bcircle back\b` | Medium | Corporate speak |
| "Touch base" | `\btouch base\b` | Medium | Corporate speak |
| "Low-hanging fruit" | `\blow[- ]hanging fruit\b` | Medium | Cliché |
| "Deep dive" | `\bdeep dive\b` | Medium | Overused |

### Structural Patterns

| Tell | Detection Method | Severity | Fix |
|------|------------------|----------|-----|
| Every paragraph starts with transition | Scan first 3 words of each para | High | Vary openings, use direct statements |
| Bullet points with identical structure | Regex: `^- \w+ed .*$` (3+ consecutive) | Medium | Mix active/passive, vary length |
| Three-point lists everywhere | Count lists per 300 words | Medium | Humans vary: 2, 4, or prose |
| Perfect grammar (no fragments) | Sentence structure analysis | Low | Add occasional fragment for emphasis |
| No contractions | `\b(do not|cannot|will not)\b` | Medium | Humans use "don't", "can't", "won't" |
| Overlong sentences (40+ words) | Word count per sentence | Low | Split or use em dash (if not Jurek) |
| Perfectly balanced paragraphs | Para length variance < 20% | Low | Vary: short punchy + longer detail |

### Tone Tells

| Tell | Pattern | Severity | Fix |
|------|---------|----------|-----|
| Overly enthusiastic | `!` count > 1 per 500 words | High | Remove most exclamation marks |
| Superlative overuse | `\b(most|best|greatest|amazing)\b` density | Medium | Use sparingly, prefer specifics |
| Hedge words | `\b(perhaps|possibly|potentially)\b` density | Low | Decisive statements |
| Apologetic tone | `\b(sorry|apologies|unfortunately)\b` | High | Confident, no apologizing |
| Corporate voice | Passive voice ratio > 20% | Medium | Active voice default |

## Jurek's Writing Style (Positive Rules)

Based on USER.md, SOUL.md, and sample messages:

| Dimension | Jurek's Style | LLM Default | Detection |
|-----------|---------------|-------------|-----------|
| Sentence length | Short, dense (10-20 words avg) | Long, flowing (25+ words) | Avg sentence length |
| Vocabulary | Precise, technical, no fluff | Verbose, hedge words | Word choice analysis |
| Tone | Direct, confident, no apologizing | Polite, deferential | Sentiment patterns |
| Punctuation | Minimal commas, periods dominate | Commas everywhere | Comma density |
| Paragraph length | 1-3 sentences | 4-6 sentences | Paragraph structure |
| Em dashes | NEVER uses them | Loves them (—) | `—` count must be 0 |
| Contractions | Uses naturally | Avoids | Contraction ratio |
| Lists | When useful, not decorative | Bullet points everywhere | List frequency |
| Opening | Straight to the point | Context-setting paragraph | First sentence type |
| Closing | Forward-looking, no summaries | "In conclusion" or thanks | Last paragraph type |

### Sample Jurek Text Analysis

(TODO: Extract 3-5 actual messages from Slack/Telegram to build empirical profile)

**Metrics to capture:**
- Avg sentence length
- Vocabulary level (Flesch-Kincaid)
- Passive voice ratio
- Contraction frequency
- Em dash count (must be zero)
- Transition word density
- Paragraph length distribution

## Test Suite Design

### Test Set A: AI-Generated Texts (10 samples)

1. GPT-4 cover letter (vanilla prompt)
2. Claude cover letter (vanilla prompt)
3. GPT-4 with "write casually"
4. Claude with "be direct"
5. Gemini cover letter
6. GPT-4 LinkedIn message
7. Claude email intro
8. ChatGPT application letter
9. GPT-4 with anti-AI prompt
10. Claude with Jurek's style guide

**Target:** Humanizer flags >= 8/10 as AI (80% precision)

### Test Set B: Human-Written Texts (10 samples)

1. Actual Jurek cover letter (if available)
2. Jurek Slack message (casual)
3. Jurek email (professional)
4. Random Hacker News comment
5. GitHub PR description (human-written)
6. Reddit r/MachineLearning comment
7. LinkedIn post (verified human)
8. Blog post excerpt (known human)
9. Email from colleague
10. Technical documentation (human-written)

**Target:** Humanizer flags <= 2/10 as AI (80% recall on human detection)

## Regex Pattern Library

```python
AI_TELLS = {
    'delve': r'\bdelve\b',
    'game_changer': r'\bgame[- ]changer\b',
    'id_be_happy': r"I'd be happy to",
    'excited_to': r'excited to \w+',
    'utilize': r'\butilize\b',
    'leverage': r'\bleverage\b',
    'in_conclusion': r'\bin conclusion\b',
    'moreover': r'\b(moreover|furthermore|additionally)\b',
    'robust': r'\brobust\b',
    'holistic': r'\bholistic\b',
    'cutting_edge': r'\bcutting[- ]edge\b',
    'state_of_art': r'\bstate[- ]of[- ]the[- ]art\b',
    'paradigm': r'\bparadigm shift\b',
    'circle_back': r'\b(circle back|touch base)\b',
    'deep_dive': r'\bdeep dive\b',
    'low_hanging': r'\blow[- ]hanging fruit\b',
}

JUREK_VIOLATIONS = {
    'em_dash': r'—',  # Count must be 0
    'no_contractions': r"\b(do not|cannot|will not|is not|are not)\b",  # Should use don't, can't, etc.
    'apologetic': r"\b(sorry|apologies|unfortunately)\b",
    'hedging': r"\b(perhaps|possibly|potentially|might|maybe)\b",
}
```

## Acceptance Criteria

- [ ] Minimum 30 AI tells catalogued with regex patterns
- [ ] Jurek's positive style guide captured (8+ dimensions)
- [ ] Test suite: 10 AI texts + 10 human texts
- [ ] Humanizer achieves >= 80% accuracy both ways (16/20 correct)
- [ ] No em dashes in positive examples (Jurek's hard rule)
- [ ] Deliverables: Python module with patterns, test harness, validation report

## Implementation Plan

1. **Research** (2h): Scrape 2026 AI detection discussions (Reddit, HN, Twitter)
2. **Pattern Building** (1h): Expand catalog to 30+ tells with regex
3. **Style Profiling** (1.5h): Analyze Jurek's actual writing (extract from Slack/Telegram logs)
4. **Test Set Creation** (1h): Generate 10 AI texts, collect 10 human texts
5. **Validation** (0.5h): Run test suite, tune thresholds

**Total: 6h**

## Next Steps

1. Mine /r/ChatGPT, /r/AIDetection for 2026 tells
2. Extract Jurek's Slack/Telegram message samples
3. Build Python module `humanizer.py` with pattern matching
4. Create test harness `test_humanizer.py`
5. Document findings in spike report

