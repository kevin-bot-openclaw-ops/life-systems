"""
Life Systems Intelligence Layer (Synthesis Module)

Three-layer architecture per ADR-001:
1. Rules Engine (free, real-time) - handles 90%+ of daily interactions
2. Weekly AI Analysis (paid, scheduled) - strategic synthesis
3. Life Move AI (paid, on-demand) - major life decisions

This module provides the Rules Engine and formatter utilities.
AI layers will be implemented in SYNTH-M1-1 and SYNTH-M2-1.
"""

from synthesis.rules.engine import RulesEngine

__all__ = ['RulesEngine']
