"""
Demand Analyzer — Market Trend Analysis

Analyzes skill demand patterns across time:
- Demand frequency (how many jobs mention this skill)
- Salary correlation (average salary for jobs requiring this skill)
- Trend direction (growing/stable/declining)
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


@dataclass
class SkillDemand:
    """Demand metrics for a single skill."""
    skill: str
    demand_count: int
    avg_salary_usd: Optional[float]
    min_salary_usd: Optional[float]
    max_salary_usd: Optional[float]
    trend: str  # "growing", "stable", "declining", "new", "insufficient_data"
    required_pct: float
    nice_to_have_pct: float
    week_over_week_change: Optional[float]  # Percentage change vs prior period


class DemandAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.min_data_points = config.get('trend', {}).get('min_data_points', 2)
        self.significant_change_pct = config.get('trend', {}).get('significant_change_pct', 0.15)
        
        # Historical data (loaded from prior reports if available)
        self.historical_demand = {}  # skill -> list of (timestamp, count)
    
    def analyze(self, skill_stats: Dict[str, Dict], listings: List[Dict],
                period_start: datetime, period_end: datetime) -> List[SkillDemand]:
        """
        Analyze skill demand across listings.
        
        Args:
            skill_stats: Output from SkillsExtractor.aggregate()
            listings: List of job listings (OpportunityDiscovered events)
            period_start: Analysis period start
            period_end: Analysis period end
        
        Returns:
            List of SkillDemand objects sorted by demand_count desc
        """
        demands = []
        
        # Build skill -> salary map
        skill_salaries = self._extract_salary_data(skill_stats, listings)
        
        # Calculate trends
        trends = self._calculate_trends(skill_stats, period_start)
        
        for skill, stats in skill_stats.items():
            demand_count = stats['total']
            salaries = skill_salaries.get(skill, [])
            
            # Salary metrics
            avg_salary = statistics.mean(salaries) if salaries else None
            min_salary = min(salaries) if salaries else None
            max_salary = max(salaries) if salaries else None
            
            # Trend
            trend_data = trends.get(skill, {})
            trend = trend_data.get('direction', 'insufficient_data')
            wow_change = trend_data.get('week_over_week_change')
            
            demands.append(SkillDemand(
                skill=skill,
                demand_count=demand_count,
                avg_salary_usd=avg_salary,
                min_salary_usd=min_salary,
                max_salary_usd=max_salary,
                trend=trend,
                required_pct=stats.get('required_pct', 0.0),
                nice_to_have_pct=stats.get('nice_to_have_pct', 0.0),
                week_over_week_change=wow_change
            ))
        
        # Sort by demand count descending
        demands.sort(key=lambda x: x.demand_count, reverse=True)
        
        # Update historical data
        for skill, stats in skill_stats.items():
            if skill not in self.historical_demand:
                self.historical_demand[skill] = []
            self.historical_demand[skill].append((period_end, stats['total']))
        
        return demands
    
    def _extract_salary_data(self, skill_stats: Dict, listings: List[Dict]) -> Dict[str, List[float]]:
        """
        Build mapping of skill -> list of salaries for jobs requiring that skill.
        
        Returns:
            Dict[skill -> List[salary_usd]]
        """
        skill_salaries = defaultdict(list)
        
        for listing in listings:
            salary = self._extract_salary_from_listing(listing)
            if salary is None:
                continue
            
            # Check which skills this listing mentions
            tech_stack = listing.get('tech_stack', [])
            description = listing.get('description', '')
            
            # Simple approach: if skill name appears anywhere, associate salary
            for skill in skill_stats.keys():
                # Check tech_stack
                if any(skill.lower() in ts.lower() for ts in tech_stack):
                    skill_salaries[skill].append(salary)
                    continue
                
                # Check description (case-insensitive)
                if skill.lower() in description.lower():
                    skill_salaries[skill].append(salary)
        
        return dict(skill_salaries)
    
    def _extract_salary_from_listing(self, listing: Dict) -> Optional[float]:
        """
        Extract salary from listing (if available).
        
        Handles various formats:
        - Direct USD value
        - Min-max range (return midpoint)
        - EUR/GBP (convert to USD at rough rate)
        - 'k' notation (e.g., $120k)
        
        Returns:
            Salary in USD, or None
        """
        salary_str = listing.get('salary', '')
        if not salary_str:
            return None
        
        # Try to parse numbers (including 'k' notation)
        import re
        
        # Check for 'k' notation (e.g., $120k, 100k)
        has_k = 'k' in salary_str.lower()
        
        # Extract numbers (with optional decimal for k notation)
        numbers = re.findall(r'[\d,]+\.?\d*', salary_str)
        if not numbers:
            return None
        
        # Remove commas and convert to float
        values = [float(n.replace(',', '')) for n in numbers]
        
        # Apply 'k' multiplier if present
        if has_k:
            values = [v * 1000 for v in values]
        
        # If it's a range, take midpoint
        if len(values) >= 2:
            salary_val = (values[0] + values[1]) / 2
        elif len(values) == 1:
            salary_val = values[0]
        else:
            return None
        
        # Detect currency and convert to USD
        if any(c in salary_str for c in ['€', 'EUR']):
            salary_val *= 1.08  # EUR to USD rough conversion
        elif any(c in salary_str for c in ['£', 'GBP']):
            salary_val *= 1.26  # GBP to USD rough conversion
        
        # Sanity check (annual salary should be 5-6 figures)
        if salary_val < 30000 or salary_val > 500000:
            return None
        
        return salary_val
    
    def _calculate_trends(self, skill_stats: Dict, period_end: datetime) -> Dict[str, Dict]:
        """
        Calculate trend direction using historical data.
        
        Returns:
            Dict[skill -> {direction, week_over_week_change}]
        """
        trends = {}
        
        for skill, stats in skill_stats.items():
            current_count = stats['total']
            
            # Check historical data
            if skill not in self.historical_demand or len(self.historical_demand[skill]) < self.min_data_points:
                trends[skill] = {'direction': 'new' if skill not in self.historical_demand else 'insufficient_data'}
                continue
            
            # Get prior period (1 week ago)
            one_week_ago = period_end - timedelta(days=7)
            historical = self.historical_demand[skill]
            
            # Find closest prior data point
            prior_count = None
            for ts, count in reversed(historical):
                if ts <= one_week_ago:
                    prior_count = count
                    break
            
            if prior_count is None or prior_count == 0:
                trends[skill] = {'direction': 'insufficient_data'}
                continue
            
            # Calculate change
            change_pct = (current_count - prior_count) / prior_count
            
            # Determine direction
            if abs(change_pct) < self.significant_change_pct:
                direction = 'stable'
            elif change_pct > 0:
                direction = 'growing'
            else:
                direction = 'declining'
            
            trends[skill] = {
                'direction': direction,
                'week_over_week_change': change_pct
            }
        
        return trends
    
    def load_historical_data(self, path: str):
        """Load historical demand data from prior reports."""
        try:
            with open(path, 'r') as f:
                for line in f:
                    event = json.loads(line)
                    if event.get('event_type') != 'MarketReportPublished':
                        continue
                    
                    timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    top_skills = event.get('data', {}).get('top_skills', [])
                    
                    for skill_data in top_skills:
                        skill = skill_data['skill']
                        count = skill_data['demand_count']
                        
                        if skill not in self.historical_demand:
                            self.historical_demand[skill] = []
                        
                        # Avoid duplicates
                        if not any(ts == timestamp for ts, _ in self.historical_demand[skill]):
                            self.historical_demand[skill].append((timestamp, count))
        
        except FileNotFoundError:
            pass  # No historical data yet
        except Exception as e:
            print(f"Warning: Failed to load historical data: {e}")
