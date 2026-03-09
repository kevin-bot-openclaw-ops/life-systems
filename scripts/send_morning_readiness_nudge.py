#!/usr/bin/env python3
"""
Morning Readiness Nudge - 8:00 AM Daily

Computes readiness score and sends Slack notification.
Part of GOAL1-02: Attractiveness State Engine.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from goals.readiness_score import ReadinessScoreEngine
from goals.morning_nudge import format_slack_nudge


SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', 'D0AFK240GBE')  # Jurek's DM


def send_slack_message(text: str) -> dict:
    """
    Send message to Slack.
    
    Args:
        text: Message text (supports Slack markdown)
        
    Returns:
        Slack API response
    """
    if not SLACK_BOT_TOKEN:
        print("WARNING: SLACK_BOT_TOKEN not set. Message not sent.")
        print(f"Would send to {SLACK_CHANNEL}:")
        print(text)
        return {'ok': False, 'error': 'no_token'}
    
    url = 'https://slack.com/api/chat.postMessage'
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    payload = {
        'channel': SLACK_CHANNEL,
        'text': text,
        'mrkdwn': True
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    return response.json()


def main():
    """Main entry point."""
    try:
        # Compute readiness score
        engine = ReadinessScoreEngine()
        score_result = engine.compute_score()
        
        # Format message
        message = format_slack_nudge(score_result)
        
        # Send to Slack
        result = send_slack_message(message)
        
        # Log result
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'score': score_result['score'],
            'status': score_result['status'],
            'slack_ok': result.get('ok', False)
        }
        
        print(json.dumps(log_data))
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        # Log error
        error_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e),
            'type': type(e).__name__
        }
        print(json.dumps(error_data), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
