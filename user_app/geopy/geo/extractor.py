"""
extractor.py - Location Extraction from Text

Extracts location mentions (strings) from caption and OCR text for geocoding.
Uses spaCy NER with fallback to regex patterns for common location formats.
"""

import re
from typing import List, Optional

# Try to import spacy, with graceful fallback
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        # Model not downloaded
        nlp = None
        SPACY_AVAILABLE = False
except ImportError:
    nlp = None
    SPACY_AVAILABLE = False


# Common Indian location patterns (regex fallback)
LOCATION_PATTERNS = [
    # Junction/signal patterns
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Junction|Signal|Circle|Square|Chowk|Nagar|Puram|Halli|Bagh|Garden|Park|Lake|Road|Street|Avenue|Lane|Bridge|Underpass|Flyover|Metro|Station|Bus Stand|Railway))\b',
    # Area names with common suffixes
    r'\b([A-Z][a-z]+(?:nagar|puram|halli|pete|pura|abad|kot|pur|ganj|wadi|guda|pet))\b',
    # Capitalized multi-word phrases (potential place names)
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b',
]


def extract_locations_spacy(text: str) -> List[str]:
    """
    Extract location entities using spaCy NER.
    
    Args:
        text: Input text to extract locations from
        
    Returns:
        List of extracted location mentions
    """
    if not SPACY_AVAILABLE or nlp is None:
        return []
    
    doc = nlp(text)
    locations = []
    
    for ent in doc.ents:
        # GPE = Countries, cities, states
        # LOC = Non-GPE locations, mountain ranges, bodies of water
        # FAC = Buildings, airports, highways, bridges
        if ent.label_ in ("GPE", "LOC", "FAC"):
            locations.append(ent.text.strip())
    
    return locations


def extract_locations_regex(text: str) -> List[str]:
    """
    Extract location mentions using regex patterns.
    Fallback when spaCy is not available or misses locations.
    
    Args:
        text: Input text to extract locations from
        
    Returns:
        List of extracted location mentions
    """
    locations = []
    
    for pattern in LOCATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            cleaned = match.strip()
            if cleaned and len(cleaned) > 2:
                locations.append(cleaned)
    
    return locations


def extract_locations(caption: Optional[str], ocr_text: Optional[str]) -> List[str]:
    """
    Extract location mentions from caption and OCR text.
    
    Combines both text sources and uses spaCy NER with regex fallback.
    Returns extracted location mentions (strings) for geocoding.
    
    Args:
        caption: Post caption text (may be None)
        ocr_text: OCR extracted text from image (may be None)
        
    Returns:
        List of unique location mentions, deduplicated
    """
    # Combine text sources
    texts = []
    if caption:
        texts.append(caption)
    if ocr_text:
        texts.append(ocr_text)
    
    combined_text = " ".join(texts)
    
    if not combined_text.strip():
        return []
    
    # Extract using both methods
    locations = []
    
    # Primary: spaCy NER
    spacy_locations = extract_locations_spacy(combined_text)
    locations.extend(spacy_locations)
    
    # Secondary: Regex patterns
    regex_locations = extract_locations_regex(combined_text)
    locations.extend(regex_locations)
    
    # Also add raw OCR text if it looks like a place name
    if ocr_text and ocr_text.strip():
        # OCR text is often a signboard with location name
        locations.append(ocr_text.strip())
    
    # Deduplicate while preserving order
    seen = set()
    unique_locations = []
    for loc in locations:
        loc_lower = loc.lower()
        if loc_lower not in seen:
            seen.add(loc_lower)
            unique_locations.append(loc)
    
    return unique_locations


if __name__ == "__main__":
    # Test extraction
    test_cases = [
        ("Flood near Silk Board junction", "Silk Board"),
        ("Heavy waterlogging reported", "KR Puram Underpass"),
        ("People stranded near Marathahalli bridge", "Marathahalli"),
        ("Water everywhere", ""),
    ]
    
    print("=== Location Extraction Test ===\n")
    print(f"spaCy available: {SPACY_AVAILABLE}\n")
    
    for caption, ocr in test_cases:
        locations = extract_locations(caption, ocr)
        print(f"Caption: {caption}")
        print(f"OCR: {ocr or '(empty)'}")
        print(f"Extracted: {locations}")
        print("-" * 40)
