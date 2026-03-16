"""
disaster_classifier.py - Text Classification for Disaster Posts

Adapted from main-el/disaster_classifier.py for integration with ml_backend.
Provides text analysis, keyword matching, entity extraction, and urgency scoring.
"""

import json
import spacy
from rapidfuzz import fuzz
from typing import List, Dict, Any, Optional

# --- Configuration ---

KEYWORDS = {
    "flood": ["flood", "inundation", "water level", "drowning", "submerged"],
    "fire": ["fire", "flames", "burning", "smoke", "wildfire", "burn", "burnt"],
    "earthquake": ["earthquake", "quake", "shaking", "tremor", "magnitude", "shake"],
    "collapse": ["collapse", "collapsed", "crumbled", "fallen", "cave-in"],
    "explosion": ["explosion", "exploded", "blast", "bomb", "detonation"]
}

URGENCY_TERMS = [
    "urgent", "help", "sos", "trapped", "rescue", "injured", "dead",
    "dying", "emergency", "critical", "blood", "ambulance"
]

MODEL_NAME = "en_core_web_sm"

# --- Lazy Model Loading ---
_nlp = None


def get_nlp():
    """Lazy load the spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(MODEL_NAME)
        except OSError:
            print(f"Warning: spaCy model '{MODEL_NAME}' not found. Run: python -m spacy download {MODEL_NAME}")
            _nlp = False  # Mark as unavailable
    return _nlp if _nlp else None


# --- Core Functions ---

def keyword_gate(text: str) -> bool:
    """
    Check if the text contains any disaster-related keywords
    using fuzzy matching.
    
    Args:
        text: Input text to check
        
    Returns:
        True if text contains disaster-related keywords
    """
    text_lower = text.lower()
    for category, words in KEYWORDS.items():
        for word in words:
            if fuzz.partial_ratio(word, text_lower) >= 80:
                return True
    return False


def classify_events(text: str) -> tuple[List[str], float]:
    """
    Classify text into disaster categories using fuzzy keyword matching.
    
    Args:
        text: Input text to classify
        
    Returns:
        Tuple of (matched_labels, confidence_score)
    """
    text_lower = text.lower()
    matched_labels = []
    total_hits = 0

    for category, words in KEYWORDS.items():
        hits_in_category = 0
        for word in words:
            if fuzz.partial_ratio(word, text_lower) >= 80:
                hits_in_category += 1

        if hits_in_category > 0:
            matched_labels.append(category)
            total_hits += hits_in_category

    if not matched_labels:
        return [], 0.0

    confidence = 0.5 + (0.1 * (total_hits - 1))
    return matched_labels, min(confidence, 1.0)


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract specific entities using spaCy NER.
    - Locations: GPE, LOC
    - Numbers: CARDINAL, QUANTITY
    
    Args:
        text: Input text to extract entities from
        
    Returns:
        Dict with 'locations' and 'numbers' lists
    """
    nlp = get_nlp()
    entities = {
        "locations": [],
        "numbers": []
    }
    
    if nlp is None:
        return entities
    
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            entities["locations"].append(ent.text)
        elif ent.label_ in ["CARDINAL", "QUANTITY"]:
            entities["numbers"].append(ent.text)
            
    return entities


def calculate_urgency(text: str) -> float:
    """
    Calculate urgency score based on presence of urgency words.
    Score: 0.2 per word, capped at 1.0.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Urgency score from 0.0 to 1.0
    """
    text_lower = text.lower()
    score = 0.0
    
    for term in URGENCY_TERMS:
        if term in text_lower:
            score += 0.2
            
    return min(score, 1.0)


def process_post(text: str) -> Optional[Dict[str, Any]]:
    """
    Main processing pipeline for a single post's text.
    
    Args:
        text: The text content to analyze (caption, OCR text, etc.)
        
    Returns:
        Dict with analysis results, or None if not disaster-related
    """
    if not text or not text.strip():
        return None
        
    # 1. Keyword Gate
    if not keyword_gate(text):
        return None

    # 2. Rule-based Classification
    labels, confidence = classify_events(text)
    
    # 3. Named Entity Recognition
    entities = extract_entities(text)
    
    # 4. Urgency Scoring
    urgency = calculate_urgency(text)
    
    # 5. Final Output Construction
    output = {
        "text_labels": labels,
        "text_confidence": confidence,
        "entities": entities,
        "urgency_score": urgency,
        "text_model_version": "rule-spacy-v1"
    }
    
    return output


def analyze_text(caption: Optional[str], ocr_text: Optional[str]) -> Dict[str, Any]:
    """
    Analyze combined caption and OCR text for disaster indicators.
    
    This is the main integration function called by the API.
    
    Args:
        caption: Post caption text
        ocr_text: OCR extracted text from image
        
    Returns:
        Dict with combined analysis results
    """
    # Combine texts
    texts = []
    if caption:
        texts.append(caption)
    if ocr_text:
        texts.append(ocr_text)
    
    combined_text = " ".join(texts)
    
    if not combined_text.strip():
        return {
            "text_labels": [],
            "text_confidence": 0.0,
            "entities": {"locations": [], "numbers": []},
            "urgency_score": 0.0,
            "is_disaster_text": False,
            "text_model_version": "rule-spacy-v1"
        }
    
    result = process_post(combined_text)
    
    if result:
        result["is_disaster_text"] = True
        return result
    else:
        return {
            "text_labels": [],
            "text_confidence": 0.0,
            "entities": extract_entities(combined_text),  # Still extract entities
            "urgency_score": 0.0,
            "is_disaster_text": False,
            "text_model_version": "rule-spacy-v1"
        }
