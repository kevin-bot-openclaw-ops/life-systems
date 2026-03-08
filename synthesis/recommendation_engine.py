"""
Unified Recommendation Engine for Life Systems

Aggregates ALL rule outputs (SYNTH + ACT) + AI analyses into a single
prioritized recommendation feed. This is the glue that makes the dashboard
a unified advisor instead of separate sections.

Per ADR-001: Combines Layer 1 (rules, $0) with Layer 2/3 (AI, $2-5).
Per LEARN-M2-1: Decision tracking + Activities API feedback loop.
"""

import sqlite3
import hashlib
import json
import logging
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from synthesis.rules.engine import RulesEngine

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Aggregates recommendations from multiple sources and prioritizes them.
    
    Sources:
    - SYNTH rules (R-DATE-*, R-CAREER-*, R-LOC-*)
    - ACT rules (R-ACT-*)
    - Weekly AI analyses (future)
    - Life Move AI analyses (future)
    
    Prioritization:
    1. Goal alignment (GOAL-1 > GOAL-2 > GOAL-3)
    2. Time sensitivity (deadlines, streaks at risk)
    3. Confidence (rule-based > AI-based > speculative)
    
    Decision tracking:
    - Accept → Log to Activities API (close the loop)
    - Snooze → Reappear after configured delay (default 4h)
    - Dismiss → Don't show again for same data pattern
    
    Example:
        engine = RecommendationEngine("life.db")
        recommendations = engine.get_top_recommendations(limit=5)
        for rec in recommendations:
            print(rec['one_liner'])
    """
    
    GOAL_PRIORITY = {
        'GOAL-1': 1,  # Find partner
        'GOAL-2': 2,  # AI career
        'GOAL-3': 3,  # Location decision
        'Health': 4,  # Supporting goal (all other goals)
    }
    
    def __init__(self, db_path: str, activities_token: Optional[str] = None):
        """
        Initialize recommendation engine.
        
        Args:
            db_path: Path to SQLite database
            activities_token: JWT token for Activities API (for accept actions)
        """
        self.db_path = db_path
        self.activities_token = activities_token
        self.rules_engine = RulesEngine(db_path)
        logger.info(f"Initialized RecommendationEngine with db={db_path}")
    
    def get_top_recommendations(
        self, 
        limit: int = 5, 
        domain: Optional[str] = None,
        include_cross_domain_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get top N prioritized recommendations.
        
        Args:
            limit: Max number of recommendations to return
            domain: Optional filter ('dating', 'career', 'location', None=all)
            include_cross_domain_context: Add health/stress context to recommendations
        
        Returns:
            List of recommendations, each with:
            {
                "rule_id": "R-DATE-01",
                "domain": "dating",
                "one_liner": "Thursday bachata is your best bet...",
                "data_table": [...],
                "goal_alignment": "GOAL-1 (find partner)",
                "priority_score": 95,
                "cross_domain_context": {"health_score": 7, "stress_level": "low"},
                "actions": [
                    {"label": "Accept + Log", "type": "accept"},
                    {"label": "Snooze 4h", "type": "snooze"},
                    {"label": "Dismiss", "type": "dismiss"}
                ]
            }
        """
        # 1. Collect all rule outputs
        all_recommendations = self.rules_engine.run_rules(domain=domain)
        
        # 2. Filter out dismissed recommendations
        all_recommendations = self._filter_dismissed(all_recommendations)
        
        # 3. Filter out snoozed recommendations (not yet due)
        all_recommendations = self._filter_snoozed(all_recommendations)
        
        # 4. Add cross-domain context if requested
        if include_cross_domain_context:
            cross_domain_ctx = self._get_cross_domain_context()
            for rec in all_recommendations:
                rec['cross_domain_context'] = cross_domain_ctx
        
        # 5. Calculate priority scores
        for rec in all_recommendations:
            rec['priority_score'] = self._calculate_priority(rec)
        
        # 6. Sort by priority score (descending)
        all_recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # 7. Add standard actions to each recommendation
        for rec in all_recommendations:
            rec['actions'] = [
                {"label": "Accept + Log", "type": "accept"},
                {"label": "Snooze 4h", "type": "snooze"},
                {"label": "Dismiss", "type": "dismiss"}
            ]
        
        # 8. Return top N
        top_recommendations = all_recommendations[:limit]
        logger.info(f"Returning {len(top_recommendations)}/{len(all_recommendations)} recommendations")
        
        return top_recommendations
    
    def record_decision(
        self, 
        rule_id: str, 
        action: str, 
        recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record a decision on a recommendation.
        
        Args:
            rule_id: Rule ID from recommendation
            action: 'accept', 'snooze', or 'dismiss'
            recommendation: Full recommendation dict (for logging context)
        
        Returns:
            Result dict with status and any logged activity
        """
        if action not in ['accept', 'snooze', 'dismiss']:
            raise ValueError(f"Invalid action: {action}. Must be accept/snooze/dismiss")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Calculate pattern hash for deduplication
            pattern_hash = self._compute_pattern_hash(recommendation)
            
            # Calculate snooze_until if snoozed (default 4h)
            snooze_until = None
            if action == 'snooze':
                snooze_until = (datetime.utcnow() + timedelta(hours=4)).isoformat() + 'Z'
            
            # Insert decision
            cursor.execute("""
                INSERT INTO recommendation_decisions
                (rule_id, domain, one_liner, data_table, goal_alignment, action, 
                 decided_at, snooze_until, pattern_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule_id,
                recommendation.get('domain'),
                recommendation.get('one_liner'),
                json.dumps(recommendation.get('data_table', [])),
                recommendation.get('goal_alignment'),
                action,
                datetime.utcnow().isoformat() + 'Z',
                snooze_until,
                pattern_hash
            ))
            
            conn.commit()
            logger.info(f"Recorded {action} decision for rule {rule_id}")
            
            # If accepted, log to Activities API
            activity_result = None
            if action == 'accept':
                activity_result = self._log_to_activities(recommendation)
            
            return {
                "status": "success",
                "action": action,
                "rule_id": rule_id,
                "snooze_until": snooze_until,
                "activity_logged": activity_result is not None,
                "activity_result": activity_result
            }
        
        finally:
            conn.close()
    
    def _filter_dismissed(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Remove recommendations that have been dismissed for this data pattern.
        
        Dismissed recommendations have a pattern_hash that matches current data.
        If the data changes significantly, they can reappear.
        """
        if not recommendations:
            return recommendations
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all dismissed pattern hashes
            cursor.execute("""
                SELECT DISTINCT pattern_hash
                FROM recommendation_decisions
                WHERE action = 'dismiss'
            """)
            
            dismissed_hashes = set(row[0] for row in cursor.fetchall())
            
            # Filter out recommendations matching dismissed patterns
            filtered = []
            for rec in recommendations:
                pattern_hash = self._compute_pattern_hash(rec)
                if pattern_hash not in dismissed_hashes:
                    filtered.append(rec)
                else:
                    logger.debug(f"Filtered dismissed recommendation: {rec['rule_id']}")
            
            return filtered
        
        finally:
            conn.close()
    
    def _filter_snoozed(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Remove recommendations that are currently snoozed.
        
        Snoozed recommendations reappear after snooze_until time has passed.
        """
        if not recommendations:
            return recommendations
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            # Get snoozed rule IDs that are still active (not yet due)
            cursor.execute("""
                SELECT DISTINCT rule_id
                FROM recommendation_decisions
                WHERE action = 'snooze'
                  AND snooze_until > ?
                ORDER BY decided_at DESC
            """, (now,))
            
            snoozed_rule_ids = set(row[0] for row in cursor.fetchall())
            
            # Filter out snoozed recommendations
            filtered = []
            for rec in recommendations:
                if rec['rule_id'] not in snoozed_rule_ids:
                    filtered.append(rec)
                else:
                    logger.debug(f"Filtered snoozed recommendation: {rec['rule_id']}")
            
            return filtered
        
        finally:
            conn.close()
    
    def _get_cross_domain_context(self) -> Dict[str, Any]:
        """
        Fetch cross-domain context (health score, stress level, etc.)
        to enrich recommendations.
        
        Example: Dating advice considers today's T-optimization score.
                 Career advice considers stress level.
        
        Returns:
            {
                "health_score": 7.0,  # 0-10 T-optimization score
                "stress_level": "low",  # low/medium/high
                "exercise_streak": 3,
                "last_activity_hours_ago": 2
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            context = {}
            
            # Health score (T-optimization from ACT-MVP-2)
            # Score calculation: sun + gym + walk/yoga + no-coffee + sauna/swim
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN activity_type = 'sun-exposure' THEN 2 ELSE 0 END) +
                    SUM(CASE WHEN activity_type = 'gym' THEN 2 ELSE 0 END) +
                    SUM(CASE WHEN activity_type IN ('walking', 'uttanasana') THEN 1.5 ELSE 0 END) +
                    SUM(CASE WHEN activity_type = 'coffee' THEN -1 ELSE 0 END) +
                    SUM(CASE WHEN activity_type IN ('sauna', 'swimming') THEN 1 ELSE 0 END) as score
                FROM activities
                WHERE occurred_date = date('now')
            """)
            
            row = cursor.fetchone()
            context['health_score'] = min(10, max(0, row[0] if row and row[0] else 0))
            
            # Stress level
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM activities
                WHERE activity_type = 'nerve-stimulus'
                  AND occurred_date >= date('now', '-7 days')
            """)
            
            row = cursor.fetchone()
            nerve_count = row[0] if row else 0
            if nerve_count >= 4:
                context['stress_level'] = 'high'
            elif nerve_count >= 2:
                context['stress_level'] = 'medium'
            else:
                context['stress_level'] = 'low'
            
            # Exercise streak
            cursor.execute("""
                WITH RECURSIVE dates(date) AS (
                    SELECT date('now')
                    UNION ALL
                    SELECT date(date, '-1 day')
                    FROM dates
                    WHERE date > date('now', '-30 days')
                ),
                daily_exercise AS (
                    SELECT DISTINCT occurred_date
                    FROM activities
                    WHERE activity_type IN ('gym', 'walking', 'uttanasana', 'swimming')
                      AND occurred_date >= date('now', '-30 days')
                )
                SELECT COUNT(*) as streak
                FROM dates d
                WHERE d.date IN (SELECT occurred_date FROM daily_exercise)
                  AND d.date >= date('now', '-7 days')
            """)
            
            row = cursor.fetchone()
            context['exercise_streak'] = row[0] if row else 0
            
            # Last activity logged (hours ago)
            cursor.execute("""
                SELECT MAX(fetched_at) as last_activity
                FROM activities
            """)
            
            row = cursor.fetchone()
            if row and row[0]:
                last_activity = datetime.fromisoformat(row[0].replace('Z', ''))
                hours_ago = (datetime.utcnow() - last_activity).total_seconds() / 3600
                context['last_activity_hours_ago'] = round(hours_ago, 1)
            else:
                context['last_activity_hours_ago'] = None
            
            return context
        
        finally:
            conn.close()
    
    def _calculate_priority(self, recommendation: Dict) -> float:
        """
        Calculate priority score for a recommendation.
        
        Priority factors:
        1. Goal alignment (GOAL-1=100, GOAL-2=90, GOAL-3=80, Health=70)
        2. Time sensitivity (+10 if deadline-related, +5 if streak at risk)
        3. Confidence (+10 for rule-based, +5 for AI-based)
        4. Cross-domain context (+5 if health score <5, career rec gets +5)
        
        Returns:
            Priority score (0-120)
        """
        score = 0.0
        
        # 1. Goal alignment (base score)
        goal = recommendation.get('goal_alignment', 'Health')
        # Extract goal ID (e.g., "GOAL-1 (find partner)" -> "GOAL-1")
        goal_id = goal.split()[0] if ' ' in goal else goal
        score += (110 - self.GOAL_PRIORITY.get(goal_id, 4) * 10)
        
        # 2. Time sensitivity
        one_liner = recommendation.get('one_liner', '').lower()
        if any(kw in one_liner for kw in ['deadline', 'days until', 'expires', 'tomorrow']):
            score += 10
        if any(kw in one_liner for kw in ['streak', 'broken', 'first time']):
            score += 5
        
        # 3. Confidence (rule-based is always high confidence)
        score += 10  # All recommendations from rules engine are high confidence
        
        # 4. Cross-domain context
        cross_ctx = recommendation.get('cross_domain_context', {})
        health_score = cross_ctx.get('health_score', 10)
        stress_level = cross_ctx.get('stress_level', 'low')
        
        # If health score is low, boost health-related recommendations
        if health_score < 5 and 'Health' in goal:
            score += 10
        
        # If stress is high, boost stress management recommendations
        if stress_level == 'high' and any(kw in one_liner for kw in ['stress', 'sauna', 'calm', 'nerve']):
            score += 5
        
        # Dating recommendations get boost if health score is good (attractiveness factor)
        if 'GOAL-1' in goal and health_score >= 7:
            score += 5
        
        return score
    
    def _compute_pattern_hash(self, recommendation: Dict) -> str:
        """
        Compute a hash of the recommendation's data pattern.
        
        Used for deduplication of dismissed recommendations.
        If the underlying data changes significantly, the hash changes
        and the recommendation can reappear.
        
        Hash includes: rule_id + rounded data values
        """
        hash_input = {
            'rule_id': recommendation.get('rule_id'),
            'domain': recommendation.get('domain'),
            # Round numeric values to reduce hash sensitivity
            'data_table': self._round_data_values(recommendation.get('data_table', []))
        }
        
        hash_str = json.dumps(hash_input, sort_keys=True)
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    def _round_data_values(self, data_table: List[Dict]) -> List[Dict]:
        """
        Round numeric values in data table to reduce hash sensitivity.
        
        Example: 7.3 and 7.4 both round to 7 (same pattern)
        """
        if not data_table:
            return []
        
        rounded = []
        for row in data_table:
            rounded_row = {}
            for key, val in row.items():
                if isinstance(val, float):
                    rounded_row[key] = round(val, 0)  # Round to nearest integer
                elif isinstance(val, int):
                    rounded_row[key] = val
                else:
                    rounded_row[key] = str(val)  # Convert to string for consistency
            rounded.append(rounded_row)
        
        return rounded
    
    def _log_to_activities(self, recommendation: Dict) -> Optional[Dict]:
        """
        Log an accepted recommendation to the Activities API.
        
        This closes the feedback loop: recommendation → accept → log activity → future recommendations.
        
        Args:
            recommendation: Full recommendation dict
        
        Returns:
            Activities API response or None if failed
        """
        if not self.activities_token:
            logger.warning("No Activities API token configured, skipping activity logging")
            return None
        
        # Extract action from recommendation
        # For now, we'll log a generic "recommendation-accepted" activity
        # In the future, we can map specific recommendations to specific activity types
        
        activity_type = self._map_recommendation_to_activity_type(recommendation)
        if not activity_type:
            logger.info(f"No activity type mapping for {recommendation['rule_id']}")
            return None
        
        # Build activity payload
        now = datetime.utcnow()
        payload = {
            "type": activity_type,
            "moment": now.isoformat() + 'Z',
            "note": f"Accepted recommendation: {recommendation['one_liner'][:100]}",
            "tags": ["recommendation-accepted", recommendation['rule_id']],
            "measurements": []
        }
        
        # POST to Activities API
        try:
            headers = {
                "Authorization": f"Bearer {self.activities_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com/occurrences",
                headers=headers,
                json=payload,
                timeout=5
            )
            
            response.raise_for_status()
            logger.info(f"Logged activity for accepted recommendation: {recommendation['rule_id']}")
            return response.json()
        
        except Exception as e:
            logger.error(f"Failed to log activity: {e}", exc_info=True)
            return None
    
    def _map_recommendation_to_activity_type(self, recommendation: Dict) -> Optional[str]:
        """
        Map a recommendation to an Activities API activity type.
        
        Examples:
        - R-ACT-05 "Do morning routine" → "uttanasana" + "walking"
        - R-ACT-04 "Get sun exposure" → "sun-exposure"
        - R-DATE-01 "Go to bachata" → (manual, not auto-logged)
        
        Returns:
            Activity type string or None if no mapping
        """
        rule_id = recommendation.get('rule_id', '')
        one_liner = recommendation.get('one_liner', '').lower()
        
        # Morning routine (yoga + walk)
        if 'morning routine' in one_liner or rule_id == 'R-ACT-05':
            return 'uttanasana'  # User can manually log walk separately
        
        # Sun exposure
        if 'sun' in one_liner and 'exposure' in one_liner:
            return 'sun-exposure'
        
        # Gym/exercise
        if any(kw in one_liner for kw in ['gym', 'workout', 'exercise']):
            return 'gym'
        
        # Sauna (stress management)
        if 'sauna' in one_liner or 'nerve' in one_liner:
            return 'sauna'
        
        # Swimming
        if 'swim' in one_liner:
            return 'swimming'
        
        # Dating apps (bumble, tinder)
        if 'bumble' in one_liner:
            return 'bumble'
        if 'tinder' in one_liner:
            return 'tinder'
        
        # Learning (duo-lingo)
        if 'spanish' in one_liner or 'duolingo' in one_liner:
            return 'duo-lingo'
        
        # No automatic mapping
        return None
