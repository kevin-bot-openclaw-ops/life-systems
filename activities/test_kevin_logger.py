"""
Tests for Kevin self-logging module.
"""

import pytest
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from activities.kevin_logger import (
    KevinLogger,
    CognitoAuthError,
    ActivitiesAPIError,
    log_current_sprint,
)


@pytest.fixture
def mock_cognito_response():
    """Mock successful Cognito authentication response."""
    return {
        "AuthenticationResult": {
            "IdToken": "mock-id-token-12345",
            "RefreshToken": "mock-refresh-token-67890",
            "ExpiresIn": 3600,
        }
    }


@pytest.fixture
def mock_refresh_response():
    """Mock successful token refresh response."""
    return {
        "AuthenticationResult": {
            "IdToken": "mock-refreshed-id-token-99999",
            "ExpiresIn": 3600,
        }
    }


@pytest.fixture
def mock_activities_response():
    """Mock successful Activities API response."""
    return {
        "id": "test-occurrence-id-12345",
        "activityType": {"name": "kevin-sprint"},
        "moment": "2026-03-08T19:00:00Z",
        "measurements": [
            {"typeName": "tasks_completed", "count": 1},
            {"typeName": "duration_minutes", "count": 120},
            {"typeName": "lines_of_code", "count": 500},
        ],
    }


@pytest.fixture
def kevin_logger(tmp_path):
    """Create KevinLogger with temp cache file."""
    cache_file = tmp_path / "auth_cache.json"
    return KevinLogger(cache_file=str(cache_file))


class TestCognitoAuth:
    """Test Cognito authentication flow."""
    
    @patch('activities.kevin_logger.requests.post')
    def test_initial_authentication(self, mock_post, kevin_logger, mock_cognito_response):
        """Test initial authentication with Cognito."""
        mock_response = Mock()
        mock_response.json.return_value = mock_cognito_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        kevin_logger._authenticate()
        
        assert kevin_logger.id_token == "mock-id-token-12345"
        assert kevin_logger.refresh_token == "mock-refresh-token-67890"
        assert kevin_logger.token_expiry is not None
        
        # Verify Cognito API was called correctly
        assert mock_post.called
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['AuthFlow'] == 'USER_PASSWORD_AUTH'
        assert payload['ClientId'] == '4ojuhbnovtcn9t2jooqu3qsbg6'
        assert payload['AuthParameters']['USERNAME'] == 'bot.jerzy.openclaw@gmail.com'
    
    @patch('activities.kevin_logger.requests.post')
    def test_authentication_failure(self, mock_post, kevin_logger):
        """Test handling of authentication failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Auth failed")
        mock_post.return_value = mock_response
        
        with pytest.raises(CognitoAuthError):
            kevin_logger._authenticate()
    
    @patch('activities.kevin_logger.requests.post')
    def test_token_refresh(self, mock_post, kevin_logger, mock_refresh_response):
        """Test token refresh flow."""
        # Set up existing refresh token
        kevin_logger.refresh_token = "existing-refresh-token"
        
        mock_response = Mock()
        mock_response.json.return_value = mock_refresh_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        kevin_logger._refresh_auth()
        
        assert kevin_logger.id_token == "mock-refreshed-id-token-99999"
        
        # Verify refresh API was called
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['AuthFlow'] == 'REFRESH_TOKEN_AUTH'
        assert payload['AuthParameters']['REFRESH_TOKEN'] == 'existing-refresh-token'
    
    @patch('activities.kevin_logger.requests.post')
    def test_token_refresh_fallback_to_full_auth(self, mock_post, kevin_logger, mock_cognito_response):
        """Test fallback to full auth if refresh fails."""
        kevin_logger.refresh_token = "expired-refresh-token"
        
        # First call (refresh) fails, second call (full auth) succeeds
        mock_refresh_fail = Mock()
        mock_refresh_fail.raise_for_status.side_effect = Exception("Refresh failed")
        
        mock_auth_success = Mock()
        mock_auth_success.json.return_value = mock_cognito_response
        mock_auth_success.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_refresh_fail, mock_auth_success]
        
        kevin_logger._refresh_auth()
        
        # Should have new token from full auth
        assert kevin_logger.id_token == "mock-id-token-12345"
        assert mock_post.call_count == 2


class TestTokenCache:
    """Test token caching behavior."""
    
    @patch('activities.kevin_logger.requests.post')
    def test_token_cache_save_and_load(self, mock_post, tmp_path, mock_cognito_response):
        """Test saving and loading token cache."""
        cache_file = tmp_path / "auth_cache.json"
        
        # Create logger and authenticate
        logger1 = KevinLogger(cache_file=str(cache_file))
        
        mock_response = Mock()
        mock_response.json.return_value = mock_cognito_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        logger1._authenticate()
        
        # Cache file should exist
        assert cache_file.exists()
        
        # Create new logger instance - should load from cache
        logger2 = KevinLogger(cache_file=str(cache_file))
        
        # Should have loaded token from cache
        assert logger2.id_token == "mock-id-token-12345"
        assert logger2.refresh_token == "mock-refresh-token-67890"
    
    def test_expired_cache_ignored(self, tmp_path):
        """Test that expired cache tokens are ignored."""
        cache_file = tmp_path / "auth_cache.json"
        
        # Write expired cache
        expired_cache = {
            "id_token": "expired-token",
            "refresh_token": "expired-refresh",
            "expiry": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }
        with open(cache_file, 'w') as f:
            json.dump(expired_cache, f)
        
        # Create logger - should not load expired token
        logger = KevinLogger(cache_file=str(cache_file))
        
        assert logger.id_token is None


class TestSprintLogging:
    """Test sprint logging to Activities API."""
    
    @patch('activities.kevin_logger.requests.post')
    def test_log_sprint_success(self, mock_post, kevin_logger, mock_cognito_response, mock_activities_response):
        """Test successful sprint logging."""
        # Setup auth
        mock_auth = Mock()
        mock_auth.json.return_value = mock_cognito_response
        mock_auth.raise_for_status = Mock()
        
        # Setup activities API response
        mock_activities = Mock()
        mock_activities.json.return_value = mock_activities_response
        mock_activities.status_code = 200
        mock_activities.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_auth, mock_activities]
        
        result = kevin_logger.log_sprint(
            tasks_completed=1,
            duration_minutes=120,
            lines_of_code=500,
            note="Completed ACT-M1-2"
        )
        
        assert result['id'] == "test-occurrence-id-12345"
        
        # Verify Activities API call
        activities_call = mock_post.call_args_list[1]
        payload = activities_call[1]['json']
        assert payload['activityTypeName'] == 'kevin-sprint'
        assert len(payload['measurements']) == 3
        assert payload['note'] == 'Completed ACT-M1-2'
        
        # Check measurements
        measurements = {m['typeName']: m['count'] for m in payload['measurements']}
        assert measurements['tasks_completed'] == 1
        assert measurements['duration_minutes'] == 120
        assert measurements['lines_of_code'] == 500
    
    @patch('activities.kevin_logger.requests.post')
    def test_log_sprint_with_401_retry(self, mock_post, kevin_logger, mock_cognito_response, mock_refresh_response, mock_activities_response):
        """Test 401 retry with token refresh."""
        # Setup: auth succeeds, first activities call gets 401, refresh succeeds, second activities call succeeds
        mock_auth = Mock()
        mock_auth.json.return_value = mock_cognito_response
        mock_auth.raise_for_status = Mock()
        
        mock_401 = Mock()
        mock_401.status_code = 401
        
        mock_refresh = Mock()
        mock_refresh.json.return_value = mock_refresh_response
        mock_refresh.raise_for_status = Mock()
        
        mock_activities_success = Mock()
        mock_activities_success.json.return_value = mock_activities_response
        mock_activities_success.status_code = 200
        mock_activities_success.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_auth, mock_401, mock_refresh, mock_activities_success]
        
        result = kevin_logger.log_sprint(
            tasks_completed=1,
            duration_minutes=120,
            lines_of_code=500
        )
        
        # Should have succeeded after retry
        assert result['id'] == "test-occurrence-id-12345"
        
        # Should have called: auth, activities (401), refresh, activities (200)
        assert mock_post.call_count == 4
    
    @patch('activities.kevin_logger.requests.post')
    def test_log_sprint_failure(self, mock_post, kevin_logger, mock_cognito_response):
        """Test handling of Activities API failure."""
        mock_auth = Mock()
        mock_auth.json.return_value = mock_cognito_response
        mock_auth.raise_for_status = Mock()
        
        mock_fail = Mock()
        mock_fail.status_code = 500
        mock_fail.raise_for_status.side_effect = Exception("API error")
        
        mock_post.side_effect = [mock_auth, mock_fail]
        
        with pytest.raises(ActivitiesAPIError):
            kevin_logger.log_sprint(
                tasks_completed=1,
                duration_minutes=120,
                lines_of_code=500
            )
    
    @patch('activities.kevin_logger.requests.post')
    def test_log_sprint_with_custom_timestamp(self, mock_post, kevin_logger, mock_cognito_response, mock_activities_response):
        """Test logging sprint with custom timestamp."""
        mock_auth = Mock()
        mock_auth.json.return_value = mock_cognito_response
        mock_auth.raise_for_status = Mock()
        
        mock_activities = Mock()
        mock_activities.json.return_value = mock_activities_response
        mock_activities.status_code = 200
        mock_activities.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_auth, mock_activities]
        
        custom_time = datetime(2026, 3, 8, 10, 0, 0, tzinfo=timezone.utc)
        
        kevin_logger.log_sprint(
            tasks_completed=1,
            duration_minutes=240,
            lines_of_code=1000,
            occurred_at=custom_time
        )
        
        # Verify timestamp in payload
        activities_call = mock_post.call_args_list[1]
        payload = activities_call[1]['json']
        assert payload['moment'] == "2026-03-08T10:00:00Z"


class TestConvenienceFunction:
    """Test the convenience log_current_sprint function."""
    
    @patch('activities.kevin_logger.KevinLogger')
    def test_log_current_sprint(self, mock_logger_class):
        """Test convenience function."""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger
        
        log_current_sprint(
            tasks_completed=2,
            duration_minutes=180,
            lines_of_code=750,
            note="Test sprint"
        )
        
        mock_logger.log_sprint.assert_called_once_with(
            tasks_completed=2,
            duration_minutes=180,
            lines_of_code=750,
            note="Test sprint"
        )
    
    @patch('activities.kevin_logger.KevinLogger')
    def test_log_current_sprint_graceful_failure(self, mock_logger_class):
        """Test that convenience function doesn't crash on error."""
        mock_logger = Mock()
        mock_logger.log_sprint.side_effect = Exception("API down")
        mock_logger_class.return_value = mock_logger
        
        # Should not raise exception
        log_current_sprint(
            tasks_completed=1,
            duration_minutes=60,
            lines_of_code=100
        )


class TestTokenExpiry:
    """Test token expiry handling."""
    
    @patch('activities.kevin_logger.requests.post')
    def test_auto_refresh_on_expiry(self, mock_post, kevin_logger, mock_cognito_response, mock_refresh_response, mock_activities_response):
        """Test automatic token refresh when expired."""
        # Setup: authenticate first
        mock_auth = Mock()
        mock_auth.json.return_value = mock_cognito_response
        mock_auth.raise_for_status = Mock()
        mock_post.return_value = mock_auth
        
        kevin_logger._authenticate()
        
        # Force token to be expired
        kevin_logger.token_expiry = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        # Setup refresh and activities responses
        mock_refresh = Mock()
        mock_refresh.json.return_value = mock_refresh_response
        mock_refresh.raise_for_status = Mock()
        
        mock_activities = Mock()
        mock_activities.json.return_value = mock_activities_response
        mock_activities.status_code = 200
        mock_activities.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_refresh, mock_activities]
        
        # Log sprint - should auto-refresh
        kevin_logger.log_sprint(
            tasks_completed=1,
            duration_minutes=60,
            lines_of_code=200
        )
        
        # Should have refreshed token
        assert kevin_logger.id_token == "mock-refreshed-id-token-99999"
