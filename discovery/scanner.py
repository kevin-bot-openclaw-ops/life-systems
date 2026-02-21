"""
Multi-source job scanner with deduplication and event publishing.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from .models import JobListing, OpportunityDiscoveredEvent
from .sources.base import JobSource


logger = logging.getLogger(__name__)


class JobScanner:
    """Orchestrates multiple job sources with deduplication."""

    def __init__(self, sources: List[JobSource], output_dir: Path):
        self.sources = sources
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Track seen listings across runs
        self.seen_file = self.output_dir / "seen_listings.json"
        self.seen_keys = self._load_seen()

    def _load_seen(self) -> set:
        """Load previously seen listing keys."""
        if self.seen_file.exists():
            with open(self.seen_file) as f:
                return set(json.load(f))
        return set()

    def _save_seen(self):
        """Save seen listing keys."""
        with open(self.seen_file, 'w') as f:
            json.dump(list(self.seen_keys), f, indent=2)

    def scan(self) -> Dict[str, any]:
        """
        Run full scan across all sources.
        
        Returns:
            Summary dict with stats and new listings
        """
        all_listings = []
        failures = []
        
        # Fetch from each source (continue on partial failures)
        for source in self.sources:
            try:
                logger.info(f"Fetching from {source.source_name}...")
                listings = source.fetch()
                all_listings.extend(listings)
                logger.info(f"✓ {source.source_name}: {len(listings)} listings")
            except Exception as e:
                logger.error(f"✗ {source.source_name} failed: {e}")
                failures.append({
                    "source": source.source_name,
                    "error": str(e),
                })
        
        # Deduplicate
        deduped = self._deduplicate(all_listings)
        
        # Filter new listings (not seen before)
        new_listings = [
            listing for listing in deduped
            if listing.dedup_key() not in self.seen_keys
        ]
        
        # Publish events for new listings
        events = []
        for listing in new_listings:
            event = OpportunityDiscoveredEvent.from_listing(listing)
            events.append(event)
            self.seen_keys.add(listing.dedup_key())
        
        # Save events to disk
        if events:
            self._publish_events(events)
        
        # Update seen keys
        self._save_seen()
        
        # Return summary
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "sources_succeeded": len(self.sources) - len(failures),
            "sources_failed": len(failures),
            "failures": failures,
            "total_fetched": len(all_listings),
            "after_dedup": len(deduped),
            "new_listings": len(new_listings),
            "events_published": len(events),
        }

    def _deduplicate(self, listings: List[JobListing]) -> List[JobListing]:
        """
        Deduplicate listings by company + role.
        Merge sources for duplicates.
        """
        dedup_map: Dict[str, JobListing] = {}
        
        for listing in listings:
            key = listing.dedup_key()
            if key in dedup_map:
                # Merge sources
                existing = dedup_map[key]
                for source in listing.sources:
                    if source not in existing.sources:
                        existing.sources.append(source)
            else:
                dedup_map[key] = listing
        
        return list(dedup_map.values())

    def _publish_events(self, events: List[OpportunityDiscoveredEvent]):
        """Publish events to output directory."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        event_file = self.output_dir / f"events_{timestamp}.jsonl"
        
        with open(event_file, 'w') as f:
            for event in events:
                # Convert to JSON-serializable dict
                event_dict = json.loads(event.model_dump_json())
                f.write(json.dumps(event_dict) + '\n')
        
        logger.info(f"Published {len(events)} events to {event_file}")
