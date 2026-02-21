"""
AI text humanizer - detect and fix LLM writing tells.
Based on APPL-SPIKE-1 research.
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class TellMatch:
    """Detected AI tell in text."""
    tell_name: str
    pattern: str
    severity: str  # Critical, High, Medium, Low
    match_text: str
    position: int
    suggestion: str = ""


class Humanizer:
    """Detect and fix AI writing tells."""
    
    # LLM artifact phrases
    AI_TELLS = {
        'delve': {
            'pattern': r'\bdelve\b',
            'severity': 'Critical',
            'suggestion': 'Use "explore", "examine", or remove entirely'
        },
        'game_changer': {
            'pattern': r'\bgame[- ]changer\b',
            'severity': 'High',
            'suggestion': 'Be specific about the impact instead'
        },
        'id_be_happy': {
            'pattern': r"I'd be happy to",
            'severity': 'High',
            'suggestion': 'Just state what you will do'
        },
        'excited_to': {
            'pattern': r'\bexcited to\b',
            'severity': 'Medium',
            'suggestion': 'Show interest through specifics, not adjectives'
        },
        'utilize': {
            'pattern': r'\butilize\b',
            'severity': 'Medium',
            'suggestion': 'Use "use"'
        },
        'leverage': {
            'pattern': r'\bleverage\b',
            'severity': 'Medium',
            'suggestion': 'Use "use" or "apply"'
        },
        'in_conclusion': {
            'pattern': r'\bin conclusion\b',
            'severity': 'Critical',
            'suggestion': 'End with action, not summary'
        },
        'moreover': {
            'pattern': r'\b(moreover|furthermore|additionally)\b',
            'severity': 'Medium',
            'suggestion': 'Vary transitions or use "Also" or start directly'
        },
        'robust': {
            'pattern': r'\brobust\b',
            'severity': 'Low',
            'suggestion': 'Be specific about what makes it strong'
        },
        'holistic': {
            'pattern': r'\bholistic\b',
            'severity': 'Medium',
            'suggestion': 'Say what you actually mean'
        },
        'cutting_edge': {
            'pattern': r'\bcutting[- ]edge\b',
            'severity': 'Medium',
            'suggestion': 'Name the specific technology'
        },
        'state_of_art': {
            'pattern': r'\bstate[- ]of[- ]the[- ]art\b',
            'severity': 'Medium',
            'suggestion': 'Be specific'
        },
        'paradigm': {
            'pattern': r'\bparadigm shift\b',
            'severity': 'High',
            'suggestion': 'Avoid buzzwords'
        },
        'circle_back': {
            'pattern': r'\b(circle back|touch base)\b',
            'severity': 'Medium',
            'suggestion': 'Use "follow up" or "discuss"'
        },
        'deep_dive': {
            'pattern': r'\bdeep dive\b',
            'severity': 'Medium',
            'suggestion': 'Use "analysis" or "investigation"'
        },
        'low_hanging': {
            'pattern': r'\blow[- ]hanging fruit\b',
            'severity': 'Medium',
            'suggestion': 'Be specific about the easy wins'
        },
        'synergy': {
            'pattern': r'\bsynergy\b',
            'severity': 'Low',
            'suggestion': 'Say what you mean concretely'
        },
    }
    
    # Jurek-specific violations
    JUREK_VIOLATIONS = {
        'em_dash': {
            'pattern': r'—',
            'severity': 'Critical',
            'suggestion': 'Jurek NEVER uses em dashes. Remove or rephrase.'
        },
        'no_contractions': {
            'pattern': r"\b(do not|cannot|will not|is not|are not|would not|should not|could not)\b",
            'severity': 'Medium',
            'suggestion': "Use contractions: don't, can't, won't, isn't, aren't, wouldn't, shouldn't, couldn't"
        },
        'apologetic': {
            'pattern': r"\b(sorry|apologies|unfortunately)\b",
            'severity': 'High',
            'suggestion': 'Jurek is direct, not apologetic. Remove.'
        },
        'hedging': {
            'pattern': r"\b(perhaps|possibly|potentially|might|maybe)\b",
            'severity': 'Low',
            'suggestion': 'Jurek is decisive. Use direct statements.'
        },
    }
    
    def __init__(self):
        self.patterns = {**self.AI_TELLS, **self.JUREK_VIOLATIONS}
    
    def scan(self, text: str) -> List[TellMatch]:
        """
        Scan text for AI tells.
        
        Returns:
            List of TellMatch objects with detected issues
        """
        matches = []
        text_lower = text.lower()
        
        for tell_name, config in self.patterns.items():
            pattern = config['pattern']
            for match in re.finditer(pattern, text_lower):
                matches.append(TellMatch(
                    tell_name=tell_name,
                    pattern=pattern,
                    severity=config['severity'],
                    match_text=match.group(),
                    position=match.start(),
                    suggestion=config.get('suggestion', ''),
                ))
        
        # Sort by position
        matches.sort(key=lambda m: m.position)
        return matches
    
    def score(self, text: str) -> Dict[str, any]:
        """
        Score text for AI-likeness.
        
        Returns:
            Dict with score (0-100, higher = more AI-like) and breakdown
        """
        matches = self.scan(text)
        
        # Severity weights
        severity_weights = {
            'Critical': 20,
            'High': 10,
            'Medium': 5,
            'Low': 2,
        }
        
        # Calculate weighted score
        total_score = sum(severity_weights.get(m.severity, 0) for m in matches)
        
        # Normalize to 0-100 (cap at 100)
        normalized_score = min(100, total_score)
        
        # Breakdown by severity
        breakdown = {
            'critical': sum(1 for m in matches if m.severity == 'Critical'),
            'high': sum(1 for m in matches if m.severity == 'High'),
            'medium': sum(1 for m in matches if m.severity == 'Medium'),
            'low': sum(1 for m in matches if m.severity == 'Low'),
        }
        
        return {
            'score': normalized_score,
            'matches': len(matches),
            'breakdown': breakdown,
            'is_likely_ai': normalized_score > 20,  # Threshold: 20+ = likely AI
        }
    
    def fix_common(self, text: str) -> str:
        """
        Auto-fix common tells where replacement is straightforward.
        
        Returns:
            Text with automatic fixes applied
        """
        # Simple replacements
        replacements = {
            r'\butilize\b': 'use',
            r'\bleverage\b': 'use',
            r'—': '-',  # Replace em dash with hyphen
            r'\bdo not\b': "don't",
            r'\bcannot\b': "can't",
            r'\bwill not\b': "won't",
            r'\bis not\b': "isn't",
            r'\bare not\b': "aren't",
            r'\bwould not\b': "wouldn't",
            r'\bshould not\b': "shouldn't",
            r'\bcould not\b': "couldn't",
        }
        
        fixed = text
        for pattern, replacement in replacements.items():
            fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
        
        return fixed
    
    def generate_report(self, text: str) -> str:
        """
        Generate human-readable report of AI tells found.
        
        Returns:
            Formatted report string
        """
        matches = self.scan(text)
        score_data = self.score(text)
        
        lines = []
        lines.append("=" * 60)
        lines.append("AI HUMANIZER REPORT")
        lines.append("=" * 60)
        lines.append(f"Score: {score_data['score']}/100 (higher = more AI-like)")
        lines.append(f"Verdict: {'⚠️ LIKELY AI' if score_data['is_likely_ai'] else '✅ Likely human'}")
        lines.append(f"Total tells found: {len(matches)}")
        lines.append("")
        
        breakdown = score_data['breakdown']
        lines.append("Breakdown by severity:")
        lines.append(f"  Critical: {breakdown['critical']}")
        lines.append(f"  High: {breakdown['high']}")
        lines.append(f"  Medium: {breakdown['medium']}")
        lines.append(f"  Low: {breakdown['low']}")
        lines.append("")
        
        if matches:
            lines.append("Detected tells:")
            for i, match in enumerate(matches, 1):
                lines.append(f"{i}. [{match.severity}] {match.tell_name}")
                lines.append(f"   Found: \"{match.match_text}\" at position {match.position}")
                if match.suggestion:
                    lines.append(f"   Fix: {match.suggestion}")
                lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Quick API
def is_likely_ai(text: str, threshold: int = 20) -> bool:
    """Quick check if text is likely AI-generated."""
    h = Humanizer()
    score_data = h.score(text)
    return score_data['score'] > threshold


def humanize(text: str) -> str:
    """Apply automatic fixes to make text more human."""
    h = Humanizer()
    return h.fix_common(text)
