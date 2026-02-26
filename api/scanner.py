"""
Job scanner integration - uses existing discovery module.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any
import hashlib

# Add parent directory to path to import discovery module
sys.path.insert(0, str(Path(__file__).parent.parent))

from discovery.scanner import JobScanner
from discovery.scorer import JobScorer
from discovery.sources import HNAlgoliaSource, WorkingNomadsSource, AIJobsUKSource

from .database import Database


def create_job_id(title: str, company: str) -> str:
    """Create a deterministic job ID."""
    key = f"{title}:{company}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:12]


async def run_scan(db: Database) -> List[Dict[str, Any]]:
    """
    Run a complete scan cycle:
    1. Fetch jobs from all sources
    2. Score each job
    3. Save to database
    """
    # Initialize scanner with sources
    sources = [
        HNAlgoliaSource(),
        WorkingNomadsSource(),
        AIJobsUKSource()
    ]
    
    # Create output directory for scanner state
    output_dir = Path("/var/lib/life-systems/scanner")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scanner = JobScanner(sources=sources, output_dir=output_dir)
    scorer = JobScorer()
    
    # Run scan - scanner.scan() doesn't return listings, we need to fetch them directly
    # For now, let's fetch from all sources and process
    all_listings = []
    for source in sources:
        try:
            listings = source.fetch()
            all_listings.extend(listings)
        except Exception as e:
            print(f"Error fetching from {source.__class__.__name__}: {e}")
            continue
    
    results = []
    for listing in all_listings:
        # Create job ID
        job_id = create_job_id(listing.role, listing.company)
        
        # Convert JobListing to dict for scoring
        listing_dict = {
            'title': listing.role,
            'company': listing.company,
            'location': listing.location.value if hasattr(listing.location, 'value') else str(listing.location),
            'remote': listing.location.value == 'remote' if hasattr(listing.location, 'value') else True,
            'description': listing.description,
            'salary_min': listing.salary_range.min if listing.salary_range else None,
            'salary_max': listing.salary_range.max if listing.salary_range else None,
            'currency': listing.salary_range.currency.value if listing.salary_range else 'EUR',
            'tech_stack': listing.tech_stack,
            'url': listing.url,
            'sources': listing.sources,
            'seniority': listing.seniority.value if hasattr(listing.seniority, 'value') else str(listing.seniority)
        }
        
        # Score the job
        scored = scorer.score_listing(listing_dict)
        score_result = {
            'passed': not scored.rejected,
            'score': scored.score,
            'breakdown': scored.breakdown.model_dump()
        }
        
        # Only save jobs that pass filters
        if score_result.get('passed', False):
            job_data = {
                'id': job_id,
                'title': listing.role,
                'company': listing.company,
                'location': listing_dict['location'],
                'remote': listing_dict['remote'],
                'description': listing.description,
                'salary_min': listing_dict['salary_min'],
                'salary_max': listing_dict['salary_max'],
                'currency': listing_dict['currency'],
                'tech_stack': listing.tech_stack,
                'url': listing.url,
                'sources': listing.sources
            }
            
            score_data = {
                'score': score_result.get('score', 0),
                'breakdown': score_result.get('breakdown', {})
            }
            
            db.save_scan_result(job_data, score_data)
            results.append(job_data)
    
    # Record scan event
    for source in sources:
        source_name = source.__class__.__name__.replace('Source', '')
        db.record_scan(source_name, len([r for r in results if source_name in r.get('sources', [])]))
    
    return results
