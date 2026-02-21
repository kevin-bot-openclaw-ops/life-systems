"""
Test harness for humanizer with AI and human text samples.
Target: >= 80% accuracy (16/20 correct classifications).
"""
import pytest
from humanizer import Humanizer, is_likely_ai


# Test Set A: AI-Generated Texts (should score high, be flagged as AI)
AI_TEXTS = [
    # 1. Vanilla GPT-4 cover letter
    """
    I'd be happy to discuss how my extensive experience in machine learning can 
    leverage cutting-edge technologies to deliver robust solutions. Furthermore, 
    I am excited to delve into the challenges of this role and utilize my skills 
    to create synergy between teams. In conclusion, I believe this is a game-changer 
    for my career.
    """,
    
    # 2. Claude cover letter
    """
    I am writing to express my excitement to join your innovative team. My holistic 
    approach to problem-solving, combined with state-of-the-art technical skills, 
    makes me an ideal candidate. Additionally, I have a proven track record of 
    delivering robust, cutting-edge solutions. I'd be happy to discuss this further.
    """,
    
    # 3. GPT-4 with "write casually"
    """
    Hey! I'd be happy to chat about this role. I've got cutting-edge experience 
    with AI and ML, and I'm excited to leverage my skills. Moreover, I think we 
    could create some real synergy here. Let's circle back and touch base soon!
    """,
    
    # 4. Corporate jargon heavy
    """
    My paradigm shift approach to deep dive analysis will leverage low-hanging fruit 
    opportunities. Furthermore, my holistic methodology ensures robust, state-of-the-art 
    deliverables. I'd be happy to utilize my cutting-edge skills to create synergy.
    """,
    
    # 5. Transition word spam
    """
    I have 10 years of experience. Moreover, I have worked with Python. Additionally, 
    I know machine learning. Furthermore, I am excited to join your team. In conclusion, 
    I believe I am a great fit.
    """,
    
    # 6. Em dash heavy (GPT-4 style)
    """
    I've built production systems — including ML pipelines — that scale to millions 
    of users. My approach — combining engineering rigor with creative problem-solving — 
    has delivered cutting-edge results. I'd be happy to discuss how I can leverage 
    these skills for your team.
    """,
    
    # 7. Formal, no contractions
    """
    I am writing to apply for this position. I do not have experience with this 
    specific framework, but I cannot imagine a better opportunity. I will not 
    disappoint if given the chance. I am excited to utilize my skills.
    """,
    
    # 8. Buzzword bingo
    """
    Excited to leverage my cutting-edge AI expertise to deliver robust, holistic 
    solutions. I'd be happy to delve into paradigm shift opportunities and create 
    synergy through state-of-the-art innovation. This is a game-changer!
    """,
    
    # 9. Apologetic + hedging
    """
    I am sorry if this is too forward, but I would perhaps be interested in this 
    role. Unfortunately, I might not have all the required skills, but I could 
    possibly learn. Maybe we could touch base to discuss this further?
    """,
    
    # 10. LinkedIn-style AI post
    """
    Excited to share my journey into AI! Leveraging cutting-edge technologies 
    has been a game-changer. Moreover, my holistic approach ensures robust 
    results. I'd be happy to delve deeper into this paradigm shift. 
    Let's circle back and create synergy!
    """,
]

# Test Set B: Human-Written Texts (should score low, NOT flagged as AI)
HUMAN_TEXTS = [
    # 1. Actual tech professional (HN style)
    """
    I built the RAG pipeline at my last startup. Turns out chunking strategy 
    matters way more than model choice. We tried FAISS, ended up with Pinecone 
    because ops complexity wasn't worth it. Happy to walk through the architecture.
    """,
    
    # 2. Casual engineer message
    """
    Hey, saw your post. I've done similar work with LLMs - mostly fine-tuning 
    for code generation. The eval setup is tricky. Want to compare notes?
    """,
    
    # 3. Direct, confident professional
    """
    I can start Monday. My last project was building ML infrastructure for fraud 
    detection - 50ms p99 latency, handling 10k req/sec. Code's on GitHub if you 
    want to see specifics.
    """,
    
    # 4. Reddit /r/MachineLearning comment
    """
    Tried this approach last month. Embedding drift killed us in production. 
    Ended up monitoring cosine similarity distributions and retraining weekly. 
    Not elegant but it worked.
    """,
    
    # 5. Short, direct application
    """
    Background: 8 years backend eng, 2 years ML. Recent work: RAG system for 
    customer support (99% answer quality, scaled to 500k users). Available now. 
    References on request.
    """,
    
    # 6. GitHub PR description
    """
    Refactored the inference pipeline to batch requests. Reduced avg latency 
    from 800ms to 120ms. Added monitoring for model drift. Tests pass, ready 
    for review.
    """,
    
    # 7. Slack message (casual tech)
    """
    The model's overfitting on that edge case. I think we need more neg examples 
    in the training set. Want to pair on it tomorrow? I've got time after standup.
    """,
    
    # 8. Email from colleague (professional but human)
    """
    Quick update: deployed the new scoring model to staging. Precision is up 
    15%, recall down 3%. Worth the trade-off? Let me know if you want to review 
    the confusion matrix before we ship.
    """,
    
    # 9. Blog post excerpt (technical but conversational)
    """
    Vector databases aren't magic. They're just ANN search with a REST API. 
    If you've got < 1M vectors, PostgreSQL with pgvector will outperform most 
    "AI databases" and cost way less. Don't believe the hype.
    """,
    
    # 10. Cover letter (human-written, direct)
    """
    I'm applying because I want to work on production ML systems. My last role 
    was building fraud detection at a fintech - dealt with class imbalance, 
    concept drift, and 99.9% uptime requirements. That's the kind of work I 
    want more of. Available to start in 2 weeks.
    """,
]


class TestHumanizer:
    """Test suite for humanizer pattern matching."""
    
    def test_ai_text_detection(self):
        """Test that AI texts are correctly flagged."""
        h = Humanizer()
        results = []
        
        for i, text in enumerate(AI_TEXTS, 1):
            score_data = h.score(text)
            is_ai = score_data['is_likely_ai']
            results.append((i, is_ai, score_data['score']))
            
        # Calculate accuracy
        correct = sum(1 for _, is_ai, _ in results if is_ai)
        accuracy = correct / len(AI_TEXTS) * 100
        
        print(f"\nAI Text Detection:")
        for i, is_ai, score in results:
            status = "✅" if is_ai else "❌"
            print(f"  {status} Sample {i}: {score}/100 - {'AI' if is_ai else 'HUMAN'}")
        print(f"  Accuracy: {correct}/{len(AI_TEXTS)} ({accuracy:.0f}%)")
        
        # Target: >= 80% (8/10)
        assert accuracy >= 80, f"AI detection accuracy {accuracy}% < 80%"
    
    def test_human_text_detection(self):
        """Test that human texts are NOT flagged as AI."""
        h = Humanizer()
        results = []
        
        for i, text in enumerate(HUMAN_TEXTS, 1):
            score_data = h.score(text)
            is_ai = score_data['is_likely_ai']
            results.append((i, not is_ai, score_data['score']))  # NOT is_ai = correct
            
        # Calculate accuracy
        correct = sum(1 for _, correct_classification, _ in results if correct_classification)
        accuracy = correct / len(HUMAN_TEXTS) * 100
        
        print(f"\nHuman Text Detection:")
        for i, correct_class, score in results:
            status = "✅" if correct_class else "❌"
            actual = "HUMAN" if not is_likely_ai(HUMAN_TEXTS[i-1]) else "AI"
            print(f"  {status} Sample {i}: {score}/100 - {actual}")
        print(f"  Accuracy: {correct}/{len(HUMAN_TEXTS)} ({accuracy:.0f}%)")
        
        # Target: >= 80% (8/10)
        assert accuracy >= 80, f"Human detection accuracy {accuracy}% < 80%"
    
    def test_overall_accuracy(self):
        """Test overall classification accuracy (16/20 minimum)."""
        h = Humanizer()
        
        # Test AI texts
        ai_correct = sum(1 for text in AI_TEXTS if h.score(text)['is_likely_ai'])
        
        # Test human texts  
        human_correct = sum(1 for text in HUMAN_TEXTS if not h.score(text)['is_likely_ai'])
        
        total_correct = ai_correct + human_correct
        total_samples = len(AI_TEXTS) + len(HUMAN_TEXTS)
        accuracy = total_correct / total_samples * 100
        
        print(f"\n{'='*60}")
        print(f"OVERALL ACCURACY")
        print(f"{'='*60}")
        print(f"AI texts correctly flagged: {ai_correct}/{len(AI_TEXTS)}")
        print(f"Human texts correctly flagged: {human_correct}/{len(HUMAN_TEXTS)}")
        print(f"Total: {total_correct}/{total_samples} ({accuracy:.0f}%)")
        print(f"{'='*60}")
        
        # Target: >= 80% (16/20)
        assert total_correct >= 16, f"Overall accuracy {total_correct}/20 < 16/20"
    
    def test_em_dash_detection(self):
        """Test that em dashes are always detected (Jurek's hard rule)."""
        h = Humanizer()
        
        text_with_em_dash = "This is a test — with an em dash — in it."
        matches = h.scan(text_with_em_dash)
        
        em_dash_matches = [m for m in matches if m.tell_name == 'em_dash']
        assert len(em_dash_matches) == 2, "Should detect both em dashes"
        assert em_dash_matches[0].severity == 'Critical'
    
    def test_auto_fix_contractions(self):
        """Test auto-fix converts formal to contractions."""
        h = Humanizer()
        
        text = "I do not think we cannot fix this. It is not working."
        fixed = h.fix_common(text)
        
        assert "don't" in fixed
        assert "can't" in fixed
        assert "isn't" in fixed
        assert "do not" not in fixed
    
    def test_auto_fix_em_dash(self):
        """Test auto-fix replaces em dashes."""
        h = Humanizer()
        
        text = "This — is a test — of em dashes."
        fixed = h.fix_common(text)
        
        assert "—" not in fixed
        assert "-" in fixed


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
