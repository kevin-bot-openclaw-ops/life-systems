"""
Tests for TASK-050 Meta Heartbeat Integration
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from goals.meta_heartbeat import MetaHeartbeat, sprint_loop_heartbeat, DORMANCY_THRESHOLDS


@pytest.fixture
def temp_state_file():
    """Create a temporary state file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_meta_response():
    """Sample meta API response."""
    return {
        'lastOccurrenceAt': '2026-03-09T21:27:56.420256806Z',
        'activeTypes': 14,
        'daysSinceLastLog': {
            'date': 0,
            'uttanasana': 2,
            'bumble': 2,
            'walking': 2,
            'nerve-stimulus': 0,
            'duo-lingo': 0,
            'gym': 0
        },
        'lookbackDays': 7
    }


class TestMetaHeartbeat:
    """Test MetaHeartbeat class."""
    
    def test_init(self, temp_state_file):
        """Test initialization."""
        heartbeat = MetaHeartbeat(
            share_token="test-token",
            state_file=temp_state_file
        )
        
        assert heartbeat.share_token == "test-token"
        assert heartbeat.state_file == temp_state_file
    
    @patch('requests.get')
    def test_fetch_meta(self, mock_get, mock_meta_response, temp_state_file):
        """Test fetching meta from API."""
        mock_get.return_value.json.return_value = mock_meta_response
        mock_get.return_value.raise_for_status = Mock()
        
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        result = heartbeat.fetch_meta(lookback_days=7)
        
        assert result == mock_meta_response
        assert mock_get.called
    
    def test_save_and_load_state(self, temp_state_file, mock_meta_response):
        """Test saving and loading state."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        # Save state
        heartbeat.save_current_state(mock_meta_response)
        
        # Load state
        loaded = heartbeat.load_previous_state()
        
        assert loaded is not None
        assert loaded['lastOccurrenceAt'] == mock_meta_response['lastOccurrenceAt']
        assert loaded['activeTypes'] == mock_meta_response['activeTypes']
        assert 'timestamp' in loaded
    
    def test_load_state_file_not_exists(self, temp_state_file):
        """Test loading state when file doesn't exist."""
        # Use a path that doesn't exist
        non_existent = Path("/tmp/non-existent-state-file.json")
        heartbeat = MetaHeartbeat(state_file=non_existent)
        
        loaded = heartbeat.load_previous_state()
        
        assert loaded is None
    
    def test_has_new_data_first_run(self, mock_meta_response, temp_state_file):
        """Test has_new_data on first run (no previous state)."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        has_new = heartbeat.has_new_data(mock_meta_response, previous_state=None)
        
        assert has_new is True
    
    def test_has_new_data_same_timestamp(self, mock_meta_response, temp_state_file):
        """Test has_new_data when timestamp unchanged."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        previous_state = {
            'lastOccurrenceAt': mock_meta_response['lastOccurrenceAt'],
            'activeTypes': 14
        }
        
        has_new = heartbeat.has_new_data(mock_meta_response, previous_state)
        
        assert has_new is False
    
    def test_has_new_data_different_timestamp(self, mock_meta_response, temp_state_file):
        """Test has_new_data when timestamp changed."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        previous_state = {
            'lastOccurrenceAt': '2026-03-08T15:00:00Z',  # Different time
            'activeTypes': 12
        }
        
        has_new = heartbeat.has_new_data(mock_meta_response, previous_state)
        
        assert has_new is True
    
    def test_detect_dormancy_no_alerts(self, temp_state_file):
        """Test dormancy detection when all types are active."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        meta = {
            'daysSinceLastLog': {
                'bumble': 1,  # Threshold is 3
                'tinder': 2,  # Threshold is 3
                'date': 3,    # Threshold is 7
                'gym': 1,     # Threshold is 2
                'duo-lingo': 2  # Threshold is 3
            }
        }
        
        alerts = heartbeat.detect_dormancy(meta)
        
        assert len(alerts) == 0
    
    def test_detect_dormancy_warning_level(self, temp_state_file):
        """Test dormancy detection at warning level."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        meta = {
            'daysSinceLastLog': {
                'bumble': 3,  # At threshold (3)
                'tinder': 1,
                'date': 2,
                'gym': 1
            }
        }
        
        alerts = heartbeat.detect_dormancy(meta)
        
        assert len(alerts) == 1
        assert alerts[0]['type'] == 'bumble'
        assert alerts[0]['days_silent'] == 3
        assert alerts[0]['severity'] == 'warning'
    
    def test_detect_dormancy_critical_level(self, temp_state_file):
        """Test dormancy detection at critical level (2x threshold)."""
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        meta = {
            'daysSinceLastLog': {
                'bumble': 7,  # 2x+ threshold (3) = critical
                'gym': 5      # 2x+ threshold (2) = critical
            }
        }
        
        alerts = heartbeat.detect_dormancy(meta)
        
        assert len(alerts) == 2
        
        # Find bumble alert
        bumble_alert = next(a for a in alerts if a['type'] == 'bumble')
        assert bumble_alert['severity'] == 'critical'
        
        # Find gym alert
        gym_alert = next(a for a in alerts if a['type'] == 'gym')
        assert gym_alert['severity'] == 'critical'
    
    @patch('requests.get')
    def test_check_skip_decision(self, mock_get, mock_meta_response, temp_state_file):
        """Test check() returns skip decision when no new data."""
        mock_get.return_value.json.return_value = mock_meta_response
        mock_get.return_value.raise_for_status = Mock()
        
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        # First check - should proceed (no previous state)
        result1 = heartbeat.check()
        assert result1['decision'] == 'proceed'
        assert result1['has_new_data'] is True
        
        # Second check - should skip (same data)
        result2 = heartbeat.check()
        assert result2['decision'] == 'skip'
        assert result2['has_new_data'] is False
    
    @patch('requests.get')
    def test_should_skip_goal_computations(self, mock_get, mock_meta_response, temp_state_file):
        """Test convenience method for sprint loop."""
        mock_get.return_value.json.return_value = mock_meta_response
        mock_get.return_value.raise_for_status = Mock()
        
        heartbeat = MetaHeartbeat(state_file=temp_state_file)
        
        # First run - should NOT skip
        should_skip1, report1 = heartbeat.should_skip_goal_computations()
        assert should_skip1 is False
        assert report1['decision'] == 'proceed'
        
        # Second run - should skip
        should_skip2, report2 = heartbeat.should_skip_goal_computations()
        assert should_skip2 is True
        assert report2['decision'] == 'skip'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
