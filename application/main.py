"""
APPL-M1-1: Application Draft Generator - CLI Entry Point

Usage:
    python -m application.main generate <scored_events.jsonl>
    python -m application.main demo
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from application.acl_opportunity_qualifier import OpportunityQualifier
from application.draft_generator import DraftGenerator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_drafts(input_path: str, output_path: str = None):
    """
    Generate drafts from OpportunityScored events.
    
    Args:
        input_path: Path to OpportunityScored events (JSONL)
        output_path: Path to write DraftGenerated events (JSONL), defaults to auto-generated
    """
    input_file = Path(input_path)
    if not input_file.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    # Auto-generate output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"application/events/drafts_{timestamp}.jsonl"
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load scored events
    scored_events = []
    with open(input_file, "r") as f:
        for line in f:
            if line.strip():
                event = json.loads(line)
                if event.get("event_type") == "OpportunityScored":
                    scored_events.append(event)
    
    logger.info(f"Loaded {len(scored_events)} OpportunityScored events from {input_path}")
    
    # Qualify candidates
    qualifier = OpportunityQualifier(score_threshold=60.0)
    candidates = qualifier.qualify_batch(scored_events)
    
    logger.info(f"Qualified {len(candidates)}/{len(scored_events)} candidates")
    
    if not candidates:
        logger.warning("No candidates qualified. Check score threshold or input data.")
        return
    
    # Generate drafts
    generator = DraftGenerator(humanize_enabled=True)
    results = generator.generate_batch(candidates)
    
    # Publish events
    for result in results:
        generator.publish_event(result, output_path)
    
    logger.info(f"Generated {len(results)} drafts")
    logger.info(f"Output written to {output_path}")
    
    # Summary statistics
    avg_words = sum(r.word_count for r in results) / len(results)
    avg_ai_score = sum(r.ai_score for r in results) / len(results)
    
    print(f"\n{'='*60}")
    print(f"DRAFT GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total qualified: {len(candidates)}")
    print(f"Drafts generated: {len(results)}")
    print(f"Average word count: {avg_words:.1f} words")
    print(f"Average AI score: {avg_ai_score:.1f}/100 (lower is better)")
    print(f"\nRole type breakdown:")
    role_counts = {}
    for r in results:
        role_counts[r.role_type] = role_counts.get(r.role_type, 0) + 1
    for role_type, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        print(f"  {role_type}: {count}")
    print(f"\nOutput: {output_path}")
    print(f"{'='*60}\n")


def demo():
    """
    Run demo with sample candidates.
    """
    logger.info("Running demo with sample candidates")
    
    # Create sample OpportunityScored events
    sample_events = [
        {
            "event_type": "OpportunityScored",
            "version": "v1",
            "timestamp": "2026-02-23T06:00:00Z",
            "context": "DISC",
            "payload": {
                "listing_id": "demo-fintech-001",
                "company": "JPMorgan Chase",
                "role": "Senior ML Engineer - Fraud Detection",
                "url": "https://example.com/job/fintech",
                "score": 88.0,
                "dimensions": {
                    "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                    "ai_ml_relevance": {"score": 80, "weight": 0.35, "reason": "3 primary + 2 secondary keywords"},
                    "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                    "salary": {"score": 100, "weight": 0.10, "reason": "160000 EUR (>= target)"},
                    "fintech_bonus": {"score": 60, "weight": 0.05, "reason": "2 fintech keywords: fraud, banking"},
                },
                "verdict": "accept",
            },
        },
        {
            "event_type": "OpportunityScored",
            "version": "v1",
            "timestamp": "2026-02-23T06:00:00Z",
            "context": "DISC",
            "payload": {
                "listing_id": "demo-research-001",
                "company": "Anthropic",
                "role": "Research Scientist - NLP",
                "url": "https://example.com/job/research",
                "score": 92.0,
                "dimensions": {
                    "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                    "ai_ml_relevance": {"score": 95, "weight": 0.35, "reason": "5 primary + 4 secondary keywords"},
                    "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                    "salary": {"score": 100, "weight": 0.10, "reason": "180000 USD (>= target)"},
                    "fintech_bonus": {"score": 0, "weight": 0.05, "reason": "No fintech signals"},
                },
                "verdict": "accept",
            },
        },
        {
            "event_type": "OpportunityScored",
            "version": "v1",
            "timestamp": "2026-02-23T06:00:00Z",
            "context": "DISC",
            "payload": {
                "listing_id": "demo-platform-001",
                "company": "Databricks",
                "role": "Senior ML Platform Engineer",
                "url": "https://example.com/job/platform",
                "score": 86.0,
                "dimensions": {
                    "remote": {"score": 100, "weight": 0.30, "reason": "Fully remote"},
                    "ai_ml_relevance": {"score": 85, "weight": 0.35, "reason": "4 primary + 3 secondary keywords"},
                    "seniority": {"score": 85, "weight": 0.20, "reason": "Seniority: senior"},
                    "salary": {"score": 100, "weight": 0.10, "reason": "170000 USD (>= target)"},
                    "fintech_bonus": {"score": 0, "weight": 0.05, "reason": "No fintech signals"},
                },
                "verdict": "accept",
            },
        },
    ]
    
    # Qualify and generate
    qualifier = OpportunityQualifier()
    candidates = qualifier.qualify_batch(sample_events)
    
    generator = DraftGenerator(humanize_enabled=True)
    results = generator.generate_batch(candidates)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"DEMO: Generated {len(results)} drafts")
    print(f"{'='*60}\n")
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Draft {i}/{len(results)} ---")
        print(f"Company: {result.company}")
        print(f"Role: {result.role}")
        print(f"Type: {result.role_type} | Words: {result.word_count} | AI Score: {result.ai_score:.1f}")
        print(f"\n{result.draft_text}\n")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="APPL-M1-1: Application Draft Generator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Generate command
    generate_parser = subparsers.add_parser(
        "generate", help="Generate drafts from OpportunityScored events"
    )
    generate_parser.add_argument(
        "input",
        help="Path to OpportunityScored events (JSONL)",
    )
    generate_parser.add_argument(
        "-o", "--output",
        help="Path to write DraftGenerated events (JSONL, auto-generated if omitted)",
        default=None,
    )
    
    # Demo command
    demo_parser = subparsers.add_parser(
        "demo", help="Run demo with sample candidates"
    )
    
    args = parser.parse_args()
    
    if args.command == "generate":
        generate_drafts(args.input, args.output)
    elif args.command == "demo":
        demo()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
