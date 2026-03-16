"""
run_geo.py - Complete Test Script for Geolocation Module

Usage:
    python run_geo.py

This script lets you test the full pipeline with:
- Team 2 JSON input (text analysis with locations)
- Team 3 JSON input (OCR extracted text)
- Image file for visual context analysis

Output: Location name, coordinates, and Google Maps link
"""

import json
import os
from geo.input_adapter import combine_team_inputs
from geo.geo_pipeline import resolve_location


def get_json_input(prompt: str) -> dict:
    """Get JSON input from user."""
    print(prompt)
    print("(Paste JSON and press Enter twice when done, or type 'skip' to skip)")
    
    lines = []
    while True:
        line = input()
        if line.strip().lower() == 'skip':
            return None
        if line == '' and lines:
            break
        lines.append(line)
    
    try:
        return json.loads('\n'.join(lines))
    except json.JSONDecodeError as e:
        print(f"  Invalid JSON: {e}")
        return None


def main():
    print("=" * 70)
    print("GEOLOCATION MODULE - COMPLETE TEST")
    print("=" * 70)
    print()
    print("This will combine inputs from Team 2, Team 3, and your image analysis")
    print("to output the final location with map coordinates.")
    print()
    print("-" * 70)
    
    # Step 1: Team 2 Input
    print("\n📝 STEP 1: Team 2 Input (Text Analysis)")
    print("-" * 40)
    print("Example format:")
    print('''  {
    "text_labels": ["flood"],
    "entities": {"locations": ["Koramangala", "Bangalore"]},
    "urgency_score": 0.6
  }''')
    print()
    
    team2_data = get_json_input("Paste Team 2 JSON:")
    
    # Step 2: Team 3 Input
    print("\n📝 STEP 2: Team 3 Input (OCR Text)")
    print("-" * 40)
    print("Example format:")
    print('''  {
    "ocr_text": "Kempegowda International Airport",
    "ocr_confidence": 0.85
  }''')
    print()
    
    team3_data = get_json_input("Paste Team 3 JSON:")
    
    # Step 3: Image Path
    print("\n🖼️  STEP 3: Image Path")
    print("-" * 40)
    image_path = input("Enter image path (or press Enter to skip): ").strip()
    if image_path and not os.path.exists(image_path):
        print(f"  Warning: File not found: {image_path}")
        image_path = None
    
    # Step 4: Original Caption (optional)
    print("\n📄 STEP 4: Original Post Caption (optional)")
    print("-" * 40)
    caption = input("Enter original caption (or press Enter to skip): ").strip()
    
    # Combine inputs
    print("\n" + "=" * 70)
    print("PROCESSING...")
    print("=" * 70)
    
    post = combine_team_inputs(
        post_id="test_post",
        team2_data=team2_data,
        team3_data=team3_data,
        original_caption=caption if caption else None,
        image_path=image_path if image_path else None
    )
    
    print(f"\n📦 Combined Input:")
    print(f"   Caption: {post.get('caption', 'None')}")
    print(f"   OCR Text: {post.get('ocr_text', 'None')}")
    print(f"   Extracted Locations: {post.get('extracted_locations', [])}")
    print(f"   Image: {post.get('image_path', 'None')}")
    
    # Resolve location
    result = resolve_location(post)
    
    # Display result
    print("\n" + "=" * 70)
    print("📍 FINAL RESULT")
    print("=" * 70)
    
    if result['location']:
        print(f"\n✅ LOCATION FOUND!")
        print(f"\n   📍 Location: {result['location']}")
        
        if result['latitude'] and result['longitude']:
            lat, lon = result['latitude'], result['longitude']
            print(f"   🌐 Coordinates: {lat:.6f}, {lon:.6f}")
            print(f"\n   🗺️  Google Maps Link:")
            print(f"   https://www.google.com/maps?q={lat},{lon}")
        
        print(f"\n   📊 Confidence: {result['confidence']:.0%}")
        print(f"   📋 Method: {result['method']}")
        
        if result.get('scene_analysis'):
            sa = result['scene_analysis']
            print(f"\n   🖼️  Scene Analysis:")
            print(f"      Type: {sa.get('scene_type', 'unknown')}")
            print(f"      Confidence: {sa.get('confidence', 0):.1%}")
        
        if result['is_ambiguous']:
            print("\n   ⚠️  Note: Location is AMBIGUOUS (confidence < 60%)")
        else:
            print("\n   ✅ HIGH CONFIDENCE result")
    else:
        print("\n❌ Could not determine location")
        print("   Try providing more specific location text or OCR data")
    
    print("\n" + "=" * 70)


def quick_test(team2_json: str, team3_json: str, image_path: str = None, caption: str = None):
    """
    Quick programmatic test function.
    
    Example:
        quick_test(
            team2_json='{"entities": {"locations": ["Koramangala"]}}',
            team3_json='{"ocr_text": "5th Block"}',
            image_path="flood.jpg"
        )
    """
    team2_data = json.loads(team2_json) if team2_json else None
    team3_data = json.loads(team3_json) if team3_json else None
    
    post = combine_team_inputs(
        post_id="quick_test",
        team2_data=team2_data,
        team3_data=team3_data,
        original_caption=caption,
        image_path=image_path
    )
    
    result = resolve_location(post)
    
    if result['latitude'] and result['longitude']:
        maps_url = f"https://www.google.com/maps?q={result['latitude']},{result['longitude']}"
    else:
        maps_url = None
    
    return {
        "location": result['location'],
        "latitude": result['latitude'],
        "longitude": result['longitude'],
        "confidence": result['confidence'],
        "maps_url": maps_url,
        "scene": result.get('scene_analysis', {}).get('scene_type'),
        "method": result['method']
    }


if __name__ == "__main__":
    main()
