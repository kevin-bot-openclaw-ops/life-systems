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
    
    scanner = JobScanner(sources=sources)
    scorer = JobScorer()
    
    # Run scan
    listings = scanner.scan()
    
    results = []
    for listing in listings:
        # Create job ID
        job_id = create_job_id(listing.get('title', ''), listing.get('company', ''))
        
        # Score the job
        score_result = scorer.score(listing)
        
        # Only save jobs that pass filters
        if score_result.get('passed', False):
            job_data = {
                'id': job_id,
                'title': listing.get('title', 'Unknown'),
                'company': listing.get('company', 'Unknown'),
                'location': listing.get('location', 'Remote'),
                'remote': listing.get('remote', True),
                'description': listing.get('description', ''),
                'salary_min': listing.get('salary_min'),
                'salary_max': listing.get('salary_max'),
                'currency': listing.get('currency', 'EUR'),
                'tech_stack': listing.get('tech_stack', []),
                'url': listing.get('url', ''),
                'sources': listing.get('sources', [])
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
