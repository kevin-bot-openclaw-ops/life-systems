"""
Tests for DATE-M1-1: Date Quality Trends Analysis

Tests quality trend detection, source analysis, timing analysis,
and ADR-005 compliant output format.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from database.date_quality_trends import (
    DateQualityTrendsAnalyzer,
    DateOccurrence,
    QualityTrend,
    SourceAnalysis,
    TimingAnalysis,
    MIN_DATES_FOR_ANALYSIS,
    build_date_quality_trends_view
)


@pytest.fixture
def analyzer():
    """Create analyzer instance with mocked API."""
    return DateQualityTrendsAnalyzer()


@pytest.fixture
def sample_date_occurrence():
    """Create a sample date occurrence dict."""
    return {
        "id": "test-date-001",
        "activityType": "date",
        "temporalMark": {
            "type": "MOMENT",
            "at": "2026-03-12T19:00:00Z"
        },
        "measurements": [
            {"kind": {"type": "COUNT", "unit": "touches"}, "value": 8},
            {"kind": {"type": "COUNT", "unit": "she-laughs"}, "value": 5},
            {"kind": {"type": "COUNT", "unit": "kiss"}, "value": 1},
            {"kind": {"type": "COUNT", "unit": "hold-hand"}, "value": 2},
            {"kind": {"type": "COUNT", "unit": "minutes"}, "value": 120},
            {"kind": {"type": "SELECT", "options": ["tinder", "bumble", "real", "dance"]}, "value": 0}
        ],
        "tags": ["date", "relationship"],
        "note": "Great connection, good chemistry"
    }


@pytest.fixture
def sample_dates() -> list[DateOccurrence]:
    """Create sample parsed dates for testing."""
    now = datetime.now(timezone.utc)
    return [
        # Recent dates (last 2 weeks) - higher quality
        DateOccurrence(
            id="d1", timestamp=now - timedelta(days=1), source="tinder",
            quality_score=8.5, touches=10, laughs=8, kisses=1, hand_holds=3,
            duration_minutes=150, note="Amazing", day_of_week="Saturday", hour_of_day=20
        ),
        DateOccurrence(
            id="d2", timestamp=now - timedelta(days=5), source="bumble",
            quality_score=7.0, touches=5, laughs=4, kisses=0, hand_holds=2,
            duration_minutes=90, note="Nice", day_of_week="Wednesday", hour_of_day=19
        ),
        DateOccurrence(
            id="d3", timestamp=now - timedelta(days=10), source="tinder",
            quality_score=9.0, touches=12, laughs=10, kisses=2, hand_holds=5,
            duration_minutes=180, note="Incredible", day_of_week="Saturday", hour_of_day=21
        ),
        # Older dates (2-4 weeks ago) - lower quality
        DateOccurrence(
            id="d4", timestamp=now - timedelta(days=18), source="bumble",
            quality_score=5.5, touches=3, laughs=2, kisses=0, hand_holds=0,
            duration_minutes=60, note="Awkward", day_of_week="Tuesday", hour_of_day=18
        ),
        DateOccurrence(
            id="d5", timestamp=now - timedelta(days=22), source="dance",
            quality_score=6.0, touches=4, laughs=3, kisses=0, hand_holds=1,
            duration_minutes=90, note="Nice but no spark", day_of_week="Thursday", hour_of_day=22
        ),
    ]


class TestDateOccurrenceParsing:
    """Test parsing of date occurrences from API."""
    
    def test_parse_moment_type(self, analyzer, sample_date_occurrence):
        """Test parsing MOMENT temporal mark."""
        result = analyzer.parse_date_occurrence(sample_date_occurrence)
        
        assert result.id == "test-date-001"
        assert result.touches == 8
        assert result.laughs == 5
        assert result.kisses == 1
        assert result.hand_holds == 2
        assert result.duration_minutes == 120
        assert result.source == "tinder"
    
    def test_parse_span_type(self, analyzer):
        """Test parsing SPAN temporal mark."""
        occ = {
            "id": "test-span",
            "activityType": "date",
            "temporalMark": {
                "type": "SPAN",
                "start": "2026-03-12T19:00:00Z",
                "end": "2026-03-12T21:30:00Z"
            },
            "measurements": [],
            "tags": ["bumble"],
            "note": ""
        }
        result = analyzer.parse_date_occurrence(occ)
        
        assert result.id == "test-span"
        assert result.source == "bumble"  # From tags
    
    def test_quality_score_computation(self, analyzer):
        """Test quality score is computed correctly."""
        occ = {
            "id": "quality-test",
            "activityType": "date",
            "temporalMark": {"type": "MOMENT", "at": "2026-03-12T19:00:00Z"},
            "measurements": [
                {"kind": {"type": "COUNT", "unit": "touches"}, "value": 5},  # +2 (capped)
                {"kind": {"type": "COUNT", "unit": "she-laughs"}, "value": 3},  # +0.9
                {"kind": {"type": "COUNT", "unit": "kiss"}, "value": 2},  # +3 (capped)
                {"kind": {"type": "COUNT", "unit": "hold-hand"}, "value": 2},  # +0.6
                {"kind": {"type": "COUNT", "unit": "minutes"}, "value": 130},  # +1
            ],
            "tags": [],
            "note": "Great fun connection"  # +0.5
        }
        result = analyzer.parse_date_occurrence(occ)
        
        # Base 5.0 + 2 + 0.9 + 3 + 0.6 + 1 + 0.5 = 13 (capped to 10)
        assert result.quality_score == 10.0
    
    def test_source_inference_from_note(self, analyzer):
        """Test source is inferred from note when not in measurements/tags."""
        occ = {
            "id": "note-source",
            "activityType": "date",
            "temporalMark": {"type": "MOMENT", "at": "2026-03-12T19:00:00Z"},
            "measurements": [],
            "tags": [],
            "note": "We matched on Tinder last week"
        }
        result = analyzer.parse_date_occurrence(occ)
        
        assert result.source == "tinder"


class TestQualityTrendAnalysis:
    """Test quality trend detection."""
    
    def test_trend_up(self, analyzer, sample_dates):
        """Test detection of upward quality trend."""
        trend = analyzer.analyze_quality_trend(sample_dates)
        
        assert trend.direction == "up"
        assert trend.recent_avg > trend.previous_avg
        assert trend.change_pct > 0
        assert trend.total_dates == 5
    
    def test_trend_down(self, analyzer):
        """Test detection of downward quality trend."""
        now = datetime.now(timezone.utc)
        dates = [
            # Recent - low quality
            DateOccurrence(
                id="d1", timestamp=now - timedelta(days=3), source="tinder",
                quality_score=4.0, touches=2, laughs=1, kisses=0, hand_holds=0,
                duration_minutes=45, note="", day_of_week="Monday", hour_of_day=18
            ),
            DateOccurrence(
                id="d2", timestamp=now - timedelta(days=7), source="bumble",
                quality_score=4.5, touches=2, laughs=2, kisses=0, hand_holds=0,
                duration_minutes=60, note="", day_of_week="Thursday", hour_of_day=19
            ),
            DateOccurrence(
                id="d3", timestamp=now - timedelta(days=10), source="tinder",
                quality_score=5.0, touches=3, laughs=2, kisses=0, hand_holds=0,
                duration_minutes=60, note="", day_of_week="Sunday", hour_of_day=20
            ),
            # Previous - high quality
            DateOccurrence(
                id="d4", timestamp=now - timedelta(days=20), source="dance",
                quality_score=8.0, touches=8, laughs=6, kisses=1, hand_holds=2,
                duration_minutes=120, note="", day_of_week="Saturday", hour_of_day=21
            ),
            DateOccurrence(
                id="d5", timestamp=now - timedelta(days=25), source="bumble",
                quality_score=7.5, touches=6, laughs=5, kisses=1, hand_holds=1,
                duration_minutes=100, note="", day_of_week="Friday", hour_of_day=20
            ),
        ]
        
        trend = analyzer.analyze_quality_trend(dates)
        
        assert trend.direction == "down"
        assert trend.recent_avg < trend.previous_avg
        assert trend.change_pct < 0
    
    def test_trend_flat(self, analyzer):
        """Test detection of flat/stable trend."""
        now = datetime.now(timezone.utc)
        dates = [
            DateOccurrence(
                id="d1", timestamp=now - timedelta(days=3), source="tinder",
                quality_score=7.0, touches=5, laughs=4, kisses=0, hand_holds=2,
                duration_minutes=90, note="", day_of_week="Monday", hour_of_day=19
            ),
            DateOccurrence(
                id="d2", timestamp=now - timedelta(days=7), source="bumble",
                quality_score=7.2, touches=5, laughs=4, kisses=0, hand_holds=2,
                duration_minutes=90, note="", day_of_week="Thursday", hour_of_day=19
            ),
            DateOccurrence(
                id="d3", timestamp=now - timedelta(days=20), source="dance",
                quality_score=7.0, touches=5, laughs=4, kisses=0, hand_holds=2,
                duration_minutes=90, note="", day_of_week="Saturday", hour_of_day=20
            ),
            DateOccurrence(
                id="d4", timestamp=now - timedelta(days=25), source="tinder",
                quality_score=6.8, touches=4, laughs=4, kisses=0, hand_holds=2,
                duration_minutes=85, note="", day_of_week="Friday", hour_of_day=20
            ),
            DateOccurrence(
                id="d5", timestamp=now - timedelta(days=27), source="bumble",
                quality_score=7.1, touches=5, laughs=4, kisses=0, hand_holds=2,
                duration_minutes=90, note="", day_of_week="Wednesday", hour_of_day=19
            ),
        ]
        
        trend = analyzer.analyze_quality_trend(dates)
        
        assert trend.direction == "flat"
        assert abs(trend.change_pct) <= 10
    
    def test_insufficient_data(self, analyzer):
        """Test insufficient data handling."""
        dates = [
            DateOccurrence(
                id="d1", timestamp=datetime.now(timezone.utc) - timedelta(days=3),
                source="tinder", quality_score=7.0, touches=5, laughs=4,
                kisses=0, hand_holds=2, duration_minutes=90, note="",
                day_of_week="Monday", hour_of_day=19
            ),
        ]
        
        trend = analyzer.analyze_quality_trend(dates)
        
        assert trend.direction == "insufficient_data"
        assert trend.total_dates == 1


class TestSourceAnalysis:
    """Test source performance analysis."""
    
    def test_source_ranking(self, analyzer, sample_dates):
        """Test sources are ranked by conversion score."""
        sources = analyzer.analyze_sources(sample_dates)
        
        # Should have multiple sources
        assert len(sources) >= 2
        
        # Should be sorted by conversion_score descending
        scores = [s.conversion_score for s in sources]
        assert scores == sorted(scores, reverse=True)
    
    def test_source_avg_quality(self, analyzer, sample_dates):
        """Test average quality is computed correctly per source."""
        sources = analyzer.analyze_sources(sample_dates)
        
        # Find tinder source
        tinder = next((s for s in sources if s.source == "tinder"), None)
        assert tinder is not None
        
        # Tinder dates have quality 8.5 and 9.0, avg = 8.75
        assert tinder.avg_quality == 8.8  # rounded to 1 decimal
        assert tinder.date_count == 2
    
    def test_empty_dates(self, analyzer):
        """Test empty dates list returns empty sources."""
        sources = analyzer.analyze_sources([])
        assert sources == []


class TestTimingAnalysis:
    """Test timing analysis."""
    
    def test_best_day_detection(self, analyzer, sample_dates):
        """Test best day of week is detected."""
        timing = analyzer.analyze_timing(sample_dates)
        
        assert timing is not None
        # Saturday has 2 dates with avg quality 8.75
        assert timing.best_day == "Saturday"
        assert timing.best_day_avg_quality > 8
    
    def test_best_hour_range(self, analyzer, sample_dates):
        """Test best hour range is detected."""
        timing = analyzer.analyze_timing(sample_dates)
        
        assert timing is not None
        # Most dates are in evening (18-22) or night (22+)
        assert "evening" in timing.best_hour_range.lower() or "night" in timing.best_hour_range.lower()
    
    def test_insufficient_data_returns_none(self, analyzer):
        """Test insufficient data returns None."""
        dates = [
            DateOccurrence(
                id="d1", timestamp=datetime.now(timezone.utc) - timedelta(days=3),
                source="tinder", quality_score=7.0, touches=5, laughs=4,
                kisses=0, hand_holds=2, duration_minutes=90, note="",
                day_of_week="Monday", hour_of_day=19
            ),
        ]
        
        timing = analyzer.analyze_timing(dates)
        assert timing is None


class TestOutputFormat:
    """Test ADR-005 compliant output format."""
    
    def test_one_liner_with_data(self, analyzer, sample_dates):
        """Test one-liner is generated correctly with data."""
        analyzer._dates_cache = sample_dates
        
        trend = analyzer.analyze_quality_trend(sample_dates)
        sources = analyzer.analyze_sources(sample_dates)
        timing = analyzer.analyze_timing(sample_dates)
        
        one_liner = analyzer.generate_one_liner(trend, sources, timing)
        
        assert len(one_liner) > 0
        assert len(one_liner) <= 200  # Should be concise
        # Should mention trend
        assert "IMPROVING" in one_liner or "dipped" in one_liner or "stable" in one_liner
    
    def test_one_liner_insufficient_data(self, analyzer):
        """Test one-liner shows empty state with insufficient data."""
        trend = QualityTrend(
            direction="insufficient_data",
            recent_avg=0,
            previous_avg=0,
            change_pct=0,
            confidence="low",
            total_dates=2
        )
        
        one_liner = analyzer.generate_one_liner(trend, [], None)
        
        assert "more date" in one_liner.lower()
        assert "2" in one_liner  # current count
    
    def test_data_table_structure(self, analyzer, sample_dates):
        """Test data table has correct structure."""
        analyzer._dates_cache = sample_dates
        
        trend = analyzer.analyze_quality_trend(sample_dates)
        sources = analyzer.analyze_sources(sample_dates)
        timing = analyzer.analyze_timing(sample_dates)
        
        data_table = analyzer.generate_data_table(trend, sources, timing, sample_dates)
        
        assert data_table["type"] == "quality_trends"
        assert "trend_summary" in data_table
        assert "sources" in data_table
        assert "timing" in data_table
        assert "recent_dates" in data_table
        
        # Check trend summary
        assert data_table["trend_summary"]["direction"] == "up"
        assert data_table["trend_summary"]["total_dates"] == 5
        
        # Check sources
        assert len(data_table["sources"]) >= 2
        
        # Check recent dates
        assert len(data_table["recent_dates"]) <= 5
    
    def test_data_table_empty_state(self, analyzer):
        """Test data table shows empty state correctly."""
        trend = QualityTrend(
            direction="insufficient_data",
            recent_avg=0,
            previous_avg=0,
            change_pct=0,
            confidence="low",
            total_dates=2
        )
        
        data_table = analyzer.generate_data_table(trend, [], None, [])
        
        assert data_table["type"] == "empty_state"
        assert "current_dates" in data_table
        assert "required_dates" in data_table
    
    def test_actions_generated(self, analyzer, sample_dates):
        """Test actions are generated correctly."""
        trend = analyzer.analyze_quality_trend(sample_dates)
        sources = analyzer.analyze_sources(sample_dates)
        timing = analyzer.analyze_timing(sample_dates)
        
        actions = analyzer.generate_actions(trend, sources, timing)
        
        assert len(actions) >= 1
        for action in actions:
            assert "action" in action
            assert "label" in action
            assert "description" in action


class TestFullAnalysis:
    """Test full analysis workflow."""
    
    @patch.object(DateQualityTrendsAnalyzer, 'fetch_dates')
    def test_analyze_returns_complete_result(self, mock_fetch, analyzer, sample_date_occurrence):
        """Test analyze() returns complete ADR-005 compliant result."""
        # Create enough dates
        dates = []
        for i in range(6):
            occ = sample_date_occurrence.copy()
            occ["id"] = f"date-{i}"
            ts = datetime.now(timezone.utc) - timedelta(days=i * 4)
            occ["temporalMark"]["at"] = ts.isoformat()
            dates.append(occ)
        
        mock_fetch.return_value = dates
        
        result = analyzer.analyze()
        
        assert "section" in result
        assert result["section"] == "date_quality_trends"
        assert result["goal_ref"] == "GOAL-1"
        assert "one_liner" in result
        assert "data_table" in result
        assert "actions" in result
        assert "generated_at" in result
    
    @patch.object(DateQualityTrendsAnalyzer, 'fetch_dates')
    def test_build_view_function(self, mock_fetch, sample_date_occurrence):
        """Test build_date_quality_trends_view convenience function."""
        dates = []
        for i in range(6):
            occ = sample_date_occurrence.copy()
            occ["id"] = f"date-{i}"
            ts = datetime.now(timezone.utc) - timedelta(days=i * 4)
            occ["temporalMark"]["at"] = ts.isoformat()
            dates.append(occ)
        
        mock_fetch.return_value = dates
        
        result = build_date_quality_trends_view()
        
        assert result["section"] == "date_quality_trends"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_all_same_source(self, analyzer):
        """Test when all dates are from same source."""
        now = datetime.now(timezone.utc)
        dates = [
            DateOccurrence(
                id=f"d{i}", timestamp=now - timedelta(days=i * 3),
                source="tinder", quality_score=7.0 + i * 0.3, touches=5, laughs=4,
                kisses=0, hand_holds=2, duration_minutes=90, note="",
                day_of_week="Monday", hour_of_day=19
            )
            for i in range(5)
        ]
        
        sources = analyzer.analyze_sources(dates)
        
        assert len(sources) == 1
        assert sources[0].source == "tinder"
        assert sources[0].date_count == 5
    
    def test_unknown_sources(self, analyzer):
        """Test handling of unknown sources."""
        now = datetime.now(timezone.utc)
        dates = [
            DateOccurrence(
                id=f"d{i}", timestamp=now - timedelta(days=i * 3),
                source="unknown", quality_score=7.0, touches=5, laughs=4,
                kisses=0, hand_holds=2, duration_minutes=90, note="",
                day_of_week="Monday", hour_of_day=19
            )
            for i in range(5)
        ]
        
        sources = analyzer.analyze_sources(dates)
        
        # Unknown sources grouped as "other"
        assert len(sources) == 1
        assert sources[0].source == "other"
    
    def test_date_highlights_generation(self, analyzer):
        """Test date highlights are generated correctly."""
        date = DateOccurrence(
            id="d1", timestamp=datetime.now(timezone.utc),
            source="tinder", quality_score=9.0, touches=10, laughs=8,
            kisses=2, hand_holds=3, duration_minutes=180, note="",
            day_of_week="Saturday", hour_of_day=20
        )
        
        highlights = analyzer._date_highlights(date)
        
        assert "💋" in highlights  # kisses
        assert "😂" in highlights  # laughs >= 5
        assert "180min" in highlights  # duration > 120


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
