"""
SYNTHESIS Module - Cross-Cutting Intelligence Utilities

This module contains shared utilities used across all domain contexts (DATE, DISC, APPL, CRST, RELOC).

Components:
- formatter: Motivation-first recommendation formatting (ADR-005)
- (future) rules_engine: Deterministic pattern matching (ADR-001 Layer 1)
- (future) weekly_ai: Strategic synthesis (ADR-001 Layer 2)
- (future) life_move_ai: Major decision analysis (ADR-001 Layer 3)
"""

from .formatter import (
    # Core data structures
    Recommendation,
    ActionButton,
    EmptyState,
    GoalReference,
    
    # Formatting functions
    format_recommendation_html,
    format_recommendation_slack,
    format_empty_state_html,
    format_empty_state_slack,
    
    # Domain-specific helpers
    format_dating_recommendation,
    format_career_recommendation,
    format_location_recommendation,
    
    # Testing utilities
    create_sample_recommendation,
    create_sample_empty_state
)

__all__ = [
    # Data structures
    "Recommendation",
    "ActionButton",
    "EmptyState",
    "GoalReference",
    
    # Formatting functions
    "format_recommendation_html",
    "format_recommendation_slack",
    "format_empty_state_html",
    "format_empty_state_slack",
    
    # Domain helpers
    "format_dating_recommendation",
    "format_career_recommendation",
    "format_location_recommendation",
    
    # Testing
    "create_sample_recommendation",
    "create_sample_empty_state"
]

__version__ = "0.1.0"
__author__ = "Kevin (kevin-bot-openclaw-ops)"
__status__ = "MVP"
