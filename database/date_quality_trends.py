"""
DATE-M1-1: Rules-Based Quality Trend Analysis

Analyzes dating quality trends from Activities API data.
Follows ADR-005 (motivation-first: one-liner + data table + actions).

Features:
- Quality trending up/down/flat over 4 weeks
- Best source by quality-weighted conversion
- Best day/time for dates
- Empty state handling for <5 dates
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from statistics import mean, stdev
import requests


# Constants
SHARE_TOKEN = "a50ea3e50186487ca3ad094bc3e177ac"
BASE_URL = "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com"
MIN_DATES_FOR_ANALYSIS = 5


@dataclass
class DateOccurrence:
    """Parsed date occurrence from Activities API."""
    id: str
    timestamp: datetime
    source: str  # tinder, bumble, real, dance, unknown
    quality_score: float  # Computed 1-10 score
    touches: int
    laughs: int
    kisses: int
    hand_holds: int
    duration_minutes: int
    note: str
    day_of_week: str
    hour_of_day: int


@dataclass
class QualityTrend:
    """Quality trend analysis result."""
    direction: str  # "up", "down", "flat", "insufficient_data"
    recent_avg: float  # Last 2 weeks average
    previous_avg: float  # 2-4 weeks ago average
    change_pct: float  # Percentage change
    confidence: str  # "high", "medium", "low"
    total_dates: int


@dataclass
class SourceAnalysis:
    """Source performance analysis."""
    source: str
    date_count: int
    avg_quality: float
    conversion_score: float  # Quality-weighted score
    best_outcome: str  # Brief description of best outcome


@dataclass
class TimingAnalysis:
    """Best timing for dates."""
    best_day: str
    best_day_avg_quality: float
    best_hour_range: str
    best_hour_avg_quality: float
    sample_size: int


class DateQualityTrendsAnalyzer:
    """
    Analyzes dating quality trends from Activities API.
    
    Usage:
        analyzer = DateQualityTrendsAnalyzer()
        result = analyzer.analyze()
        print(result['one_liner'])
        print(result['data_table'])
    """
    
    def __init__(self, share_token: str = SHARE_TOKEN, base_url: str = BASE_URL):
        self.share_token = share_token
        self.base_url = base_url
        self._dates_cache: Optional[List[DateOccurrence]] = None
    
    def fetch_dates(self, days: int = 60) -> List[Dict]:
        """
        Fetch date occurrences from Activities API.
        
        Args:
            days: Number of days to look back (default 60 for 4+ weeks of data)
            
        Returns:
            List of raw date occurrence dicts from API
        """
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/shared/{self.share_token}/occurrences/dates/{from_date}/{to_date}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Filter for date activity type only
        all_occurrences = response.json()
        return [occ for occ in all_occurrences if occ.get("activityType") == "date"]
    
    def parse_date_occurrence(self, occ: Dict) -> DateOccurrence:
        """
        Parse a date occurrence into structured data.
        
        Args:
            occ: Raw occurrence dict from API
            
        Returns:
            DateOccurrence dataclass
        """
        temporal_mark = occ.get("temporalMark", {})
        
        # Parse timestamp
        if temporal_mark.get("type") == "MOMENT":
            timestamp_str = temporal_mark.get("at", "")
        else:
            timestamp_str = temporal_mark.get("start", "")
        
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now()
        
        # Parse measurements
        measurements = occ.get("measurements", [])
        touches = 0
        laughs = 0
        kisses = 0
        hand_holds = 0
        duration_minutes = 90  # Default
        source = "unknown"
        
        for m in measurements:
            kind = m.get("kind", {})
            unit = kind.get("unit", "")
            kind_name = kind.get("name", "")
            value = int(m.get("value", 0))
            
            if "touch" in unit.lower():
                touches = value
            elif "laugh" in unit.lower():
                laughs = value
            elif "kiss" in unit.lower():
                kisses = value
            elif "hold-hand" in unit.lower() or "hand" in unit.lower():
                hand_holds = value
            elif "minute" in unit.lower():
                duration_minutes = value
            elif kind.get("type") == "SELECT":
                # Source is a SELECT measurement
                options = kind.get("options", [])
                if options and value < len(options):
                    source = options[value]
        
        # Fallback: check tags for source
        tags = occ.get("tags", [])
        if source == "unknown":
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower in ["tinder", "bumble", "real", "dance", "social", "event", "app"]:
                    source = tag_lower
                    break
        
        # Compute quality score (1-10)
        quality_score = self._compute_quality_score(
            touches=touches,
            laughs=laughs,
            kisses=kisses,
            hand_holds=hand_holds,
            duration_minutes=duration_minutes,
            note=occ.get("note", "")
        )
        
        return DateOccurrence(
            id=occ.get("id", ""),
            timestamp=timestamp,
            source=source if source != "unknown" else self._infer_source_from_note(occ.get("note", "")),
            quality_score=quality_score,
            touches=touches,
            laughs=laughs,
            kisses=kisses,
            hand_holds=hand_holds,
            duration_minutes=duration_minutes,
            note=occ.get("note", ""),
            day_of_week=timestamp.strftime("%A"),
            hour_of_day=timestamp.hour
        )
    
    def _compute_quality_score(
        self,
        touches: int,
        laughs: int,
        kisses: int,
        hand_holds: int,
        duration_minutes: int,
        note: str
    ) -> float:
        """
        Compute a quality score (1-10) for a date.
        
        Scoring formula:
        - Base: 5.0
        - Touches: +0.5 per touch (max +2)
        - Laughs: +0.3 per laugh (max +1.5)
        - Kisses: +1.5 per kiss (max +3)
        - Hand holds: +0.3 per hold (max +1)
        - Duration: +0.5 for >90min, +1 for >120min
        - Positive note keywords: +0.5
        - Negative note keywords: -0.5
        """
        score = 5.0
        
        # Physical escalation
        score += min(touches * 0.5, 2.0)
        score += min(laughs * 0.3, 1.5)
        score += min(kisses * 1.5, 3.0)
        score += min(hand_holds * 0.3, 1.0)
        
        # Duration bonus
        if duration_minutes > 120:
            score += 1.0
        elif duration_minutes > 90:
            score += 0.5
        
        # Note sentiment
        note_lower = note.lower() if note else ""
        positive_keywords = ["good", "great", "fun", "connection", "smile", "laugh", "chemistry", "enjoy"]
        negative_keywords = ["nervous", "stressed", "closed", "rejected", "didn't", "no chemistry", "not feel"]
        
        for keyword in positive_keywords:
            if keyword in note_lower:
                score += 0.5
                break
        
        for keyword in negative_keywords:
            if keyword in note_lower:
                score -= 0.5
                break
        
        # Clamp to 1-10
        return max(1.0, min(10.0, round(score, 1)))
    
    def _infer_source_from_note(self, note: str) -> str:
        """Infer date source from note text."""
        if not note:
            return "unknown"
        
        note_lower = note.lower()
        
        if "tinder" in note_lower:
            return "tinder"
        elif "bumble" in note_lower:
            return "bumble"
        elif "dance" in note_lower or "bachata" in note_lower or "salsa" in note_lower:
            return "dance"
        elif "real" in note_lower or "street" in note_lower or "approached" in note_lower:
            return "real"
        elif "matched" in note_lower or "app" in note_lower:
            return "app"
        
        return "unknown"
    
    def get_dates(self, days: int = 60) -> List[DateOccurrence]:
        """
        Get parsed date occurrences.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of DateOccurrence objects, sorted by timestamp (newest first)
        """
        if self._dates_cache is not None:
            return self._dates_cache
        
        raw_dates = self.fetch_dates(days=days)
        parsed = [self.parse_date_occurrence(occ) for occ in raw_dates]
        # Sort by timestamp, newest first
        parsed.sort(key=lambda d: d.timestamp, reverse=True)
        self._dates_cache = parsed
        return parsed
    
    def analyze_quality_trend(self, dates: List[DateOccurrence]) -> QualityTrend:
        """
        Analyze quality trend over the past 4 weeks.
        
        Compares last 2 weeks vs previous 2 weeks.
        """
        if len(dates) < MIN_DATES_FOR_ANALYSIS:
            return QualityTrend(
                direction="insufficient_data",
                recent_avg=0,
                previous_avg=0,
                change_pct=0,
                confidence="low",
                total_dates=len(dates)
            )
        
        now = datetime.now(dates[0].timestamp.tzinfo) if dates and dates[0].timestamp.tzinfo else datetime.now()
        two_weeks_ago = now - timedelta(days=14)
        four_weeks_ago = now - timedelta(days=28)
        
        recent_dates = [d for d in dates if d.timestamp >= two_weeks_ago]
        previous_dates = [d for d in dates if four_weeks_ago <= d.timestamp < two_weeks_ago]
        
        if not recent_dates:
            recent_avg = 0
        else:
            recent_avg = mean([d.quality_score for d in recent_dates])
        
        if not previous_dates:
            previous_avg = recent_avg  # Can't compare without baseline
            change_pct = 0
            direction = "flat"
            confidence = "low"
        else:
            previous_avg = mean([d.quality_score for d in previous_dates])
            
            if previous_avg > 0:
                change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
            else:
                change_pct = 0
            
            # Determine direction
            if change_pct > 10:
                direction = "up"
            elif change_pct < -10:
                direction = "down"
            else:
                direction = "flat"
            
            # Confidence based on sample size
            total_samples = len(recent_dates) + len(previous_dates)
            if total_samples >= 10:
                confidence = "high"
            elif total_samples >= 5:
                confidence = "medium"
            else:
                confidence = "low"
        
        return QualityTrend(
            direction=direction,
            recent_avg=round(recent_avg, 1),
            previous_avg=round(previous_avg, 1),
            change_pct=round(change_pct, 1),
            confidence=confidence,
            total_dates=len(dates)
        )
    
    def analyze_sources(self, dates: List[DateOccurrence]) -> List[SourceAnalysis]:
        """
        Analyze performance by date source.
        
        Returns sources ranked by quality-weighted conversion score.
        """
        if not dates:
            return []
        
        source_data: Dict[str, List[DateOccurrence]] = {}
        for d in dates:
            source = d.source if d.source != "unknown" else "other"
            if source not in source_data:
                source_data[source] = []
            source_data[source].append(d)
        
        results = []
        for source, source_dates in source_data.items():
            avg_quality = mean([d.quality_score for d in source_dates])
            # Conversion score = avg_quality * sqrt(count) to balance quality and volume
            conversion_score = avg_quality * (len(source_dates) ** 0.5)
            
            # Find best outcome
            best_date = max(source_dates, key=lambda d: d.quality_score)
            best_outcome = f"{best_date.quality_score}/10" + (f", {best_date.kisses} kiss(es)" if best_date.kisses > 0 else "")
            
            results.append(SourceAnalysis(
                source=source,
                date_count=len(source_dates),
                avg_quality=round(avg_quality, 1),
                conversion_score=round(conversion_score, 1),
                best_outcome=best_outcome
            ))
        
        # Sort by conversion score
        results.sort(key=lambda x: x.conversion_score, reverse=True)
        return results
    
    def analyze_timing(self, dates: List[DateOccurrence]) -> Optional[TimingAnalysis]:
        """
        Analyze best day and time for dates.
        """
        if len(dates) < MIN_DATES_FOR_ANALYSIS:
            return None
        
        # Group by day of week
        day_data: Dict[str, List[float]] = {}
        for d in dates:
            if d.day_of_week not in day_data:
                day_data[d.day_of_week] = []
            day_data[d.day_of_week].append(d.quality_score)
        
        # Find best day
        best_day = max(day_data.keys(), key=lambda day: mean(day_data[day]))
        best_day_avg = mean(day_data[best_day])
        
        # Group by hour range (evening vs afternoon vs other)
        hour_ranges = {
            "evening (18-22)": [],
            "afternoon (14-18)": [],
            "night (22+)": [],
            "other": []
        }
        
        for d in dates:
            if 18 <= d.hour_of_day < 22:
                hour_ranges["evening (18-22)"].append(d.quality_score)
            elif 14 <= d.hour_of_day < 18:
                hour_ranges["afternoon (14-18)"].append(d.quality_score)
            elif d.hour_of_day >= 22:
                hour_ranges["night (22+)"].append(d.quality_score)
            else:
                hour_ranges["other"].append(d.quality_score)
        
        # Find best hour range with data
        non_empty_ranges = {k: v for k, v in hour_ranges.items() if v}
        if non_empty_ranges:
            best_hour = max(non_empty_ranges.keys(), key=lambda h: mean(non_empty_ranges[h]))
            best_hour_avg = mean(non_empty_ranges[best_hour])
        else:
            best_hour = "N/A"
            best_hour_avg = 0
        
        return TimingAnalysis(
            best_day=best_day,
            best_day_avg_quality=round(best_day_avg, 1),
            best_hour_range=best_hour,
            best_hour_avg_quality=round(best_hour_avg, 1),
            sample_size=len(dates)
        )
    
    def generate_one_liner(
        self,
        trend: QualityTrend,
        sources: List[SourceAnalysis],
        timing: Optional[TimingAnalysis]
    ) -> str:
        """
        Generate motivation-first one-liner (ADR-005 compliant).
        """
        if trend.direction == "insufficient_data":
            remaining = MIN_DATES_FOR_ANALYSIS - trend.total_dates
            return f"After {remaining} more date(s), I'll show you quality patterns. Current: {trend.total_dates} logged."
        
        # Build one-liner
        parts = []
        
        # Quality trend
        if trend.direction == "up":
            parts.append(f"Your dating quality is IMPROVING (+{trend.change_pct:.0f}% in 2 weeks)! 📈")
        elif trend.direction == "down":
            parts.append(f"Quality dipped {abs(trend.change_pct):.0f}% recently. Let's analyze why. 📉")
        else:
            parts.append(f"Quality stable at {trend.recent_avg}/10 avg. Consistent is good! 📊")
        
        # Best source
        if sources:
            best = sources[0]
            parts.append(f"{best.source.title()} is your best channel ({best.avg_quality}/10 avg, {best.date_count} dates).")
        
        return " ".join(parts)
    
    def generate_data_table(
        self,
        trend: QualityTrend,
        sources: List[SourceAnalysis],
        timing: Optional[TimingAnalysis],
        dates: List[DateOccurrence]
    ) -> Dict[str, Any]:
        """
        Generate data table structure (ADR-005 compliant).
        """
        if trend.direction == "insufficient_data":
            return {
                "type": "empty_state",
                "message": f"Log {MIN_DATES_FOR_ANALYSIS - trend.total_dates} more dates to unlock trend analysis.",
                "current_dates": trend.total_dates,
                "required_dates": MIN_DATES_FOR_ANALYSIS
            }
        
        return {
            "type": "quality_trends",
            "trend_summary": {
                "direction": trend.direction,
                "recent_avg": trend.recent_avg,
                "previous_avg": trend.previous_avg,
                "change_pct": trend.change_pct,
                "confidence": trend.confidence,
                "total_dates": trend.total_dates
            },
            "sources": [
                {
                    "source": s.source,
                    "dates": s.date_count,
                    "avg_quality": s.avg_quality,
                    "score": s.conversion_score,
                    "best": s.best_outcome
                }
                for s in sources
            ],
            "timing": {
                "best_day": timing.best_day if timing else "N/A",
                "best_day_quality": timing.best_day_avg_quality if timing else 0,
                "best_time": timing.best_hour_range if timing else "N/A",
                "best_time_quality": timing.best_hour_avg_quality if timing else 0,
            } if timing else None,
            "recent_dates": [
                {
                    "date": d.timestamp.strftime("%Y-%m-%d"),
                    "source": d.source,
                    "quality": d.quality_score,
                    "highlights": self._date_highlights(d)
                }
                for d in dates[:5]  # Last 5 dates
            ]
        }
    
    def _date_highlights(self, d: DateOccurrence) -> str:
        """Generate brief highlights for a date."""
        parts = []
        if d.kisses > 0:
            parts.append(f"{d.kisses}💋")
        if d.hand_holds > 0:
            parts.append(f"{d.hand_holds}🤝")
        if d.laughs >= 5:
            parts.append(f"{d.laughs}😂")
        if d.duration_minutes > 120:
            parts.append(f"{d.duration_minutes}min")
        
        return " ".join(parts) if parts else "—"
    
    def generate_actions(
        self,
        trend: QualityTrend,
        sources: List[SourceAnalysis],
        timing: Optional[TimingAnalysis]
    ) -> List[Dict[str, str]]:
        """
        Generate actionable recommendations (ADR-005 compliant).
        """
        actions = []
        
        if trend.direction == "insufficient_data":
            actions.append({
                "action": "log_date",
                "label": "Log a Date",
                "description": "Open Activities app and log your next date."
            })
            return actions
        
        # Source optimization
        if len(sources) >= 2:
            best = sources[0]
            worst = sources[-1]
            if best.avg_quality - worst.avg_quality >= 1.5:
                actions.append({
                    "action": "optimize_source",
                    "label": f"Focus on {best.source.title()}",
                    "description": f"Your {best.source} dates average {best.avg_quality}/10 vs {worst.source} at {worst.avg_quality}/10. Double down on what works."
                })
        
        # Timing optimization
        if timing and timing.sample_size >= 5:
            actions.append({
                "action": "optimize_timing",
                "label": f"Schedule {timing.best_day} {timing.best_hour_range}",
                "description": f"Your best dates happen on {timing.best_day} {timing.best_hour_range} ({timing.best_day_avg_quality}/10 avg)."
            })
        
        # Trend-based action
        if trend.direction == "down":
            actions.append({
                "action": "review_dates",
                "label": "Review Recent Notes",
                "description": "Check your date notes for patterns. What changed in the last 2 weeks?"
            })
        elif trend.direction == "up":
            actions.append({
                "action": "maintain_momentum",
                "label": "Keep It Up!",
                "description": "Quality is trending up. Stay consistent with your current approach."
            })
        
        return actions
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run full analysis and return ADR-005 compliant output.
        
        Returns:
            Dict with: one_liner, data_table, actions, goal_ref
        """
        # Fetch and parse dates
        dates = self.get_dates()
        
        # Run analyses
        trend = self.analyze_quality_trend(dates)
        sources = self.analyze_sources(dates)
        timing = self.analyze_timing(dates)
        
        # Generate outputs
        one_liner = self.generate_one_liner(trend, sources, timing)
        data_table = self.generate_data_table(trend, sources, timing, dates)
        actions = self.generate_actions(trend, sources, timing)
        
        return {
            "section": "date_quality_trends",
            "goal_ref": "GOAL-1",
            "one_liner": one_liner,
            "data_table": data_table,
            "actions": actions,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }


def build_date_quality_trends_view() -> Dict[str, Any]:
    """
    Convenience function for sprint integration.
    Returns ADR-005 compliant date quality trends view.
    """
    analyzer = DateQualityTrendsAnalyzer()
    return analyzer.analyze()


# CLI for testing
if __name__ == "__main__":
    import json
    analyzer = DateQualityTrendsAnalyzer()
    result = analyzer.analyze()
    print(json.dumps(result, indent=2, default=str))
