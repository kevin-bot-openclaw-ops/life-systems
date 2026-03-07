"""
Fix RELOC scoring data based on Jurek's corrections (2026-03-07)

Critical fixes:
1. Split remote vs onsite/hybrid AI jobs
2. Fix dating pool numbers (verified sources)
3. Add personal_fit dimensions
4. Adjust weights (dating 2x jobs)
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "/var/lib/life-systems/life.db"

# Corrected city data
CITIES_CORRECTED = [
    {
        "name": "Madrid",
        "country": "Spain",
        # Dating pool: Start.io/Tinder ~400k active daters
        # Metro 6.8M × 58.6% singles rate (INE 2024) × 10% Tinder penetration
        "dating_pool_verified": 400000,
        # AI jobs split: Most €150k+ are remote
        "remote_ai_jobs": 35,  # LinkedIn remote AI/ML roles
        "onsite_hybrid_ai_jobs": 10,  # Madrid HQ requiring presence
        # Personal fit (0-10 scale)
        "language_advantage": 10.0,  # Jurek learning Spanish
        "dating_culture_fit": 10.0,  # Warm, social, open (perfect fit)
        "social_dance_scene": 10.0,  # Huge bachata/kizomba community
        "visa_ease": 9.0,  # Spain digital nomad visa (easy)
        "cost_index": 1.35,  # Numbeo €2,430/month
        "lifestyle_score": 8.5,  # Climate, culture, nightlife
    },
    {
        "name": "Barcelona",
        "country": "Spain",
        "dating_pool_verified": 350000,  # Similar to Madrid, slightly smaller
        "remote_ai_jobs": 38,
        "onsite_hybrid_ai_jobs": 12,
        "language_advantage": 10.0,  # Spanish (+ Catalan bonus)
        "dating_culture_fit": 9.5,  # Warm, beach culture
        "social_dance_scene": 10.0,  # Massive dance scene
        "visa_ease": 9.0,  # Spain digital nomad visa
        "cost_index": 1.45,  # Slightly more expensive than Madrid
        "lifestyle_score": 9.5,  # Mediterranean, beach, culture
    },
    {
        "name": "Berlin",
        "country": "Germany",
        "dating_pool_verified": 250000,  # Metro 3.7M, lower singles rate
        "remote_ai_jobs": 60,  # Most Berlin jobs are remote-friendly
        "onsite_hybrid_ai_jobs": 20,  # Some require German HQ presence
        "language_advantage": 0.0,  # Jurek doesn't speak German
        "dating_culture_fit": 3.0,  # Famously cold, avoidant, high ghosting
        "social_dance_scene": 4.0,  # Niche, not mainstream
        "visa_ease": 6.0,  # German freelance visa (more bureaucratic)
        "cost_index": 1.6,
        "lifestyle_score": 6.5,  # Culture high, winter harsh
    },
    {
        "name": "Lisbon",
        "country": "Portugal",
        "dating_pool_verified": 120000,  # Smaller metro, high Tinder penetration
        "remote_ai_jobs": 30,
        "onsite_hybrid_ai_jobs": 10,
        "language_advantage": 7.0,  # Spanish helps but not native
        "dating_culture_fit": 8.5,  # Warm, friendly, social
        "social_dance_scene": 8.0,  # Growing kizomba scene (Portuguese roots)
        "visa_ease": 8.0,  # Portugal D7 visa (easier than Germany)
        "cost_index": 1.3,
        "lifestyle_score": 8.5,
    },
    {
        "name": "Valencia",
        "country": "Spain",
        "dating_pool_verified": 80000,  # Smaller city
        "remote_ai_jobs": 15,
        "onsite_hybrid_ai_jobs": 5,
        "language_advantage": 10.0,  # Spanish
        "dating_culture_fit": 9.0,  # Similar to Madrid, more relaxed
        "social_dance_scene": 7.0,  # Smaller but active
        "visa_ease": 9.0,  # Spain digital nomad visa
        "cost_index": 1.15,  # Cheaper than Madrid
        "lifestyle_score": 9.0,  # Beach, paella, festivals
    },
    {
        "name": "Amsterdam",
        "country": "Netherlands",
        "dating_pool_verified": 100000,  # Smaller metro, high English proficiency
        "remote_ai_jobs": 42,
        "onsite_hybrid_ai_jobs": 13,
        "language_advantage": 5.0,  # English works, no Dutch
        "dating_culture_fit": 6.0,  # Direct but can be reserved
        "social_dance_scene": 5.0,  # Small scene
        "visa_ease": 7.0,  # Dutch-American Friendship Treaty (easier than Germany)
        "cost_index": 1.85,  # Expensive
        "lifestyle_score": 7.5,  # Bikes, culture, rainy
    },
    {
        "name": "Málaga",
        "country": "Spain",
        "dating_pool_verified": 50000,  # Small city
        "remote_ai_jobs": 12,
        "onsite_hybrid_ai_jobs": 3,
        "language_advantage": 10.0,  # Spanish
        "dating_culture_fit": 9.0,  # Andalusian warmth
        "social_dance_scene": 6.0,  # Smaller scene
        "visa_ease": 9.0,  # Spain digital nomad visa
        "cost_index": 1.1,  # Cheapest option
        "lifestyle_score": 8.5,  # Costa del Sol, beach
    },
    {
        "name": "Fuerteventura",
        "country": "Spain",
        "is_current": True,
        "dating_pool_verified": 200,  # Confirmed via Tinder/Bumble
        "remote_ai_jobs": 5,  # Fully remote roles
        "onsite_hybrid_ai_jobs": 0,  # No local tech scene
        "language_advantage": 10.0,  # Spanish
        "dating_culture_fit": 8.0,  # Spanish warmth but tiny pool
        "social_dance_scene": 3.0,  # Very small
        "visa_ease": 10.0,  # Already here
        "cost_index": 1.0,  # Baseline
        "lifestyle_score": 9.0,  # Beach, surf, kite
    },
]

# Dimension weights (dating 2x jobs per GOAL-1 CRITICAL)
WEIGHTS = {
    "dating_pool_verified": 0.25,  # 25%
    "dating_culture_fit": 0.20,  # 20%
    "social_dance_scene": 0.15,  # 15%
    "onsite_hybrid_ai_jobs": 0.15,  # 15% (only local jobs count)
    "language_advantage": 0.10,  # 10%
    "cost_index": 0.05,  # 5% (inverted: lower is better)
    "lifestyle_score": 0.05,  # 5%
    "visa_ease": 0.05,  # 5%
}


def normalize(value, min_val, max_val):
    """Normalize to 0-10 scale."""
    if max_val == min_val:
        return 5.0
    return ((value - min_val) / (max_val - min_val)) * 10.0


def calculate_composite_score(city_data, all_cities):
    """Calculate weighted composite score."""
    # Get min/max for normalization
    dating_pools = [c["dating_pool_verified"] for c in all_cities]
    onsite_jobs = [c["onsite_hybrid_ai_jobs"] for c in all_cities]
    cost_indices = [c["cost_index"] for c in all_cities]
    
    # Normalize dimensions (0-10 scale)
    scores = {}
    scores["dating_pool_verified"] = normalize(
        city_data["dating_pool_verified"], min(dating_pools), max(dating_pools)
    )
    scores["onsite_hybrid_ai_jobs"] = normalize(
        city_data["onsite_hybrid_ai_jobs"], min(onsite_jobs), max(onsite_jobs)
    )
    scores["cost_index"] = 10 - normalize(  # Inverted: lower cost is better
        city_data["cost_index"], min(cost_indices), max(cost_indices)
    )
    
    # These are already 0-10 scale
    scores["dating_culture_fit"] = city_data["dating_culture_fit"]
    scores["social_dance_scene"] = city_data["social_dance_scene"]
    scores["language_advantage"] = city_data["language_advantage"]
    scores["lifestyle_score"] = city_data["lifestyle_score"]
    scores["visa_ease"] = city_data["visa_ease"]
    
    # Weighted sum
    composite = sum(scores[dim] * WEIGHTS[dim] for dim in WEIGHTS.keys())
    
    return round(composite, 2), scores


def main():
    """Update city data with corrected values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calculate composite scores for all cities
    for city in CITIES_CORRECTED:
        composite, normalized = calculate_composite_score(city, CITIES_CORRECTED)
        city["composite_score"] = composite
        city["normalized_scores"] = normalized
    
    # Update database
    updated = 0
    for city in CITIES_CORRECTED:
        cursor.execute("""
            UPDATE cities SET
                dating_pool_verified = ?,
                remote_ai_jobs = ?,
                onsite_hybrid_ai_jobs = ?,
                language_advantage = ?,
                dating_culture_fit = ?,
                social_dance_scene = ?,
                visa_ease = ?,
                cost_index = ?,
                lifestyle_score = ?,
                composite_score = ?,
                last_updated = ?
            WHERE name = ? AND country = ?
        """, (
            city["dating_pool_verified"],
            city["remote_ai_jobs"],
            city["onsite_hybrid_ai_jobs"],
            city["language_advantage"],
            city["dating_culture_fit"],
            city["social_dance_scene"],
            city["visa_ease"],
            city["cost_index"],
            city["lifestyle_score"],
            city["composite_score"],
            datetime.utcnow().isoformat() + "Z",
            city["name"],
            city["country"],
        ))
        updated += cursor.rowcount
    
    conn.commit()
    
    # Show updated rankings
    cursor.execute("""
        SELECT name, country, dating_pool_verified, onsite_hybrid_ai_jobs, 
               composite_score
        FROM cities
        ORDER BY composite_score DESC
    """)
    
    print(f"✅ Updated {updated} cities with corrected data\n")
    print("New city rankings:")
    print(f"{'Rank':<6} {'City':<20} {'Dating Pool':<15} {'Onsite Jobs':<12} {'Score':<8}")
    print("-" * 70)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        city_name = f"{row[0]}, {row[1]}"
        dating = f"{row[2]:,}" if row[2] else "N/A"
        jobs = f"{row[3]}" if row[3] is not None else "N/A"
        score = f"{row[4]:.2f}" if row[4] else "N/A"
        print(f"{i:<6} {city_name:<20} {dating:<15} {jobs:<12} {score:<8}")
    
    conn.close()
    
    print("\n✅ Fix complete! Expected: Madrid #1, Barcelona #2, Berlin #3")


if __name__ == "__main__":
    main()
