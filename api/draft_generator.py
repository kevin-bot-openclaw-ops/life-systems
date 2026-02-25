"""
Draft cover letter generator integration.
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic


# Initialize Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT = """You are a professional cover letter writer helping Jurek Plocha, a senior software engineer transitioning from banking systems to AI/ML roles.

Jurek's background:
- 15+ years experience in Java/banking (Credit Suisse, Deutsche Bank, GFT)
- Currently building AI/ML projects: OpenClaw (multi-agent orchestration), Tech Radar (NLP + job market analysis), RAG pipelines, fraud detection ML
- Looking for: Senior AI/ML Engineer, ML Platform Engineer, or Agent Systems Architect roles
- Salary target: €150k+
- Remote-only, EU timezone
- Location: Currently in Canary Islands

Writing style:
- Concise and direct (150-200 words)
- No fluff phrases like "I am writing to express my interest"
- Lead with the strongest hook (what makes Jurek uniquely qualified)
- Mention specific company/role details
- End with clear next step
- NO em dashes (use commas or periods)
- Sound human, not AI-generated

Your task: Write a cover letter draft for the job provided. Make it role-specific."""


VARIANT_PROMPTS = {
    "fintech": "Emphasize Jurek's banking systems experience and how it bridges to AI/ML for financial services. Highlight fraud detection ML project.",
    "ml_research": "Lead with Jurek's AI/ML projects (RAG, OpenClaw, NLP). Frame banking experience as production systems expertise.",
    "platform": "Emphasize infrastructure, deployment, monitoring. Highlight MLOps aspects of portfolio projects.",
    "general": "Balance between AI/ML skills and enterprise architecture background."
}


def generate_draft(job: Dict[str, Any], variant: Optional[str] = None) -> str:
    """
    Generate a cover letter draft using Claude API.
    
    Args:
        job: Job data dict with title, company, description, etc.
        variant: Optional variant (fintech, ml_research, platform, general)
    
    Returns:
        Draft cover letter text
    """
    if not variant or variant not in VARIANT_PROMPTS:
        variant = "general"
    
    user_prompt = f"""Job: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}

Location: {job.get('location', 'Remote')}
Description: {job.get('description', 'No description available')[:500]}

Variant: {variant}
Variant guidance: {VARIANT_PROMPTS[variant]}

Write a 150-200 word cover letter draft. Be specific to this company and role."""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )
        
        draft = response.content[0].text.strip()
        
        # Basic humanization: remove common AI tells
        draft = draft.replace(" — ", ", ")  # No em dashes
        draft = draft.replace("—", ",")
        
        # Remove common AI phrases
        ai_tells = [
            "I am writing to express my interest",
            "I am excited to apply",
            "I would be honored",
            "I would welcome the opportunity",
            "Thank you for considering my application"
        ]
        for tell in ai_tells:
            if tell in draft:
                draft = draft.replace(tell, "")
        
        return draft.strip()
        
    except Exception as e:
        # Fallback if Claude API fails
        return f"""I'm a senior engineer with 15 years in banking systems now building production AI. Recently shipped OpenClaw (multi-agent orchestration), Tech Radar (NLP job market analysis), and RAG pipelines.

Your {job.get('title', 'role')} at {job.get('company', 'your company')} matches my background: enterprise-grade reliability + modern AI/ML stack.

Available for a call this week. Portfolio: github.com/kevin-bot-openclaw-ops"""


# Fallback: simple template-based generator if no API key
def generate_draft_template(job: Dict[str, Any], variant: Optional[str] = None) -> str:
    """Template-based fallback draft generator."""
    company = job.get('company', 'your company')
    title = job.get('title', 'this role')
    
    if variant == "fintech":
        hook = f"15 years building mission-critical banking systems + recent AI/ML work = exactly what {company}'s {title} needs."
        body = "Credit Suisse, Deutsche Bank: regulatory compliance, payment systems, fraud detection. Now: RAG pipelines, ML fraud models, multi-agent orchestration (OpenClaw). Banking rigor + AI innovation."
    elif variant == "ml_research":
        hook = f"I build production AI systems. OpenClaw (multi-agent orchestration), RAG pipelines, NLP job market analysis. {company}'s {title} is the next challenge."
        body = "Recent projects: RAG with sentence-transformers + FAISS, fraud detection ML (XGBoost, AUPRC 0.87), NLP sentiment analysis. 15 years enterprise systems gives me production discipline most ML researchers lack."
    elif variant == "platform":
        hook = f"Deploying ML systems at scale requires more than model training. {company}'s {title} needs both—I have both."
        body = "MLOps pipeline: MLflow tracking, model registry, FastAPI serving, PSI drift monitoring, GitHub Actions CI/CD. Backed by 15 years running production systems in banking."
    else:
        hook = f"Senior engineer transitioning from banking systems to AI/ML. {company}'s {title} bridges both."
        body = "Background: 15yr Java/banking (Credit Suisse, Deutsche Bank). Current: OpenClaw (agents), Tech Radar (NLP), RAG pipelines, fraud detection ML. Remote, EU timezone, €150k+."
    
    return f"""{hook}

{body}

Available for a call this week.

Portfolio: github.com/kevin-bot-openclaw-ops"""
