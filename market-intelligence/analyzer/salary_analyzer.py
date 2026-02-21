"""
Salary Analyzer — Role-based Salary Range Analysis

Analyzes salary distributions by role type.
Provides percentiles, medians, and sample sizes.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import statistics


@dataclass
class SalaryRange:
    """Salary distribution for a role type."""
    role_type: str
    sample_size: int
    min_usd: Optional[float]
    median_usd: Optional[float]
    max_usd: Optional[float]
    q1_usd: Optional[float]  # 25th percentile
    q3_usd: Optional[float]  # 75th percentile
    avg_usd: Optional[float]


class SalaryAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.target_roles = config.get('jurek_profile', {}).get('target_roles', [])
        
        # Role classification patterns
        self.role_patterns = {
            'AI Engineer': ['ai engineer', 'artificial intelligence engineer'],
            'ML Engineer': ['ml engineer', 'machine learning engineer', 'mle'],
            'AI Platform Engineer': ['ai platform', 'ml platform', 'mlops'],
            'Agent Systems Engineer': ['agent', 'agentic', 'multi-agent'],
            'LLM Engineer': ['llm engineer', 'large language model']
        }
    
    def analyze(self, listings: List[Dict]) -> List[SalaryRange]:
        """
        Analyze salary ranges by role type.
        
        Args:
            listings: List of job listings (OpportunityDiscovered events)
        
        Returns:
            List of SalaryRange objects for each role type
        """
        # Group listings by role type
        role_salaries = {role: [] for role in self.target_roles}
        
        for listing in listings:
            role_title = listing.get('role', '').lower()
            salary = self._extract_salary(listing)
            
            if salary is None:
                continue
            
            # Classify role
            role_type = self._classify_role(role_title)
            if role_type and role_type in role_salaries:
                role_salaries[role_type].append(salary)
        
        # Calculate distributions
        ranges = []
        for role_type, salaries in role_salaries.items():
            if not salaries:
                continue
            
            salaries.sort()
            n = len(salaries)
            
            ranges.append(SalaryRange(
                role_type=role_type,
                sample_size=n,
                min_usd=salaries[0],
                max_usd=salaries[-1],
                median_usd=statistics.median(salaries),
                q1_usd=salaries[n // 4] if n >= 4 else None,
                q3_usd=salaries[3 * n // 4] if n >= 4 else None,
                avg_usd=statistics.mean(salaries)
            ))
        
        # Sort by sample size (most data first)
        ranges.sort(key=lambda x: x.sample_size, reverse=True)
        
        return ranges
    
    def _classify_role(self, role_title: str) -> Optional[str]:
        """
        Classify role title into target role type.
        
        Returns:
            Role type string or None
        """
        for role_type, patterns in self.role_patterns.items():
            if any(pattern in role_title for pattern in patterns):
                return role_type
        
        return None
    
    def _extract_salary(self, listing: Dict) -> Optional[float]:
        """Extract salary from listing (midpoint if range)."""
        salary_str = listing.get('salary', '')
        if not salary_str:
            return None
        
        import re
        numbers = re.findall(r'[\d,]+', salary_str)
        if not numbers:
            return None
        
        values = [int(n.replace(',', '')) for n in numbers]
        
        # Midpoint if range
        if len(values) >= 2:
            salary_val = (values[0] + values[1]) / 2
        elif len(values) == 1:
            salary_val = values[0]
        else:
            return None
        
        # Currency conversion
        if any(c in salary_str for c in ['€', 'EUR']):
            salary_val *= 1.08
        elif any(c in salary_str for c in ['£', 'GBP']):
            salary_val *= 1.26
        
        # Sanity check
        if salary_val < 30000 or salary_val > 500000:
            return None
        
        return salary_val
