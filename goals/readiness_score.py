"""
GOAL1-02: Attractiveness State Engine (Daily Readiness Score)

Computes daily testosterone/attractiveness optimization score from
behavioral data. Guides user toward high-state days for dating success.
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


# Configuration
SHARE_TOKEN = "a50ea3e50186487ca3ad094bc3e177ac"  # Working token
BASE_URL = "https://xznxeho9da.execute-api.eu-central-1.amazonaws.com"

# Score components (max 7.0)
SCORING_RULES = {
    'resistance_training': {
        'types': ['gym'],
        'points': 2.0,
        'criteria': 'today or yesterday',
        'priority': 1
    },
    'sun_exposure': {
        'types': ['sun-exposure'],
        'points': 1.5,
        'criteria': '≥15 min today',
        'min_duration': 15,
        'priority': 2
    },
    'sleep': {
        'types': ['sleep'],
        'points': 1.5,
        'criteria': '≥7h (6h=half, <5h=0)',
        'thresholds': {'full': 420, 'half': 360, 'none': 300},  # minutes
        'priority': 3
    },
    'cold_heat_stress': {
        'types': ['sauna', 'nerve-stimulus', 'cold-exposure'],
        'points': 1.0,
        'criteria': 'any in last 48h',
        'priority': 4
    },
    'low_cortisol': {
        'types': ['coffee'],
        'points': 0.5,
        'criteria': '≤2 cups today',
        'max_count': 2,
        'priority': 5
    },
    'movement': {
        'types': ['walking', 'swimming'],
        'points': 0.5,
        'criteria': 'any today',
        'priority': 6
    }
}

# Activity inactivity penalty
INACTIVITY_PENALTY = -1.0
INACTIVITY_HOURS = 3  # If no activity logs in last 3h AND no gym/walking/swimming


class ReadinessScoreEngine:
    """Computes daily attractiveness/readiness score."""
    
    def __init__(self, share_token: str = SHARE_TOKEN):
        self.share_token = share_token
        self.base_url = BASE_URL
    
    def fetch_daily_stats(self, from_date: str, to_date: str, types: List[str]) -> Dict:
        """
        Fetch daily aggregated stats from Activities API.
        
        Args:
            from_date: ISO date string (YYYY-MM-DD)
            to_date: ISO date string (YYYY-MM-DD)
            types: List of activity type names
            
        Returns:
            Dict with daily stats
        """
        types_param = ','.join(types)
        url = f"{self.base_url}/shared/{self.share_token}/stats/daily?from={from_date}&to={to_date}&types={types_param}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def fetch_meta(self, lookback_days: int = 1) -> Dict:
        """Fetch meta to check last activity time (for inactivity penalty)."""
        url = f"{self.base_url}/shared/{self.share_token}/meta?lookbackDays={lookback_days}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def compute_score(self, date: Optional[str] = None) -> Dict:
        """
        Compute readiness score for a given date.
        
        Args:
            date: ISO date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dict with score, breakdown, and recommendations
        """
        if date is None:
            date = datetime.now(timezone.utc).date().isoformat()
        
        # Fetch data for today and yesterday (for resistance training rule)
        today = datetime.fromisoformat(date).date()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        
        # Collect all activity types we care about
        all_types = set()
        for rule in SCORING_RULES.values():
            all_types.update(rule['types'])
        
        # Fetch stats for last 3 days (covers 48h lookback)
        stats = self.fetch_daily_stats(
            from_date=two_days_ago.isoformat(),
            to_date=today.isoformat(),
            types=list(all_types)
        )
        
        # Parse stats by day
        stats_by_day = {day['date']: day['types'] for day in stats['days']}
        
        today_stats = stats_by_day.get(today.isoformat(), {})
        yesterday_stats = stats_by_day.get(yesterday.isoformat(), {})
        two_days_ago_stats = stats_by_day.get(two_days_ago.isoformat(), {})
        
        # Compute score components
        breakdown = []
        total_score = 0.0
        missing_actions = []
        
        # 1. Resistance training (gym today or yesterday)
        gym_today = today_stats.get('gym', {}).get('count', 0)
        gym_yesterday = yesterday_stats.get('gym', {}).get('count', 0)
        
        if gym_today > 0 or gym_yesterday > 0:
            total_score += 2.0
            breakdown.append({
                'component': 'Resistance Training',
                'points': 2.0,
                'earned': 2.0,
                'status': 'complete',
                'detail': f"Gym: {gym_today + gym_yesterday}x in last 2 days"
            })
        else:
            breakdown.append({
                'component': 'Resistance Training',
                'points': 2.0,
                'earned': 0.0,
                'status': 'missing',
                'detail': 'No gym session in last 48h'
            })
            missing_actions.append({'action': 'Gym session (heavy weights)', 'points': 2.0, 'priority': 1})
        
        # 2. Sun exposure (≥15 min today)
        sun_today = today_stats.get('sun-exposure', {})
        sun_duration = sun_today.get('totalDurationMin', 0) or 0
        
        if sun_duration >= 15:
            total_score += 1.5
            breakdown.append({
                'component': 'Sun Exposure',
                'points': 1.5,
                'earned': 1.5,
                'status': 'complete',
                'detail': f"{sun_duration} min today"
            })
        else:
            breakdown.append({
                'component': 'Sun Exposure',
                'points': 1.5,
                'earned': 0.0,
                'status': 'missing',
                'detail': f"Only {sun_duration} min (need 15+)"
            })
            missing_actions.append({'action': 'Sun exposure 20+ min (shirtless)', 'points': 1.5, 'priority': 2})
        
        # 3. Sleep (≥7h = full, 6h = half, <5h = 0)
        sleep_today = today_stats.get('sleep', {})
        sleep_duration = sleep_today.get('totalDurationMin', 0) or 0
        
        sleep_points = 0.0
        if sleep_duration >= 420:  # 7h
            sleep_points = 1.5
            sleep_detail = f"{sleep_duration/60:.1f}h (excellent)"
        elif sleep_duration >= 360:  # 6h
            sleep_points = 0.75
            sleep_detail = f"{sleep_duration/60:.1f}h (adequate)"
        else:
            sleep_detail = f"{sleep_duration/60:.1f}h (poor)" if sleep_duration > 0 else "Not logged"
        
        total_score += sleep_points
        breakdown.append({
            'component': 'Sleep Quality',
            'points': 1.5,
            'earned': sleep_points,
            'status': 'complete' if sleep_points >= 1.5 else ('partial' if sleep_points > 0 else 'missing'),
            'detail': sleep_detail
        })
        
        if sleep_points < 1.5:
            missing_actions.append({'action': 'Sleep 7-8h tonight', 'points': 1.5 - sleep_points, 'priority': 3})
        
        # 4. Cold/heat stress (sauna, nerve-stimulus, cold-exposure in last 48h)
        stress_48h = 0
        for day_stats in [today_stats, yesterday_stats, two_days_ago_stats]:
            for stress_type in ['sauna', 'nerve-stimulus', 'cold-exposure']:
                stress_48h += day_stats.get(stress_type, {}).get('count', 0)
        
        if stress_48h > 0:
            total_score += 1.0
            breakdown.append({
                'component': 'Cold/Heat Stress',
                'points': 1.0,
                'earned': 1.0,
                'status': 'complete',
                'detail': f"{stress_48h}x in last 48h"
            })
        else:
            breakdown.append({
                'component': 'Cold/Heat Stress',
                'points': 1.0,
                'earned': 0.0,
                'status': 'missing',
                'detail': 'No sauna/cold in 48h'
            })
            missing_actions.append({'action': 'Sauna or cold plunge', 'points': 1.0, 'priority': 4})
        
        # 5. Low cortisol (coffee ≤2 today)
        coffee_today = today_stats.get('coffee', {}).get('count', 0)
        
        if coffee_today <= 2:
            total_score += 0.5
            breakdown.append({
                'component': 'Low Cortisol',
                'points': 0.5,
                'earned': 0.5,
                'status': 'complete',
                'detail': f"{coffee_today} coffees today (≤2)"
            })
        else:
            breakdown.append({
                'component': 'Low Cortisol',
                'points': 0.5,
                'earned': 0.0,
                'status': 'violated',
                'detail': f"{coffee_today} coffees (>2 = high cortisol)"
            })
        
        # 6. Movement (walking or swimming today)
        walking_today = today_stats.get('walking', {}).get('count', 0)
        swimming_today = today_stats.get('swimming', {}).get('count', 0)
        
        if walking_today > 0 or swimming_today > 0:
            total_score += 0.5
            breakdown.append({
                'component': 'Movement',
                'points': 0.5,
                'earned': 0.5,
                'status': 'complete',
                'detail': f"Walking: {walking_today}x, Swimming: {swimming_today}x"
            })
        else:
            breakdown.append({
                'component': 'Movement',
                'points': 0.5,
                'earned': 0.0,
                'status': 'missing',
                'detail': 'No walking or swimming today'
            })
            missing_actions.append({'action': 'Walk 20+ min', 'points': 0.5, 'priority': 6})
        
        # 7. Inactivity penalty (check meta for last activity time)
        # TODO: Implement inactivity check via meta.lastOccurrenceAt
        # For now, skip this penalty
        
        # Round score to 1 decimal
        total_score = round(total_score, 1)
        
        # Determine color/status
        if total_score >= 5.0:
            color = 'green'
            status = 'READY'
            recommendation = "High state! Great day for swiping and dates."
        elif total_score >= 3.5:
            color = 'yellow'
            status = 'MODERATE'
            recommendation = "Decent state. Do 1-2 more actions before swiping."
        else:
            color = 'red'
            status = 'LOW'
            recommendation = "Low state. Skip dating apps today, focus on optimization."
        
        # Sort missing actions by priority
        missing_actions.sort(key=lambda x: x['priority'])
        
        return {
            'date': date,
            'score': total_score,
            'max_score': 7.0,
            'percentage': round(total_score / 7.0 * 100, 1),
            'status': status,
            'color': color,
            'recommendation': recommendation,
            'breakdown': breakdown,
            'missing_actions': missing_actions[:2],  # Top 2 priorities
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def compute_30day_trend(self) -> List[Dict]:
        """Compute readiness score for last 30 days (for trend chart)."""
        today = datetime.now(timezone.utc).date()
        scores = []
        
        # Compute in batches to reduce API calls (10 days per request)
        for batch_start in range(30, 0, -10):
            end_date = today - timedelta(days=batch_start - 10)
            start_date = today - timedelta(days=batch_start)
            
            # For simplicity, compute per-day scores
            # In production, optimize with single stats call
            for day_offset in range(batch_start, max(batch_start - 10, 0), -1):
                score_date = today - timedelta(days=day_offset)
                try:
                    day_score = self.compute_score(date=score_date.isoformat())
                    scores.append({
                        'date': score_date.isoformat(),
                        'score': day_score['score'],
                        'status': day_score['status']
                    })
                except Exception as e:
                    # Skip days with errors (likely no data)
                    print(f"Warning: Failed to compute score for {score_date}: {e}")
                    continue
        
        return scores


def main():
    """CLI entry point for testing."""
    engine = ReadinessScoreEngine()
    
    # Compute today's score
    result = engine.compute_score()
    
    import json
    print(json.dumps(result, indent=2))
    
    # Show summary
    print(f"\n{'='*60}")
    print(f"Daily Readiness Score: {result['score']}/7.0 ({result['status']})")
    print(f"Recommendation: {result['recommendation']}")
    
    if result['missing_actions']:
        print(f"\nTop priorities:")
        for i, action in enumerate(result['missing_actions'], 1):
            print(f"  {i}. {action['action']} (+{action['points']} points)")


if __name__ == '__main__':
    main()
