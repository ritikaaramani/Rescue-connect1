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
    geocode_success: bool = True,
    conflict_detected: bool = False,
    granularity: str = "poi",  # poi, city, state, country
    is_scene_only: bool = False,
    road_mismatch: bool = False
) -> Tuple[float, str, bool]:
    """
    Calculate confidence score based on available data sources.
    """
    score = 0.0
    methods = []
    
    # 1. Base Score / Ground Truth
    if has_gps:
        if not conflict_detected:
            return 1.0, "GPS Verified", False
        else:
            score = 0.85
            methods.append("GPS (Conflict Detected)")
    else:
        # 2. Text-based Evidence
        if has_ocr:
            score += 0.8
            methods.append("OCR Landmark")
        
        if has_caption:
            score += 0.6 if not has_ocr else 0.1 # Boost if caption + OCR
            methods.append("Caption" if not has_ocr else "Text Match")

    # 3. Penalties
    if not has_gps:
        # Road Mismatch (Query="Road" vs Result="Statue/Shop")
        if road_mismatch:
            score -= 0.25
            methods.append("Type Mismatch")
            
        # Granularity penalty
        if granularity == "state":
            score -= 0.15
        elif granularity == "country":
            score -= 0.3
        
        # Geocode failure
        if not geocode_success and score > 0:
            score *= 0.5
            methods.append("(geocode failed)")

    # 4. Scene Only Block
    if is_scene_only and score == 0:
        return 0.0, "Insufficient Evidence (Scene Only)", True

    # Cap at 1.0
    score = min(score, 1.0)
    score = max(score, 0.0)
    
    # Determine ambiguity (Threshold 0.4 for Uncertainty)
    is_ambiguous = score < 0.4
    
    # Build method string
    method_str = " + ".join(dict.fromkeys(methods)) if methods else "none"
    
    return score, method_str, is_ambiguous


def score_location_result(
    gps: Optional[Dict[str, float]],
    ocr_text: Optional[str],
    caption: Optional[str],
    geocode_result: Optional[Dict[str, Any]],
    conflict_detected: bool = False,
    granularity: str = "poi",
    is_scene_only: bool = False
) -> Dict[str, Any]:
    """
    Score a complete location inference result.
    """
    has_gps = gps is not None and gps.get("lat") is not None
    has_ocr = bool(ocr_text and ocr_text.strip())
    has_caption = bool(caption and caption.strip())
    geocode_success = geocode_result is not None
    
    # Extract road mismatch from geocode result
    road_mismatch = False
    if geocode_result:
        road_mismatch = geocode_result.get("road_mismatch", False)
    
    confidence, method, is_ambiguous = calculate_confidence(
        has_gps=has_gps,
        has_ocr=has_ocr,
        has_caption=has_caption,
        geocode_success=geocode_success,
        conflict_detected=conflict_detected,
        granularity=granularity,
        is_scene_only=is_scene_only,
        road_mismatch=road_mismatch
    )
    
    return {
        "confidence": round(confidence, 2),
        "method": method,
        "is_ambiguous": is_ambiguous
    }
