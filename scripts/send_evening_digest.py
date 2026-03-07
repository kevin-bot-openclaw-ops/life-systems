#!/usr/bin/env python3
"""
Evening Activities Digest via Slack
Sends daily activities summary to Jurek's DM.
"""

import sys
import os
from pathlib import Path
from datetime import date
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from activities.digest import DailyDigest


SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "D0AFK240GBE"  # Jurek's DM channel


def send_slack_message(text: str, token: str = SLACK_BOT_TOKEN, channel: str = SLACK_CHANNEL) -> bool:
    """
    Send message to Slack channel.
    
    Args:
        text: Message text (Slack markdown format)
        token: Slack bot token
        channel: Target channel ID
        
    Returns:
        True if successful, False otherwise
    """
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        return False
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": channel,
        "text": text,
        "mrkdwn": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data.get("ok"):
            print(f"ERROR: Slack API error: {data.get('error')}", file=sys.stderr)
            return False
        
        return True
    
    except Exception as e:
        print(f"ERROR: Failed to send Slack message: {e}", file=sys.stderr)
        return False


def main():
    """Generate and send evening digest."""
    # Generate digest for today
    digest = DailyDigest()
    target_date = date.today()
    
    try:
        one_liner, data_table, anomalies = digest.generate_digest(target_date)
        message = digest.format_for_slack(one_liner, data_table, anomalies)
        
        # Print to stdout for debugging
        print(f"=== Evening Digest for {target_date.isoformat()} ===")
        print(message)
        print("\n=== Sending to Slack ===")
        
        # Send to Slack
        success = send_slack_message(message)
        
        if success:
            print("✓ Sent successfully")
            return 0
        else:
            print("✗ Failed to send", file=sys.stderr)
            return 1
    
    except Exception as e:
        print(f"ERROR: Failed to generate digest: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
