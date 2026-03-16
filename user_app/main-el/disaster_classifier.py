import json
import spacy
from rapidfuzz import fuzz
from typing import List, Dict, Any, Optional

# --- Configuration ---

KEYWORDS = {
    "flood": ["flood", "inundation", "water level", "drowning", "submerged"],
    "fire": ["fire", "flames", "burning", "smoke", "wildfire","burn","burnt"],
    "earthquake": ["earthquake", "quake", "shaking", "tremor", "magnitude","shake"],
    "collapse": ["collapse", "collapsed", "crumbled", "fallen", "cave-in"],
    "explosion": ["explosion", "exploded", "blast", "bomb", "detonation"]
}

URGENCY_TERMS = [
    "urgent", "help", "sos", "trapped", "rescue", "injured", "dead",
    "dying", "emergency", "critical", "blood", "ambulance"
]

MODEL_NAME = "en_core_web_sm"

# --- Functions ---

def load_model():
    """Load the spaCy model."""
    try:
        return spacy.load(MODEL_NAME)
    except OSError:
        print(f"Error: Model '{MODEL_NAME}' not found. Please run: python -m spacy download {MODEL_NAME}")
        return None

def keyword_gate(text: str) -> bool:
    """
    Check if the text contains any disaster-related keywords
    using fuzzy matching.
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

def extract_entities(doc: spacy.tokens.Doc) -> Dict[str, List[str]]:
    """
    Extract specific entities using spaCy NER.
    - Locations: GPE, LOC
    - Numbers: CARDINAL, QUANTITY
    """
    entities = {
        "locations": [],
        "numbers": []
    }
    
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
    """
    text_lower = text.lower()
    score = 0.0
    
    for term in URGENCY_TERMS:
        if term in text_lower:
            score += 0.2
            
    return min(score, 1.0)

def process_post(text: str, nlp) -> Optional[Dict[str, Any]]:
    """
    Main processing pipeline for a single post.
    """
    # 1. Keyword Gate
    if not keyword_gate(text):
        return None

    # 2. Rule-based Classification
    labels, confidence = classify_events(text)
    
    # 3. Named Entity Recognition
    doc = nlp(text)
    entities = extract_entities(doc)
    
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

def main():
    """
    Main function to demonstrate the module.
    """
    # Initialize model
    print("Loading model...")
    nlp = load_model()
    if not nlp:
        return

    # Example inputs
    examples = [
        "Urgent! Massive fire in downtown building. We need help.",
        "Just having a coffee with friends. What a lovely day!",
        "Flash flod warning for Kerla. 50 families are trapped on the roof. SOS!",
        "The earthquake shook the entire city of Tokyo. Magnitude 5.4 detected."
    ]

    print("\n--- Processing Examples ---\n")
    
    for i, text in enumerate(examples, 1):
        print(f"Input {i}: {text}")
        result = process_post(text, nlp)
        # Using json.dumps for pretty printing the JSON output
        if result:
            with open(f"output_{i}.json", "w") as f:
                json.dump(result, f, indent=2)
            print(f"Output saved to output_{i}.json\n")
        else:
            print("Output: None (Discarded)\n")


if __name__ == "__main__":
    main()
