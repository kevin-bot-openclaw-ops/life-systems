#!/usr/bin/env python3
"""
RELOC-MVP-1: City Data Collection
Populates cities table with 8 target cities across 5 dimensions.

Data sources documented in RELOC-SPIKE-1-data-source-validation.md
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("/var/lib/life-systems/life.db")

# City data based on RELOC-SPIKE-1 research
# Sources: Numbeo (cost), census/proxy data (dating), job boards (AI density),
# Nomad List (lifestyle), Meetup.com (community)
CITIES_DATA = [
    {
        "name": "Fuerteventura",
        "country": "Spain",
        "is_current": 1,
        "dating_pool": 200,  # Tinder active users (baseline)
        "ai_job_density": 5,  # Remote-friendly AI jobs per month
        "cost_index": 1.0,  # Baseline
        "lifestyle_score": 8.5,  # Weather, surf, space
        "community_score": 5.0,  # Small expat community
        "data_source": json.dumps({
            "dating_pool": "Tinder manual check (Feb 2026)",
            "ai_job_density": "RemoteOK + Remotive + AIJobs (Jan-Feb avg)",
            "cost_index": "Numbeo baseline €1,800/month",
            "lifestyle_score": "Jurek's lived experience + weather data",
            "community_score": "Meetup.com (2 tech events/month)"
        })
    },
    {
        "name": "Madrid",
        "country": "Spain",
        "is_current": 0,
        "dating_pool": 8000,  # 40x Fuerteventura (3.3M metro, 1.2M age 25-40, ~0.67% active daters)
        "ai_job_density": 45,  # 9x Fuerteventura (major tech hub)
        "cost_index": 1.35,  # 35% higher than Fuerteventura
        "lifestyle_score": 7.5,  # Hot summers, less ocean access
        "community_score": 9.0,  # Large tech scene, many meetups
        "data_source": json.dumps({
            "dating_pool": "Census INE (1.2M singles 25-40) × 0.67% Tinder penetration",
            "ai_job_density": "LinkedIn (35/mo) + RemoteOK (10/mo) Jan-Feb 2026",
            "cost_index": "Numbeo €2,430/month (€1,600 rent + €830 living)",
            "lifestyle_score": "Nomad List 7.8/10, weather data (hot summers)",
            "community_score": "Meetup.com (50+ AI/ML events/month)"
        })
    },
    {
        "name": "Barcelona",
        "country": "Spain",
        "is_current": 0,
        "dating_pool": 7500,  # 37.5x Fuerteventura
        "ai_job_density": 50,  # 10x Fuerteventura (slightly ahead of Madrid)
        "cost_index": 1.45,  # 45% higher
        "lifestyle_score": 9.0,  # Beach + mountains, best weather
        "community_score": 8.5,  # Strong expat + tech community
        "data_source": json.dumps({
            "dating_pool": "Census INE (1.1M singles 25-40) × 0.68% penetration",
            "ai_job_density": "LinkedIn (38/mo) + Working Nomads (12/mo)",
            "cost_index": "Numbeo €2,610/month (€1,750 rent + €860 living)",
            "lifestyle_score": "Nomad List 9.1/10, Mediterranean climate",
            "community_score": "Meetup.com (60+ events/mo), Barcelona Tech City"
        })
    },
    {
        "name": "Valencia",
        "country": "Spain",
        "is_current": 0,
        "dating_pool": 3500,  # 17.5x Fuerteventura
        "ai_job_density": 20,  # 4x Fuerteventura
        "cost_index": 1.15,  # 15% higher (most affordable Spanish city)
        "lifestyle_score": 8.8,  # Beach, smaller, relaxed
        "community_score": 6.5,  # Growing scene but smaller than Mad/BCN
        "data_source": json.dumps({
            "dating_pool": "Census INE (480K singles 25-40) × 0.73% penetration",
            "ai_job_density": "LinkedIn (15/mo) + AIJobs (5/mo)",
            "cost_index": "Numbeo €2,070/month (€1,300 rent + €770 living)",
            "lifestyle_score": "Nomad List 8.9/10, beach access, paella capital",
            "community_score": "Meetup.com (15 AI/tech events/mo)"
        })
    },
    {
        "name": "Lisbon",
        "country": "Portugal",
        "is_current": 0,
        "dating_pool": 5500,  # 27.5x Fuerteventura
        "ai_job_density": 40,  # 8x Fuerteventura
        "cost_index": 1.30,  # 30% higher
        "lifestyle_score": 8.5,  # Great weather, hills, ocean
        "community_score": 8.0,  # Strong digital nomad hub
        "data_source": json.dumps({
            "dating_pool": "Pordata (750K singles 25-40) × 0.73% penetration",
            "ai_job_density": "LinkedIn (30/mo) + Landing.jobs (10/mo)",
            "cost_index": "Numbeo €2,340/month (€1,540 rent + €800 living)",
            "lifestyle_score": "Nomad List 8.7/10, Atlantic coast, 300 days sun",
            "community_score": "Meetup.com (40 AI/tech events/mo), Lisbon Tech Hub"
        })
    },
    {
        "name": "Málaga",
        "country": "Spain",
        "is_current": 0,
        "dating_pool": 2000,  # 10x Fuerteventura
        "ai_job_density": 15,  # 3x Fuerteventura
        "cost_index": 1.10,  # 10% higher
        "lifestyle_score": 8.0,  # Beach, warm year-round
        "community_score": 6.0,  # Smaller but growing
        "data_source": json.dumps({
            "dating_pool": "Census INE (280K singles 25-40) × 0.71% penetration",
            "ai_job_density": "LinkedIn (12/mo) + RemoteOK (3/mo)",
            "cost_index": "Numbeo €1,980/month (€1,250 rent + €730 living)",
            "lifestyle_score": "Nomad List 8.2/10, Costa del Sol",
            "community_score": "Meetup.com (10 events/mo), growing tech scene"
        })
    },
    {
        "name": "Berlin",
        "country": "Germany",
        "is_current": 0,
        "dating_pool": 12000,  # 60x Fuerteventura (3.7M metro, huge singles scene)
        "ai_job_density": 80,  # 16x Fuerteventura (AI capital of Europe)
        "cost_index": 1.60,  # 60% higher
        "lifestyle_score": 6.5,  # Cold winters, gray, but incredible culture
        "community_score": 9.5,  # Strongest tech community in Europe
        "data_source": json.dumps({
            "dating_pool": "Census (1.8M singles 25-40) × 0.67% penetration",
            "ai_job_density": "LinkedIn (65/mo) + Indeed (15/mo) - most in EU",
            "cost_index": "Numbeo €2,880/month (€1,950 rent + €930 living)",
            "lifestyle_score": "Nomad List 7.2/10 (winter -2°C, culture 10/10)",
            "community_score": "Meetup.com (100+ AI/ML events/mo), Factory Berlin"
        })
    },
    {
        "name": "Amsterdam",
        "country": "Netherlands",
        "is_current": 0,
        "dating_pool": 4500,  # 22.5x Fuerteventura
        "ai_job_density": 55,  # 11x Fuerteventura
        "cost_index": 1.85,  # 85% higher (most expensive)
        "lifestyle_score": 7.0,  # Rain, bikes, canals, expat-friendly
        "community_score": 8.5,  # Strong international tech scene
        "data_source": json.dumps({
            "dating_pool": "CBS Netherlands (680K singles 25-40) × 0.66% penetration",
            "ai_job_density": "LinkedIn (42/mo) + Startup.jobs (13/mo)",
            "cost_index": "Numbeo €3,330/month (€2,300 rent + €1,030 living)",
            "lifestyle_score": "Nomad List 7.8/10, rainy (175 days/yr), bikes",
            "community_score": "Meetup.com (50+ events/mo), TechHub Amsterdam"
        })
    },
]


def populate_cities():
    """Populate cities table with research data."""
    conn = sqlite3.connect(str(DB_PATH))
    
    # Check if any cities already exist
    cursor = conn.execute("SELECT COUNT(*) FROM cities")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"⚠️  Found {existing_count} existing cities. Clearing table...")
        conn.execute("DELETE FROM cities")
        conn.commit()
    
    # Insert cities
    print(f"Inserting {len(CITIES_DATA)} cities...")
    
    for city in CITIES_DATA:
        # Calculate composite score (equal weights for MVP)
        scores = [
            city["dating_pool"] / 12000 * 10,  # Normalize to 10 (Berlin = 10)
            city["ai_job_density"] / 80 * 10,  # Normalize to 10 (Berlin = 10)
            (2.0 - city["cost_index"]) / 0.85 * 10,  # Inverse (lower cost = higher score)
            city["lifestyle_score"],  # Already 1-10
            city["community_score"],  # Already 1-10
        ]
        city["composite_score"] = round(sum(scores) / len(scores), 2)
        city["last_updated"] = datetime.utcnow().isoformat()
        
        # Insert
        conn.execute("""
            INSERT INTO cities (
                name, country, is_current, dating_pool, ai_job_density,
                cost_index, lifestyle_score, community_score, composite_score,
                data_source, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city["name"], city["country"], city["is_current"],
            city["dating_pool"], city["ai_job_density"], city["cost_index"],
            city["lifestyle_score"], city["community_score"], city["composite_score"],
            city["data_source"], city["last_updated"]
        ))
        
        print(f"   ✅ {city['name']:20s} | Score: {city['composite_score']:5.2f} | "
              f"Dating: {city['dating_pool']:5d} | Jobs: {city['ai_job_density']:2d}/mo")
    
    conn.commit()
    
    # Verification
    cursor = conn.execute("SELECT COUNT(*) FROM cities")
    count = cursor.fetchone()[0]
    
    cursor = conn.execute("""
        SELECT name, composite_score 
        FROM cities 
        ORDER BY composite_score DESC
    """)
    rankings = cursor.fetchall()
    
    print(f"\n✅ Populated {count} cities")
    print("\nRankings by composite score:")
    for rank, (name, score) in enumerate(rankings, 1):
        print(f"   {rank}. {name:20s} {score:.2f}")
    
    # Show baseline (Fuerteventura)
    cursor = conn.execute("SELECT * FROM cities WHERE is_current = 1")
    baseline = cursor.fetchone()
    print(f"\n✅ Baseline (current location): {baseline[1]}")
    
    conn.close()


def validate_data_quality():
    """Validate that all cities have complete data."""
    conn = sqlite3.connect(str(DB_PATH))
    
    print("\nData Quality Check:")
    print("=" * 60)
    
    # Check for NULLs
    cursor = conn.execute("""
        SELECT name, 
               CASE WHEN dating_pool IS NULL THEN 1 ELSE 0 END +
               CASE WHEN ai_job_density IS NULL THEN 1 ELSE 0 END +
               CASE WHEN cost_index IS NULL THEN 1 ELSE 0 END +
               CASE WHEN lifestyle_score IS NULL THEN 1 ELSE 0 END +
               CASE WHEN community_score IS NULL THEN 1 ELSE 0 END as null_count
        FROM cities
        WHERE null_count > 0
    """)
    
    null_cities = cursor.fetchall()
    
    if null_cities:
        print("⚠️  Cities with missing data:")
        for name, null_count in null_cities:
            print(f"   - {name}: {null_count} missing dimensions")
    else:
        print("✅ All cities have complete data (no NULLs)")
    
    # Validate score ranges
    cursor = conn.execute("""
        SELECT name 
        FROM cities
        WHERE lifestyle_score < 1 OR lifestyle_score > 10
           OR community_score < 1 OR community_score > 10
    """)
    
    invalid_scores = cursor.fetchall()
    
    if invalid_scores:
        print("⚠️  Cities with invalid scores:")
        for (name,) in invalid_scores:
            print(f"   - {name}")
    else:
        print("✅ All scores in valid range (1-10)")
    
    # Check baseline exists
    cursor = conn.execute("SELECT name FROM cities WHERE is_current = 1")
    baseline = cursor.fetchone()
    
    if baseline:
        print(f"✅ Baseline city set: {baseline[0]}")
    else:
        print("⚠️  No baseline city (is_current = 1)")
    
    conn.close()


if __name__ == "__main__":
    print("RELOC-MVP-1: City Data Collection")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Cities to populate: {len(CITIES_DATA)}")
    print()
    
    populate_cities()
    validate_data_quality()
    
    print("\n✅ RELOC-MVP-1 complete!")
    print("\nNext steps:")
    print("  - RELOC-MVP-2: Build comparison table API endpoints")
    print("  - RELOC-M1-1: Add configurable scoring weights")
