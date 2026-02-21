"""
Main entry point for job discovery scanner.
"""
import argparse
import logging
import sys
from pathlib import Path
import yaml
from .scanner import JobScanner
from .sources import HNAlgoliaSource, WorkingNomadsSource, AIJobsUKSource


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_sources(config: dict) -> list:
    """Build enabled source instances from config."""
    source_map = {
        "hn_algolia": HNAlgoliaSource,
        "working_nomads": WorkingNomadsSource,
        "aijobs_uk": AIJobsUKSource,
    }
    
    sources = []
    for source_name, source_config in config["sources"].items():
        if source_config.get("enabled", False):
            if source_name in source_map:
                source_class = source_map[source_name]
                sources.append(source_class())
                logger.info(f"✓ Enabled source: {source_name}")
            else:
                logger.warning(f"⚠ Source '{source_name}' enabled but not implemented yet")
    
    return sources


def main():
    """Run the job scanner."""
    parser = argparse.ArgumentParser(description="Multi-source job discovery scanner")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to config.yaml"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "events",
        help="Output directory for events"
    )
    
    args = parser.parse_args()
    
    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # Build sources
    sources = build_sources(config)
    if not sources:
        logger.error("No sources enabled in config")
        sys.exit(1)
    
    logger.info(f"Starting scan with {len(sources)} sources")
    
    # Run scanner
    scanner = JobScanner(sources, args.output_dir)
    summary = scanner.scan()
    
    # Print summary
    logger.info("=" * 60)
    logger.info("SCAN COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Sources succeeded: {summary['sources_succeeded']}")
    logger.info(f"Sources failed: {summary['sources_failed']}")
    if summary['failures']:
        for failure in summary['failures']:
            logger.warning(f"  ✗ {failure['source']}: {failure['error']}")
    logger.info(f"Total fetched: {summary['total_fetched']}")
    logger.info(f"After dedup: {summary['after_dedup']}")
    logger.info(f"New listings: {summary['new_listings']}")
    logger.info(f"Events published: {summary['events_published']}")
    logger.info("=" * 60)
    
    # Exit code based on results
    if summary['sources_succeeded'] == 0:
        logger.error("All sources failed")
        sys.exit(1)
    elif summary['sources_failed'] > 0:
        logger.warning("Some sources failed but continuing")
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
