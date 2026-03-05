#!/usr/bin/env python3
"""Quick test for dashboard location section."""

import sys
from pathlib import Path

# Add database directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.dashboard_v2 import get_dashboard_view_model
import json

if __name__ == "__main__":
    try:
        dashboard = get_dashboard_view_model()
        
        # Check if location section exists
        if "location" not in dashboard:
            print("❌ ERROR: location section missing from dashboard")
            sys.exit(1)
        
        location = dashboard["location"]
        
        # Validate required fields
        required = ["goal", "one_liner", "data_table", "actions", "empty_state", "days_until_deadline"]
        missing = [field for field in required if field not in location]
        
        if missing:
            print(f"❌ ERROR: Missing fields in location section: {missing}")
            sys.exit(1)
        
        print("✅ Location section structure valid")
        print(f"\n📍 {location['goal']}")
        print(f"💡 {location['one_liner']}")
        print(f"📊 Data table: {len(location['data_table'])} cities")
        print(f"⏰ Days until deadline: {location['days_until_deadline']}")
        print(f"🎯 Empty state: {location['empty_state']}")
        
        # Pretty print full response
        print("\n" + "="*80)
        print("Full location section:")
        print(json.dumps(location, indent=2))
        
        print("\n✅ DASH-M1-2 test passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
