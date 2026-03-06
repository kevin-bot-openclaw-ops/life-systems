"""
Rules Engine for Life Systems Intelligence Layer

Deterministic pattern-matching on personal data.
Free, real-time, transparent insights.

Usage:
    from synthesis.rules.engine import RulesEngine
    
    engine = RulesEngine(db_path="life.db")
    recommendations = engine.run_rules(domain="dating")
"""

from synthesis.rules.engine import RulesEngine

__all__ = ['RulesEngine']
