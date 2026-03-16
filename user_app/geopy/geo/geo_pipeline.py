"""
geo_pipeline.py - Main Geolocation Inference Pipeline

YOUR ROLE IN THE TEAM:
You receive:
  - Caption/location text from Team Member 2 (text analysis)
  - OCR-extracted text from Team Member 3 (image text extraction)
  - The actual image (for visual context clues)

You output:
  - Precise location with coordinates and confidence

Pipeline Flow:
1. Accept manual input (caption, OCR text, image path)
2. Extract location mentions from text
3. Analyze image for scene context (bridge, road, water, etc.)
4. Geocode extracted locations
5. Boost confidence based on image-text correlation
6. Return complete result

Image input is analyzed for visual context to improve location accuracy.
"""

import json
import os
from typing import Dict, Any, Optional, List

from .extractor import extract_locations
from .geocoder import geocode_best, GEOPY_AVAILABLE
from .scorer import score_location_result, AMBIGUITY_THRESHOLD
from .scene_model import analyze_image, SCENE_LOCATION_HINTS


def resolve_location(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve the most likely location for a disaster-related post.
    
    Given a post with image, caption, OCR text, and optional GPS,
    infer the most likely location and confidence.
    
    If GPS exists, treat it as a strong candidate and verify it using 
    text and OCR when available.
    
    Args:
        post: Dict containing:
            - post_id: Unique identifier
            - caption: Caption text (may be None)
            - ocr_text: OCR extracted text from Team 3 (may be None)
            - extracted_locations: List of locations from Team 2 (optional)
            - gps: Dict with 'lat' and 'lon' keys (may be None)
            - image_path: Path to image for visual context analysis
            - disaster_type: Type of disaster from Team 2 (optional)
            
    Returns:
        Dict with:
            - post_id: Same as input
            - location: Display name of resolved location
            - latitude: Latitude coordinate
            - longitude: Longitude coordinate
            - confidence: Confidence score (0-1)
            - is_ambiguous: Whether location is ambiguous (confidence < 0.6)
            - method: Description of methods used
            - scene_analysis: Visual context from image (if provided)
    """
    post_id = post.get("post_id", "unknown")
    caption = post.get("caption")
    ocr_text = post.get("ocr_text")
    gps = post.get("gps")
    image_path = post.get("image_path")
    
    # Get pre-extracted locations from Team 2 (if available)
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
        # GPS exists - use it as primary location
        result["latitude"] = gps["lat"]
        result["longitude"] = gps["lon"]
        result["location"] = f"GPS: ({gps['lat']:.4f}, {gps['lon']:.4f})"
        
        # Still extract text locations to potentially enhance the display name
        if caption or ocr_text:
            extracted = extract_locations(caption, ocr_text)
            if extracted and GEOPY_AVAILABLE:
                geocode_result = geocode_best(extracted)
                if geocode_result:
                    # Use geocoded name but keep GPS coordinates
                    result["location"] = geocode_result["display_name"]
        
        # GPS is strong evidence
        geocode_result = {"verified": True}  # Mark as having location data
    
    # Step 3: No GPS - rely on text extraction
    else:
        # Use locations from Team 2 if available, otherwise extract from text
        if extracted_locations:
            extracted = list(extracted_locations)  # Copy list
        else:
            extracted = extract_locations(caption, ocr_text)
        
        if extracted:
            # Add scene-based location hints to search
            if scene_result and scene_result.get("location_hints"):
                # Append scene hints to help narrow down location
                hints = scene_result["location_hints"]
                for loc in extracted[:]:  # Copy to avoid modifying during iteration
                    for hint in hints:
                        enhanced = f"{loc} {hint}"
                        if enhanced not in extracted:
                            extracted.append(enhanced)
            
            # Try to geocode the extracted locations
            geocode_result = geocode_best(extracted)
            
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
    
    # Step 4: Calculate confidence score
    score_result = score_location_result(
        gps=gps,
        ocr_text=ocr_text,
        caption=caption,
        geocode_result=geocode_result
    )
    
    # Apply image boost
    base_confidence = score_result["confidence"]
    final_confidence = min(base_confidence + image_boost, 1.0)
    
    result["confidence"] = round(final_confidence, 2)
    result["is_ambiguous"] = final_confidence < AMBIGUITY_THRESHOLD
    
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


def interactive_test():
    """
    Interactive testing mode - manually input caption, OCR text, and image path.
    
    Use this until Team 2 and Team 3 modules are ready.
    """
    print("=" * 60)
    print("GEOLOCATION MODULE - INTERACTIVE TEST MODE")
    print("=" * 60)
    print()
    print("Enter data manually. Press Enter to skip optional fields.")
    print("Type 'quit' to exit.")
    print()
    
    post_counter = 1
    
    while True:
        print("-" * 60)
        print(f"POST #{post_counter}")
        print("-" * 60)
        
        # Get caption (from Team 2)
        caption = input("Caption text (from Team 2): ").strip()
        if caption.lower() == 'quit':
            break
        
        # Get OCR text (from Team 3)
        ocr_text = input("OCR extracted text (from Team 3): ").strip()
        if ocr_text.lower() == 'quit':
            break
        
        # Get image path
        image_path = input("Image path (optional): ").strip()
        if image_path.lower() == 'quit':
            break
        
        # Get GPS (optional)
        gps_input = input("GPS lat,lon (optional, e.g. 12.97,77.59): ").strip()
        gps = None
        if gps_input and ',' in gps_input:
            try:
                lat, lon = map(float, gps_input.split(','))
                gps = {"lat": lat, "lon": lon}
            except:
                print("  Invalid GPS format, ignoring.")
        
        # Build post
        post = {
            "post_id": f"manual_{post_counter}",
            "caption": caption if caption else None,
            "ocr_text": ocr_text if ocr_text else None,
            "gps": gps,
            "image_path": image_path if image_path and os.path.exists(image_path) else None
        }
        
        print()
        print("Processing...")
        
        # Resolve location
        result = resolve_location(post)
        
        # Display result
        print()
        print("=" * 40)
        print("RESULT")
        print("=" * 40)
        print(f"Location: {result['location'] or 'NOT FOUND'}")
        if result['latitude'] and result['longitude']:
            print(f"Coordinates: ({result['latitude']:.4f}, {result['longitude']:.4f})")
        print(f"Confidence: {result['confidence']}")
        print(f"Method: {result['method']}")
        
        if result['scene_analysis']:
            sa = result['scene_analysis']
            print(f"Scene Type: {sa.get('scene_type', 'N/A')}")
            print(f"Scene Confidence: {sa.get('confidence', 'N/A')}")
        
        if result['is_ambiguous']:
            print("⚠️  AMBIGUOUS (confidence < 0.6)")
        else:
            print("✅ HIGH CONFIDENCE")
        
        print()
        post_counter += 1
    
    print("\nGoodbye!")


def load_samples(filepath: str) -> List[Dict[str, Any]]:
    """Load sample posts from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_result(result: Dict[str, Any]):
    """Pretty print a single result."""
    print(f"Post ID: {result['post_id']}")
    print(f"Location: {result['location'] or 'NOT FOUND'}")
    if result['latitude'] and result['longitude']:
        print(f"Coordinates: ({result['latitude']:.4f}, {result['longitude']:.4f})")
    print(f"Confidence: {result['confidence']}")
    print(f"Method: {result['method']}")
    if result.get('scene_analysis'):
        sa = result['scene_analysis']
        print(f"Scene: {sa.get('scene_type', 'N/A')} ({sa.get('confidence', 0):.0%})")
    if result['is_ambiguous']:
        print("⚠️  AMBIGUOUS (confidence < 0.6)")
    print("-" * 60)


def main():
    """Main entry point - run pipeline on sample data or interactive mode."""
    import sys
    
    # Check for interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_test()
        return
    
    print("=" * 60)
    print("GEOLOCATION INFERENCE MODULE")
    print("=" * 60)
    print()
    print("Tip: Run with --interactive for manual testing")
    print()
    
    # Check dependencies
    from .extractor import SPACY_AVAILABLE
    from .scene_model import TORCH_AVAILABLE
    print(f"spaCy available: {SPACY_AVAILABLE}")
    print(f"geopy available: {GEOPY_AVAILABLE}")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    print()
    
    # Load sample data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(script_dir, "..", "data", "samples.json")
    
    if os.path.exists(samples_path):
        posts = load_samples(samples_path)
        print(f"Loaded {len(posts)} sample posts")
        print()
        
        # Process each post
        for post in posts:
            caption_preview = (post.get('caption', '') or '')[:40]
            ocr_preview = post.get('ocr_text', '') or ''
            print(f"Input: caption='{caption_preview}...', ocr='{ocr_preview}'")
            result = resolve_location(post)
            print_result(result)
            print()
    else:
        # Demo with inline data
        print("Sample data not found. Running inline demo...")
        print()
        
        demo_posts = [
            {
                "post_id": "demo_1",
                "caption": "Flood near Silk Board junction",
                "ocr_text": "Silk Board",
                "gps": None,
                "image_path": None
            },
            {
                "post_id": "demo_2", 
                "caption": "Water everywhere",
                "ocr_text": "",
                "gps": None,
                "image_path": None
            }
        ]
        
        for post in demo_posts:
            print(f"Input: caption='{post['caption']}', ocr='{post['ocr_text']}'")
            result = resolve_location(post)
            print_result(result)
            print()


if __name__ == "__main__":
    main()
