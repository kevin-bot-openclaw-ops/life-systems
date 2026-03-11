#!/usr/bin/env python3
"""Test advisor.html format."""

import sys
import json
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "api"))

# Mock the database dependency
class MockDB:
    pass

# Mock verify_auth
def mock_auth():
    return "testuser"

# Import after mocking
from api.main import _transform_career_to_advisor
from database.dashboard_v2 import get_dashboard_view_model

if __name__ == "__main__":
    try:
        # Get raw dashboard data
        data = get_dashboard_view_model()
        
        print("="*80)
        print("Raw dashboard data:")
        print(json.dumps(data, indent=2)[:1000])
        print("\n")
        
        # Transform career to advisor format
        career_advisor = _transform_career_to_advisor(data["career"])
        
        print("="*80)
        print("Career advisor format:")
        print(json.dumps(career_advisor, indent=2))
        print("\n")
        
        # Check location format
        print("="*80)
        print("Location advisor format:")
        print(json.dumps(data["location"], indent=2))
        print("\n")
        
        # Build full advisor response
        advisor_response = {
            "advisor": {
                "dating": {
                    "goal": "GOAL-1: Partner + Family",
                    "one_liner": "After you log your first date, I'll start tracking patterns.",
                    "data_table": [],
                    "actions": [],
                    "empty_state": True
                },
                "career": career_advisor,
                "location": data["location"],
                "recommendations": []
            },
            "timestamp": data["fetchedAt"]
        }
        
        print("="*80)
        print("Full advisor response:")
        print(json.dumps(advisor_response, indent=2))
        
        # Validate structure
        required_sections = ["dating", "career", "location"]
        for section in required_sections:
            if section not in advisor_response["advisor"]:
                print(f"❌ ERROR: Missing section: {section}")
                sys.exit(1)
            
            sec_data = advisor_response["advisor"][section]
            required_fields = ["goal", "one_liner", "data_table", "actions", "empty_state"]
            for field in required_fields:
                if field not in sec_data:
                    print(f"❌ ERROR: Missing field {field} in {section}")
                    sys.exit(1)
        
        print("\n✅ All advisor format checks passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
