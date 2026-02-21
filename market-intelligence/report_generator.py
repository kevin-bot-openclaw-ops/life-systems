"""
Report Generator — Market Intelligence Report Generation

Orchestrates the full analysis pipeline:
1. Read OpportunityDiscovered events
2. Extract skills
3. Analyze demand and trends
4. Analyze salary ranges
5. Generate gap analysis
6. Publish MarketReportPublished event
"""

import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from analyzer import (
    SkillsExtractor,
    DemandAnalyzer,
    GapAnalyzer
)
from analyzer.salary_analyzer import SalaryAnalyzer


class ReportGenerator:
    def __init__(self, config_path: str = "config.yaml"):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize analyzers
        self.skills_extractor = SkillsExtractor(self.config)
        self.demand_analyzer = DemandAnalyzer(self.config)
        self.salary_analyzer = SalaryAnalyzer(self.config)
        self.gap_analyzer = GapAnalyzer(self.config)
        
        # Paths
        self.input_events_path = Path("../discovery/events/OpportunityDiscovered_v1.jsonl")
        self.output_events_path = Path("events/MarketReportPublished_v1.jsonl")
        self.historical_reports_path = Path("events/MarketReportPublished_v1.jsonl")
        
        # Ensure output directory exists
        self.output_events_path.parent.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, period_days: int = 7) -> Dict:
        """
        Generate weekly market intelligence report.
        
        Args:
            period_days: Number of days to analyze (default 7 for weekly)
        
        Returns:
            Report data dict
        """
        # Define period
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        print(f"Generating market report for {period_start.date()} to {period_end.date()}...")
        
        # Load historical data for trend analysis
        if self.historical_reports_path.exists():
            self.demand_analyzer.load_historical_data(str(self.historical_reports_path))
        
        # Load OpportunityDiscovered events
        listings = self._load_listings(period_start, period_end)
        
        print(f"Loaded {len(listings)} listings from discovery events")
        
        # Check minimum threshold
        min_listings = self.config.get('report', {}).get('min_listings_per_cycle', 100)
        if len(listings) < min_listings:
            print(f"Warning: Only {len(listings)} listings (target: {min_listings})")
        
        # Extract skills from all listings
        all_mentions = []
        for listing in listings:
            description = listing.get('description', '')
            tech_stack = listing.get('tech_stack', [])
            mentions = self.skills_extractor.extract(description, tech_stack)
            all_mentions.extend(mentions)
        
        print(f"Extracted {len(all_mentions)} skill mentions")
        
        # Aggregate skill stats
        skill_stats = self.skills_extractor.aggregate(all_mentions)
        
        # Demand analysis
        demand_results = self.demand_analyzer.analyze(
            skill_stats, listings, period_start, period_end
        )
        
        # Get top N skills
        top_n = self.config.get('report', {}).get('top_n_skills', 10)
        top_skills = demand_results[:top_n]
        
        print(f"Top {len(top_skills)} skills by demand:")
        for i, skill in enumerate(top_skills, 1):
            print(f"  {i}. {skill.skill}: {skill.demand_count} mentions, trend={skill.trend}")
        
        # Salary analysis
        salary_ranges = self.salary_analyzer.analyze(listings)
        
        # Gap analysis
        gap_analysis = self.gap_analyzer.analyze(
            [self._demand_to_dict(d) for d in demand_results],
            top_n=top_n
        )
        
        # Build report data
        report_data = {
            'event_type': 'MarketReportPublished',
            'version': 1,
            'timestamp': period_end.isoformat() + 'Z',
            'period_start': period_start.date().isoformat(),
            'period_end': period_end.date().isoformat(),
            'data': {
                'top_skills': [self._demand_to_dict(d) for d in top_skills],
                'salary_ranges': [self._salary_to_dict(s) for s in salary_ranges],
                'gap_analysis': gap_analysis,
                'insights': gap_analysis['insights'],
                'metadata': {
                    'total_listings': len(listings),
                    'unique_skills': len(skill_stats),
                    'total_skill_mentions': len(all_mentions)
                }
            }
        }
        
        return report_data
    
    def publish_report(self, report_data: Dict):
        """
        Publish report as MarketReportPublished event.
        
        Appends to JSONL event log.
        """
        with open(self.output_events_path, 'a') as f:
            f.write(json.dumps(report_data) + '\n')
        
        print(f"\n✓ Report published to {self.output_events_path}")
    
    def _load_listings(self, period_start: datetime, period_end: datetime) -> List[Dict]:
        """
        Load OpportunityDiscovered events from input path.
        
        Filters to events within the specified period.
        """
        listings = []
        
        if not self.input_events_path.exists():
            print(f"Warning: Input events file not found: {self.input_events_path}")
            return []
        
        with open(self.input_events_path, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line)
                    
                    # Parse timestamp
                    ts_str = event.get('timestamp', '')
                    if not ts_str:
                        continue
                    
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    
                    # Filter by period
                    if period_start <= ts <= period_end:
                        listings.append(event.get('data', {}))
                
                except Exception as e:
                    print(f"Warning: Failed to parse event line: {e}")
                    continue
        
        return listings
    
    def _demand_to_dict(self, demand) -> Dict:
        """Convert SkillDemand to dict."""
        return {
            'skill': demand.skill,
            'demand_count': demand.demand_count,
            'avg_salary_usd': demand.avg_salary_usd,
            'min_salary_usd': demand.min_salary_usd,
            'max_salary_usd': demand.max_salary_usd,
            'trend': demand.trend,
            'required_pct': round(demand.required_pct, 2),
            'nice_to_have_pct': round(demand.nice_to_have_pct, 2),
            'week_over_week_change': demand.week_over_week_change
        }
    
    def _salary_to_dict(self, salary_range) -> Dict:
        """Convert SalaryRange to dict."""
        return {
            'role_type': salary_range.role_type,
            'sample_size': salary_range.sample_size,
            'min_usd': salary_range.min_usd,
            'median_usd': salary_range.median_usd,
            'max_usd': salary_range.max_usd,
            'q1_usd': salary_range.q1_usd,
            'q3_usd': salary_range.q3_usd,
            'avg_usd': salary_range.avg_usd
        }
