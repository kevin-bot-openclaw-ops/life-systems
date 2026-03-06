"""
Test suite for SYNTH-MVP-2: One-Liner + Data Table Formatter

Tests all acceptance criteria:
- AC-1: Shared function format_recommendation() -> HTML + Slack markdown
- AC-2: One-liner max 120 chars, includes goal reference
- AC-3: Data table max 5 columns, max 10 rows
- AC-4: Actions max 3 buttons per recommendation
- AC-5: Works in both dashboard HTML and Slack markdown
- AC-6: Empty state template format
"""

import pytest
from synthesis.formatter import (
    Recommendation,
    ActionButton,
    EmptyState,
    GoalReference,
    format_recommendation_html,
    format_recommendation_slack,
    format_empty_state_html,
    format_empty_state_slack,
    format_dating_recommendation,
    format_career_recommendation,
    format_location_recommendation,
    create_sample_recommendation,
    create_sample_empty_state
)


class TestRecommendationValidation:
    """Test validation constraints on Recommendation objects"""
    
    def test_one_liner_length_limit(self):
        """AC-2: One-liner must be max 120 characters"""
        long_one_liner = "x" * 121
        
        with pytest.raises(ValueError, match="One-liner too long"):
            Recommendation(
                one_liner=long_one_liner,
                data_rows=[{"col": "value"}],
                actions=[ActionButton(label="Test", action="test")],
                goal=GoalReference.CAREER
            )
    
    def test_one_liner_exactly_120_chars_allowed(self):
        """Edge case: exactly 120 characters is allowed"""
        one_liner = "x" * 120
        
        rec = Recommendation(
            one_liner=one_liner,
            data_rows=[{"col": "value"}],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        
        assert len(rec.one_liner) == 120
    
    def test_max_10_data_rows(self):
        """AC-3: Data table must have max 10 rows"""
        too_many_rows = [{"col": f"value{i}"} for i in range(11)]
        
        with pytest.raises(ValueError, match="Too many data rows"):
            Recommendation(
                one_liner="Test",
                data_rows=too_many_rows,
                actions=[ActionButton(label="Test", action="test")],
                goal=GoalReference.CAREER
            )
    
    def test_exactly_10_rows_allowed(self):
        """Edge case: exactly 10 rows is allowed"""
        ten_rows = [{"col": f"value{i}"} for i in range(10)]
        
        rec = Recommendation(
            one_liner="Test",
            data_rows=ten_rows,
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        
        assert len(rec.data_rows) == 10
    
    def test_max_5_columns(self):
        """AC-3: Data table must have max 5 columns"""
        too_many_cols = {f"col{i}": f"value{i}" for i in range(6)}
        
        with pytest.raises(ValueError, match="Too many columns"):
            Recommendation(
                one_liner="Test",
                data_rows=[too_many_cols],
                actions=[ActionButton(label="Test", action="test")],
                goal=GoalReference.CAREER
            )
    
    def test_exactly_5_columns_allowed(self):
        """Edge case: exactly 5 columns is allowed"""
        five_cols = {f"col{i}": f"value{i}" for i in range(5)}
        
        rec = Recommendation(
            one_liner="Test",
            data_rows=[five_cols],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        
        assert len(rec.data_rows[0]) == 5
    
    def test_max_3_actions(self):
        """AC-4: Max 3 action buttons"""
        too_many_actions = [
            ActionButton(label=f"Action{i}", action=f"action{i}")
            for i in range(4)
        ]
        
        with pytest.raises(ValueError, match="Too many actions"):
            Recommendation(
                one_liner="Test",
                data_rows=[{"col": "value"}],
                actions=too_many_actions,
                goal=GoalReference.CAREER
            )
    
    def test_exactly_3_actions_allowed(self):
        """Edge case: exactly 3 actions is allowed"""
        three_actions = [
            ActionButton(label=f"Action{i}", action=f"action{i}")
            for i in range(3)
        ]
        
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"col": "value"}],
            actions=three_actions,
            goal=GoalReference.CAREER
        )
        
        assert len(rec.actions) == 3


class TestHTMLFormatting:
    """Test HTML output for dashboard display"""
    
    def test_html_contains_one_liner(self):
        """AC-5: HTML output includes one-liner"""
        rec = create_sample_recommendation()
        html = format_recommendation_html(rec)
        
        assert rec.one_liner in html
        assert 'class="one-liner"' in html
    
    def test_html_contains_goal_reference(self):
        """AC-2: HTML includes goal reference"""
        rec = create_sample_recommendation()
        html = format_recommendation_html(rec)
        
        assert f'data-goal="{rec.goal.value}"' in html
    
    def test_html_table_structure(self):
        """AC-5: HTML contains properly formatted table"""
        rec = create_sample_recommendation()
        html = format_recommendation_html(rec)
        
        assert '<table class="data-table">' in html
        assert '<thead>' in html
        assert '<tbody>' in html
        assert '<th>' in html
        assert '<td>' in html
    
    def test_html_table_headers(self):
        """HTML table headers are formatted correctly"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"source_name": "Test", "avg_quality": 8.5}],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        html = format_recommendation_html(rec)
        
        # Headers should be capitalized and spaces instead of underscores
        assert "<th>Source Name</th>" in html
        assert "<th>Avg Quality</th>" in html
    
    def test_html_numeric_formatting(self):
        """Numeric values are formatted to 1 decimal place"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"score": 8.567}],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        html = format_recommendation_html(rec)
        
        assert "8.6" in html
        assert "8.567" not in html
    
    def test_html_action_buttons(self):
        """AC-5: HTML contains action buttons"""
        rec = create_sample_recommendation()
        html = format_recommendation_html(rec)
        
        assert 'class="actions"' in html
        assert '<button' in html or '<a' in html
        assert 'data-action=' in html
    
    def test_html_primary_action_styling(self):
        """Primary action has distinct CSS class"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"col": "value"}],
            actions=[
                ActionButton(label="Primary", action="approve", primary=True),
                ActionButton(label="Secondary", action="skip", primary=False)
            ],
            goal=GoalReference.CAREER
        )
        html = format_recommendation_html(rec)
        
        assert 'btn-primary' in html
        assert 'btn-secondary' in html
    
    def test_html_action_with_url(self):
        """Actions with URLs render as links"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"col": "value"}],
            actions=[
                ActionButton(label="Details", action="details", url="/details/123")
            ],
            goal=GoalReference.CAREER
        )
        html = format_recommendation_html(rec)
        
        assert '<a href="/details/123"' in html
        assert 'Details</a>' in html


class TestSlackFormatting:
    """Test Slack markdown output for notifications"""
    
    def test_slack_contains_one_liner(self):
        """AC-5: Slack output includes bold one-liner"""
        rec = create_sample_recommendation()
        slack = format_recommendation_slack(rec)
        
        assert f"*{rec.one_liner}*" in slack
    
    def test_slack_table_structure(self):
        """AC-5: Slack contains code-block table"""
        rec = create_sample_recommendation()
        slack = format_recommendation_slack(rec)
        
        assert "```" in slack
        assert "|" in slack  # Column separator
        assert "-" in slack  # Header separator
    
    def test_slack_table_headers(self):
        """Slack table headers are formatted correctly"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"source_name": "Test", "avg_quality": 8.5}],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        slack = format_recommendation_slack(rec)
        
        assert "Source Name | Avg Quality" in slack
    
    def test_slack_numeric_formatting(self):
        """Numeric values formatted to 1 decimal place in Slack"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"score": 8.567}],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        slack = format_recommendation_slack(rec)
        
        assert "8.6" in slack
        assert "8.567" not in slack
    
    def test_slack_action_prompts(self):
        """AC-5: Slack includes action prompts"""
        rec = create_sample_recommendation()
        slack = format_recommendation_slack(rec)
        
        # Should include action labels
        for action in rec.actions:
            assert action.label in slack
    
    def test_slack_primary_action_emoji(self):
        """Primary actions marked with ▶️ emoji in Slack"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"col": "value"}],
            actions=[
                ActionButton(label="Primary", action="approve", primary=True),
                ActionButton(label="Secondary", action="skip", primary=False)
            ],
            goal=GoalReference.CAREER
        )
        slack = format_recommendation_slack(rec)
        
        assert "▶️" in slack  # Primary action marker
        assert "•" in slack  # Secondary action marker
    
    def test_slack_action_with_url(self):
        """Actions with URLs included as Slack links"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"col": "value"}],
            actions=[
                ActionButton(label="Details", action="details", url="https://example.com")
            ],
            goal=GoalReference.CAREER
        )
        slack = format_recommendation_slack(rec)
        
        assert "(<https://example.com>)" in slack


class TestEmptyState:
    """Test empty state formatting"""
    
    def test_empty_state_message_format(self):
        """AC-6: Empty state follows template format"""
        empty = EmptyState(
            count_needed=5,
            data_type="dates",
            insight_type="quality trends",
            goal=GoalReference.PARTNER
        )
        
        message = empty.to_message()
        
        assert message == "After 5 more dates, I'll show you quality trends."
    
    def test_empty_state_html(self):
        """AC-5: Empty state renders as HTML"""
        empty = create_sample_empty_state()
        html = format_empty_state_html(empty)
        
        assert 'class="empty-state"' in html
        assert empty.to_message() in html
        assert f'data-goal="{empty.goal.value}"' in html
    
    def test_empty_state_slack(self):
        """AC-5: Empty state renders as Slack markdown"""
        empty = create_sample_empty_state()
        slack = format_empty_state_slack(empty)
        
        # Should be italicized
        assert slack.startswith("_")
        assert slack.endswith("_")
        assert empty.to_message() in slack


class TestHelperFunctions:
    """Test domain-specific helper functions"""
    
    def test_dating_helper(self):
        """format_dating_recommendation() creates valid recommendation"""
        rec = format_dating_recommendation(
            one_liner="Test insight",
            source_data=[{"Source": "Tinder", "Quality": 7.5}]
        )
        
        assert rec.goal == GoalReference.PARTNER
        assert len(rec.actions) == 2  # View details + Dismiss
        assert rec.actions[0].primary is True
    
    def test_career_helper(self):
        """format_career_recommendation() creates valid recommendation"""
        rec = format_career_recommendation(
            one_liner="Test job",
            job_data=[{"Company": "Test", "Score": 85}]
        )
        
        assert rec.goal == GoalReference.CAREER
        assert len(rec.actions) == 3  # Apply, Skip, Save
        assert any(a.label == "Apply" for a in rec.actions)
    
    def test_location_helper(self):
        """format_location_recommendation() creates valid recommendation"""
        rec = format_location_recommendation(
            one_liner="Test city",
            city_data=[{"City": "Madrid", "Score": 8.5}]
        )
        
        assert rec.goal == GoalReference.LOCATION
        assert len(rec.actions) == 2  # Full analysis + Dismiss
    
    def test_helpers_enforce_row_limit(self):
        """Helpers enforce 10-row limit"""
        large_dataset = [{"col": f"value{i}"} for i in range(20)]
        
        rec = format_career_recommendation(
            one_liner="Test",
            job_data=large_dataset
        )
        
        assert len(rec.data_rows) == 10  # Should truncate to max


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_data_rows(self):
        """Recommendation with no data rows is valid"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        
        html = format_recommendation_html(rec)
        slack = format_recommendation_slack(rec)
        
        # Should not crash, just skip table
        assert rec.one_liner in html
        assert rec.one_liner in slack
    
    def test_no_actions(self):
        """Recommendation with no actions is valid"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[{"col": "value"}],
            actions=[],
            goal=GoalReference.CAREER
        )
        
        html = format_recommendation_html(rec)
        slack = format_recommendation_slack(rec)
        
        # Should not crash
        assert rec.one_liner in html
        assert rec.one_liner in slack
    
    def test_unicode_in_one_liner(self):
        """Unicode characters handled correctly"""
        rec = Recommendation(
            one_liner="Madrid → better life 🎯",
            data_rows=[{"City": "Madrid", "Score": 8.5}],
            actions=[ActionButton(label="Details", action="details")],
            goal=GoalReference.LOCATION
        )
        
        html = format_recommendation_html(rec)
        slack = format_recommendation_slack(rec)
        
        assert "→" in html
        assert "🎯" in html
        assert "→" in slack
        assert "🎯" in slack
    
    def test_missing_data_in_row(self):
        """Missing values in data rows handled gracefully"""
        rec = Recommendation(
            one_liner="Test",
            data_rows=[
                {"col1": "value1", "col2": "value2"},
                {"col1": "value3"}  # Missing col2
            ],
            actions=[ActionButton(label="Test", action="test")],
            goal=GoalReference.CAREER
        )
        
        html = format_recommendation_html(rec)
        # Should not crash, empty cell rendered
        assert "<td></td>" in html or "<td>None</td>" in html


class TestRealWorldExamples:
    """Test with real-world data from ADR-005 examples"""
    
    def test_dating_bachata_example(self):
        """Example from ADR-005: Dating pattern insight"""
        rec = Recommendation(
            one_liner="Thursday bachata is your best bet -- 3x more quality connections than apps.",
            data_rows=[
                {"Source": "Bachata", "Dates": 4, "Avg Quality": 7.8, "Follow-up Rate": "75%"},
                {"Source": "Tinder", "Dates": 8, "Avg Quality": 5.2, "Follow-up Rate": "25%"},
                {"Source": "Social", "Dates": 2, "Avg Quality": 8.0, "Follow-up Rate": "50%"}
            ],
            actions=[
                ActionButton(label="View details", action="details", primary=True),
                ActionButton(label="Dismiss", action="dismiss")
            ],
            goal=GoalReference.PARTNER
        )
        
        html = format_recommendation_html(rec)
        slack = format_recommendation_slack(rec)
        
        # Verify structure
        assert "bachata" in html.lower()
        assert "3x" in html or "3x" in slack
        assert "Bachata" in html
        assert "7.8" in html
    
    def test_career_job_match_example(self):
        """Example from ADR-005: Career morning brief"""
        rec = Recommendation(
            one_liner="This role could be your bridge to AI leadership -- 95% match, fully remote.",
            data_rows=[
                {"Dimension": "Role match", "Score": "9/10", "Why": "MCP + financial services"},
                {"Dimension": "Remote", "Score": "10/10", "Why": "Fully remote, no office visits"},
                {"Dimension": "Salary", "Score": "8/10", "Why": "EUR 140-160k range"},
                {"Dimension": "Tech overlap", "Score": "9/10", "Why": "Java + Python + LLM"}
            ],
            actions=[
                ActionButton(label="Apply", action="approve", primary=True),
                ActionButton(label="Skip", action="skip"),
                ActionButton(label="Save for later", action="save")
            ],
            goal=GoalReference.CAREER
        )
        
        html = format_recommendation_html(rec)
        slack = format_recommendation_slack(rec)
        
        # Verify structure
        assert "95%" in html
        assert "AI leadership" in html
        assert "9/10" in html or "9/10" in slack
        assert "MCP" in html
    
    def test_location_madrid_example(self):
        """Example from ADR-005: Location comparison"""
        rec = Recommendation(
            one_liner="Madrid doubles your dating pool and has 3x more AI jobs -- strongest candidate.",
            data_rows=[
                {"City": "Madrid", "Dating Pool": "~2,000", "AI Jobs/mo": 45, "Cost Index": 0.85, "Lifestyle": "8/10"},
                {"City": "Fuerteventura", "Dating Pool": "~200", "AI Jobs/mo": 2, "Cost Index": 0.70, "Lifestyle": "9/10"},
                {"City": "Barcelona", "Dating Pool": "~1,800", "AI Jobs/mo": 38, "Cost Index": 0.90, "Lifestyle": "8/10"}
            ],
            actions=[
                ActionButton(label="Full analysis", action="details", primary=True),
                ActionButton(label="Dismiss", action="dismiss")
            ],
            goal=GoalReference.LOCATION
        )
        
        html = format_recommendation_html(rec)
        slack = format_recommendation_slack(rec)
        
        # Verify structure
        assert "Madrid" in html
        assert "doubles" in html.lower() or "doubles" in slack.lower()
        assert "2,000" in html or "2000" in html
        assert "0.85" in html or "0.9" in html  # Formatted float


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
