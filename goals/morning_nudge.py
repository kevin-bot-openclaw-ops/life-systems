"""
GOAL1-02: Morning Slack Nudge (8:00 AM)

Proactive push notification with readiness score and missing actions.
Guides user to optimize before dating apps.
"""

import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from goals.readiness_score import ReadinessScoreEngine


def format_slack_nudge(score_result: dict) -> str:
    """
    Format readiness score as Slack message.
    
    Args:
        score_result: Result from ReadinessScoreEngine.compute_score()
        
    Returns:
        Formatted Slack message
    """
    score = score_result['score']
    max_score = score_result['max_score']
    status = score_result['status']
    color = score_result['color']
    missing = score_result['missing_actions']
    
    # Emoji by status
    emoji_map = {
        'READY': '🟢',
        'MODERATE': '🟡',
        'LOW': '🔴'
    }
    emoji = emoji_map.get(status, '⚪')
    
    # Build message
    lines = [
        f"{emoji} *Your base state today: {score}/{max_score}* ({status})",
        ""
    ]
    
    if status == 'READY':
        lines.append("✅ High state! Great day for swiping and dates.")
    elif status == 'MODERATE':
        lines.append("⚠️ Decent state. Do these before swiping:")
        for i, action in enumerate(missing, 1):
            lines.append(f"  {i}. {action['action']} (+{action['points']} points)")
    else:  # LOW
        lines.append("❌ Low state. Skip dating apps today, focus on optimization:")
        for i, action in enumerate(missing, 1):
            lines.append(f"  {i}. {action['action']} (+{action['points']} points)")
    
    lines.append("")
    lines.append(f"_Readiness score = testosterone optimization. High state = better dates._")
    
    return "\n".join(lines)


def send_morning_nudge() -> dict:
    """
    Main entry point for 8AM cron job.
    
    Computes readiness score and sends Slack notification.
    
    Returns:
        Dict with status and message
    """
    # Compute score
    engine = ReadinessScoreEngine()
    score_result = engine.compute_score()
    
    # Format message
    message = format_slack_nudge(score_result)
    
    # Send to Slack
    # TODO: Integrate with actual Slack API
    # For now, just print
    print("=" * 60)
    print("MORNING NUDGE (8:00 AM)")
    print("=" * 60)
    print(message)
    print("=" * 60)
    
    return {
        'status': 'sent',
        'score': score_result['score'],
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


def main():
    """CLI entry point for testing."""
    send_morning_nudge()


if __name__ == '__main__':
    main()
