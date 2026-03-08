"""
Kevin Self-Logging Module
Logs Kevin's autonomous work sprint activities to the Activities app using JWT authentication.

Kevin's account: bot.jerzy.openclaw@gmail.com
Cognito Client ID: 4ojuhbnovtcn9t2jooqu3qsbg6
Region: eu-central-1

Activity type: kevin-sprint
Measurements:
  - tasks_completed (COUNT)
  - duration_minutes (COUNT)
  - lines_of_code (COUNT)
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import requests
import hashlib
import hmac
import base64

logger = logging.getLogger(__name__)

# Cognito configuration
COGNITO_CLIENT_ID = "4ojuhbnovtcn9t2jooqu3qsbg6"
COGNITO_REGION = "eu-central-1"
COGNITO_ENDPOINT = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"

# Activities API
BASE_URL = "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com"

# Kevin's credentials (stored in env vars for security in production)
KEVIN_EMAIL = os.getenv("KEVIN_EMAIL", "bot.jerzy.openclaw@gmail.com")
KEVIN_PASSWORD = os.getenv("KEVIN_PASSWORD", "asdf23rfasdv23rtadfgz2ASD")


class CognitoAuthError(Exception):
    """Raised when Cognito authentication fails."""
    pass


class ActivitiesAPIError(Exception):
    """Raised when Activities API call fails."""
    pass


class KevinLogger:
    """Kevin's self-logging client for Activities app."""
    
    def __init__(self, cache_file: str = "/tmp/kevin_auth_cache.json"):
        self.cache_file = cache_file
        self.id_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        # Try to load cached tokens
        self._load_cache()
    
    def _load_cache(self):
        """Load cached auth tokens if they exist and are valid."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                
                # Check if token is still valid (with 5min buffer)
                expiry = datetime.fromisoformat(cache.get("expiry", ""))
                if expiry > datetime.now(timezone.utc):
                    self.id_token = cache.get("id_token")
                    self.refresh_token = cache.get("refresh_token")
                    self.token_expiry = expiry
                    logger.info("Loaded cached auth token")
        except Exception as e:
            logger.warning(f"Failed to load auth cache: {e}")
    
    def _save_cache(self):
        """Save auth tokens to cache file."""
        try:
            cache = {
                "id_token": self.id_token,
                "refresh_token": self.refresh_token,
                "expiry": self.token_expiry.isoformat() if self.token_expiry else None,
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
            logger.info("Saved auth token to cache")
        except Exception as e:
            logger.warning(f"Failed to save auth cache: {e}")
    
    def _authenticate(self):
        """
        Authenticate with Cognito using USER_PASSWORD_AUTH flow.
        
        Raises:
            CognitoAuthError: If authentication fails
        """
        logger.info("Authenticating with Cognito...")
        
        payload = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": COGNITO_CLIENT_ID,
            "AuthParameters": {
                "USERNAME": KEVIN_EMAIL,
                "PASSWORD": KEVIN_PASSWORD,
            }
        }
        
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        }
        
        try:
            response = requests.post(
                COGNITO_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            auth_result = data.get("AuthenticationResult", {})
            self.id_token = auth_result.get("IdToken")
            self.refresh_token = auth_result.get("RefreshToken")
            
            # Token expires in ExpiresIn seconds (default 3600 = 1 hour)
            expires_in = auth_result.get("ExpiresIn", 3600)
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            if not self.id_token:
                raise CognitoAuthError("No IdToken in Cognito response")
            
            self._save_cache()
            logger.info("Authentication successful")
            
        except requests.RequestException as e:
            raise CognitoAuthError(f"Cognito auth request failed: {e}")
        except Exception as e:
            raise CognitoAuthError(f"Authentication failed: {e}")
    
    def _refresh_auth(self):
        """
        Refresh auth token using refresh token.
        
        Raises:
            CognitoAuthError: If refresh fails
        """
        if not self.refresh_token:
            # No refresh token, do full auth
            self._authenticate()
            return
        
        logger.info("Refreshing auth token...")
        
        payload = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "ClientId": COGNITO_CLIENT_ID,
            "AuthParameters": {
                "REFRESH_TOKEN": self.refresh_token,
            }
        }
        
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        }
        
        try:
            response = requests.post(
                COGNITO_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            auth_result = data.get("AuthenticationResult", {})
            self.id_token = auth_result.get("IdToken")
            
            # Refresh token stays the same
            expires_in = auth_result.get("ExpiresIn", 3600)
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            if not self.id_token:
                raise CognitoAuthError("No IdToken in refresh response")
            
            self._save_cache()
            logger.info("Token refresh successful")
            
        except Exception:
            # Refresh failed, do full auth
            logger.warning("Token refresh failed, doing full auth")
            self._authenticate()
    
    def _ensure_authenticated(self):
        """Ensure we have a valid auth token."""
        if not self.id_token or not self.token_expiry:
            self._authenticate()
            return
        
        # Check if token is expired (with 5min buffer)
        now = datetime.now(timezone.utc)
        buffer = 300  # 5 minutes
        if self.token_expiry.timestamp() - now.timestamp() < buffer:
            self._refresh_auth()
    
    def log_sprint(
        self,
        tasks_completed: int,
        duration_minutes: int,
        lines_of_code: int,
        note: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Log a Kevin work sprint to the Activities app.
        
        Args:
            tasks_completed: Number of tasks completed in this sprint
            duration_minutes: Duration of the sprint in minutes
            lines_of_code: Lines of code written (added/modified)
            note: Optional note about the sprint
            occurred_at: When the sprint occurred (default: now)
            
        Returns:
            API response dict
            
        Raises:
            ActivitiesAPIError: If logging fails
        """
        self._ensure_authenticated()
        
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)
        
        # Format: ISO 8601 with Z suffix
        timestamp = occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Build the occurrence payload
        # Note: This assumes the activity type "kevin-sprint" exists in the Activities app
        # and has the three measurement types configured
        payload = {
            "activityTypeName": "kevin-sprint",
            "moment": timestamp,  # kevin-sprint is a MOMENT activity (not a SPAN)
            "note": note or "",
            "measurements": [
                {
                    "typeName": "tasks_completed",
                    "count": tasks_completed
                },
                {
                    "typeName": "duration_minutes",
                    "count": duration_minutes
                },
                {
                    "typeName": "lines_of_code",
                    "count": lines_of_code
                }
            ],
            "tags": []
        }
        
        headers = {
            "Authorization": f"Bearer {self.id_token}",
            "Content-Type": "application/json",
        }
        
        url = f"{BASE_URL}/occurrences"
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            # If we get 401, try refreshing token and retry once
            if response.status_code == 401:
                logger.warning("Got 401, refreshing token and retrying...")
                self._refresh_auth()
                headers["Authorization"] = f"Bearer {self.id_token}"
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                f"Logged kevin-sprint: {tasks_completed} tasks, "
                f"{duration_minutes}min, {lines_of_code} LOC"
            )
            
            return data
            
        except Exception as e:
            raise ActivitiesAPIError(f"Failed to log sprint: {e}")


def log_current_sprint(
    tasks_completed: int = 1,
    duration_minutes: int = 60,
    lines_of_code: int = 0,
    note: Optional[str] = None
):
    """
    Convenience function to log the current autonomous sprint.
    
    Usage in autonomous sprint script:
        from activities.kevin_logger import log_current_sprint
        log_current_sprint(tasks_completed=1, duration_minutes=240, lines_of_code=500)
    """
    logger = KevinLogger()
    try:
        logger.log_sprint(
            tasks_completed=tasks_completed,
            duration_minutes=duration_minutes,
            lines_of_code=lines_of_code,
            note=note
        )
    except Exception as e:
        # Don't crash the sprint if logging fails
        logging.error(f"Failed to log sprint: {e}")


def main():
    """CLI entry point for manual testing."""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 4:
        print("Usage: python kevin_logger.py <tasks_completed> <duration_minutes> <lines_of_code> [note]")
        print("Example: python kevin_logger.py 1 240 500 'Completed ACT-M1-2'")
        sys.exit(1)
    
    tasks = int(sys.argv[1])
    duration = int(sys.argv[2])
    loc = int(sys.argv[3])
    note = sys.argv[4] if len(sys.argv) > 4 else None
    
    print(f"Logging sprint: {tasks} tasks, {duration}min, {loc} LOC")
    if note:
        print(f"Note: {note}")
    
    logger = KevinLogger()
    try:
        result = logger.log_sprint(
            tasks_completed=tasks,
            duration_minutes=duration,
            lines_of_code=loc,
            note=note
        )
        print(f"✓ Logged successfully: {result.get('id', 'unknown id')}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
