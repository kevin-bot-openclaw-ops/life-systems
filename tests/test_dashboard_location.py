"""
Tests for DASH-M1-2: Location Section in Advisor View
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.dashboard_v2 import build_location_view, get_dashboard_view_model
from database.db import get_db


def test_location_section_structure():
    """DASH-M1-2 AC-1: Location section visible on advisor view."""
    dashboard = get_dashboard_view_model()
    
    assert "location" in dashboard, "Dashboard missing location section"
    location = dashboard["location"]
    
    # Required fields per ADR-005
    assert "goal" in location
    assert "one_liner" in location
    assert "data_table" in location
    assert "actions" in location
    assert "empty_state" in location
    assert "days_until_deadline" in location
    
    print("✅ Location section has all required fields")


def test_location_one_liner():
    """DASH-M1-2 AC-2: Shows one-liner recommendation."""
    conn = get_db()
    location = build_location_view(conn)
    conn.close()
    
    assert "one_liner" in location
    assert len(location["one_liner"]) > 0
    
    # One-liner should include days until deadline
    assert "days until" in location["one_liner"] or "day until" in location["one_liner"]
    
    print(f"✅ One-liner: {location['one_liner']}")


def test_location_top_3_comparison():
    """DASH-M1-2 AC-3: Shows top 3 cities comparison table."""
    conn = get_db()
    location = build_location_view(conn)
    conn.close()
    
    if not location.get("empty_state"):
        assert "data_table" in location
        assert isinstance(location["data_table"], list)
        assert len(location["data_table"]) <= 3, "Should show top 3 cities max"
        
        # Check table structure
        if location["data_table"]:
            first_row = location["data_table"][0]
            assert "city" in first_row
            assert "dating_pool" in first_row
            assert "ai_jobs_mo" in first_row
            assert "cost_index" in first_row
            assert "lifestyle" in first_row
            assert "score" in first_row
            
            print(f"✅ Data table has {len(location['data_table'])} cities")
    else:
        print("✅ Empty state handled correctly")


def test_location_deadline_countdown():
    """DASH-M1-2 AC-4: Shows countdown to decision deadline (May 1, 2026)."""
    from datetime import date
    
    conn = get_db()
    location = build_location_view(conn)
    conn.close()
    
    assert "days_until_deadline" in location
    days = location["days_until_deadline"]
    
    # Validate it's a reasonable number (should be positive until May 1, 2026)
    deadline = date(2026, 5, 1)
    today = date.today()
    expected_days = (deadline - today).days
    
    assert days == expected_days, f"Expected {expected_days} days, got {days}"
    
    print(f"✅ Countdown: {days} days until May 1, 2026")


def test_location_actions():
    """DASH-M1-2 AC-5: Has action buttons."""
    conn = get_db()
    location = build_location_view(conn)
    conn.close()
    
    assert "actions" in location
    assert isinstance(location["actions"], list)
    
    if not location.get("empty_state"):
        assert len(location["actions"]) > 0, "Non-empty state should have actions"
        
        # Validate action structure
        for action in location["actions"]:
            assert "type" in action
            assert "label" in action
            assert "href" in action
        
        print(f"✅ {len(location['actions'])} action(s) available")
    else:
        print("✅ Empty state actions handled")


def test_location_mobile_responsive():
    """
    DASH-M1-2 AC-5: Mobile responsive (375px).
    This is a structural check - actual responsive behavior tested in browser.
    """
    conn = get_db()
    location = build_location_view(conn)
    conn.close()
    
    # Check that data structures are reasonable for mobile
    if location.get("data_table"):
        # Max 6 columns for mobile readability
        if location["data_table"]:
            first_row = location["data_table"][0]
            assert len(first_row) <= 6, "Table too wide for mobile (max 6 columns)"
            
    # One-liner should be < 200 chars for mobile readability
    if location.get("one_liner"):
        assert len(location["one_liner"]) < 200, "One-liner too long for mobile"
    
    print("✅ Data structures suitable for mobile")


def test_goal_tag_format():
    """Verify goal tag matches ADR-005 format."""
    conn = get_db()
    location = build_location_view(conn)
    conn.close()
    
    assert location["goal"] == "GOAL-3: Location Optionality"
    print(f"✅ Goal tag: {location['goal']}")


def test_integration_with_advisor_view():
    """Test that location section integrates with full dashboard."""
    dashboard = get_dashboard_view_model()
    
    # All three sections should exist
    assert "career" in dashboard
    assert "dating" in dashboard
    assert "location" in dashboard
    
    # Location should have correct format
    location = dashboard["location"]
    assert location.get("goal") == "GOAL-3: Location Optionality"
    
    print("✅ Location section integrated with dashboard")


if __name__ == "__main__":
    import pytest
    
    # Run all tests
    pytest.main([__file__, "-v"])
