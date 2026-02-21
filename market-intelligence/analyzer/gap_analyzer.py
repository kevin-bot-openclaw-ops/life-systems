"""
Gap Analyzer — Skills Gap Analysis

Compares Jurek's current skills against market demand.
Identifies:
- Strengths (skills Jurek has that are in demand)
- Gaps (high-demand skills Jurek lacks)
- Bridge skills (unique combinations that differentiate)
"""

from typing import List, Dict, Set


class GapAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.jurek_skills = set(config.get('jurek_profile', {}).get('skills', []))
    
    def analyze(self, top_skills: List[Dict], top_n: int = 10) -> Dict:
        """
        Analyze skill gaps.
        
        Args:
            top_skills: List of {skill, demand_count, ...} from DemandAnalyzer
            top_n: Consider top N skills from market
        
        Returns:
            Gap analysis dict with strengths, gaps, bridge_skills, insights
        """
        # Extract top N market skills
        market_top = [s['skill'] for s in top_skills[:top_n]]
        market_set = set(market_top)
        
        # Strengths: skills Jurek has that are in market top N
        strengths = sorted(list(self.jurek_skills & market_set))
        
        # Gaps: market top N skills Jurek doesn't have
        gaps = sorted(list(market_set - self.jurek_skills))
        
        # Bridge skills: Jurek's skills that combine domains
        bridge_skills = self._identify_bridge_skills(top_skills)
        
        # Generate insights
        insights = self._generate_insights(top_skills, strengths, gaps, bridge_skills)
        
        return {
            'jurek_skills': sorted(list(self.jurek_skills)),
            'market_top_10': market_top,
            'strengths': strengths,
            'gaps': gaps,
            'bridge_skills': bridge_skills,
            'insights': insights
        }
    
    def _identify_bridge_skills(self, top_skills: List[Dict]) -> List[str]:
        """
        Identify bridge skills that combine two domains (e.g., Java + AI).
        
        Bridge skills are unique positioning advantages.
        """
        bridge_candidates = {
            'LangChain': 'AI + Python',
            'RAG': 'AI + Information Retrieval',
            'Spring AI': 'Java + AI (rare combination)',
            'LangChain4j': 'Java + AI (rare combination)',
            'Banking Domain': 'Finance + Tech (10+ yrs)',
            'System Design': 'Enterprise Architecture',
            'Microservices': 'Distributed Systems'
        }
        
        bridge_skills = []
        for skill in self.jurek_skills:
            if skill in bridge_candidates:
                # Check if it appears in top skills (has market demand)
                if any(s['skill'] == skill for s in top_skills[:20]):
                    bridge_skills.append(skill)
        
        return sorted(bridge_skills)
    
    def _generate_insights(self, top_skills: List[Dict], strengths: List[str],
                          gaps: List[str], bridge_skills: List[str]) -> List[str]:
        """
        Generate human-readable insights about market positioning.
        
        Returns:
            List of insight strings
        """
        insights = []
        
        # Trend insights (growing skills)
        growing = [s for s in top_skills[:20] if s.get('trend') == 'growing']
        if growing:
            top_growing = growing[0]
            wow = top_growing.get('week_over_week_change', 0)
            if wow and wow > 0:
                insights.append(
                    f"{top_growing['skill']} demand up {int(wow*100)}% week-over-week — "
                    f"{'in your stack' if top_growing['skill'] in strengths else 'consider adding to portfolio'}"
                )
        
        # Salary premium insights
        skill_salaries = [(s['skill'], s.get('avg_salary_usd', 0)) for s in top_skills[:20]
                         if s.get('avg_salary_usd')]
        if len(skill_salaries) >= 2:
            skill_salaries.sort(key=lambda x: x[1], reverse=True)
            highest = skill_salaries[0]
            insights.append(
                f"{highest[0]} roles average ${int(highest[1]/1000)}k — "
                f"{'your strength' if highest[0] in strengths else 'gap to close'}"
            )
        
        # Bridge skill insights
        for bridge in bridge_skills:
            matching = [s for s in top_skills[:30] if s['skill'] == bridge]
            if matching:
                demand = matching[0]['demand_count']
                insights.append(
                    f"{bridge} mentioned in {demand} roles — unique positioning (bridge skill)"
                )
        
        # Gap prioritization
        if gaps:
            # Find gaps with highest demand
            gap_demands = [(g, next((s['demand_count'] for s in top_skills if s['skill'] == g), 0))
                          for g in gaps]
            gap_demands.sort(key=lambda x: x[1], reverse=True)
            
            if gap_demands and gap_demands[0][1] > 0:
                top_gap, count = gap_demands[0]
                insights.append(
                    f"{top_gap} is your highest-priority gap ({count} mentions in top roles)"
                )
        
        # Required vs nice-to-have insights
        high_required = [s for s in top_skills[:10] if s.get('required_pct', 0) > 0.8]
        if high_required:
            for skill_data in high_required[:2]:  # Top 2
                skill = skill_data['skill']
                req_pct = skill_data.get('required_pct', 0)
                if skill in strengths:
                    insights.append(
                        f"{skill} is hard requirement in {int(req_pct*100)}% of roles (you have this)"
                    )
                elif skill in gaps:
                    insights.append(
                        f"{skill} is hard requirement in {int(req_pct*100)}% of roles (priority gap)"
                    )
        
        return insights
