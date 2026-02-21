"""
Skills Extractor — NLP + Pattern-based Skill Extraction from Job Descriptions

Extracts technical skills from job descriptions with context (required vs nice-to-have).
Normalizes skill names using taxonomy from config.yaml.
"""

import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class SkillMention:
    """Represents a single skill mention in a job description."""
    skill: str  # Normalized skill name
    context: str  # "required" or "nice_to_have"
    raw_text: str  # Original text fragment


class SkillsExtractor:
    def __init__(self, config: Dict):
        self.config = config
        self.skill_synonyms = config.get('skill_synonyms', {})
        self.required_patterns = config.get('required_patterns', [])
        self.nice_to_have_patterns = config.get('nice_to_have_patterns', [])
        
        # Build reverse synonym map (any variant -> canonical name)
        self.synonym_map = {}
        for canonical, variants in self.skill_synonyms.items():
            for variant in variants:
                self.synonym_map[variant.lower()] = canonical
        
        # Common tech skills to look for (beyond synonyms)
        self.known_skills = set(self.skill_synonyms.keys())
    
    def extract(self, job_description: str, tech_stack: List[str] = None) -> List[SkillMention]:
        """
        Extract skills from job description.
        
        Args:
            job_description: Raw job text
            tech_stack: Explicit skills from structured data
        
        Returns:
            List of SkillMention objects
        """
        mentions = []
        
        # First, extract from explicit tech_stack if provided
        if tech_stack:
            for skill in tech_stack:
                normalized = self._normalize_skill(skill)
                if normalized:
                    mentions.append(SkillMention(
                        skill=normalized,
                        context="required",  # Assume explicit tech_stack = required
                        raw_text=skill
                    ))
        
        # Then scan description text for skills
        # Split into sections (required vs nice-to-have)
        sections = self._split_by_context(job_description)
        
        for context, text in sections:
            skills = self._extract_skills_from_text(text)
            for skill, raw in skills:
                mentions.append(SkillMention(
                    skill=skill,
                    context=context,
                    raw_text=raw
                ))
        
        return mentions
    
    def _normalize_skill(self, raw_skill: str) -> str:
        """Normalize skill name using synonym map."""
        cleaned = raw_skill.strip().lower()
        
        # Check synonym map
        if cleaned in self.synonym_map:
            return self.synonym_map[cleaned]
        
        # Check if it's a known canonical skill
        for canonical in self.known_skills:
            if canonical.lower() == cleaned:
                return canonical
        
        # Return as-is if not in taxonomy (will be counted but not normalized)
        return raw_skill.strip()
    
    def _split_by_context(self, text: str) -> List[Tuple[str, str]]:
        """
        Split job description into required vs nice-to-have sections.
        
        Returns:
            List of (context, text) tuples
        """
        sections = []
        lines = text.split('\n')
        current_context = "required"  # Default
        current_chunk = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if line signals context switch
            is_required = any(pattern in line_lower for pattern in self.required_patterns)
            is_nice = any(pattern in line_lower for pattern in self.nice_to_have_patterns)
            
            if is_nice and not is_required:
                # Save previous chunk
                if current_chunk:
                    sections.append((current_context, '\n'.join(current_chunk)))
                current_context = "nice_to_have"
                current_chunk = [line]
            elif is_required and not is_nice:
                if current_chunk:
                    sections.append((current_context, '\n'.join(current_chunk)))
                current_context = "required"
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        # Save final chunk
        if current_chunk:
            sections.append((current_context, '\n'.join(current_chunk)))
        
        return sections if sections else [("required", text)]
    
    def _extract_skills_from_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract skill mentions from text using pattern matching.
        
        Returns:
            List of (normalized_skill, raw_text) tuples
        """
        skills = []
        text_lower = text.lower()
        
        # Check each known skill (case-insensitive)
        for canonical in self.known_skills:
            # Build regex pattern for this skill + its variants
            variants = self.skill_synonyms.get(canonical, [canonical])
            pattern = r'\b(' + '|'.join(re.escape(v) for v in variants) + r')\b'
            
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                skills.append((canonical, match.group(0)))
        
        # Also check synonym map for any unlisted variants
        for variant, canonical in self.synonym_map.items():
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Find the original case version
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    skills.append((canonical, match.group(0)))
        
        # Deduplicate (same skill mentioned multiple times)
        seen = set()
        unique_skills = []
        for skill, raw in skills:
            if skill not in seen:
                seen.add(skill)
                unique_skills.append((skill, raw))
        
        return unique_skills
    
    def aggregate(self, mentions: List[SkillMention]) -> Dict[str, Dict]:
        """
        Aggregate skill mentions into summary stats.
        
        Returns:
            Dict mapping skill -> {required_count, nice_count, total, required_pct}
        """
        stats = {}
        
        for mention in mentions:
            if mention.skill not in stats:
                stats[mention.skill] = {
                    'required_count': 0,
                    'nice_count': 0,
                    'total': 0
                }
            
            stats[mention.skill]['total'] += 1
            if mention.context == "required":
                stats[mention.skill]['required_count'] += 1
            else:
                stats[mention.skill]['nice_count'] += 1
        
        # Calculate required percentage
        for skill, data in stats.items():
            if data['total'] > 0:
                data['required_pct'] = data['required_count'] / data['total']
                data['nice_to_have_pct'] = data['nice_count'] / data['total']
        
        return stats
