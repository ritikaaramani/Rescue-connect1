"""
geo_pipeline.py - Main Geolocation Inference Pipeline

Orchestrates location inference by combining:
- Text extraction (caption + OCR)
- Image scene analysis
- Geocoding
- Confidence scoring
"""

import os
from typing import Dict, Any, Optional, List

from .extractor import extract_locations
from .geocoder import geocode_best, GEOPY_AVAILABLE
from .scorer import score_location_result, AMBIGUITY_THRESHOLD
from .scene_model import analyze_image, SCENE_LOCATION_HINTS


def resolve_location(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve the most likely location for a disaster-related post.
    
    Args:
        post: Dict containing:
            - post_id: Unique identifier
            - caption: Caption text (may be None)
            - ocr_text: OCR extracted text (may be None)
            - extracted_locations: List of locations (optional)
            - gps: Dict with 'lat' and 'lon' keys (may be None)
            - image_path: Path to image for visual context analysis
            - disaster_type: Type of disaster (optional)
            
    Returns:
        Dict with:
            - post_id: Same as input
            - location: Display name of resolved location
            - latitude: Latitude coordinate
            - longitude: Longitude coordinate
            - confidence: Confidence score (0-1)
            - is_ambiguous: Whether location is ambiguous
            - method: Description of methods used
            - scene_analysis: Visual context from image
    """
    post_id = post.get("post_id", "unknown")
    caption = post.get("caption")
    ocr_text = post.get("ocr_text")
    gps = post.get("gps")
    image_path = post.get("image_path")
    
    # Get pre-extracted locations if available
    extracted_locations = post.get("extracted_locations", [])
    
    # Initialize result
    result = {
        "post_id": post_id,
        "location": None,
        "latitude": None,
        "longitude": None,
        "confidence": 0.0,
        "is_ambiguous": True,
        "method": "none",
        "scene_analysis": None
    }
    
    geocode_result = None
    scene_result = None
    image_boost = 0.0
    
    # Step 1: Analyze image for visual context (if provided)
    if image_path and os.path.exists(image_path):
        scene_result = analyze_image(image_path)
        result["scene_analysis"] = scene_result
    
    # Step 2: Handle GPS if present
    if gps and gps.get("lat") is not None and gps.get("lon") is not None:
        result["latitude"] = gps["lat"]
        result["longitude"] = gps["lon"]
        result["location"] = f"GPS: ({gps['lat']:.4f}, {gps['lon']:.4f})"
        
        # Still extract text locations to enhance display name
        if caption or ocr_text:
            extracted = extract_locations(caption, ocr_text)
            if extracted and GEOPY_AVAILABLE:
                geocode_result = geocode_best(extracted)
                if geocode_result:
                    result["location"] = geocode_result["display_name"]
        
        geocode_result = {"verified": True}
    
    # Step 3: No GPS - rely on text extraction
    else:
        if extracted_locations:
            extracted = list(extracted_locations)
        else:
            extracted = extract_locations(caption, ocr_text)
            
        # Add provided location hints (from image analysis)
        location_hints = post.get("location_hints", [])
        if location_hints:
            for hint in location_hints:
                if hint and hint not in extracted:
                    extracted.append(hint)
        
        if extracted:
            # Add scene-based location hints (if local analysis run)
            if scene_result and scene_result.get("location_hints"):
                hints = scene_result["location_hints"]
                for loc in extracted[:]:
                    for hint in hints:
                        enhanced = f"{loc} {hint}"
                        if enhanced not in extracted:
                            extracted.append(enhanced)
            
            # Sort extracted locations by length (descending) to prioritize specific names
            # e.g. "Kempegowda International Airport" > "International Airport"
            extracted.sort(key=len, reverse=True)
            
            # Generate context-aware queries
            # Combine specific locations with other extracted entities (e.g. cities) to resolve ambiguity
            # e.g. "Hindustan Aeronautics Limited" + "Bangalore" -> "Hindustan Aeronautics Limited, Bangalore"
            enhanced_queries = []
            for loc in extracted:
                # Add combinations with other hints first (highest priority)
                for context in extracted:
                    if context != loc and context not in loc and loc not in context:
                        # Limit length to avoid super long invalid queries
                        if len(loc) + len(context) < 100:
                            enhanced_queries.append(f"{loc}, {context}")
                
                # Add the original location (fallback)
                enhanced_queries.append(loc)
            
            # Remove duplicates while preserving order
            final_queries = list(dict.fromkeys(enhanced_queries))
            
            # Try to geocode
            geocode_result = geocode_best(final_queries)
            
            if geocode_result:
                result["latitude"] = geocode_result["latitude"]
                result["longitude"] = geocode_result["longitude"]
                result["location"] = geocode_result["display_name"]
                
                # Calculate image boost if scene matches location
                if scene_result:
                    scene_type = scene_result.get("scene_type", "unknown")
                    for hint in SCENE_LOCATION_HINTS.get(scene_type, []):
                        if hint.lower() in geocode_result["display_name"].lower():
                            image_boost = 0.15
                            break
    
    # Check for conflicts and granularity
    conflict_detected = False
    granularity = "poi"
    
    # 1. Conflict Detection (GPS vs Geocode)
    # Using simple Haversine approx or geopy if imported
    if gps and geocode_result:
        from geopy.distance import geodesic
        gps_pt = (gps["lat"], gps["lon"])
        geo_pt = (geocode_result["latitude"], geocode_result["longitude"])
        distance = geodesic(gps_pt, geo_pt).km
        if distance > 50: # 50km threshold
            conflict_detected = True
            
    # 2. Extract Granularity
    if geocode_result:
        granularity = geocode_result.get("granularity", "poi")
        
    # 3. Check for Scene Only
    # Logic: If no text evidence (Caption, OCR, OR Hints), but we have a location => likely Scene inference.
    is_scene_only = False
    
    # Check if we have ANY text-based evidence
    location_hints = post.get("location_hints", [])
    has_visual_text = bool(location_hints and len(location_hints) > 0)
    has_text = bool(caption or ocr_text or has_visual_text)
    
    if not has_text and not gps and geocode_result:
        is_scene_only = True
        
    # Step 4: Calculate confidence score
    # Treat visual text hints as OCR equivalent for scoring
    effective_ocr = ocr_text
    if not effective_ocr and has_visual_text:
        effective_ocr = " ".join(location_hints)

    score_result = score_location_result(
        gps=gps,
        ocr_text=effective_ocr,
        caption=caption,
        geocode_result=geocode_result,
        conflict_detected=conflict_detected,
        granularity=granularity,
        is_scene_only=is_scene_only
    )
    
    # Apply image boost
    base_confidence = score_result["confidence"]
    final_confidence = min(base_confidence + image_boost, 1.0)
    
    result["confidence"] = round(final_confidence, 2)
    result["is_ambiguous"] = score_result["is_ambiguous"]
    
    # Build method string
    methods = [score_result["method"]]
    if scene_result and scene_result.get("scene_type") != "unknown":
        methods.append(f"scene:{scene_result['scene_type']}")
    if image_boost > 0:
        methods.append("image_boost")
    
    result["method"] = " + ".join(methods)
    
    return result


def process_batch(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process a batch of posts and return location results.
    
    Args:
        posts: List of post dicts
        
    Returns:
        List of location result dicts
    """
    results = []
    for post in posts:
        result = resolve_location(post)
        results.append(result)
    return results


async def resolve_location_async(
    caption: Optional[str],
    ocr_text: Optional[str],
    image_url: Optional[str] = None,
    gps: Optional[Dict[str, float]] = None,
    extracted_locations: Optional[List[str]] = None,
    location_hints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Async wrapper for location resolution.
    
    This is the main integration function for the API.
    
    Args:
        caption: Post caption text
        ocr_text: OCR extracted text
        image_url: URL of image (not currently used for scene analysis)
        gps: GPS coordinates dict
        extracted_locations: Pre-extracted locations
        location_hints: Additional location hints (e.g. from Gemini)
        
    Returns:
        Location result dict
    """
    post = {
        "post_id": "api_request",
        "caption": caption,
        "ocr_text": ocr_text,
        "gps": gps,
        "extracted_locations": extracted_locations or [],
        "location_hints": location_hints or [],
        "image_path": None  # Would need to download image for scene analysis
    }
    
    return resolve_location(post)
