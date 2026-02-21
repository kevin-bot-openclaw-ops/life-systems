"""Job scoring engine CLI - DISC-MVP-2."""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List
from scorer import JobScorer, ScoringWeights, OpportunityScored


def load_config(config_path: Path) -> dict:
    """Load scoring configuration from YAML."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_opportunity_events(events_dir: Path) -> List[dict]:
    """Load OpportunityDiscovered events from JSONL files."""
    events = []
    
    if not events_dir.exists():
        return events

    for events_file in sorted(events_dir.glob('events_*.jsonl')):
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if event.get('event_type') == 'OpportunityDiscovered':
                        events.append(event['payload'])
    
    return events


def save_scored_events(events: List[OpportunityScored], output_path: Path):
    """Save OpportunityScored events to JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for event in events:
            f.write(event.model_dump_json() + '\n')


def main():
    """Score all discovered job listings."""
    base_dir = Path(__file__).parent
    
    # Load config
    config = load_config(base_dir / 'config.yaml')
    weights = ScoringWeights(**config['weights'])
    salary_floor = config['filters']['salary_floor_eur']

    # Validate weights
    if not weights.validate_sum():
        print(f"ERROR: Weights don't sum to 1.0 (sum={sum([weights.remote_match, weights.ai_ml_relevance, weights.seniority_match, weights.salary_match, weights.fintech_bonus])})")
        return

    # Initialize scorer
    scorer = JobScorer(weights=weights, salary_floor=salary_floor)

    # Load opportunity events
    events_dir = base_dir.parent / 'events'
    listings = load_opportunity_events(events_dir)

    if not listings:
        print(f"No OpportunityDiscovered events found in {events_dir}")
        return

    print(f"Loaded {len(listings)} job listings from {events_dir}")

    # Score each listing
    scored_events = []
    accepted = 0
    rejected = 0

    for listing in listings:
        scored_job = scorer.score_listing(listing)
        event = scorer.publish_event(scored_job)
        scored_events.append(event)

        if scored_job.rejected:
            rejected += 1
        else:
            accepted += 1

    # Save scored events
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_path = events_dir / f'scored_{timestamp}.jsonl'
    save_scored_events(scored_events, output_path)

    # Summary
    print(f"\nScoring complete:")
    print(f"  Total listings: {len(listings)}")
    print(f"  Accepted: {accepted}")
    print(f"  Rejected: {rejected}")
    print(f"  Output: {output_path}")

    # Top 10 matches
    accepted_listings = [e for e in scored_events if not e.payload.rejected]
    top_10 = sorted(accepted_listings, key=lambda e: e.payload.score, reverse=True)[:10]

    if top_10:
        print(f"\nTop 10 matches:")
        for i, event in enumerate(top_10, 1):
            job = event.payload
            listing = next(l for l in listings if l['listing_id'] == job.listing_id)
            print(f"  {i}. {listing['company']} - {listing['role']}")
            print(f"     Score: {job.score:.1f} | Remote: {job.breakdown.remote_match:.0f} | AI/ML: {job.breakdown.ai_ml_relevance:.0f} | Seniority: {job.breakdown.seniority_match:.0f} | Salary: {job.breakdown.salary_match:.0f} | Fintech: {job.breakdown.fintech_bonus:.0f}")


if __name__ == '__main__':
    main()
