"""
Rules Engine for Life Systems Intelligence Layer

Executes deterministic pattern-matching rules on personal data.
Free, real-time, transparent insights that handle 90%+ of daily interactions.

Per ADR-001: Rules layer = $0 cost, <1s execution time.
Per ADR-005: All outputs in motivation-first format (one-liner + data table + goal ref).
"""

import sqlite3
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Configurable rules engine that executes SQL-based pattern detection.
    
    Rules are defined in rules_config.yaml. Each rule:
    - Has a trigger condition (data availability check)
    - Runs a SQL query to fetch relevant data
    - Formats output using a template
    - Returns recommendation in standardized format
    
    Example:
        engine = RulesEngine("life.db")
        recommendations = engine.run_rules(domain="dating")
        for rec in recommendations:
            print(rec['one_liner'])
            print(rec['data_table'])
    """
    
    def __init__(self, db_path: str, config_path: Optional[str] = None):
        """
        Initialize rules engine.
        
        Args:
            db_path: Path to SQLite database
            config_path: Path to rules_config.yaml (defaults to same dir as this file)
        """
        self.db_path = db_path
        
        if config_path is None:
            config_path = Path(__file__).parent / "rules_config.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.rules = config['rules']
            self.empty_states = config.get('empty_states', {})
        
        logger.info(f"Loaded {len(self.rules)} rules from {config_path}")
    
    def run_rules(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute all enabled rules and return fired recommendations.
        
        Args:
            domain: Optional filter ('dating', 'career', 'location', None=all)
        
        Returns:
            List of recommendations that fired:
            [
                {
                    "rule_id": "R-DATE-01",
                    "rule_name": "Best Source by Quality",
                    "domain": "dating",
                    "one_liner": "Thursday bachata is your best bet...",
                    "data_table": [{"source": "bachata", "avg_quality": 8.2, ...}],
                    "goal_alignment": "GOAL-1 (find partner)",
                    "fired_at": "2026-03-06T09:53:00Z",
                    "empty_state": False
                },
                ...
            ]
        """
        recommendations = []
        
        for rule in self.rules:
            # Skip disabled rules
            if not rule.get('enabled', True):
                continue
            
            # Filter by domain if specified
            if domain and rule['domain'] != domain:
                continue
            
            try:
                recommendation = self._execute_rule(rule)
                if recommendation:
                    recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"Error executing rule {rule['id']}: {e}", exc_info=True)
        
        logger.info(f"Executed {len(self.rules)} rules, {len(recommendations)} fired")
        return recommendations
    
    def _execute_rule(self, rule: Dict) -> Optional[Dict[str, Any]]:
        """
        Execute a single rule.
        
        Returns:
            Recommendation dict if rule fires, None if insufficient data.
        """
        rule_id = rule['id']
        
        # Check if minimum data is available
        data_check = self._check_data_availability(rule)
        if not data_check['sufficient']:
            # Return empty state recommendation
            return self._format_empty_state(rule, data_check)
        
        # Execute the rule query
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(rule['trigger']['query'])
            rows = cursor.fetchall()
            
            if not rows or len(rows) == 0:
                return None
            
            # Convert rows to list of dicts
            data = [dict(row) for row in rows]
            
            # Format output
            return self._format_recommendation(rule, data)
        
        finally:
            conn.close()
    
    def _check_data_availability(self, rule: Dict) -> Dict[str, Any]:
        """
        Check if sufficient data exists to run this rule.
        
        Returns:
            {
                "sufficient": bool,
                "current_count": int,
                "min_required": int,
                "remaining": int
            }
        """
        rule_id = rule['id']
        min_data = rule.get('min_data_points', 1)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Domain-specific data count queries
            if rule['domain'] == 'dating':
                cursor.execute("SELECT COUNT(*) as count FROM dates")
            elif rule['domain'] == 'career':
                if 'New High-Match' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM jobs j
                        JOIN scores s ON j.id = s.job_id
                        WHERE s.composite_score >= 85
                          AND j.discovered_at >= datetime('now', '-24 hours')
                    """)
                elif 'Decision Throughput' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM decisions
                        WHERE decided_at >= datetime('now', '-7 days')
                    """)
                elif 'Skill Demand' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT date(discovered_at)) as count
                        FROM jobs
                        WHERE discovered_at >= datetime('now', '-60 days')
                    """)
                else:
                    cursor.execute("SELECT COUNT(*) as count FROM jobs")
            elif rule['domain'] == 'location':
                cursor.execute("""
                    SELECT COUNT(DISTINCT last_updated) as count
                    FROM cities
                """)
            elif rule['domain'] == 'activities':
                # Activity rules have different data requirements
                if 'Dating Pool Exhaustion' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM activities
                        WHERE activity_type IN ('bumble', 'tinder')
                          AND occurred_date >= date('now', '-14 days')
                    """)
                elif 'Stress Escalation' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM activities
                        WHERE activity_type = 'nerve-stimulus'
                          AND occurred_date >= date('now', '-14 days')
                    """)
                elif 'Exercise Consistency' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM activities
                        WHERE activity_type IN ('gym', 'walking', 'swimming', 'yoga', 'uttanasana')
                          AND occurred_date >= date('now', '-7 days')
                    """)
                elif 'Testosterone Protocol' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM activities
                        WHERE occurred_date = date('now')
                    """)
                elif 'Morning Routine' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT occurred_date) as count FROM activities
                        WHERE occurred_date >= date('now', '-7 days')
                    """)
                elif 'Dating-Activity Correlation' in rule['name']:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM dates
                        WHERE date_of >= date('now', '-90 days')
                    """)
                else:
                    cursor.execute("SELECT COUNT(*) as count FROM activities")
            else:
                return {"sufficient": True, "current_count": min_data, "min_required": min_data, "remaining": 0}
            
            result = cursor.fetchone()
            current_count = result[0] if result else 0
            
            return {
                "sufficient": current_count >= min_data,
                "current_count": current_count,
                "min_required": min_data,
                "remaining": max(0, min_data - current_count)
            }
        
        finally:
            conn.close()
    
    def _format_recommendation(self, rule: Dict, data: List[Dict]) -> Dict[str, Any]:
        """
        Format rule output into standardized recommendation format.
        
        Args:
            rule: Rule definition
            data: Query results (list of dicts)
        
        Returns:
            Formatted recommendation with one-liner + data table
        """
        rule_id = rule['id']
        output_config = rule['output']
        template = output_config['template']
        
        # Extract template variables from data
        variables = self._extract_template_variables(rule_id, data)
        
        # Format one-liner
        one_liner = template.format(**variables)
        
        # Build data table
        data_table = self._build_data_table(rule, data)
        
        return {
            "rule_id": rule_id,
            "rule_name": rule['name'],
            "domain": rule['domain'],
            "one_liner": one_liner,
            "data_table": data_table,
            "goal_alignment": output_config['goal_ref'],
            "fired_at": datetime.utcnow().isoformat() + 'Z',
            "empty_state": False
        }
    
    def _extract_template_variables(self, rule_id: str, data: List[Dict]) -> Dict[str, Any]:
        """
        Extract variables needed for template formatting from query results.
        
        This is rule-specific logic that knows how to interpret each rule's data.
        """
        variables = {}
        
        if rule_id == "R-DATE-01":
            # Best source by quality
            if len(data) >= 2:
                variables['best_source'] = data[0]['source']
                variables['best_avg'] = round(data[0]['avg_quality'], 1)
                variables['second_source'] = data[1]['source']
                variables['second_avg'] = round(data[1]['avg_quality'], 1)
            elif len(data) == 1:
                variables['best_source'] = data[0]['source']
                variables['best_avg'] = round(data[0]['avg_quality'], 1)
                variables['second_source'] = "other sources"
                variables['second_avg'] = "N/A"
        
        elif rule_id == "R-DATE-02":
            # Investment decision signal
            if len(data) >= 3:
                variables['who'] = data[0]['who']
                variables['count'] = len(data)
                qualities = [row['quality'] for row in data]
                trend_str = " → ".join(str(q) for q in qualities)
                variables['trend'] = trend_str
                
                # Determine recommendation
                if qualities[-1] >= 8 and (qualities[-1] >= qualities[-2] or qualities[-1] == qualities[-2]):
                    variables['recommendation'] = "Worth investing."
                elif qualities[-1] < 7:
                    variables['recommendation'] = "Consider moving on."
                else:
                    variables['recommendation'] = "Keep exploring."
        
        elif rule_id == "R-DATE-03":
            # Quality trend
            row = data[0]
            recent = row.get('recent_avg')
            prior = row.get('prior_avg')
            
            if recent and prior:
                delta = round(recent - prior, 1)
                if delta > 0.5:
                    variables['trend_direction'] = "trending up"
                    variables['delta'] = f"+{delta} avg"
                elif delta < -0.5:
                    variables['trend_direction'] = "trending down"
                    variables['delta'] = f"{delta} avg"
                else:
                    variables['trend_direction'] = "flat"
                    variables['delta'] = f"{delta:+.1f} avg"
            else:
                variables['trend_direction'] = "insufficient data"
                variables['delta'] = "N/A"
        
        elif rule_id == "R-DATE-04":
            # Engagement check
            row = data[0]
            days = int(row.get('days_since', 0))
            variables['days'] = days
        
        elif rule_id == "R-CAREER-01":
            # New high-match jobs
            variables['count'] = len(data)
            if data:
                top = data[0]
                variables['top_score'] = round(top['composite_score'], 0)
                variables['top_company'] = top['company']
                variables['top_salary'] = top.get('salary_range', 'Not specified')
                variables['top_location'] = top.get('location', 'Not specified')
        
        elif rule_id == "R-CAREER-02":
            # Decision throughput
            row = data[0]
            total = row.get('total', 0)
            approved = row.get('approved', 0)
            skipped = row.get('skipped', 0)
            variables['total'] = total
            variables['approved'] = approved
            variables['skipped'] = skipped
            variables['approval_rate'] = round((approved / total * 100) if total > 0 else 0, 0)
        
        elif rule_id == "R-CAREER-03":
            # Skill demand shift
            if data:
                # Find skill with biggest growth
                max_growth = None
                max_pct = 0
                for row in data:
                    current = row.get('current_count', 0)
                    prior = row.get('prior_count', 1)  # Avoid division by zero
                    pct_change = ((current - prior) / prior * 100) if prior > 0 else 0
                    if abs(pct_change) > abs(max_pct):
                        max_pct = pct_change
                        max_growth = row
                
                if max_growth:
                    variables['top_skill'] = max_growth['skill']
                    variables['trend_direction'] = "up" if max_pct > 0 else "down"
                    variables['percent_change'] = round(abs(max_pct), 0)
                    variables['source_count'] = len(data)
                    
                    if max_pct > 30:
                        variables['positioning'] = "You're early."
                    elif max_pct > 10:
                        variables['positioning'] = "Growing demand."
                    elif max_pct < -10:
                        variables['positioning'] = "Declining demand."
                    else:
                        variables['positioning'] = "Stable."
        
        elif rule_id == "R-LOC-01":
            # City ranking change
            if len(data) >= 2:
                top = data[0]
                second = data[1]
                variables['top_city'] = top['city']
                variables['current_score'] = round(top['current_score'], 1)
                variables['second_city'] = second['city']
                variables['second_score'] = round(second['current_score'], 1)
                
                # Placeholder for differentiator (would need more detailed query)
                variables['differentiator'] = "composite score"
                variables['diff_pct'] = round(abs((top['current_score'] - second['current_score']) / second['current_score'] * 100), 0)
        
        elif rule_id == "R-ACT-01":
            # Dating pool exhaustion
            if data:
                row = data[0]
                variables['app'] = row.get('app', 'dating app')
                variables['N'] = row.get('N', 0)
        
        elif rule_id == "R-ACT-02":
            # Stress escalation
            if data:
                row = data[0]
                variables['increase'] = row.get('increase', 0)
        
        elif rule_id == "R-ACT-03":
            # Exercise consistency
            if data:
                row = data[0]
                variables['N'] = row.get('N', 0)
                variables['days_ago'] = row.get('days_ago', 0)
        
        elif rule_id == "R-ACT-04":
            # Testosterone protocol score
            if data:
                row = data[0]
                variables['score'] = row.get('score', 0)
                variables['missing_items'] = row.get('missing_items', 'none')
        
        elif rule_id == "R-ACT-05":
            # Morning routine adherence
            if data:
                row = data[0]
                variables['complete_days'] = row.get('complete_days', 0)
                variables['adherence_pct'] = row.get('adherence_pct', 0)
        
        elif rule_id == "R-ACT-06":
            # Dating-activity correlation
            if data:
                row = data[0]
                # Template is hardcoded, no variables needed beyond what's in the query
                # But we'll extract them for safety
                pass
        
        return variables
    
    def _build_data_table(self, rule: Dict, data: List[Dict]) -> List[Dict[str, Any]]:
        """
        Build formatted data table from query results.
        
        Returns:
            List of dicts with standardized column names from config.
        """
        output_config = rule['output']
        columns = output_config.get('data_table_columns', [])
        headers = output_config.get('data_table_headers', [])
        
        if not columns:
            return []
        
        # Build table with renamed columns
        table = []
        for row in data[:10]:  # Max 10 rows per ADR-005
            formatted_row = {}
            for col, header in zip(columns, headers):
                value = row.get(col)
                # Format value
                if value is not None:
                    if isinstance(value, float):
                        value = round(value, 1)
                formatted_row[header] = value
            table.append(formatted_row)
        
        return table
    
    def _format_empty_state(self, rule: Dict, data_check: Dict) -> Dict[str, Any]:
        """
        Format empty state recommendation when insufficient data.
        
        Per ADR-005: "After [N] more [data_type], I'll show you [insight_type]."
        """
        rule_id = rule['id']
        template = self.empty_states.get(rule_id, "Insufficient data for {rule_name}.")
        
        message = template.format(
            remaining=data_check['remaining'],
            rule_name=rule['name']
        )
        
        return {
            "rule_id": rule_id,
            "rule_name": rule['name'],
            "domain": rule['domain'],
            "one_liner": message,
            "data_table": [],
            "goal_alignment": rule['output']['goal_ref'],
            "fired_at": datetime.utcnow().isoformat() + 'Z',
            "empty_state": True
        }


def main():
    """
    CLI entry point for rules engine.
    
    Usage:
        python -m synthesis.rules.engine [--domain dating|career|location]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Life Systems Rules Engine")
    parser.add_argument('--domain', choices=['dating', 'career', 'location'], help="Filter by domain")
    parser.add_argument('--db', default='life.db', help="Path to database")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    engine = RulesEngine(db_path=args.db)
    recommendations = engine.run_rules(domain=args.domain)
    
    print(f"\n{'='*80}")
    print(f"RULES ENGINE REPORT")
    print(f"{'='*80}\n")
    
    if not recommendations:
        print("No rules fired. Need more data or all empty states.\n")
        return
    
    for rec in recommendations:
        print(f"[{rec['rule_id']}] {rec['rule_name']}")
        print(f"Domain: {rec['domain']} | Goal: {rec['goal_alignment']}")
        print(f"\n{rec['one_liner']}\n")
        
        if rec['data_table'] and not rec['empty_state']:
            # Print table
            if rec['data_table']:
                headers = list(rec['data_table'][0].keys())
                print("  " + " | ".join(f"{h:20s}" for h in headers))
                print("  " + "-" * (len(headers) * 23))
                for row in rec['data_table']:
                    print("  " + " | ".join(f"{str(row.get(h, 'N/A')):20s}" for h in headers))
        
        print(f"\n{'-'*80}\n")


if __name__ == "__main__":
    main()
