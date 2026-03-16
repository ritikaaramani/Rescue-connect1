"""
scorer.py - Confidence Scoring Logic

Rule-based confidence scoring for location inference.
Provides explainable scores based on available data sources.

Scoring Rules:
- GPS present: +0.5
- OCR text present: +0.3  
- Caption present: +0.2

If confidence < 0.6, location is marked as ambiguous.
"""

from typing import Dict, Any, Optional, Tuple


# Confidence thresholds
AMBIGUITY_THRESHOLD = 0.6  # Below this, location is marked ambiguous

# Score weights for each data source
WEIGHTS = {
    "gps": 0.5,
    "ocr": 0.3,
    "caption": 0.2,
}


def calculate_confidence(
    has_gps: bool,
    has_ocr: bool,
    has_caption: bool,
    geocode_success: bool = True
) -> Tuple[float, str, bool]:
    """
    Calculate confidence score based on available data sources.
    
    This uses a deterministic, rule-based approach for explainability.
    
    Args:
        has_gps: Whether GPS coordinates are available
        has_ocr: Whether OCR text was extracted
        has_caption: Whether caption text is available
        geocode_success: Whether geocoding was successful
        
    Returns:
        Tuple of (confidence_score, method_description, is_ambiguous)
    """
    score = 0.0
    methods = []
    
    # Add scores for each available source
    if has_gps:
        score += WEIGHTS["gps"]
        methods.append("GPS")
    
    if has_ocr:
        score += WEIGHTS["ocr"]
        methods.append("OCR")
    
    if has_caption:
        score += WEIGHTS["caption"]
        methods.append("caption")
    
    # If geocoding failed, reduce confidence
    if not geocode_success and score > 0:
        score *= 0.5
        methods.append("(geocode failed)")
    
    # Cap at 1.0
    score = min(score, 1.0)
    
    # Determine ambiguity
    is_ambiguous = score < AMBIGUITY_THRESHOLD
    
    # Build method string
    method_str = " + ".join(methods) if methods else "none"
    
    return score, method_str, is_ambiguous


def score_location_result(
    gps: Optional[Dict[str, float]],
    ocr_text: Optional[str],
    caption: Optional[str],
    geocode_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Score a complete location inference result.
    
    Args:
        gps: GPS coordinates dict with 'lat' and 'lon' keys
        ocr_text: Extracted OCR text
        caption: Post caption
        geocode_result: Result from geocoding
        
    Returns:
        Dict with confidence, method, is_ambiguous
    """
    has_gps = gps is not None and gps.get("lat") is not None
    has_ocr = bool(ocr_text and ocr_text.strip())
    has_caption = bool(caption and caption.strip())
    geocode_success = geocode_result is not None
    
    confidence, method, is_ambiguous = calculate_confidence(
        has_gps=has_gps,
        has_ocr=has_ocr,
        has_caption=has_caption,
        geocode_success=geocode_success
    )
    
    return {
        "confidence": round(confidence, 2),
        "method": method,
        "is_ambiguous": is_ambiguous
    }


if __name__ == "__main__":
    # Test scoring
    print("=== Confidence Scoring Test ===\n")
    
    test_cases = [
        # (gps, ocr, caption, geocode_success)
        ({"lat": 12.9, "lon": 77.6}, "Silk Board", "Flood near junction", True),
        (None, "KR Puram", "Heavy waterlogging", True),
        (None, "", "Flood in the area", True),
        (None, "", "", False),
        ({"lat": 12.9, "lon": 77.6}, "", "", True),
    ]
    
    for gps, ocr, caption, geocode_ok in test_cases:
        result = score_location_result(
            gps=gps,
            ocr_text=ocr,
            caption=caption,
            geocode_result={"lat": 0, "lon": 0} if geocode_ok else None
        )
        
        print(f"GPS: {'Yes' if gps else 'No'}, OCR: '{ocr or 'empty'}', Caption: '{caption[:20] if caption else 'empty'}'")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Method: {result['method']}")
        print(f"  Ambiguous: {result['is_ambiguous']}")
        print("-" * 50)
