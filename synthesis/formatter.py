"""
SYNTH-MVP-2: One-Liner + Data Table Formatter

Shared utility for formatting recommendations in motivation-first format (ADR-005).

Every recommendation follows the structure:
1. One-liner connecting action to life goal (max 120 chars)
2. Data table showing evidence (max 5 columns, max 10 rows)
3. Action buttons (max 3)

Outputs both HTML (for dashboard) and Slack markdown (for notifications).
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class GoalReference(Enum):
    """Life goals that recommendations can reference"""
    FAMILY = "family"
    PARTNER = "partner"
    CAREER = "career"
    LOCATION = "location"
    FINANCIAL = "financial"


@dataclass
class ActionButton:
    """Action button configuration"""
    label: str
    action: str  # approve, skip, save, details, dismiss, etc.
    url: Optional[str] = None  # For links
    primary: bool = False  # Highlight as primary action


@dataclass
class Recommendation:
    """
    Motivation-first recommendation structure.
    
    Fields:
        one_liner: Sharp insight connecting action to life goal (max 120 chars)
        data_rows: Evidence table (list of dicts, max 10 rows)
        actions: Action buttons (max 3)
        goal: Which life goal this connects to
        context: Optional additional context (not shown by default)
    """
    one_liner: str
    data_rows: List[Dict[str, Any]]
    actions: List[ActionButton]
    goal: GoalReference
    context: Optional[str] = None
    
    def __post_init__(self):
        """Validate recommendation constraints"""
        if len(self.one_liner) > 120:
            raise ValueError(f"One-liner too long: {len(self.one_liner)} chars (max 120)")
        
        if len(self.data_rows) > 10:
            raise ValueError(f"Too many data rows: {len(self.data_rows)} (max 10)")
        
        if len(self.actions) > 3:
            raise ValueError(f"Too many actions: {len(self.actions)} (max 3)")
        
        # Validate column count (max 5 columns)
        if self.data_rows:
            num_cols = len(self.data_rows[0].keys())
            if num_cols > 5:
                raise ValueError(f"Too many columns: {num_cols} (max 5)")


@dataclass
class EmptyState:
    """
    Empty state when not enough data is available.
    
    Format: "After [N] more [data_type], I'll show you [insight_type]."
    Example: "After 5 more dates, I'll show you quality trends."
    """
    count_needed: int
    data_type: str  # "dates", "job applications", "weeks", etc.
    insight_type: str  # "quality trends", "best sources", "patterns", etc.
    goal: GoalReference
    
    def to_message(self) -> str:
        """Generate motivating empty state message"""
        return f"After {self.count_needed} more {self.data_type}, I'll show you {self.insight_type}."


def format_recommendation_html(rec: Recommendation) -> str:
    """
    Format recommendation as HTML for dashboard display.
    
    Args:
        rec: Recommendation object
        
    Returns:
        HTML string with semantic markup
    """
    # Header with one-liner
    html = f'<div class="recommendation" data-goal="{rec.goal.value}">\n'
    html += f'  <div class="one-liner">{rec.one_liner}</div>\n'
    
    # Data table
    if rec.data_rows:
        html += '  <table class="data-table">\n'
        
        # Header row (extract keys from first row)
        headers = list(rec.data_rows[0].keys())
        html += '    <thead>\n      <tr>\n'
        for header in headers:
            # Capitalize and format header
            formatted_header = header.replace('_', ' ').title()
            html += f'        <th>{formatted_header}</th>\n'
        html += '      </tr>\n    </thead>\n'
        
        # Data rows
        html += '    <tbody>\n'
        for row in rec.data_rows:
            html += '      <tr>\n'
            for header in headers:
                value = row.get(header, '')
                # Format numeric values
                if isinstance(value, float):
                    value = f"{value:.1f}"
                html += f'        <td>{value}</td>\n'
            html += '      </tr>\n'
        html += '    </tbody>\n'
        
        html += '  </table>\n'
    
    # Action buttons
    if rec.actions:
        html += '  <div class="actions">\n'
        for action in rec.actions:
            button_class = 'btn-primary' if action.primary else 'btn-secondary'
            if action.url:
                html += f'    <a href="{action.url}" class="btn {button_class}" data-action="{action.action}">{action.label}</a>\n'
            else:
                html += f'    <button class="btn {button_class}" data-action="{action.action}">{action.label}</button>\n'
        html += '  </div>\n'
    
    html += '</div>'
    
    return html


def format_recommendation_slack(rec: Recommendation) -> str:
    """
    Format recommendation as Slack markdown for notifications.
    
    Args:
        rec: Recommendation object
        
    Returns:
        Slack markdown string
    """
    # One-liner (bold)
    slack = f"*{rec.one_liner}*\n\n"
    
    # Data table (Slack supports limited table formatting)
    if rec.data_rows:
        headers = list(rec.data_rows[0].keys())
        
        # Format headers
        header_row = " | ".join([h.replace('_', ' ').title() for h in headers])
        slack += f"```\n{header_row}\n"
        slack += "-" * len(header_row) + "\n"
        
        # Format data rows
        for row in rec.data_rows:
            values = []
            for header in headers:
                value = row.get(header, '')
                # Format numeric values
                if isinstance(value, float):
                    value = f"{value:.1f}"
                values.append(str(value))
            slack += " | ".join(values) + "\n"
        
        slack += "```\n\n"
    
    # Action prompts (Slack doesn't have inline buttons in markdown)
    if rec.actions:
        for i, action in enumerate(rec.actions, 1):
            emoji = "▶️" if action.primary else "•"
            slack += f"{emoji} _{action.label}_"
            if action.url:
                slack += f" (<{action.url}>)"
            if i < len(rec.actions):
                slack += " | "
        slack += "\n"
    
    return slack


def format_empty_state_html(empty: EmptyState) -> str:
    """
    Format empty state as HTML.
    
    Args:
        empty: EmptyState object
        
    Returns:
        HTML string
    """
    html = f'<div class="empty-state" data-goal="{empty.goal.value}">\n'
    html += f'  <div class="empty-message">{empty.to_message()}</div>\n'
    html += '</div>'
    
    return html


def format_empty_state_slack(empty: EmptyState) -> str:
    """
    Format empty state as Slack markdown.
    
    Args:
        empty: EmptyState object
        
    Returns:
        Slack markdown string
    """
    return f"_{empty.to_message()}_"


# Convenience functions for common patterns

def format_dating_recommendation(
    one_liner: str,
    source_data: List[Dict[str, Any]],
    primary_action: str = "View details"
) -> Recommendation:
    """
    Helper for dating recommendations.
    
    Args:
        one_liner: Insight about dating patterns
        source_data: List of dicts with source performance data
        primary_action: Label for primary action button
        
    Returns:
        Recommendation object
    """
    actions = [
        ActionButton(label=primary_action, action="details", primary=True),
        ActionButton(label="Dismiss", action="dismiss")
    ]
    
    return Recommendation(
        one_liner=one_liner,
        data_rows=source_data[:10],  # Max 10 rows
        actions=actions,
        goal=GoalReference.PARTNER
    )


def format_career_recommendation(
    one_liner: str,
    job_data: List[Dict[str, Any]],
    job_id: Optional[str] = None
) -> Recommendation:
    """
    Helper for career recommendations.
    
    Args:
        one_liner: Insight about job match
        job_data: List of dicts with job scores
        job_id: Optional job ID for direct actions
        
    Returns:
        Recommendation object
    """
    actions = [
        ActionButton(label="Apply", action="approve", primary=True),
        ActionButton(label="Skip", action="skip"),
        ActionButton(label="Save", action="save")
    ]
    
    return Recommendation(
        one_liner=one_liner,
        data_rows=job_data[:10],  # Max 10 rows
        actions=actions,
        goal=GoalReference.CAREER
    )


def format_location_recommendation(
    one_liner: str,
    city_data: List[Dict[str, Any]]
) -> Recommendation:
    """
    Helper for location recommendations.
    
    Args:
        one_liner: Insight about city comparison
        city_data: List of dicts with city scores
        
    Returns:
        Recommendation object
    """
    actions = [
        ActionButton(label="Full analysis", action="details", primary=True),
        ActionButton(label="Dismiss", action="dismiss")
    ]
    
    return Recommendation(
        one_liner=one_liner,
        data_rows=city_data[:10],  # Max 10 rows
        actions=actions,
        goal=GoalReference.LOCATION
    )


# Example usage and testing helpers

def create_sample_recommendation() -> Recommendation:
    """Create a sample recommendation for testing"""
    return Recommendation(
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


def create_sample_empty_state() -> EmptyState:
    """Create a sample empty state for testing"""
    return EmptyState(
        count_needed=5,
        data_type="dates",
        insight_type="quality trends and best sources",
        goal=GoalReference.PARTNER
    )


if __name__ == "__main__":
    # Demo output
    print("=== MOTIVATION-FIRST FORMATTER DEMO ===\n")
    
    # Sample recommendation
    rec = create_sample_recommendation()
    
    print("HTML OUTPUT:")
    print(format_recommendation_html(rec))
    print("\n" + "="*50 + "\n")
    
    print("SLACK OUTPUT:")
    print(format_recommendation_slack(rec))
    print("\n" + "="*50 + "\n")
    
    # Sample empty state
    empty = create_sample_empty_state()
    
    print("EMPTY STATE HTML:")
    print(format_empty_state_html(empty))
    print("\n" + "="*50 + "\n")
    
    print("EMPTY STATE SLACK:")
    print(format_empty_state_slack(empty))
