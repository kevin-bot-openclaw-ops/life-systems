"""
Recommendations Engine CLI

Standalone script to test the recommendation engine.

Usage:
    python -m synthesis.main list              # List top 5 recommendations
    python -m synthesis.main list --limit 10   # List top 10
    python -m synthesis.main list --domain dating  # Filter by domain
    python -m synthesis.main decide R-DATE-01 accept  # Accept a recommendation
"""

import argparse
import json
import logging
from pathlib import Path

from synthesis.recommendation_engine import RecommendationEngine

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def list_recommendations(db_path: str, limit: int, domain: str = None):
    """List top recommendations."""
    engine = RecommendationEngine(db_path)
    
    recommendations = engine.get_top_recommendations(
        limit=limit,
        domain=domain,
        include_cross_domain_context=True
    )
    
    if not recommendations:
        print("No recommendations available.")
        print("This could mean:")
        print("  - Insufficient data (need dates, jobs, activities)")
        print("  - All recommendations have been dismissed")
        print("  - All recommendations are currently snoozed")
        return
    
    print(f"\nTop {len(recommendations)} Recommendations:\n")
    print("=" * 80)
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['rule_id']}] {rec['domain'].upper()}")
        print(f"   Goal: {rec['goal_alignment']}")
        print(f"   Priority: {rec['priority_score']:.1f}")
        print(f"\n   {rec['one_liner']}")
        
        if rec.get('data_table'):
            print(f"\n   Data:")
            for row in rec['data_table'][:5]:  # Show first 5 rows
                print(f"     {json.dumps(row)}")
        
        if rec.get('cross_domain_context'):
            ctx = rec['cross_domain_context']
            print(f"\n   Context:")
            print(f"     Health Score: {ctx.get('health_score', 'N/A')}")
            print(f"     Stress Level: {ctx.get('stress_level', 'N/A')}")
            print(f"     Exercise Streak: {ctx.get('exercise_streak', 0)} days")
        
        print(f"\n   Actions: Accept | Snooze 4h | Dismiss")
        print("=" * 80)


def decide_recommendation(db_path: str, rule_id: str, action: str):
    """Record a decision on a recommendation."""
    if action not in ['accept', 'snooze', 'dismiss']:
        print(f"Error: Invalid action '{action}'. Must be accept/snooze/dismiss")
        return
    
    engine = RecommendationEngine(db_path)
    
    # Get all recommendations to find the one matching rule_id
    recommendations = engine.get_top_recommendations(limit=50)
    
    recommendation = None
    for rec in recommendations:
        if rec['rule_id'] == rule_id:
            recommendation = rec
            break
    
    if not recommendation:
        print(f"Error: Recommendation {rule_id} not found or already processed")
        return
    
    # Record decision
    result = engine.record_decision(rule_id, action, recommendation)
    
    print(f"\n✓ Decision recorded: {action}")
    print(f"  Rule ID: {result['rule_id']}")
    
    if result.get('snooze_until'):
        print(f"  Snoozed until: {result['snooze_until']}")
    
    if result.get('activity_logged'):
        print(f"  ✓ Activity logged to Activities API")
        if result.get('activity_result'):
            print(f"    Activity ID: {result['activity_result'].get('id')}")
    
    print()


def show_history(db_path: str, limit: int, action_filter: str = None):
    """Show recommendation decision history."""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT rule_id, domain, action, decided_at, one_liner
            FROM recommendation_decisions
            {where_clause}
            ORDER BY decided_at DESC
            LIMIT ?
        """
        
        params = []
        where_clause = ""
        
        if action_filter:
            where_clause = "WHERE action = ?"
            params.append(action_filter)
        
        params.append(limit)
        
        cursor.execute(query.format(where_clause=where_clause), params)
        rows = cursor.fetchall()
        
        if not rows:
            print("No decision history found.")
            return
        
        print(f"\nDecision History ({len(rows)} items):\n")
        print("=" * 80)
        
        for row in rows:
            print(f"\n[{row['rule_id']}] {row['domain'].upper()} - {row['action'].upper()}")
            print(f"  {row['one_liner'][:100]}")
            print(f"  Decided: {row['decided_at']}")
        
        print("=" * 80)
    
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Life Systems Recommendation Engine CLI")
    parser.add_argument('--db', default='life.db', help='Path to database (default: life.db)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List top recommendations')
    list_parser.add_argument('--limit', type=int, default=5, help='Max recommendations')
    list_parser.add_argument('--domain', choices=['dating', 'career', 'location', 'activities'], 
                            help='Filter by domain')
    
    # Decide command
    decide_parser = subparsers.add_parser('decide', help='Record a decision on a recommendation')
    decide_parser.add_argument('rule_id', help='Rule ID (e.g., R-DATE-01)')
    decide_parser.add_argument('action', choices=['accept', 'snooze', 'dismiss'], help='Action to take')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show decision history')
    history_parser.add_argument('--limit', type=int, default=20, help='Max history items')
    history_parser.add_argument('--action', choices=['accept', 'snooze', 'dismiss'], 
                               help='Filter by action')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'list':
        list_recommendations(args.db, args.limit, args.domain)
    elif args.command == 'decide':
        decide_recommendation(args.db, args.rule_id, args.action)
    elif args.command == 'history':
        show_history(args.db, args.limit, args.action)


if __name__ == '__main__':
    main()
