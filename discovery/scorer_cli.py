"""
CLI for DISC-MVP-2: Job Scoring Engine

Usage:
    python -m discovery.scorer_cli score <events_file> [--output <output_file>]
    python -m discovery.scorer_cli config [--show|--edit]
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List

from discovery.scorer import JobScorer


def score_events(events_file: Path, output_file: Path = None, config_path: Path = None):
    """
    Score OpportunityDiscovered events and publish OpportunityScored events.
    
    Args:
        events_file: Input JSONL file with OpportunityDiscovered events
        output_file: Output JSONL file for OpportunityScored events (defaults to scored_<timestamp>.jsonl)
        config_path: Optional custom config path
    """
    if not events_file.exists():
        print(f"Error: Events file not found: {events_file}")
        return
    
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = events_file.parent / f"scored_{timestamp}.jsonl"
    
    scorer = JobScorer(config_path=config_path)
    
    # Load events
    events = []
    with open(events_file, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    print(f"Loaded {len(events)} events from {events_file}")
    
    # Score each listing
    scored_count = 0
    rejected_count = 0
    
    for event in events:
        if event.get('event_type') != 'OpportunityDiscovered':
            continue
        
        scored = scorer.score_listing(event['payload'])
        
        if scored.rejected:
            rejected_count += 1
            print(f"  REJECTED: {event['payload']['company']} - {scored.rejection_reason}")
        else:
            scored_count += 1
            print(f"  SCORED {scored.score:5.1f}: {event['payload']['company']} - {event['payload']['role']}")
        
        scorer.publish_scored_event(scored, output_file)
    
    print(f"\nResults:")
    print(f"  Scored: {scored_count}")
    print(f"  Rejected: {rejected_count}")
    print(f"  Output: {output_file}")


def show_config(config_path: Path = None):
    """Display current scoring configuration."""
    scorer = JobScorer(config_path=config_path)
    
    print("Current Scoring Configuration:\n")
    print("Weights:")
    for field, value in scorer.config.weights.model_dump().items():
        print(f"  {field:20s}: {value:.2f}")
    
    print("\nHard Filters:")
    for field, value in scorer.config.hard_filters.model_dump().items():
        print(f"  {field:20s}: {value}")
    
    print(f"\nAI/ML Keywords: {len(scorer.config.ai_ml_keywords)} keywords")
    print(f"Fintech Keywords: {len(scorer.config.fintech_keywords)} keywords")
    print(f"Target Seniority: {', '.join(scorer.config.target_seniority)}")


def main():
    parser = argparse.ArgumentParser(description='Job Scoring Engine CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Score command
    score_parser = subparsers.add_parser('score', help='Score discovered opportunities')
    score_parser.add_argument('events_file', type=Path, help='Input JSONL file with OpportunityDiscovered events')
    score_parser.add_argument('--output', '-o', type=Path, help='Output JSONL file for scored events')
    score_parser.add_argument('--config', '-c', type=Path, help='Custom config file path')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show or edit configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current config')
    config_parser.add_argument('--edit', action='store_true', help='Open config file in editor')
    config_parser.add_argument('--config', '-c', type=Path, help='Custom config file path')
    
    args = parser.parse_args()
    
    if args.command == 'score':
        score_events(args.events_file, args.output, args.config)
    
    elif args.command == 'config':
        if args.show or not args.edit:
            show_config(args.config)
        if args.edit:
            config_path = args.config or Path(__file__).parent / "scorer_config.yaml"
            import subprocess
            subprocess.run(['$EDITOR', str(config_path)] if '$EDITOR' in os.environ else ['nano', str(config_path)])
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
