"""
Tests for GOAL1-02 Readiness Score Engine
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

from goals.readiness_score import ReadinessScoreEngine, SCORING_RULES


@pytest.fixture
def mock_daily_stats_high_score():
    """Mock daily stats for a high-score day."""
    return {
        'from': '2026-03-07',
        'to': '2026-03-09',
        'days': [
            {
                'date': '2026-03-07',
                'types': {
                    'gym': {'count': 0, 'totalDurationMin': None},
                    'sun-exposure': {'count': 0, 'totalDurationMin': None},
                    'sleep': {'count': 0, 'totalDurationMin': None},
                    'sauna': {'count': 1, 'totalDurationMin': 30},
                    'coffee': {'count': 0, 'totalDurationMin': None},
                    'walking': {'count': 0, 'totalDurationMin': None},
                    'swimming': {'count': 0, 'totalDurationMin': None}
                }
            },
            {
                'date': '2026-03-08',
                'types': {
                    'gym': {'count': 1, 'totalDurationMin': 60},
                    'sun-exposure': {'count': 0, 'totalDurationMin': None},
                    'sleep': {'count': 0, 'totalDurationMin': None},
                    'sauna': {'count': 0, 'totalDurationMin': None},
                    'coffee': {'count': 0, 'totalDurationMin': None},
                    'walking': {'count': 0, 'totalDurationMin': None},
                    'swimming': {'count': 0, 'totalDurationMin': None}
                }
            },
            {
                'date': '2026-03-09',
                'types': {
                    'gym': {'count': 0, 'totalDurationMin': None},
                    'sun-exposure': {'count': 1, 'totalDurationMin': 25},
                    'sleep': {'count': 1, 'totalDurationMin': 480},  # 8h
                    'sauna': {'count': 0, 'totalDurationMin': None},
                    'cold-exposure': {'count': 1, 'totalDurationMin': 10},
                    'coffee': {'count': 1, 'totalDurationMin': None},
                    'walking': {'count': 1, 'totalDurationMin': 30},
                    'swimming': {'count': 0, 'totalDurationMin': None}
                }
            }
        ]
    }


@pytest.fixture
def mock_daily_stats_low_score():
    """Mock daily stats for a low-score day."""
    return {
        'from': '2026-03-07',
        'to': '2026-03-09',
        'days': [
            {
                'date': '2026-03-07',
                'types': {
                    'gym': {'count': 0, 'totalDurationMin': None},
                    'sun-exposure': {'count': 0, 'totalDurationMin': None},
                    'sleep': {'count': 0, 'totalDurationMin': None},
                    'sauna': {'count': 0, 'totalDurationMin': None},
                    'coffee': {'count': 0, 'totalDurationMin': None},
                    'walking': {'count': 0, 'totalDurationMin': None},
                    'swimming': {'count': 0, 'totalDurationMin': None}
                }
            },
            {
                'date': '2026-03-08',
                'types': {
                    'gym': {'count': 0, 'totalDurationMin': None},
                    'sun-exposure': {'count': 0, 'totalDurationMin': None},
                    'sleep': {'count': 0, 'totalDurationMin': None},
                    'sauna': {'count': 0, 'totalDurationMin': None},
                    'coffee': {'count': 0, 'totalDurationMin': None},
                    'walking': {'count': 0, 'totalDurationMin': None},
                    'swimming': {'count': 0, 'totalDurationMin': None}
                }
            },
            {
                'date': '2026-03-09',
                'types': {
                    'gym': {'count': 0, 'totalDurationMin': None},
                    'sun-exposure': {'count': 0, 'totalDurationMin': None},
                    'sleep': {'count': 1, 'totalDurationMin': 300},  # 5h (poor)
                    'sauna': {'count': 0, 'totalDurationMin': None},
                    'coffee': {'count': 4, 'totalDurationMin': None},  # Too many
                    'walking': {'count': 0, 'totalDurationMin': None},
                    'swimming': {'count': 0, 'totalDurationMin': None}
                }
            }
        ]
    }


class TestReadinessScoreEngine:
    """Test ReadinessScoreEngine class."""
    
    @patch('requests.get')
    def test_high_score_day(self, mock_get, mock_daily_stats_high_score):
        """Test scoring on a high-quality day."""
        mock_get.return_value.json.return_value = mock_daily_stats_high_score
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Should score high (gym yesterday + sun + sleep + cold + coffee + walking)
        # = 2.0 + 1.5 + 1.5 + 1.0 + 0.5 + 0.5 = 7.0
        assert result['score'] == 7.0
        assert result['status'] == 'READY'
        assert result['color'] == 'green'
        assert len(result['missing_actions']) == 0
    
    @patch('requests.get')
    def test_low_score_day(self, mock_get, mock_daily_stats_low_score):
        """Test scoring on a low-quality day."""
        mock_get.return_value.json.return_value = mock_daily_stats_low_score
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Should score low (only poor sleep, too much coffee = penalty)
        # Sleep <6h = 0 points, coffee >2 = 0 points
        assert result['score'] == 0.0
        assert result['status'] == 'LOW'
        assert result['color'] == 'red'
        assert len(result['missing_actions']) > 0
    
    @patch('requests.get')
    def test_resistance_training_yesterday(self, mock_get, mock_daily_stats_high_score):
        """Test that gym yesterday counts for resistance training."""
        mock_get.return_value.json.return_value = mock_daily_stats_high_score
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Find resistance training component
        rt_component = next(c for c in result['breakdown'] if c['component'] == 'Resistance Training')
        
        assert rt_component['earned'] == 2.0
        assert rt_component['status'] == 'complete'
        assert 'Gym: 1x in last 2 days' in rt_component['detail']
    
    @patch('requests.get')
    def test_sun_exposure_threshold(self, mock_get, mock_daily_stats_high_score):
        """Test sun exposure requires ≥15 min."""
        # Modify to have only 10 min sun
        stats = mock_daily_stats_high_score.copy()
        stats['days'][2]['types']['sun-exposure']['totalDurationMin'] = 10
        
        mock_get.return_value.json.return_value = stats
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Find sun exposure component
        sun_component = next(c for c in result['breakdown'] if c['component'] == 'Sun Exposure')
        
        assert sun_component['earned'] == 0.0
        assert sun_component['status'] == 'missing'
        assert '10 min' in sun_component['detail']
    
    @patch('requests.get')
    def test_sleep_thresholds(self, mock_get, mock_daily_stats_high_score):
        """Test sleep scoring thresholds (7h=full, 6h=half, <5h=0)."""
        engine = ReadinessScoreEngine()
        
        # Test 8h sleep (full points)
        stats_8h = mock_daily_stats_high_score.copy()
        stats_8h['days'][2]['types']['sleep']['totalDurationMin'] = 480
        mock_get.return_value.json.return_value = stats_8h
        mock_get.return_value.raise_for_status = Mock()
        result_8h = engine.compute_score(date='2026-03-09')
        sleep_8h = next(c for c in result_8h['breakdown'] if c['component'] == 'Sleep Quality')
        assert sleep_8h['earned'] == 1.5
        
        # Test 6h sleep (half points)
        stats_6h = mock_daily_stats_high_score.copy()
        stats_6h['days'][2]['types']['sleep']['totalDurationMin'] = 360
        mock_get.return_value.json.return_value = stats_6h
        result_6h = engine.compute_score(date='2026-03-09')
        sleep_6h = next(c for c in result_6h['breakdown'] if c['component'] == 'Sleep Quality')
        assert sleep_6h['earned'] == 0.75
        
        # Test 5h sleep (no points)
        stats_5h = mock_daily_stats_high_score.copy()
        stats_5h['days'][2]['types']['sleep']['totalDurationMin'] = 300
        mock_get.return_value.json.return_value = stats_5h
        result_5h = engine.compute_score(date='2026-03-09')
        sleep_5h = next(c for c in result_5h['breakdown'] if c['component'] == 'Sleep Quality')
        assert sleep_5h['earned'] == 0.0
    
    @patch('requests.get')
    def test_cold_heat_stress_48h(self, mock_get, mock_daily_stats_high_score):
        """Test cold/heat stress counts occurrences in last 48h."""
        mock_get.return_value.json.return_value = mock_daily_stats_high_score
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Find cold/heat stress component
        stress_component = next(c for c in result['breakdown'] if c['component'] == 'Cold/Heat Stress')
        
        # Should count: sauna on Mar 7 + cold-exposure on Mar 9 = 2x in 48h
        assert stress_component['earned'] == 1.0
        assert stress_component['status'] == 'complete'
    
    @patch('requests.get')
    def test_coffee_penalty(self, mock_get, mock_daily_stats_low_score):
        """Test coffee >2 cups = no points."""
        mock_get.return_value.json.return_value = mock_daily_stats_low_score
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Find low cortisol component
        cortisol_component = next(c for c in result['breakdown'] if c['component'] == 'Low Cortisol')
        
        assert cortisol_component['earned'] == 0.0
        assert cortisol_component['status'] == 'violated'
        assert '4 coffees' in cortisol_component['detail']
    
    @patch('requests.get')
    def test_missing_actions_prioritized(self, mock_get, mock_daily_stats_low_score):
        """Test missing actions are sorted by priority."""
        mock_get.return_value.json.return_value = mock_daily_stats_low_score
        mock_get.return_value.raise_for_status = Mock()
        
        engine = ReadinessScoreEngine()
        result = engine.compute_score(date='2026-03-09')
        
        # Should have multiple missing actions
        assert len(result['missing_actions']) >= 2
        
        # First should be highest priority
        first_action = result['missing_actions'][0]
        assert 'priority' in first_action
        assert first_action['points'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
